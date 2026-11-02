import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy.dialects import postgresql

from app.services.nucleo_service import (
    listar_nucleos_elegibles_impresion,
    listar_nucleos_por_consejo_impresion,
)


class EligiblePrintTests(unittest.IsolatedAsyncioTestCase):
    async def test_print_groups_include_council_municipality_and_province(self):
        row = SimpleNamespace(
            id=5,
            codigo="H-5",
            direccion="Calle 1",
            circunscripcion="3",
            bodega=7,
            consejo_id=2,
            consejo="Centro",
            municipio="Municipio A",
            provincia="Provincia B",
            procede_ayuda=None,
            tiene_perfil_1=True,
            perfil_codigo=1,
            perfil_nombre="Perfil Uno",
        )
        unprofiled_row = SimpleNamespace(
            id=6,
            codigo="H-6",
            direccion="Calle 2",
            circunscripcion=None,
            bodega=None,
            consejo_id=2,
            consejo="Centro",
            municipio="Municipio A",
            provincia="Provincia B",
            procede_ayuda=True,
            tiene_perfil_1=False,
            perfil_codigo=None,
            perfil_nombre=None,
        )
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(all=lambda: [row, unprofiled_row]),
            SimpleNamespace(all=lambda: [
                (5, "Ana", "12345678901", "Femenino"),
                (6, "Luis", "12345678902", "Masculino"),
            ]),
        ]

        result = await listar_nucleos_elegibles_impresion(db)

        sql = str(db.execute.await_args_list[0].args[0].compile(dialect=postgresql.dialect()))
        self.assertIn("JOIN municipio", sql)
        self.assertIn("JOIN provincia", sql)
        self.assertIn("LEFT OUTER JOIN", sql)
        self.assertIn("NOT (EXISTS", sql)
        self.assertIn("procede_ayuda IS true", sql)
        self.assertEqual(
            {key: result[0][key] for key in ("consejo", "municipio", "provincia")},
            {
                "consejo": "Centro",
                "municipio": "Municipio A",
                "provincia": "Provincia B",
            },
        )
        self.assertEqual(
            [grupo["perfil"]["nombre"] for grupo in result[0]["grupos"]],
            ["Perfil Uno", "Sin perfil"],
        )
        self.assertIs(result[0]["grupos"][0]["nucleos"][0]["procede"], True)
        self.assertEqual(result[0]["grupos"][0]["nucleos"][0]["personas"][0]["sexo"], "F")
        self.assertEqual(result[0]["grupos"][1]["nucleos"][0]["personas"][0]["sexo"], "M")

    async def test_all_nuclei_print_uses_effective_proceed_status(self):
        def row(nucleo_id, proceed, has_profile_one, profile_code, profile_name):
            return SimpleNamespace(
                id=nucleo_id,
                codigo=f"H-{nucleo_id}",
                direccion="Calle 1",
                circunscripcion="3",
                bodega=7,
                consejo_id=2,
                consejo="Centro",
                municipio="Municipio A",
                provincia="Provincia B",
                procede_ayuda=proceed,
                tiene_perfil_1=has_profile_one,
                perfil_codigo=profile_code,
                perfil_nombre=profile_name,
            )

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(all=lambda: [
                row(5, None, True, 1, "Perfil Uno"),
                row(5, None, True, 2, "Perfil Dos"),
                row(6, False, False, 3, "Perfil Tres"),
                row(7, None, False, None, None),
            ]),
            SimpleNamespace(all=lambda: [(5, "Ana", "12345678901", "Femenino")]),
        ]

        result = await listar_nucleos_por_consejo_impresion(db, consejo_id=2)

        grupos = {grupo["perfil"]["nombre"]: grupo["nucleos"] for grupo in result[0]["grupos"]}
        self.assertEqual([nucleo["procede"] for nucleo in grupos["Perfil Uno"]], [True])
        self.assertEqual([nucleo["procede"] for nucleo in grupos["Perfil Dos"]], [True])
        self.assertEqual([nucleo["procede"] for nucleo in grupos["Perfil Tres"]], [False])
        self.assertEqual([nucleo["procede"] for nucleo in grupos["Sin perfil"]], [None])
        self.assertEqual(grupos["Perfil Uno"][0]["personas"][0]["sexo"], "F")
        self.assertEqual(grupos["Perfil Uno"][0]["direccion_completa"], "Calle 1 - 3")
        self.assertEqual(grupos["Perfil Tres"][0]["personas"], [])


if __name__ == "__main__":
    unittest.main()