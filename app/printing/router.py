from pathlib import Path
import os
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.nucleo_service import contar_por_consejo, listar_perfiles_vulnerabilidad


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
