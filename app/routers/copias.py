import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from ..services.copias_service import (
    crear_copia,
    restablecer_archivo,
)


router = APIRouter(prefix="/copias", tags=["copias"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["static_version"] = lambda: str(int(time.time()))


@router.get("", name="pagina_copias")
async def pagina_copias(request: Request, error: str = "", restaurado: str = ""):
    return templates.TemplateResponse(
        "copias/index.html",
        {"request": request, "error": error, "restaurado": restaurado},
    )


@router.post("/crear", name="crear_copia")
async def crear_copia_manual():
    try:
        archivo, nombre = await crear_copia()
        return FileResponse(
            path=archivo,
            filename=nombre,
            media_type="application/sql",
            background=BackgroundTask(lambda: archivo.unlink(missing_ok=True)),
        )
    except Exception as exc:
        detalle = str(exc).strip() or repr(exc)
        print("ERROR AL CREAR COPIA:", detalle)
        return await pagina_copias_redirect(error=detalle)


async def pagina_copias_redirect(nombre: str = "", error: str = ""):
    from urllib.parse import quote
    parametro = f"creado={quote(nombre)}" if nombre else f"error={quote(error)}"
    return RedirectResponse(url=f"/copias?{parametro}", status_code=303)


@router.post("/restaurar", name="restaurar_copia")
async def restaurar_copia(archivo: UploadFile = File(...), confirmar: str = Form(...)):
    if confirmar != "RESTABLECER":
        raise HTTPException(status_code=400, detail="Debe escribir RESTABLECER para confirmar.")

    nombre_original = Path(archivo.filename or "copia")
    if nombre_original.suffix.lower() not in {".sql", ".backup", ".dump"}:
        raise HTTPException(status_code=400, detail="Formato no permitido. Use .sql, .backup o .dump.")

    temporal = None
    try:
        with NamedTemporaryFile(delete=False, suffix=nombre_original.suffix.lower()) as destino:
            temporal = Path(destino.name)
            contenido = await archivo.read()
            destino.write(contenido)
        await restablecer_archivo(temporal)
    except Exception as exc:
        return await pagina_copias_redirect(error=str(exc))
    finally:
        await archivo.close()
        if temporal and temporal.exists():
            temporal.unlink()

    from urllib.parse import quote
    return RedirectResponse(url=f"/copias?restaurado={quote(nombre_original.name)}", status_code=303)
