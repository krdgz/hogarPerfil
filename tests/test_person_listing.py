import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy.dialects import postgresql

from app import models
from app.services.nucleo_service import (
    _consulta_listado_personas,
    listar_personas_listado,
)


class PersonListingTests(unittest.IsolatedAsyncioTestCase):
    def test_query_filters_profiles_and_age_per_person(self):
        sql = str(
            _consulta_listado_personas(
                perfil_id=3,
                edad_min=18,
                edad_max=65,
            ).compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        self.assertIn("persona.id", sql)
        self.assertIn("persona.cedula", sql)
        self.assertIn("persona_vulnerabilidad.perfil_vulnerabilidad_id = 3", sql)
        self.assertIn(">= 18", sql)
        self.assertIn("<= 65", sql)
        self.assertIn("bodega.codigo", sql)

    async def test_listing_returns_one_person_with_profile_and_warehouse(self):
        persona = models.Persona(
            id=17,
            nombre_apellidos="Ana Pérez",
            cedula="90010112345",
        )
        row = SimpleNamespace(
            Persona=persona,
            nucleo_id=4,
            codigo="N-4",
            provincia="Provincia",
            municipio="Municipio",
            consejo="Consejo",
            direccion="Calle 1",
            circunscripcion="2",
            bodega=15,
            procede=True,
            tiene_perfil_1=False,
            sexo="Femenino",
        )
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(all=lambda: [row]),
            SimpleNamespace(all=lambda: [(17, "Perfil", 3)]),
        ]

        result = await listar_personas_listado(db, limit=50)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["nombre_apellidos"], "Ana Pérez")
        self.assertEqual(result[0]["perfil_resumen"], "Perfil (3)")
        self.assertEqual(result[0]["bodega"], 15)
        self.assertEqual(result[0]["sexo"], "F")


if __name__ == "__main__":
    unittest.main()