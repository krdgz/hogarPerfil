import os
import asyncio
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote


BASE_DIR = Path(__file__).resolve().parents[2]
BACKUPS_DIR = BASE_DIR / "backups"


def _database_config() -> dict[str, str]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "dbname": unquote(parsed.path.lstrip("/")),
            "user": unquote(parsed.username or "postgres"),
            "password": unquote(parsed.password or ""),
        }
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB", "hogares"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }


def _executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    common = Path(os.environ.get("ProgramFiles", "")) / "PostgreSQL"
    if common.exists():
        candidates = sorted(common.glob(f"*/bin/{name}.exe"), reverse=True)
        if candidates:
            return str(candidates[0])
    raise RuntimeError(f"No se encontró {name}. Instale PostgreSQL 16 o agregue sus herramientas al PATH.")


def _process_env(config: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]
    env["PGHOST"] = config["host"]
    env["PGPORT"] = config["port"]
    env["PGUSER"] = config["user"]
    env["PGDATABASE"] = config["dbname"]
    return env


def ensure_backups_dir() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR


def listar_copias() -> list[dict]:
    directorio = ensure_backups_dir()
    archivos = sorted(
        (item for item in directorio.iterdir() if item.is_file() and item.suffix.lower() in {".sql", ".backup", ".dump"}),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    resultado = []
    for item in archivos:
        stat = item.stat()
        resultado.append({
            "nombre": item.name,
            "tamaño": stat.st_size,
            "fecha": datetime.fromtimestamp(stat.st_mtime),
        })
    return resultado


async def crear_copia(prefix: str = "hogares") -> tuple[Path, str]:
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"{prefix}_{sello}.sql"
    archivo = Path(tempfile.gettempdir()) / nombre
    config = _database_config()
    comando = [
        _executable("pg_dump"),
        "--host", config["host"],
        "--port", config["port"],
        "--username", config["user"],
        "--dbname", config["dbname"],
        "--format=plain",
        "--encoding=UTF8",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--file", str(archivo),
    ]
    proceso = await asyncio.to_thread(
        subprocess.run,
        comando,
        capture_output=True,
        env=_process_env(config),
        check=False,
    )
    if proceso.returncode != 0:
        if archivo.exists():
            archivo.unlink()
        mensaje = proceso.stderr.decode("utf-8", errors="replace").strip() or proceso.stdout.decode("utf-8", errors="replace").strip()
        raise RuntimeError(mensaje or "No fue posible crear la copia de seguridad.")
    return archivo, archivo.name


async def crear_copia_temporal(prefijo: str) -> Path:
    archivo, _ = await crear_copia(prefijo)
    return archivo


async def restablecer_archivo(archivo: Path) -> str:
    if not archivo.is_file():
        raise ValueError("El archivo de copia no existe.")
    config = _database_config()
    extension = archivo.suffix.lower()

    if extension == ".sql":
        comando = [
            _executable("psql"),
            "--host", config["host"],
            "--port", config["port"],
            "--username", config["user"],
            "--dbname", config["dbname"],
            "--set", "ON_ERROR_STOP=1",
            "--file", str(archivo),
        ]
    elif extension in {".backup", ".dump"}:
        comando = [
            _executable("pg_restore"),
            "--host", config["host"],
            "--port", config["port"],
            "--username", config["user"],
            "--dbname", config["dbname"],
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            str(archivo),
        ]
    else:
        raise ValueError("Formato no permitido. Use archivos .sql, .backup o .dump.")

    proceso = await asyncio.to_thread(
        subprocess.run,
        comando,
        capture_output=True,
        env=_process_env(config),
        check=False,
    )
    salida = proceso.stderr.decode("utf-8", errors="replace").strip()
    if proceso.returncode != 0:
        raise RuntimeError(salida or proceso.stdout.decode("utf-8", errors="replace").strip() or "No fue posible restablecer la copia.")
    return salida


def obtener_copia(nombre: str) -> Path:
    directorio = ensure_backups_dir().resolve()
    candidato = (directorio / nombre).resolve()
    if candidato.parent != directorio or not candidato.is_file():
        raise FileNotFoundError("Copia no encontrada.")
    return candidato
