from datetime import date

from sqlalchemy import Integer, and_, case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models as m
from ..schemas import NucleoIn


def edad_en_anos_desde_ci(ci: str | None) -> int | None:
    if ci is None:
        return None
    ci = str(ci).strip()
    if not ci or len(ci) < 11:
        return None
    try:
        year = int(ci[0:2])
        month = int(ci[2:4])
        day = int(ci[4:6])
    except ValueError:
        return None
    if month < 1 or month > 12 or day < 1 or day > 31:
        return None
    today = date.today()
    century = 2000 if year <= (today.year % 100) + 5 else 1900
    try:
        birth_date = date(century + year, month, day)
    except ValueError:
        return None
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _edad_ci_sql_expr():
    current_year = func.extract("year", func.current_date())
    current_year_2dig = current_year % 100
    cedula_valida = m.Persona.cedula.op("~")(r"^[0-9]{11}$")
    year_part = case(
        (cedula_valida, func.substr(m.Persona.cedula, 1, 2).cast(Integer)),
        else_=None,
    )
    month_part = case(
        (cedula_valida, func.substr(m.Persona.cedula, 3, 2).cast(Integer)),
        else_=None,
    )
    day_part = case(
        (cedula_valida, func.substr(m.Persona.cedula, 5, 2).cast(Integer)),
        else_=None,
    )
    nacimiento_ano = case(
        (year_part <= current_year_2dig + 5, 2000 + year_part),
        else_=1900 + year_part,
    )
    dia_maximo = case(
        (month_part.in_([1, 3, 5, 7, 8, 10, 12]), 31),
        (month_part.in_([4, 6, 9, 11]), 30),
        (
            month_part == 2,
            case(
                (
                    and_(
                        nacimiento_ano % 400 == 0,
                        nacimiento_ano != 0,
                    ),
                    29,
                ),
                (
                    and_(
                        nacimiento_ano % 4 == 0,
                        nacimiento_ano % 100 != 0,
                    ),
                    29,
                ),
                else_=28,
            ),
        ),
        else_=0,
    )
    fecha_nacimiento = case(
        (
            and_(
                cedula_valida,
                month_part.between(1, 12),
                day_part.between(1, dia_maximo),
            ),
            func.make_date(nacimiento_ano, month_part, day_part),
        ),
        else_=None,
    )
    return func.extract("year", func.age(func.current_date(), fecha_nacimiento)).cast(Integer)


def _conteo_personas_edad_rango(perfil_id: int | None, edad_min: int, edad_max: int):
    edad = _edad_ci_sql_expr()
    condiciones = [
        edad.is_not(None),
        edad >= edad_min,
        edad <= edad_max,
    ]
    if perfil_id is not None:
        condiciones.append(
            m.PersonaVulnerabilidad.perfil_vulnerabilidad_id == perfil_id
        )
    return func.count(
        func.distinct(
            case(
                (and_(*condiciones), m.Persona.id),
                else_=None,
            )
        )
    )


async def _validar_cedulas(db: AsyncSession, data: NucleoIn, hogar_id: int | None) -> None:
    personas_por_cedula: dict[str, list[str]] = {}
    for persona in data.personas:
        cedula = (persona.cedula or "").strip()
        nombre = persona.nombre_apellidos.strip() or "Persona sin nombre"
        if cedula:
            personas_por_cedula.setdefault(cedula, []).append(nombre)

    cedulas = list(personas_por_cedula)
    if not cedulas:
        return

    errores = []
    for cedula, nombres in personas_por_cedula.items():
        if len(nombres) > 1:
            errores.append(
                f"El carné {cedula} está repetido en este núcleo entre: {', '.join(nombres)} "
                f"(núcleo {data.codigo})."
            )

    stmt = (
        select(m.Persona.cedula, m.Persona.nombre_apellidos, m.HogarNucleo.codigo)
        .join(m.HogarNucleo, m.HogarNucleo.id == m.Persona.hogar_id)
        .where(m.Persona.cedula.in_(cedulas))
    )
    if hogar_id is not None:
        stmt = stmt.where(m.Persona.hogar_id != hogar_id)
    existentes = (await db.execute(stmt)).all()
    for cedula, nombre_existente, codigo_nucleo in existentes:
        nombres_enviados = ", ".join(personas_por_cedula[cedula])
        errores.append(
            f"El carné {cedula} de {nombres_enviados} ya está registrado para "
            f"{nombre_existente} en el núcleo {codigo_nucleo}."
        )

    if errores:
        raise ValueError("No se guardó el núcleo. " + " ".join(errores))


async def _guardar_nucleo(db: AsyncSession, data: NucleoIn, hogar: m.HogarNucleo | None = None) -> m.HogarNucleo:
    codigo_existente = await db.scalar(
        select(m.HogarNucleo.id).where(m.HogarNucleo.codigo == data.codigo)
    )
    if codigo_existente is not None and (hogar is None or codigo_existente != hogar.id):
        raise ValueError(f"Ya existe un núcleo con el código {data.codigo}.")

    await _validar_cedulas(db, data, hogar.id if hogar is not None else None)

    circunscripcion_id = data.circunscripcion_id
    codigo_circunscripcion = (data.circunscripcion_codigo or "").strip()
    if codigo_circunscripcion:
        circunscripcion = await db.scalar(select(m.Circunscripcion).where(
            m.Circunscripcion.consejo_popular_id == data.consejo_popular_id,
            m.Circunscripcion.codigo == codigo_circunscripcion,
        ))
        if circunscripcion is None:
            circunscripcion = m.Circunscripcion(
                codigo=codigo_circunscripcion,
                nombre=None,
                consejo_popular_id=data.consejo_popular_id,
            )
            db.add(circunscripcion)
            await db.flush()
        circunscripcion_id = circunscripcion.id

    bodega_id = data.bodega_id
    codigo_bodega = (data.bodega_codigo or "").strip()
    if codigo_bodega:
        try:
            codigo_bodega_numero = int(codigo_bodega)
        except ValueError as exc:
            raise ValueError("El código de bodega debe ser numérico") from exc
        bodega = await db.scalar(select(m.Bodega).where(
            m.Bodega.consejo_popular_id == data.consejo_popular_id,
            m.Bodega.codigo == codigo_bodega_numero,
        ))
        if bodega is None:
            bodega = m.Bodega(
                codigo=codigo_bodega_numero,
                nombre=None,
                consejo_popular_id=data.consejo_popular_id,
            )
            db.add(bodega)
            await db.flush()
        bodega_id = bodega.id

    if hogar is None:
        hogar = m.HogarNucleo(codigo=data.codigo)
        db.add(hogar)
    else:
        persona_ids = select(m.Persona.id).where(m.Persona.hogar_id == hogar.id)
        await db.execute(delete(m.PersonaOcupacion).where(m.PersonaOcupacion.persona_id.in_(persona_ids)))
        await db.execute(delete(m.PersonaVulnerabilidad).where(m.PersonaVulnerabilidad.persona_id.in_(persona_ids)))
        await db.execute(delete(m.Persona).where(m.Persona.hogar_id == hogar.id))
        await db.execute(delete(m.GastoHogar).where(m.GastoHogar.hogar_id == hogar.id))
        await db.execute(delete(m.DiversidadAlimentariaHogar).where(m.DiversidadAlimentariaHogar.hogar_id == hogar.id))
        await db.execute(delete(m.EstrategiaAfrontamientoHogar).where(m.EstrategiaAfrontamientoHogar.hogar_id == hogar.id))

    hogar.codigo = data.codigo
    hogar.direccion = data.direccion
    hogar.fecha_entrevista = (
        __import__("datetime").datetime.combine(data.fecha_entrevista, __import__("datetime").time.min)
        if data.fecha_entrevista else None
    )
    hogar.entrevistador_nombre = data.entrevistador_nombre
    hogar.provincia_id = data.provincia_id
    hogar.municipio_id = data.municipio_id
    hogar.consejo_popular_id = data.consejo_popular_id
    hogar.circunscripcion_id = circunscripcion_id
    hogar.bodega_id = bodega_id
    hogar.zona_residencia_id = data.zona_residencia_id
    hogar.procede_ayuda = data.procede_ayuda
    hogar.observaciones = data.observaciones
    if hogar.id is None:
        await db.flush()

    for p in data.personas:
        nombre = p.nombre_apellidos.strip()
        if not nombre:
            continue
        cedula = p.cedula.strip() if p.cedula else None
        persona = m.Persona(
            hogar_id=hogar.id,
            nombre_apellidos=nombre,
            cedula=cedula,
            color_piel_id=p.color_piel_id,
            parentesco_jefe_id=p.parentesco_id,
            sexo_id=p.sexo_id,
            nivel_escolaridad_id=p.nivel_escolaridad_id,
            vinculacion_sne_id=p.vinculacion_sne_id,
            esta_en_registro_consumidor=p.esta_en_registro_consumidor,
            fuente_ingreso_id=p.fuente_ingreso_id,
            ingreso_mensual_cup=p.ingreso_mensual_cup,
            trabaja=p.trabaja,
            motivo_no_trabaja_id=p.motivo_no_trabaja_id,
        )
        db.add(persona)
        await db.flush()

        if p.perfil_id:
            db.add(m.PersonaVulnerabilidad(
                persona_id=persona.id, perfil_vulnerabilidad_id=p.perfil_id))

        if p.trabaja:
            for index, item in enumerate(p.ocupaciones):
                ocup = m.PersonaOcupacion(
                    persona_id=persona.id,
                    es_principal=index == 0,
                    tipo_ocupacion=item.tipo_ocupacion,
                )
                setattr(ocup, f"{item.tipo_ocupacion}_id", item.ocupacion_catalogo_id)
                db.add(ocup)

    for g in data.gastos:
        if (g.monto_cup and g.monto_cup > 0) or g.orden_importancia is not None:
            db.add(m.GastoHogar(
                hogar_id=hogar.id,
                tipo_gasto_id=g.tipo_gasto_id,
                monto_cup=g.monto_cup,
                orden_importancia=g.orden_importancia,
            ))

    for d in data.diversidad:
        if (d.gusta is None and d.encontrado_en_mercado is None
                and (d.frecuencia_semanal_dias or 0) == 0):
            continue
        db.add(m.DiversidadAlimentariaHogar(
            hogar_id=hogar.id,
            grupo_alimento_id=d.grupo_alimento_id,
            gusta=d.gusta,
            encontrado_en_mercado=d.encontrado_en_mercado,
            frecuencia_semanal_dias=d.frecuencia_semanal_dias or 0,
        ))

    for e in data.estrategias:
        db.add(m.EstrategiaAfrontamientoHogar(
            hogar_id=hogar.id,
            estrategia_id=e.estrategia_id,
            aplica=e.aplica,
        ))

    await db.commit()
    await db.refresh(hogar)
    return hogar


async def crear_nucleo(db: AsyncSession, data: NucleoIn) -> m.HogarNucleo:
    return await _guardar_nucleo(db, data)


async def obtener_ultimo_codigo_nucleo(db: AsyncSession) -> str | None:
    return await db.scalar(
        select(m.HogarNucleo.codigo)
        .order_by(m.HogarNucleo.id.desc())
        .limit(1)
    )


def _consulta_listado_nucleos(
    busqueda: str | None = None,
    consejo_id: int | None = None,
    perfil_id: int | None = None,
):
    stmt = (
        select(
            m.HogarNucleo,
            m.Provincia.nombre.label("provincia"),
            m.Municipio.nombre.label("municipio"),
            m.ConsejoPopular.nombre.label("consejo"),
        )
        .join(m.Provincia, m.HogarNucleo.provincia_id == m.Provincia.id)
        .join(m.Municipio, m.HogarNucleo.municipio_id == m.Municipio.id)
        .join(m.ConsejoPopular, m.HogarNucleo.consejo_popular_id == m.ConsejoPopular.id)
        .order_by(m.HogarNucleo.id.desc())
    )
    if consejo_id is not None:
        stmt = stmt.where(m.HogarNucleo.consejo_popular_id == consejo_id)
    if perfil_id is not None:
        miembro_con_perfil = (
            select(m.PersonaVulnerabilidad.persona_id)
            .join(m.Persona, m.Persona.id == m.PersonaVulnerabilidad.persona_id)
            .where(
                m.Persona.hogar_id == m.HogarNucleo.id,
                m.PersonaVulnerabilidad.perfil_vulnerabilidad_id == perfil_id,
            )
            .exists()
        )
        stmt = stmt.where(miembro_con_perfil)
    termino = (busqueda or "").strip()
    if termino:
        patron = f"%{termino}%"
        persona_coincide = select(m.Persona.id).where(
            m.Persona.hogar_id == m.HogarNucleo.id,
            or_(m.Persona.nombre_apellidos.ilike(patron), m.Persona.cedula.ilike(patron)),
        ).exists()
        perfil_coincide = (
            select(m.PersonaVulnerabilidad.persona_id)
            .join(m.CatalogoPerfilVulnerabilidad,
                  m.CatalogoPerfilVulnerabilidad.id == m.PersonaVulnerabilidad.perfil_vulnerabilidad_id)
            .join(m.Persona, m.Persona.id == m.PersonaVulnerabilidad.persona_id)
            .where(
                m.Persona.hogar_id == m.HogarNucleo.id,
                m.CatalogoPerfilVulnerabilidad.nombre.ilike(patron),
            )
            .exists()
        )
        stmt = stmt.where(or_(
            m.HogarNucleo.codigo.ilike(patron),
            m.HogarNucleo.direccion.ilike(patron),
            m.Provincia.nombre.ilike(patron),
            m.Municipio.nombre.ilike(patron),
            m.ConsejoPopular.nombre.ilike(patron),
            persona_coincide,
            perfil_coincide,
        ))
    return stmt


async def listar_consejos_populares(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(
        select(m.ConsejoPopular.id, m.ConsejoPopular.nombre).order_by(m.ConsejoPopular.nombre)
    )).all()
    return [{"id": consejo_id, "nombre": nombre} for consejo_id, nombre in rows]


async def listar_perfiles_vulnerabilidad(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(
        select(
            m.CatalogoPerfilVulnerabilidad.id,
            m.CatalogoPerfilVulnerabilidad.codigo,
            m.CatalogoPerfilVulnerabilidad.nombre,
        ).order_by(m.CatalogoPerfilVulnerabilidad.codigo)
    )).all()
    return [
        {"id": perfil_id, "codigo": codigo, "nombre": nombre}
        for perfil_id, codigo, nombre in rows
    ]


async def contar_por_consejo(db: AsyncSession, perfil_id: int | None = None) -> list[dict]:
    tiene_perfil_1 = (
        select(m.PersonaVulnerabilidad.id)
        .join(m.Persona, m.Persona.id == m.PersonaVulnerabilidad.persona_id)
        .join(
            m.CatalogoPerfilVulnerabilidad,
            m.CatalogoPerfilVulnerabilidad.id == m.PersonaVulnerabilidad.perfil_vulnerabilidad_id,
        )
        .where(
            m.Persona.hogar_id == m.HogarNucleo.id,
            m.CatalogoPerfilVulnerabilidad.codigo == 1,
        )
        .correlate(m.HogarNucleo)
        .exists()
    )
    nucleos_con_perfil = func.count(func.distinct(case(
        (m.PersonaVulnerabilidad.perfil_vulnerabilidad_id == perfil_id, m.HogarNucleo.id),
        else_=None,
    )))
    personas_con_perfil = func.count(func.distinct(case(
        (m.PersonaVulnerabilidad.perfil_vulnerabilidad_id == perfil_id, m.Persona.id),
        else_=None,
    )))
    columnas = [
        m.ConsejoPopular.id.label("consejo_id"),
        m.ConsejoPopular.nombre.label("consejo"),
        func.count(func.distinct(m.HogarNucleo.id)).label("nucleos"),
        func.count(func.distinct(m.Persona.id)).label("personas"),
        nucleos_con_perfil.label("nucleos_perfil"),
        personas_con_perfil.label("personas_perfil"),
        func.count(func.distinct(case(
            (or_(m.HogarNucleo.procede_ayuda.is_(True), tiene_perfil_1), m.HogarNucleo.id),
            else_=None,
        ))).label("nucleos_proceden"),
        func.count(func.distinct(case(
            (and_(m.HogarNucleo.procede_ayuda.is_(False), ~tiene_perfil_1), m.HogarNucleo.id),
            else_=None,
        ))).label("nucleos_no_proceden"),
        func.count(func.distinct(case(
            (and_(m.HogarNucleo.procede_ayuda.is_(None), ~tiene_perfil_1), m.HogarNucleo.id),
            else_=None,
        ))).label("nucleos_sin_procesar"),
    ]
    if perfil_id == 5:
        columnas.extend([
            _conteo_personas_edad_rango(perfil_id, 0, 3).label("personas_perfil_0_3"),
            _conteo_personas_edad_rango(perfil_id, 0, 5).label("personas_perfil_0_5"),
            _conteo_personas_edad_rango(None, 0, 3).label("personas_ci_0_3"),
            _conteo_personas_edad_rango(None, 0, 5).label("personas_ci_0_5"),
        ])
    elif perfil_id in {6, 7}:
        columnas.extend([
            _conteo_personas_edad_rango(perfil_id, 0, 7).label("personas_perfil_0_7"),
            _conteo_personas_edad_rango(perfil_id, 8, 13).label("personas_perfil_8_13"),
        ])
    stmt = (
        select(*columnas)
        .outerjoin(m.HogarNucleo, m.HogarNucleo.consejo_popular_id == m.ConsejoPopular.id)
        .outerjoin(m.Persona, m.Persona.hogar_id == m.HogarNucleo.id)
        .outerjoin(m.PersonaVulnerabilidad, m.PersonaVulnerabilidad.persona_id == m.Persona.id)
        .where(func.upper(func.trim(m.ConsejoPopular.nombre)) != "SIN DATO")
        .group_by(m.ConsejoPopular.id, m.ConsejoPopular.nombre)
        .order_by(m.ConsejoPopular.nombre)
    )
    rows = (await db.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]


async def contar_nucleos(
    db: AsyncSession,
    busqueda: str | None = None,
    consejo_id: int | None = None,
    perfil_id: int | None = None,
) -> int:
    stmt = _consulta_listado_nucleos(busqueda, consejo_id, perfil_id).order_by(None).with_only_columns(m.HogarNucleo.id)
    return await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


async def contar_personas_en_nucleos(
    db: AsyncSession,
    busqueda: str | None = None,
    consejo_id: int | None = None,
    perfil_id: int | None = None,
) -> int:
    hogares = _consulta_listado_nucleos(busqueda, consejo_id, perfil_id).order_by(None).with_only_columns(m.HogarNucleo.id)
    stmt = select(func.count(m.Persona.id)).where(m.Persona.hogar_id.in_(hogares))
    return await db.scalar(stmt) or 0


async def contar_personas_con_perfil(
    db: AsyncSession,
    busqueda: str | None,
    consejo_id: int | None,
    perfil_id: int,
) -> int:
    hogares = _consulta_listado_nucleos(busqueda, consejo_id, perfil_id).order_by(None).with_only_columns(m.HogarNucleo.id)
    stmt = (
        select(func.count(func.distinct(m.PersonaVulnerabilidad.persona_id)))
        .join(m.Persona, m.Persona.id == m.PersonaVulnerabilidad.persona_id)
        .where(
            m.PersonaVulnerabilidad.perfil_vulnerabilidad_id == perfil_id,
            m.Persona.hogar_id.in_(hogares),
        )
    )
    return await db.scalar(stmt) or 0


async def listar_nucleos(
    db: AsyncSession,
    offset: int | None = None,
    limit: int | None = None,
    busqueda: str | None = None,
    consejo_id: int | None = None,
    perfil_id: int | None = None,
) -> list[dict]:
    stmt = _consulta_listado_nucleos(busqueda, consejo_id, perfil_id)
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()
    hogar_ids = [hogar.id for hogar, _, _, _ in rows]
    personas_por_hogar: dict[int, list[dict]] = {}
    perfiles_por_hogar: dict[int, list[tuple[str, str, int]]] = {}
    if hogar_ids:
        persona_rows = (await db.execute(
            select(m.Persona.hogar_id, m.Persona.id, m.Persona.nombre_apellidos, m.Persona.cedula)
            .where(m.Persona.hogar_id.in_(hogar_ids))
            .order_by(m.Persona.hogar_id, m.Persona.id)
        )).all()
        for hogar_id, _, nombre, cedula in persona_rows:
            personas_por_hogar.setdefault(hogar_id, []).append({
                "nombre_apellidos": nombre,
                "cedula": cedula,
            })

        perfil_rows = (await db.execute(
            select(
                m.Persona.hogar_id,
                m.CatalogoPerfilVulnerabilidad.nombre,
                m.CatalogoPerfilVulnerabilidad.codigo,
                func.count(m.PersonaVulnerabilidad.persona_id).label("cantidad"),
            )
            .join(
                m.PersonaVulnerabilidad,
                m.PersonaVulnerabilidad.perfil_vulnerabilidad_id == m.CatalogoPerfilVulnerabilidad.id,
            )
            .join(m.Persona, m.Persona.id == m.PersonaVulnerabilidad.persona_id)
            .where(m.Persona.hogar_id.in_(hogar_ids))
            .group_by(
                m.Persona.hogar_id,
                m.CatalogoPerfilVulnerabilidad.id,
                m.CatalogoPerfilVulnerabilidad.nombre,
                m.CatalogoPerfilVulnerabilidad.codigo,
            )
            .order_by(m.Persona.hogar_id, m.CatalogoPerfilVulnerabilidad.nombre)
        )).all()
        for hogar_id, nombre, codigo, cantidad in perfil_rows:
            perfiles_por_hogar.setdefault(hogar_id, []).append((nombre, codigo, cantidad))

    result = []
    for hogar, provincia, municipio, consejo in rows:
        perfil_counts = perfiles_por_hogar.get(hogar.id, [])
        max_perfil_count = max((cantidad for _, _, cantidad in perfil_counts), default=0)
        perfiles_principales = [(nombre, codigo) for nombre, codigo, cantidad in perfil_counts if cantidad == max_perfil_count]
        if not perfiles_principales:
            perfil_resumen = "Sin perfil asignado"
        elif len(perfiles_principales) == 1:
            nombre, codigo = perfiles_principales[0]
            perfil_resumen = f"{nombre} ({codigo})"
        else:
            perfil_resumen = " / ".join(f"{nombre} ({codigo})" for nombre, codigo in perfiles_principales)
        result.append({
            "id": hogar.id,
            "codigo": hogar.codigo,
            "provincia": provincia,
            "municipio": municipio,
            "consejo_popular": consejo,
            "direccion": hogar.direccion,
            "personas": personas_por_hogar.get(hogar.id, []),
            "perfil_resumen": perfil_resumen,
        })
    return result


async def obtener_nucleo(db: AsyncSession, nucleo_id: int) -> dict | None:
    hogar = await db.get(m.HogarNucleo, nucleo_id)
    if hogar is None:
        return None

    personas = (await db.scalars(select(m.Persona).where(m.Persona.hogar_id == hogar.id).order_by(m.Persona.id))).all()
    persona_ids = [persona.id for persona in personas]
    perfiles = (await db.execute(
        select(m.PersonaVulnerabilidad.persona_id, m.PersonaVulnerabilidad.perfil_vulnerabilidad_id)
        .where(m.PersonaVulnerabilidad.persona_id.in_(persona_ids))
    )).all() if persona_ids else []
    ocupaciones = (await db.scalars(
        select(m.PersonaOcupacion).where(m.PersonaOcupacion.persona_id.in_(persona_ids))
    )).all() if persona_ids else []
    perfil_por_persona = {persona_id: perfil_id for persona_id, perfil_id in perfiles}
    ocupaciones_por_persona: dict[int, list[dict]] = {}
    for ocupacion in ocupaciones:
        catalogo_id = getattr(ocupacion, f"{ocupacion.tipo_ocupacion}_id")
        if catalogo_id:
            ocupaciones_por_persona.setdefault(ocupacion.persona_id, []).append({
                "tipo_ocupacion": ocupacion.tipo_ocupacion,
                "ocupacion_catalogo_id": catalogo_id,
            })

    circunscripcion = await db.get(m.Circunscripcion, hogar.circunscripcion_id) if hogar.circunscripcion_id else None
    bodega = await db.get(m.Bodega, hogar.bodega_id) if hogar.bodega_id else None
    return {
        "id": hogar.id,
        "codigo": hogar.codigo,
        "direccion": hogar.direccion,
        "fecha_entrevista": hogar.fecha_entrevista.date().isoformat() if hogar.fecha_entrevista else None,
        "entrevistador_nombre": hogar.entrevistador_nombre,
        "provincia_id": hogar.provincia_id,
        "municipio_id": hogar.municipio_id,
        "consejo_popular_id": hogar.consejo_popular_id,
        "circunscripcion_codigo": circunscripcion.codigo if circunscripcion else "",
        "bodega_codigo": str(bodega.codigo) if bodega else "",
        "zona_residencia_id": hogar.zona_residencia_id,
        "procede_ayuda": hogar.procede_ayuda,
        "observaciones": hogar.observaciones,
        "personas": [{
            "perfil_id": perfil_por_persona.get(p.id),
            "nombre_apellidos": p.nombre_apellidos,
            "cedula": p.cedula,
            "color_piel_id": p.color_piel_id,
            "parentesco_id": p.parentesco_jefe_id,
            "sexo_id": p.sexo_id,
            "nivel_escolaridad_id": p.nivel_escolaridad_id,
            "vinculacion_sne_id": p.vinculacion_sne_id,
            "esta_en_registro_consumidor": p.esta_en_registro_consumidor,
            "fuente_ingreso_id": p.fuente_ingreso_id,
            "ingreso_mensual_cup": float(p.ingreso_mensual_cup) if p.ingreso_mensual_cup is not None else None,
            "trabaja": p.trabaja,
            "motivo_no_trabaja_id": p.motivo_no_trabaja_id,
            "ocupaciones": ocupaciones_por_persona.get(p.id, []),
        } for p in personas],
        "gastos": [{
            "tipo_gasto_id": gasto.tipo_gasto_id,
            "monto_cup": float(gasto.monto_cup),
            "orden_importancia": gasto.orden_importancia,
        } for gasto in (await db.scalars(select(m.GastoHogar).where(m.GastoHogar.hogar_id == hogar.id))).all()],
        "diversidad": [{
            "grupo_alimento_id": item.grupo_alimento_id,
            "gusta": item.gusta,
            "encontrado_en_mercado": item.encontrado_en_mercado,
            "frecuencia_semanal_dias": item.frecuencia_semanal_dias,
        } for item in (await db.scalars(select(m.DiversidadAlimentariaHogar).where(m.DiversidadAlimentariaHogar.hogar_id == hogar.id))).all()],
        "estrategias": [{
            "estrategia_id": item.estrategia_id,
            "aplica": item.aplica,
        } for item in (await db.scalars(select(m.EstrategiaAfrontamientoHogar).where(m.EstrategiaAfrontamientoHogar.hogar_id == hogar.id))).all()],
    }


async def actualizar_nucleo(db: AsyncSession, nucleo_id: int, data: NucleoIn) -> m.HogarNucleo | None:
    hogar = await db.get(m.HogarNucleo, nucleo_id)
    if hogar is None:
        return None
    return await _guardar_nucleo(db, data, hogar)


async def eliminar_nucleo(db: AsyncSession, nucleo_id: int) -> bool:
    hogar = await db.get(m.HogarNucleo, nucleo_id)
    if hogar is None:
        return False
    persona_ids = select(m.Persona.id).where(m.Persona.hogar_id == hogar.id)
    await db.execute(delete(m.PersonaOcupacion).where(m.PersonaOcupacion.persona_id.in_(persona_ids)))
    await db.execute(delete(m.PersonaVulnerabilidad).where(m.PersonaVulnerabilidad.persona_id.in_(persona_ids)))
    await db.execute(delete(m.Persona).where(m.Persona.hogar_id == hogar.id))
    await db.execute(delete(m.GastoHogar).where(m.GastoHogar.hogar_id == hogar.id))
    await db.execute(delete(m.DiversidadAlimentariaHogar).where(m.DiversidadAlimentariaHogar.hogar_id == hogar.id))
    await db.execute(delete(m.EstrategiaAfrontamientoHogar).where(m.EstrategiaAfrontamientoHogar.hogar_id == hogar.id))
    await db.delete(hogar)
    await db.commit()
    return True