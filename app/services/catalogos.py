from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models as m


async def _all(db: AsyncSession, model, order_by=None):
    stmt = select(model)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    res = await db.execute(stmt)
    return res.scalars().all()


async def cargar_catalogos(db: AsyncSession) -> dict:
    return {
        "provincias": await _all(db, m.Provincia, m.Provincia.nombre),
        "municipios": await _all(db, m.Municipio, m.Municipio.nombre),
        "consejos": await _all(db, m.ConsejoPopular, m.ConsejoPopular.nombre),
        "circunscripciones": await _all(db, m.Circunscripcion, m.Circunscripcion.codigo),
        "bodegas": await _all(db, m.Bodega, m.Bodega.codigo),
        "zonas_residencia": await _all(db, m.ZonaResidencia, m.ZonaResidencia.id),
        "perfiles": await _all(db, m.CatalogoPerfilVulnerabilidad, m.CatalogoPerfilVulnerabilidad.codigo),
        "colores_piel": await _all(db, m.CatalogoColorPiel, m.CatalogoColorPiel.codigo),
        "parentescos": await _all(db, m.CatalogoParentesco, m.CatalogoParentesco.codigo),
        "sexos": await _all(db, m.CatalogoSexo, m.CatalogoSexo.codigo),
        "escolaridades": await _all(db, m.CatalogoNivelEscolaridad, m.CatalogoNivelEscolaridad.codigo),
        "vinculaciones_sne": await _all(db, m.CatalogoVinculacionSNE, m.CatalogoVinculacionSNE.codigo),
        "fuentes_ingreso": await _all(db, m.CatalogoFuenteIngreso, m.CatalogoFuenteIngreso.codigo),
        "sectores_estatal": await _all(db, m.CatalogoSectorEstatal, m.CatalogoSectorEstatal.codigo),
        "empresas_mixtas": await _all(db, m.CatalogoEmpresaMixta, m.CatalogoEmpresaMixta.codigo),
        "sectores_agropecuario": await _all(db, m.CatalogoSectorAgropecuario, m.CatalogoSectorAgropecuario.codigo),
        "sectores_no_estatal": await _all(db, m.CatalogoSectorNoEstatal, m.CatalogoSectorNoEstatal.codigo),
        "trabajos_informales": await _all(db, m.CatalogoTrabajoInformal, m.CatalogoTrabajoInformal.codigo),
        "motivos_no_trabaja": await _all(db, m.CatalogoMotivoNoTrabaja, m.CatalogoMotivoNoTrabaja.codigo),
        "tipos_gasto": await _all(db, m.CatalogoTipoGastoPrincipal, m.CatalogoTipoGastoPrincipal.codigo),
        "grupos_alimento": await _all(db, m.CatalogoGrupoAlimento, m.CatalogoGrupoAlimento.codigo),
        "estrategias": await _all(db, m.CatalogoEstrategiaAfrontamiento, m.CatalogoEstrategiaAfrontamiento.codigo),
    }


def catalogos_a_json(cat: dict) -> dict:
    """Convierte los catálogos a JSON serializable para usar desde JS."""
    def conv(items):
        return [{"id": x.id, "codigo": x.codigo, "nombre": x.nombre} for x in items]

    data = {k: conv(v) for k, v in cat.items()}
    # Añadimos las relaciones padre-hijo para filtrado dinámico:
    data["municipios"] = [
        {"id": x.id, "codigo": x.codigo, "nombre": x.nombre, "provincia_id": x.provincia_id}
        for x in cat["municipios"]
    ]
    data["consejos"] = [
        {"id": x.id, "codigo": x.codigo, "nombre": x.nombre, "municipio_id": x.municipio_id}
        for x in cat["consejos"]
    ]
    data["circunscripciones"] = [
        {"id": x.id, "codigo": x.codigo, "nombre": x.nombre or "", "consejo_popular_id": x.consejo_popular_id}
        for x in cat["circunscripciones"]
    ]
    data["bodegas"] = [
        {"id": x.id, "codigo": x.codigo, "nombre": x.nombre or "", "consejo_popular_id": x.consejo_popular_id}
        for x in cat["bodegas"]
    ]
    return data