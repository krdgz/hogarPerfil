#!/usr/bin/env python3
"""
Script de migración de datos desde Excel (datos.xlsx) a PostgreSQL.
Utiliza los modelos definidos en models.py.
"""

import unicodedata
import pandas as pd
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Provincia, Municipio, ConsejoPopular, Circunscripcion, ZonaResidencia, Bodega,
    CatalogoPerfilVulnerabilidad, CatalogoColorPiel, CatalogoParentesco, CatalogoSexo,
    CatalogoNivelEscolaridad, CatalogoVinculacionSNE, CatalogoFuenteIngreso,
    CatalogoSectorEstatal, CatalogoEmpresaMixta, CatalogoSectorAgropecuario,
    CatalogoSectorNoEstatal, CatalogoTrabajoInformal, CatalogoMotivoNoTrabaja,
    CatalogoTipoGastoPrincipal, CatalogoGrupoAlimento, CatalogoEstrategiaAfrontamiento,
    HogarNucleo, GastoHogar, DiversidadAlimentariaHogar, EstrategiaAfrontamientoHogar,
    Persona, PersonaVulnerabilidad, PersonaOcupacion
)
from .database import DATABASE_URL

sync_engine = create_engine(
    DATABASE_URL.replace("+asyncpg", "+psycopg2"),
    echo=False,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def normalize(s):
    """Normaliza una cadena: mayúsculas, sin acentos, sin puntuación."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    s = ''.join(c for c in s if c.isalnum() or c.isspace())
    return s


def get_val(row, idx):
    """Extrae un valor de una fila de pandas por índice de columna."""
    try:
        val = row.iloc[idx]
    except IndexError:
        return None
    if pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == '':
            return None
    return val


def get_bool(val):
    """Convierte 'SI'/'NO' a True/False, o None."""
    if val is None:
        return None
    if isinstance(val, str):
        v = val.strip().upper()
        if v == 'SI':
            return True
        if v == 'NO':
            return False
    return None


def find_col_index(df, text):
    """Busca el índice de una columna cuyo nombre contenga el texto dado."""
    text_lower = text.lower().strip()
    for i, col in enumerate(df.columns):
        if text_lower in str(col).lower():
            return i
    return None


def get_procede(first_row, procede_idx, n_cols):
    """
    Intenta obtener el valor booleano de procede en la columna indicada.
    Si no es si/no, prueba columnas adyacentes (por si hay desfase).
    """
    for offset in [0, 1, -1, 2, -2]:
        i = procede_idx + offset
        if 0 <= i < n_cols:
            val = get_val(first_row, i)
            b = get_bool(val)
            if b is not None:
                return b
    return None


# ----------------------------------------------------------------------
# Funciones geográficas
# ----------------------------------------------------------------------
def get_or_create_provincia(db: Session, nombre: str):
    nombre = nombre.strip()
    inst = db.query(Provincia).filter(func.upper(Provincia.nombre) == nombre.upper()).first()
    if inst:
        return inst
    codigo = nombre.upper()[:10]
    inst = Provincia(codigo=codigo, nombre=nombre)
    db.add(inst)
    db.flush()
    return inst


def get_or_create_municipio(db: Session, nombre: str, provincia_id: int):
    nombre = nombre.strip()
    inst = db.query(Municipio).filter(
        func.upper(Municipio.nombre) == nombre.upper(),
        Municipio.provincia_id == provincia_id
    ).first()
    if inst:
        return inst
    codigo = nombre.upper()[:10]
    inst = Municipio(codigo=codigo, nombre=nombre, provincia_id=provincia_id)
    db.add(inst)
    db.flush()
    return inst


def get_or_create_consejo_popular(db: Session, nombre_raw: str, municipio_id: int):
    nombre_raw = nombre_raw.strip()
    if '. ' in nombre_raw:
        parts = nombre_raw.split('. ', 1)
        codigo = parts[0].strip()
        nombre = parts[1].strip()
    else:
        codigo = nombre_raw
        nombre = nombre_raw
    inst = db.query(ConsejoPopular).filter(
        func.upper(ConsejoPopular.nombre) == nombre.upper(),
        ConsejoPopular.municipio_id == municipio_id
    ).first()
    if inst:
        return inst
    inst = ConsejoPopular(codigo=codigo, nombre=nombre, municipio_id=municipio_id)
    db.add(inst)
    db.flush()
    return inst


def get_or_create_circunscripcion(db: Session, codigo: str, consejo_popular_id: int):
    codigo = str(codigo).strip()
    inst = db.query(Circunscripcion).filter(
        Circunscripcion.codigo == codigo,
        Circunscripcion.consejo_popular_id == consejo_popular_id
    ).first()
    if inst:
        return inst
    inst = Circunscripcion(codigo=codigo, consejo_popular_id=consejo_popular_id)
    db.add(inst)
    db.flush()
    return inst


def get_or_create_zona_residencia(db: Session, nombre: str):
    nombre = nombre.strip()
    inst = db.query(ZonaResidencia).filter(func.upper(ZonaResidencia.nombre) == nombre.upper()).first()
    if inst:
        return inst
    codigo = 'URBANA' if 'urbana' in nombre.lower() else 'RURAL'
    inst = ZonaResidencia(codigo=codigo, nombre=nombre)
    db.add(inst)
    db.flush()
    return inst


def get_or_create_bodega(db: Session, codigo_raw, consejo_popular_id: int):
    try:
        codigo = int(str(codigo_raw).strip())
    except (ValueError, TypeError):
        return None
    inst = db.query(Bodega).filter(
        Bodega.codigo == codigo,
        Bodega.consejo_popular_id == consejo_popular_id
    ).first()
    if inst:
        return inst
    inst = Bodega(codigo=codigo, consejo_popular_id=consejo_popular_id)
    db.add(inst)
    db.flush()
    return inst


# ----------------------------------------------------------------------
# Script principal
# ----------------------------------------------------------------------
def main():
    print("Leyendo archivo Excel...")
    df = pd.read_excel('app/forms.xlsx', header=2)
    df = df.dropna(how='all')
    n_cols = len(df.columns)

    # ----- Localizar columna 'procede' -----
    procede_idx = find_col_index(df, 'procede')
    if procede_idx is None:
        print("ADVERTENCIA: No se encontró columna 'procede' por nombre. Usando última columna.")
        procede_idx = n_cols - 1
    print(f"Columna 'procede' en índice {procede_idx} (nombre: {df.columns[procede_idx]!r})")

    # ----- Índices de estrategias de afrontamiento (5 columnas) -----
    # Según encabezado: Recurrir, Pedir, Reducir, Disminuir, Adultos restringen
    estrategia_cols = [70, 71, 72, 73, 74]

    with SessionLocal() as db:
        print("Cargando catálogos...")
        cat_color_piel = {normalize(c.nombre): c.id for c in db.query(CatalogoColorPiel).all()}
        cat_parentesco = {normalize(c.nombre): c.id for c in db.query(CatalogoParentesco).all()}
        cat_sexo = {normalize(c.nombre): c.id for c in db.query(CatalogoSexo).all()}
        cat_nivel_escolaridad = {normalize(c.nombre): c.id for c in db.query(CatalogoNivelEscolaridad).all()}
        cat_vinculacion_sne = {normalize(c.nombre): c.id for c in db.query(CatalogoVinculacionSNE).all()}
        cat_fuente_ingreso = {normalize(c.nombre): c.id for c in db.query(CatalogoFuenteIngreso).all()}
        cat_sector_estatal = {normalize(c.nombre): c.id for c in db.query(CatalogoSectorEstatal).all()}
        cat_empresa_mixta = {normalize(c.nombre): c.id for c in db.query(CatalogoEmpresaMixta).all()}
        cat_sector_agropecuario = {normalize(c.nombre): c.id for c in db.query(CatalogoSectorAgropecuario).all()}
        cat_sector_no_estatal = {normalize(c.nombre): c.id for c in db.query(CatalogoSectorNoEstatal).all()}
        cat_trabajo_informal = {normalize(c.nombre): c.id for c in db.query(CatalogoTrabajoInformal).all()}
        cat_motivo_no_trabaja = {normalize(c.nombre): c.id for c in db.query(CatalogoMotivoNoTrabaja).all()}
        cat_perfil_vulnerabilidad = {normalize(c.nombre): c.id for c in db.query(CatalogoPerfilVulnerabilidad).all()}
        cat_tipo_gasto = {c.codigo: c.id for c in db.query(CatalogoTipoGastoPrincipal).all()}
        cat_grupo_alimento = {c.codigo: c.id for c in db.query(CatalogoGrupoAlimento).all()}
        cat_estrategia = {c.codigo: c.id for c in db.query(CatalogoEstrategiaAfrontamiento).all()}

        print("Procesando hogares...")
        grouped = df.groupby(df.columns[0])
        for hogar_codigo, group in grouped:
            if pd.isna(hogar_codigo):
                continue
            hogar_codigo = str(hogar_codigo).strip()
            first_row = group.iloc[0]

            # --- Datos geográficos ---
            provincia_nombre = get_val(first_row, 1)
            municipio_nombre = get_val(first_row, 2)
            consejo_nombre_raw = get_val(first_row, 3)
            circunscripcion_codigo = get_val(first_row, 4)
            zona_nombre = get_val(first_row, 5)
            bodega_codigo_raw = get_val(first_row, 6)
            direccion = get_val(first_row, 9)

            if not provincia_nombre or not municipio_nombre or not consejo_nombre_raw:
                print(f"  Hogar {hogar_codigo}: faltan datos geográficos, se omite.")
                continue

            provincia = get_or_create_provincia(db, provincia_nombre)
            municipio = get_or_create_municipio(db, municipio_nombre, provincia.id)
            consejo = get_or_create_consejo_popular(db, consejo_nombre_raw, municipio.id)
            circunscripcion = None
            if circunscripcion_codigo:
                circunscripcion = get_or_create_circunscripcion(db, circunscripcion_codigo, consejo.id)
            zona = get_or_create_zona_residencia(db, zona_nombre) if zona_nombre else None
            bodega = None
            if bodega_codigo_raw:
                bodega = get_or_create_bodega(db, bodega_codigo_raw, consejo.id)

            # --- Valor de procede (columna final) ---
            procede_ayuda = get_procede(first_row, procede_idx, n_cols)
            if procede_ayuda is not None:
                print(f"  Hogar {hogar_codigo}: procede_ayuda = {procede_ayuda}")

            # --- Crear/obtener HogarNucleo ---
            hogar = db.query(HogarNucleo).filter(HogarNucleo.codigo == hogar_codigo).first()
            if not hogar:
                hogar = HogarNucleo(
                    codigo=hogar_codigo,
                    direccion=direccion,
                    provincia_id=provincia.id,
                    municipio_id=municipio.id,
                    consejo_popular_id=consejo.id,
                    circunscripcion_id=circunscripcion.id if circunscripcion else None,
                    bodega_id=bodega.id if bodega else None,
                    zona_residencia_id=zona.id if zona else None,
                    procede_ayuda=procede_ayuda,
                )
                db.add(hogar)
                db.flush()
                print(f"  Hogar creado: {hogar_codigo}")
            else:
                # Actualizar procede_ayuda si antes no se había seteado
                if hogar.procede_ayuda is None and procede_ayuda is not None:
                    hogar.procede_ayuda = procede_ayuda
                print(f"  Hogar ya existe: {hogar_codigo}")

            # --- Gastos del hogar (8 pares monto/orden) ---
            gasto_cols = [
                (25, 26), (27, 28), (29, 30), (31, 32),
                (33, 34), (35, 36), (37, 38), (39, 40)
            ]
            for idx, (monto_idx, orden_idx) in enumerate(gasto_cols, start=1):
                monto = get_val(first_row, monto_idx)
                orden = get_val(first_row, orden_idx)
                if monto is not None:
                    tipo_id = cat_tipo_gasto.get(idx)
                    if not tipo_id:
                        continue
                    existing = db.query(GastoHogar).filter(
                        GastoHogar.hogar_id == hogar.id,
                        GastoHogar.tipo_gasto_id == tipo_id
                    ).first()
                    if not existing:
                        gasto = GastoHogar(
                            hogar_id=hogar.id,
                            tipo_gasto_id=tipo_id,
                            monto_cup=float(monto),
                            orden_importancia=int(orden) if orden is not None else None
                        )
                        db.add(gasto)
            db.flush()

            # --- Diversidad alimentaria (9 grupos × 3 columnas) ---
            diversidad_cols = [
                (43, 44, 45), (46, 47, 48), (49, 50, 51),
                (52, 53, 54), (55, 56, 57), (58, 59, 60),
                (61, 62, 63), (64, 65, 66), (67, 68, 69)
            ]
            for idx, (gusta_idx, mercado_idx, frec_idx) in enumerate(diversidad_cols, start=1):
                gusta_val = get_val(first_row, gusta_idx)
                mercado_val = get_val(first_row, mercado_idx)
                frec_val = get_val(first_row, frec_idx)
                if gusta_val is not None or mercado_val is not None or frec_val is not None:
                    grupo_id = cat_grupo_alimento.get(idx)
                    if not grupo_id:
                        continue
                    existing = db.query(DiversidadAlimentariaHogar).filter(
                        DiversidadAlimentariaHogar.hogar_id == hogar.id,
                        DiversidadAlimentariaHogar.grupo_alimento_id == grupo_id
                    ).first()
                    if not existing:
                        div = DiversidadAlimentariaHogar(
                            hogar_id=hogar.id,
                            grupo_alimento_id=grupo_id,
                            gusta=get_bool(gusta_val),
                            encontrado_en_mercado=get_bool(mercado_val),
                            frecuencia_semanal_dias=int(frec_val) if frec_val is not None else 0
                        )
                        db.add(div)
            db.flush()

            # --- Estrategias de afrontamiento ---
            for idx, col_idx in enumerate(estrategia_cols, start=1):
                val = get_val(first_row, col_idx)
                if val is not None:
                    estrategia_id = cat_estrategia.get(idx)
                    if not estrategia_id:
                        continue
                    existing = db.query(EstrategiaAfrontamientoHogar).filter(
                        EstrategiaAfrontamientoHogar.hogar_id == hogar.id,
                        EstrategiaAfrontamientoHogar.estrategia_id == estrategia_id
                    ).first()
                    if not existing:
                        est = EstrategiaAfrontamientoHogar(
                            hogar_id=hogar.id,
                            estrategia_id=estrategia_id,
                            aplica=get_bool(val) or False
                        )
                        db.add(est)
            db.flush()

            # --- Personas del hogar ---
            for _, row in group.iterrows():
                nombre_apellidos = get_val(row, 7)
                cedula = get_val(row, 8)
                if not cedula:
                    continue

                persona = db.query(Persona).filter(
                    Persona.cedula == cedula,
                    Persona.hogar_id == hogar.id
                ).first()
                if persona:
                    continue

                color_piel_nombre = get_val(row, 11)
                color_piel_id = cat_color_piel.get(normalize(color_piel_nombre)) if color_piel_nombre else None

                parentesco_nombre = get_val(row, 12)
                parentesco_id = cat_parentesco.get(normalize(parentesco_nombre)) if parentesco_nombre else None

                sexo_nombre = get_val(row, 13)
                sexo_id = cat_sexo.get(normalize(sexo_nombre)) if sexo_nombre else None

                nivel_escolaridad_nombre = get_val(row, 14)
                nivel_escolaridad_id = cat_nivel_escolaridad.get(normalize(nivel_escolaridad_nombre)) if nivel_escolaridad_nombre else None

                vinculacion_sne_nombre = get_val(row, 15)
                vinculacion_sne_id = cat_vinculacion_sne.get(normalize(vinculacion_sne_nombre)) if vinculacion_sne_nombre else None

                registro_consumidor_val = get_val(row, 16)
                esta_en_registro_consumidor = get_bool(registro_consumidor_val)

                fuente_ingreso_nombre = get_val(row, 17)
                fuente_ingreso_id = cat_fuente_ingreso.get(normalize(fuente_ingreso_nombre)) if fuente_ingreso_nombre else None

                ingreso_mensual = get_val(row, 18)
                ingreso_mensual_cup = float(ingreso_mensual) if ingreso_mensual else None

                motivo_no_trabaja_nombre = get_val(row, 24)
                motivo_no_trabaja_id = cat_motivo_no_trabaja.get(normalize(motivo_no_trabaja_nombre)) if motivo_no_trabaja_nombre else None

                # Ocupaciones (columnas 19 a 23)
                ocupaciones = []
                for idx, col_idx in enumerate([19, 20, 21, 22, 23], start=1):
                    val = get_val(row, col_idx)
                    if val is not None:
                        ocupaciones.append((idx, val))

                trabaja = len(ocupaciones) > 0

                persona = Persona(
                    hogar_id=hogar.id,
                    nombre_apellidos=nombre_apellidos,
                    cedula=cedula,
                    color_piel_id=color_piel_id,
                    parentesco_jefe_id=parentesco_id,
                    sexo_id=sexo_id,
                    nivel_escolaridad_id=nivel_escolaridad_id,
                    vinculacion_sne_id=vinculacion_sne_id,
                    esta_en_registro_consumidor=esta_en_registro_consumidor,
                    fuente_ingreso_id=fuente_ingreso_id,
                    ingreso_mensual_cup=ingreso_mensual_cup,
                    trabaja=trabaja,
                    motivo_no_trabaja_id=motivo_no_trabaja_id
                )
                db.add(persona)
                db.flush()

                # Vulnerabilidad
                perfil_vuln_nombre = get_val(row, 10)
                if perfil_vuln_nombre:
                    perfil_vuln_nombre = perfil_vuln_nombre.rstrip(':').strip()
                    perfil_vuln_id = cat_perfil_vulnerabilidad.get(normalize(perfil_vuln_nombre))
                    if perfil_vuln_id:
                        pv = PersonaVulnerabilidad(
                            persona_id=persona.id,
                            perfil_vulnerabilidad_id=perfil_vuln_id
                        )
                        db.add(pv)

                # Ocupaciones
                for idx, val in ocupaciones:
                    tipo = None
                    fk_id = None
                    if idx == 1:
                        tipo = 'sector_estatal'
                        fk_id = cat_sector_estatal.get(normalize(val))
                    elif idx == 2:
                        tipo = 'empresa_mixta'
                        fk_id = cat_empresa_mixta.get(normalize(val))
                    elif idx == 3:
                        tipo = 'sector_agropecuario'
                        fk_id = cat_sector_agropecuario.get(normalize(val))
                    elif idx == 4:
                        tipo = 'sector_no_estatal'
                        fk_id = cat_sector_no_estatal.get(normalize(val))
                    elif idx == 5:
                        tipo = 'trabajo_informal'
                        fk_id = cat_trabajo_informal.get(normalize(val))

                    if tipo:
                        es_principal = (idx == ocupaciones[0][0])
                        ocupacion = PersonaOcupacion(
                            persona_id=persona.id,
                            es_principal=es_principal,
                            tipo_ocupacion=tipo,
                            sector_estatal_id=fk_id if tipo == 'sector_estatal' else None,
                            empresa_mixta_id=fk_id if tipo == 'empresa_mixta' else None,
                            sector_agropecuario_id=fk_id if tipo == 'sector_agropecuario' else None,
                            sector_no_estatal_id=fk_id if tipo == 'sector_no_estatal' else None,
                            trabajo_informal_id=fk_id if tipo == 'trabajo_informal' else None
                        )
                        db.add(ocupacion)

        db.commit()
        print("Migración completada exitosamente.")


if __name__ == "__main__":
    main()