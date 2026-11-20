from pathlib import Path
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.nucleo_service import (
    contar_por_consejo,
    listar_consejos_populares,
    listar_nucleos_elegibles_impresion,
    listar_nucleos_por_consejo_impresion,
    listar_perfiles_vulnerabilidad,
    edad_en_anos_desde_ci,
    normalizar_rango_edad,
    listar_personas_listado,
)


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _resumen_perfil(perfil: dict, filas: list[dict]) -> dict:
    perfil_id = perfil["id"]
    return {
        "perfil": perfil,
        "filas": filas,
        "total_nucleos": sum(fila["nucleos_perfil"] for fila in filas),
        "total_personas": sum(fila["personas_perfil"] for fila in filas),
        "total_edad_perfil_0_3": sum(
            fila.get("personas_perfil_0_3") or 0 for fila in filas
        ) if perfil_id == 5 else None,
        "total_edad_perfil_0_5": sum(
            fila.get("personas_perfil_0_5") or 0 for fila in filas
        ) if perfil_id == 5 else None,
        "total_edad_ci_0_3": sum(
            fila.get("personas_ci_0_3") or 0 for fila in filas
        ) if perfil_id == 5 else None,
        "total_edad_ci_0_5": sum(
            fila.get("personas_ci_0_5") or 0 for fila in filas
        ) if perfil_id == 5 else None,
        "total_edad_0_7": sum(
            fila.get("personas_perfil_0_7") or 0 for fila in filas
        ) if perfil_id in {6, 7} else None,
        "total_edad_8_13": sum(
            fila.get("personas_perfil_8_13") or 0 for fila in filas
        ) if perfil_id in {6, 7} else None,
    }


def _filtrar_grupos_impresion(
    grupos_consejos: list[dict],
    *,
    perfil_codigo: int | None = None,
    solo_sin_perfil: bool = False,
    sexo: str | None = None,
    estado: str | None = None,
    busqueda: str = "",
    edad_min: int | None = None,
    edad_max: int | None = None,
) -> list[dict]:
    busqueda = busqueda.casefold().strip()
    edad_min, edad_max = normalizar_rango_edad(edad_min, edad_max)
    resultado = []
    for consejo in grupos_consejos:
        grupos = []
        for grupo in consejo["grupos"]:
            codigo = grupo["perfil"]["codigo"]
            if solo_sin_perfil and codigo is not None:
                continue
            if perfil_codigo is not None and codigo != perfil_codigo:
                continue

            nucleos = []
            for nucleo in grupo["nucleos"]:
                personas = nucleo.get("personas", [])
                if sexo == "F" and not any(persona.get("sexo") == "F" for persona in personas):
                    continue
                if sexo == "M" and not any(persona.get("sexo") == "M" for persona in personas):
                    continue
                if sexo == "sin-sexo" and not any(not persona.get("sexo") for persona in personas):
                    continue
                if edad_min is not None or edad_max is not None:
                    edades = [edad_en_anos_desde_ci(persona.get("cedula")) for persona in personas]
                    if not any(
                        edad is not None
                        and (edad_min is None or edad >= edad_min)
                        and (edad_max is None or edad <= edad_max)
                        for edad in edades
                    ):
                        continue
                procede = nucleo.get("procede")
                if estado == "procede" and procede is not True:
                    continue
                if estado == "no_procede" and procede is not False:
                    continue
                if estado == "pendiente" and procede is not None:
                    continue
                if busqueda:
                    campos = [
                        nucleo.get("codigo", ""),
                        nucleo.get("direccion_completa", nucleo.get("direccion", "")),
                        nucleo.get("circunscripcion", ""),
                        nucleo.get("bodega", ""),
                        *(persona.get("nombre", "") for persona in personas),
                        *(persona.get("cedula", "") for persona in personas),
                    ]
                    if not any(busqueda in str(campo or "").casefold() for campo in campos):
                        continue
                nucleos.append(nucleo)
            if nucleos:
                grupos.append({**grupo, "nucleos": nucleos})
        if grupos:
            resultado.append({**consejo, "grupos": grupos})
    return resultado


@router.get("/nucleos/conteo/impresion", name="pagina_impresion_estadisticas")
async def pagina_impresion_estadisticas(
    request: Request,
    modo: Literal["completo", "todo", "general", "perfil", "todos-perfiles"] = "completo",
    perfil_id: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    perfiles = await listar_perfiles_vulnerabilidad(db)
    perfil = next((item for item in perfiles if item["id"] == perfil_id), None)
    filas_generales = await contar_por_consejo(db)
    general = {
        "filas": filas_generales,
        "total_nucleos": sum(fila["nucleos"] for fila in filas_generales),
        "total_personas": sum(fila["personas"] for fila in filas_generales),
        "total_proceden": sum(fila["nucleos_proceden"] for fila in filas_generales),
        "total_no_proceden": sum(fila["nucleos_no_proceden"] for fila in filas_generales),
        "total_pendientes": sum(fila["nucleos_sin_procesar"] for fila in filas_generales),
    }

    resumen_seleccionado = None
    if modo in {"todo", "perfil"} and perfil is not None:
        filas_perfil = await contar_por_consejo(db, perfil["id"])
        resumen_seleccionado = _resumen_perfil(perfil, filas_perfil)

    resumenes_perfiles = []
    if modo in {"completo", "todos-perfiles"}:
        for item in perfiles:
            filas_perfil = await contar_por_consejo(db, item["id"])
            resumenes_perfiles.append(_resumen_perfil(item, filas_perfil))

    return templates.TemplateResponse(
        "estadisticas.html",
        {
            "request": request,
            "modo": modo,
            "perfil_id": perfil_id,
            "perfil": perfil,
            "general": general,
            "resumen_seleccionado": resumen_seleccionado,
            "resumenes_perfiles": resumenes_perfiles,
            "directora_nombre": os.getenv("DIRECTORA_NOMBRE", "").strip(),
        },
    )


@router.get("/nucleos/elegibles/impresion", name="pagina_impresion_nucleos_elegibles")
async def pagina_impresion_nucleos_elegibles(
    request: Request,
    tipo: Literal["elegibles", "todos"] = "elegibles",
    consejo_id: str = Query(""),
    perfil_id: str = Query(""),
    sexo: Literal["", "F", "M", "sin-sexo"] = "",
    estado: Literal["", "procede", "no_procede", "pendiente"] = "",
    q: str = Query("", max_length=100),
    edad_min: str = Query(""),
    edad_max: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    consejo_id_param = consejo_id.strip()
    if consejo_id_param:
        try:
            consejo_id = int(consejo_id_param)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="consejo_id debe ser un entero") from exc
        if consejo_id < 1:
            raise HTTPException(status_code=422, detail="consejo_id debe ser mayor que cero")
    else:
        consejo_id = None
    consejos = await listar_consejos_populares(db)
    if consejo_id is not None and consejo_id not in {consejo["id"] for consejo in consejos}:
        consejo_id = None
    perfiles = await listar_perfiles_vulnerabilidad(db)
    perfil_seleccionado = None
    solo_sin_perfil = perfil_id == "sin-perfil"
    if perfil_id and not solo_sin_perfil:
        try:
            perfil_seleccionado = next(
                (perfil for perfil in perfiles if perfil["id"] == int(perfil_id)),
                None,
            )
        except ValueError:
            perfil_seleccionado = None
    perfil_codigo = perfil_seleccionado["codigo"] if perfil_seleccionado else None
    grupos_consejos = (
        await listar_nucleos_por_consejo_impresion(db, consejo_id)
        if tipo == "todos"
        else await listar_nucleos_elegibles_impresion(db, consejo_id)
    )
    edad_min, edad_max = normalizar_rango_edad(edad_min, edad_max)
    grupos_consejos = _filtrar_grupos_impresion(
        grupos_consejos,
        perfil_codigo=perfil_codigo,
        solo_sin_perfil=solo_sin_perfil,
        sexo=sexo or None,
        estado=estado or None,
        busqueda=q,
        edad_min=edad_min,
        edad_max=edad_max,
    )
    return templates.TemplateResponse(
        "nucleos_elegibles.html",
        {
            "request": request,
            "tipo": tipo,
            "consejo_id": consejo_id,
            "perfil_id": perfil_id,
            "sexo": sexo,
            "estado": estado,
            "busqueda": q,
            "edad_min": edad_min,
            "edad_max": edad_max,
            "perfil": perfil_seleccionado,
            "grupos_consejos": grupos_consejos,
            "directora_nombre": os.getenv("DIRECTORA_NOMBRE", "").strip(),
        },
    )


@router.get("/nucleos/personas/impresion", name="pagina_impresion_personas")
async def pagina_impresion_personas(
    request: Request,
    tipo: Literal["elegibles", "todos"] = "elegibles",
    consejo_id: str = Query(""),
    perfil_id: str = Query(""),
    sexo: Literal["", "F", "M", "sin-sexo"] = "",
    estado: Literal["", "procede", "no_procede", "pendiente"] = "",
    q: str = Query("", max_length=100),
    edad_min: str = Query(""),
    edad_max: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    consejo_id_param = consejo_id.strip()
    if consejo_id_param:
        try:
            consejo_id = int(consejo_id_param)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="consejo_id debe ser un entero") from exc
        if consejo_id < 1:
            raise HTTPException(status_code=422, detail="consejo_id debe ser mayor que cero")
    else:
        consejo_id = None
    consejos = await listar_consejos_populares(db)
    if consejo_id is not None and consejo_id not in {consejo["id"] for consejo in consejos}:
        consejo_id = None
    perfiles = await listar_perfiles_vulnerabilidad(db)
    perfil_seleccionado = None
    solo_sin_perfil = perfil_id == "sin-perfil"
    if perfil_id and not solo_sin_perfil:
        try:
            perfil_seleccionado = next(
                (perfil for perfil in perfiles if perfil["id"] == int(perfil_id)),
                None,
            )
        except ValueError:
            perfil_seleccionado = None
    perfil_id_param = perfil_seleccionado["id"] if perfil_seleccionado else None
    edad_min, edad_max = normalizar_rango_edad(edad_min, edad_max)
    personas = await listar_personas_listado(
        db,
        busqueda=q,
        consejo_id=consejo_id,
        perfil_id="sin-perfil" if solo_sin_perfil else perfil_id_param,
        estado=estado or None,
        edad_min=edad_min,
        edad_max=edad_max,
        solo_elegibles=tipo == "elegibles",
    )
    if sexo == "F":
        personas = [persona for persona in personas if persona["sexo"] == "F"]
    elif sexo == "M":
        personas = [persona for persona in personas if persona["sexo"] == "M"]
    elif sexo == "sin-sexo":
        personas = [persona for persona in personas if not persona["sexo"]]
    return templates.TemplateResponse(
        "personas.html",
        {
            "request": request,
            "tipo": tipo,
            "consejo_id": consejo_id,
            "perfil_id": perfil_id,
            "perfil": perfil_seleccionado,
            "sexo": sexo,
            "estado": estado,
            "busqueda": q,
            "edad_min": edad_min,
            "edad_max": edad_max,
            "personas": personas,
            "directora_nombre": os.getenv("DIRECTORA_NOMBRE", "").strip(),
        },
    )
