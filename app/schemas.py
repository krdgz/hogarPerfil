from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class OcupacionIn(BaseModel):
    tipo_ocupacion: str
    ocupacion_catalogo_id: int


class PersonaIn(BaseModel):
    perfil_id: Optional[int] = None
    nombre_apellidos: str = ""
    cedula: Optional[str] = None
    color_piel_id: Optional[int] = None
    parentesco_id: Optional[int] = None
    sexo_id: Optional[int] = None
    nivel_escolaridad_id: Optional[int] = None
    vinculacion_sne_id: Optional[int] = None
    esta_en_registro_consumidor: Optional[bool] = None
    fuente_ingreso_id: Optional[int] = None
    ingreso_mensual_cup: Optional[Decimal] = None

    trabaja: Optional[bool] = None
    tipo_ocupacion: Optional[str] = None
    ocupacion_catalogo_id: Optional[int] = None
    motivo_no_trabaja_id: Optional[int] = None
    ocupaciones: List[OcupacionIn] = Field(default_factory=list)

    @field_validator("cedula", mode="before")
    @classmethod
    def validar_cedula(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("El carné debe contener exactamente 11 números o dejarse vacío.")
        value = value.strip()
        if value == "":
            return None
        if re.fullmatch(r"[0-9]{11}", value) is None:
            raise ValueError("El carné debe contener exactamente 11 números o dejarse vacío.")
        return value


class GastoIn(BaseModel):
    tipo_gasto_id: int
    monto_cup: Decimal = Decimal("0")
    orden_importancia: Optional[int] = Field(default=None, ge=1, le=3)


class DiversidadIn(BaseModel):
    grupo_alimento_id: int
    gusta: Optional[bool] = None
    encontrado_en_mercado: Optional[bool] = None
    frecuencia_semanal_dias: int = Field(default=0, ge=0, le=7)


class EstrategiaIn(BaseModel):
    estrategia_id: int
    aplica: bool = False


class NucleoIn(BaseModel):
    codigo: str
    fecha_entrevista: Optional[date] = None
    entrevistador_nombre: Optional[str] = None
    provincia_id: int
    municipio_id: int
    consejo_popular_id: int
    circunscripcion_id: Optional[int] = None
    bodega_id: Optional[int] = None
    circunscripcion_codigo: Optional[str] = None
    bodega_codigo: Optional[str] = None
    zona_residencia_id: int
    direccion: Optional[str] = None
    procede_ayuda: Optional[bool] = None
    observaciones: Optional[str] = None

    personas: List[PersonaIn] = Field(default_factory=list)
    gastos: List[GastoIn] = Field(default_factory=list)
    diversidad: List[DiversidadIn] = Field(default_factory=list)
    estrategias: List[EstrategiaIn] = Field(default_factory=list)


class NucleoOut(BaseModel):
    id: int
    codigo: str


class EstadoNucleoIn(BaseModel):
    procede_ayuda: Optional[bool]