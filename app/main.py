from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .printing.router import router as printing_router
from .routers import nucleo

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Caracterización de Hogares")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount(
    "/print-static",
    StaticFiles(directory=BASE_DIR / "printing" / "static"),
    name="print_static",
)
app.include_router(nucleo.router)
app.include_router(printing_router)


@app.get("/")
async def root():
    return {"msg": "OK", "form": "/nucleos/nuevo"}