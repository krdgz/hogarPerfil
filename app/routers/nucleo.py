from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from urllib.parse import urlsplit

from ..database import get_db
from ..schemas import NucleoIn, NucleoOut
from ..services.catalogos import cargar_catalogos, catalogos_a_json
from ..services.nucleo_service import (
    actualizar_nucleo,
    contar_nucleos,
    contar_por_consejo,
    crear_nucleo,
    eliminar_nucleo,
    listar_consejos_populares,
    listar_nucleos,
    listar_perfiles_vulnerabilidad,
    obtener_nucleo,
    obtener_ultimo_codigo_nucleo,
)

router = APIRouter(prefix="/nucleos", tags=["nucleos"])
templates = Jinja2Templates(directory="app/templates")
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def static_version() -> str:
    latest_change = max((path.stat().st_mtime_ns for path in STATIC_DIR.rglob("*") if path.is_file()), default=0)
    return str(latest_change)


templates.env.globals["static_version"] = static_version


def _integrity_error_message(exc: IntegrityError, codigo: str) -> str:
    original = exc.orig
    constraint = getattr(original, "constraint_name", None)
    if constraint is None:
        constraint = getattr(getattr(original, "diag", None), "constraint_name", None)
    if constraint == "hogar_nucleo_codigo_key":
        return f"Ya existe un núcleo con el código {codigo}."
    return "No se pudo guardar el núcleo porque algunos datos están duplicados o no cumplen las restricciones."


def _optional_positive_id(value: str, parameter_name: str) -> int | None:
    if not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{parameter_name} debe ser un entero") from exc
    if parsed <= 0:
        raise HTTPException(status_code=422, detail=f"{parameter_name} debe ser mayor que cero")
    return parsed


def _safe_list_return_to(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme or parsed.netloc or parsed.path != "/nucleos":
        return "/nucleos"
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


@router.get("/nuevo", response_class=HTMLResponse)
async def formulario_nuevo(
    request: Request,
    return_to: str = "",
    guardado: bool = False,
    codigo_guardado: str = "",
    db: AsyncSession = Depends(get_db),
):
    cat = await cargar_catalogos(db)
    return templates.TemplateResponse(
        "nucleo/form.html",
        {
            "request": request,
            "catalogos": cat,
            "catalogos_json": catalogos_a_json(cat),
            "modo": "nuevo",
            "nucleo": None,
            "return_to": _safe_list_return_to(return_to),
            "guardado": guardado,
            "codigo_guardado": codigo_guardado,
        },
    )


@router.get("", response_class=HTMLResponse)
async def pagina_listado(
    request: Request,
    page: int = Query(1, ge=1),
    q: str = "",
    consejo_id: str = "",
    perfil_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    page_size = 50
    consejo_id = _optional_positive_id(consejo_id, "consejo_id")
    perfil_id = _optional_positive_id(perfil_id, "perfil_id")
    consejos = await listar_consejos_populares(db)
    perfiles = await listar_perfiles_vulnerabilidad(db)
    consejo_ids = {consejo["id"] for consejo in consejos}
    perfil_ids = {perfil["id"] for perfil in perfiles}
    if consejo_id not in consejo_ids:
        consejo_id = None
    if perfil_id not in perfil_ids:
        perfil_id = None
    total = await contar_nucleos(db, q, consejo_id, perfil_id)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    return templates.TemplateResponse(
        "nucleo/listado.html",
        {
            "request": request,
            "nucleos": await listar_nucleos(
                db,
                offset=(page - 1) * page_size,
                limit=page_size,
                busqueda=q,
                consejo_id=consejo_id,
                perfil_id=perfil_id,
            ),
            "consejos": consejos,
            "consejo_id": consejo_id,
            "perfiles": perfiles,
            "perfil_id": perfil_id,
            "busqueda": q,
            "pagina": page,
            "total": total,
            "total_paginas": total_pages,
            "desde": (page - 1) * page_size + 1 if total else 0,
            "hasta": min(page * page_size, total),
            "return_to": request.url.path + (f"?{request.url.query}" if request.url.query else ""),
        },
    )


@router.get("/conteo", response_class=HTMLResponse)
async def pagina_conteo_personas(
    request: Request,
    perfil_id: str = "",
    return_to: str = "",
    scroll_y: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    selected_profile_id = _optional_positive_id(perfil_id, "perfil_id")
    perfiles = await listar_perfiles_vulnerabilidad(db)
    profile_ids = {perfil["id"] for perfil in perfiles}
    if selected_profile_id not in profile_ids:
        selected_profile_id = None
    conteos = await contar_por_consejo(db, selected_profile_id)
    total_edad_perfil_0_3 = (
        sum(row.get("personas_perfil_0_3") or 0 for row in conteos)
        if selected_profile_id == 5
        else None
    )
    total_edad_perfil_0_5 = (
        sum(row.get("personas_perfil_0_5") or 0 for row in conteos)
        if selected_profile_id == 5
        else None
    )
    total_edad_ci_0_3 = (
        sum(row.get("personas_ci_0_3") or 0 for row in conteos)
        if selected_profile_id == 5
        else None
    )
    total_edad_ci_0_5 = (
        sum(row.get("personas_ci_0_5") or 0 for row in conteos)
        if selected_profile_id == 5
        else None
    )
    total_edad_0_7 = (
        sum(row.get("personas_perfil_0_7") or 0 for row in conteos)
        if selected_profile_id in {6, 7}
        else None
    )
    total_edad_8_13 = (
        sum(row.get("personas_perfil_8_13") or 0 for row in conteos)
        if selected_profile_id in {6, 7}
        else None
    )
    return templates.TemplateResponse(
        "nucleo/conteo.html",
        {
            "request": request,
            "perfiles": perfiles,
            "perfil_id": selected_profile_id,
            "perfil_seleccionado": next(
                (perfil for perfil in perfiles if perfil["id"] == selected_profile_id),
                None,
            ),
            "return_to": _safe_list_return_to(return_to),
            "scroll_y": scroll_y,
            "conteos": conteos,
            "total_nucleos": sum(row["nucleos"] for row in conteos),
            "total_personas": sum(row["personas"] for row in conteos),
            "total_nucleos_proceden": sum(row["nucleos_proceden"] for row in conteos),
            "total_nucleos_no_proceden": sum(row["nucleos_no_proceden"] for row in conteos),
            "total_nucleos_sin_procesar": sum(row["nucleos_sin_procesar"] for row in conteos),
            "total_nucleos_perfil": (
                sum(row["nucleos_perfil"] for row in conteos)
                if selected_profile_id is not None
                else None
            ),
            "total_personas_perfil": (
                sum(row["personas_perfil"] for row in conteos)
                if selected_profile_id is not None
                else None
            ),
            "total_edad_perfil_0_3": total_edad_perfil_0_3,
            "total_edad_perfil_0_5": total_edad_perfil_0_5,
            "total_edad_ci_0_3": total_edad_ci_0_3,
            "total_edad_ci_0_5": total_edad_ci_0_5,
            "total_edad_0_7": total_edad_0_7,
            "total_edad_8_13": total_edad_8_13,
        },
    )


@router.get("/{nucleo_id}", response_class=HTMLResponse)
async def formulario_consulta(
    request: Request,
    nucleo_id: int,
    return_to: str = "",
    guardado: bool = False,
    db: AsyncSession = Depends(get_db),
):
    nucleo = await obtener_nucleo(db, nucleo_id)
    if nucleo is None:
        raise HTTPException(status_code=404, detail="Núcleo no encontrado")
    cat = await cargar_catalogos(db)
    return templates.TemplateResponse(
        "nucleo/form.html",
        {
            "request": request,
            "catalogos": cat,
            "catalogos_json": catalogos_a_json(cat),
            "modo": "consulta",
            "nucleo": nucleo,
            "return_to": _safe_list_return_to(return_to),
            "guardado": guardado,
        },
    )


@router.get("/api/listado", response_class=JSONResponse)
async def api_listado(db: AsyncSession = Depends(get_db)):
    return await listar_nucleos(db)


@router.get("/api/ultimo-codigo", response_class=JSONResponse)
async def api_ultimo_codigo(db: AsyncSession = Depends(get_db)):
    return {"codigo": await obtener_ultimo_codigo_nucleo(db)}


@router.get("/api/{nucleo_id}")
async def api_obtener(nucleo_id: int, db: AsyncSession = Depends(get_db)):
    nucleo = await obtener_nucleo(db, nucleo_id)
    if nucleo is None:
        raise HTTPException(status_code=404, detail="Núcleo no encontrado")
    return nucleo


@router.post("", response_model=NucleoOut, status_code=201)
async def guardar_nucleo(payload: NucleoIn, db: AsyncSession = Depends(get_db)):
    try:
        hogar = await crear_nucleo(db, payload)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=_integrity_error_message(exc, payload.codigo)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo guardar el núcleo. Intente nuevamente.") from exc
    return NucleoOut(id=hogar.id, codigo=hogar.codigo)


@router.put("/{nucleo_id}", response_model=NucleoOut)
async def editar_nucleo(nucleo_id: int, payload: NucleoIn, db: AsyncSession = Depends(get_db)):
    try:
        hogar = await actualizar_nucleo(db, nucleo_id, payload)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=_integrity_error_message(exc, payload.codigo)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo guardar el núcleo. Intente nuevamente.") from exc
    if hogar is None:
        raise HTTPException(status_code=404, detail="Núcleo no encontrado")
    return NucleoOut(id=hogar.id, codigo=hogar.codigo)


@router.delete("/{nucleo_id}", status_code=204)
async def borrar_nucleo(nucleo_id: int, db: AsyncSession = Depends(get_db)):
    if not await eliminar_nucleo(db, nucleo_id):
        raise HTTPException(status_code=404, detail="Núcleo no encontrado")