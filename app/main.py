from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import nucleo

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Caracterización de Hogares")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(nucleo.router)


@app.get("/")
async def root():
    return {"msg": "OK", "form": "/nucleos/nuevo"}