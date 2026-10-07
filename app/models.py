from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False)


# ============ CATÁLOGOS ============

class Provincia(Base, TimestampMixin):
    __tablename__ = "provincia"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)


class Municipio(Base, TimestampMixin):
    __tablename__ = "municipio"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    provincia_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("provincia.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("provincia_id", "codigo"),
        UniqueConstraint("provincia_id", "nombre"),
    )


class ConsejoPopular(Base, TimestampMixin):
    __tablename__ = "consejo_popular"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    municipio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("municipio.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("municipio_id", "codigo"),
        UniqueConstraint("municipio_id", "nombre"),
    )


class Circunscripcion(Base, TimestampMixin):
    __tablename__ = "circunscripcion"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[Optional[str]] = mapped_column(Text)
    consejo_popular_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consejo_popular.id"), nullable=False)
    __table_args__ = (UniqueConstraint("consejo_popular_id", "codigo"),)


class ZonaResidencia(Base, TimestampMixin):
    __tablename__ = "zona_residencia"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class Bodega(Base, TimestampMixin):
    __tablename__ = "bodega"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[Optional[str]] = mapped_column(Text)
    consejo_popular_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consejo_popular.id"), nullable=False)
    __table_args__ = (UniqueConstraint("consejo_popular_id", "codigo"),)


class CatalogoPerfilVulnerabilidad(Base, TimestampMixin):
    __tablename__ = "catalogo_perfil_vulnerabilidad"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoColorPiel(Base, TimestampMixin):
    __tablename__ = "catalogo_color_piel"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoParentesco(Base, TimestampMixin):
    __tablename__ = "catalogo_parentesco"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoSexo(Base, TimestampMixin):
    __tablename__ = "catalogo_sexo"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoNivelEscolaridad(Base, TimestampMixin):
    __tablename__ = "catalogo_nivel_escolaridad"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoVinculacionSNE(Base, TimestampMixin):
    __tablename__ = "catalogo_vinculacion_sne"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoFuenteIngreso(Base, TimestampMixin):
    __tablename__ = "catalogo_fuente_ingreso"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoSectorEstatal(Base, TimestampMixin):
    __tablename__ = "catalogo_sector_estatal"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoEmpresaMixta(Base, TimestampMixin):
    __tablename__ = "catalogo_empresa_mixta"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoSectorAgropecuario(Base, TimestampMixin):
    __tablename__ = "catalogo_sector_agropecuario"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoSectorNoEstatal(Base, TimestampMixin):
    __tablename__ = "catalogo_sector_no_estatal"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoTrabajoInformal(Base, TimestampMixin):
    __tablename__ = "catalogo_trabajo_informal"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoMotivoNoTrabaja(Base, TimestampMixin):
    __tablename__ = "catalogo_motivo_no_trabaja"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoTipoGastoPrincipal(Base, TimestampMixin):
    __tablename__ = "catalogo_tipo_gasto_principal"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoGrupoAlimento(Base, TimestampMixin):
    __tablename__ = "catalogo_grupo_alimento"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class CatalogoEstrategiaAfrontamiento(Base, TimestampMixin):
    __tablename__ = "catalogo_estrategia_afrontamiento"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


# ============ HOGAR / NÚCLEO ============

class HogarNucleo(Base, TimestampMixin):
    __tablename__ = "hogar_nucleo"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(Text)
    fecha_entrevista: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    entrevistador_nombre: Mapped[Optional[str]] = mapped_column(Text)
    provincia_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("provincia.id"), nullable=False)
    municipio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("municipio.id"), nullable=False)
    consejo_popular_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consejo_popular.id"), nullable=False)
    circunscripcion_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("circunscripcion.id"))
    bodega_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("bodega.id"))
    zona_residencia_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("zona_residencia.id"), nullable=False)
    procede_ayuda: Mapped[Optional[bool]] = mapped_column(Boolean)
    observaciones: Mapped[Optional[str]] = mapped_column(Text)

    personas: Mapped[list["Persona"]] = relationship(back_populates="hogar", cascade="all, delete-orphan")
    gastos: Mapped[list["GastoHogar"]] = relationship(cascade="all, delete-orphan")
    diversidad: Mapped[list["DiversidadAlimentariaHogar"]] = relationship(cascade="all, delete-orphan")
    estrategias: Mapped[list["EstrategiaAfrontamientoHogar"]] = relationship(cascade="all, delete-orphan")


class GastoHogar(Base, TimestampMixin):
    __tablename__ = "gasto_hogar"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    hogar_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hogar_nucleo.id"), nullable=False)
    tipo_gasto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("catalogo_tipo_gasto_principal.id"), nullable=False)
    monto_cup: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    orden_importancia: Mapped[Optional[int]] = mapped_column(SmallInteger)
    __table_args__ = (UniqueConstraint("hogar_id", "tipo_gasto_id"),)


class DiversidadAlimentariaHogar(Base, TimestampMixin):
    __tablename__ = "diversidad_alimentaria_hogar"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    hogar_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hogar_nucleo.id"), nullable=False)
    grupo_alimento_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("catalogo_grupo_alimento.id"), nullable=False)
    gusta: Mapped[Optional[bool]] = mapped_column(Boolean)
    encontrado_en_mercado: Mapped[Optional[bool]] = mapped_column(Boolean)
    frecuencia_semanal_dias: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("hogar_id", "grupo_alimento_id"),)


class EstrategiaAfrontamientoHogar(Base, TimestampMixin):
    __tablename__ = "estrategia_afrontamiento_hogar"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    hogar_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hogar_nucleo.id"), nullable=False)
    estrategia_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("catalogo_estrategia_afrontamiento.id"), nullable=False)
    aplica: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    __table_args__ = (UniqueConstraint("hogar_id", "estrategia_id"),)


# ============ PERSONA ============

class Persona(Base, TimestampMixin):
    __tablename__ = "persona"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    hogar_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hogar_nucleo.id"), nullable=False)
    nombre_apellidos: Mapped[str] = mapped_column(Text, nullable=False)
    cedula: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    color_piel_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_color_piel.id"))
    parentesco_jefe_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_parentesco.id"))
    sexo_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_sexo.id"))
    nivel_escolaridad_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_nivel_escolaridad.id"))
    vinculacion_sne_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_vinculacion_sne.id"))
    esta_en_registro_consumidor: Mapped[Optional[bool]] = mapped_column(Boolean)
    fuente_ingreso_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_fuente_ingreso.id"))
    ingreso_mensual_cup: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    trabaja: Mapped[Optional[bool]] = mapped_column(Boolean)
    motivo_no_trabaja_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_motivo_no_trabaja.id"))
    __table_args__ = (UniqueConstraint("hogar_id", "cedula"),)

    hogar: Mapped[HogarNucleo] = relationship(back_populates="personas")


class PersonaVulnerabilidad(Base, TimestampMixin):
    __tablename__ = "persona_vulnerabilidad"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    persona_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("persona.id"), nullable=False)
    perfil_vulnerabilidad_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("catalogo_perfil_vulnerabilidad.id"), nullable=False)
    __table_args__ = (UniqueConstraint("persona_id", "perfil_vulnerabilidad_id"),)


class PersonaOcupacion(Base, TimestampMixin):
    __tablename__ = "persona_ocupacion"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    persona_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("persona.id"), nullable=False)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tipo_ocupacion: Mapped[str] = mapped_column(String(30), nullable=False)
    sector_estatal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_sector_estatal.id"))
    empresa_mixta_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_empresa_mixta.id"))
    sector_agropecuario_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_sector_agropecuario.id"))
    sector_no_estatal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_sector_no_estatal.id"))
    trabajo_informal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("catalogo_trabajo_informal.id"))
    __table_args__ = (
        CheckConstraint(
            "tipo_ocupacion IN ('sector_estatal','empresa_mixta','sector_agropecuario','sector_no_estatal','trabajo_informal')",
            name="chk_persona_ocupacion_tipo",
        ),
    )