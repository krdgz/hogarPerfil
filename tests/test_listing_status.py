import unittest
from unittest.mock import AsyncMock, Mock
from decimal import Decimal

from sqlalchemy.dialects import postgresql

from app import models
from app.services.nucleo_service import (
    PERFIL_SIN_PERFIL,
    _consulta_listado_nucleos,
    actualizar_estado_nucleo,
    calcular_promedio_ingresos_nucleo,
)


class ListingStatusTests(unittest.IsolatedAsyncioTestCase):
    def test_sin_perfil_filter_matches_nuclei_without_any_profile(self):
        sql = str(
            _consulta_listado_nucleos(perfil_id=PERFIL_SIN_PERFIL).compile(
                dialect=postgresql.dialect(),
            )
        )

        self.assertIn("NOT (EXISTS", sql)
        self.assertIn("persona.hogar_id = hogar_nucleo.id", sql)

    def test_status_filters_match_each_tri_state(self):
        expected = {
            "procede": ("procede_ayuda IS true", "catalogo_perfil_vulnerabilidad.codigo = "),
            "no_procede": ("procede_ayuda IS false", "NOT (EXISTS"),
            "pendiente": ("procede_ayuda IS NULL", "NOT (EXISTS"),
        }

        for status, conditions in expected.items():
            with self.subTest(status=status):
                sql = str(
                    _consulta_listado_nucleos(estado=status).compile(
                        dialect=postgresql.dialect(),
                    )
                )
                for condition in conditions:
                    self.assertIn(condition, sql)
                if status == "procede":
                    self.assertIn(" OR (EXISTS", sql)

    def test_age_range_requires_a_matching_person_with_valid_age(self):
        sql = str(
            _consulta_listado_nucleos(edad_min=20, edad_max=30).compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        self.assertIn("EXISTS (SELECT persona.id", sql)
        self.assertIn("persona.hogar_id = hogar_nucleo.id", sql)
        self.assertIn("make_date", sql)
        self.assertIn(">= 20", sql)
        self.assertIn("<= 30", sql)

    async def test_updates_only_status_and_commits(self):
        for status in (True, False, None):
            with self.subTest(status=status):
                db = AsyncMock()
                hogar = models.HogarNucleo(id=7, codigo="N-7", procede_ayuda=False)
                db.get.return_value = hogar
                db.scalar.return_value = False

                result = await actualizar_estado_nucleo(db, 7, status)

                self.assertIs(result, hogar)
                self.assertIs(hogar.procede_ayuda, status)
                db.commit.assert_awaited_once()

    async def test_profile_one_is_forced_to_proceed(self):
        db = AsyncMock()
        hogar = models.HogarNucleo(id=7, codigo="N-7", procede_ayuda=None)
        db.get.return_value = hogar
        db.scalar.return_value = True

        result = await actualizar_estado_nucleo(db, 7, None)

        self.assertIs(result.procede_ayuda, True)
        db.commit.assert_awaited_once()

    async def test_calculates_only_requested_nucleus_average_in_one_query(self):
        db = AsyncMock()
        db.execute.return_value = Mock(
            one_or_none=Mock(
                return_value=(
                    12,
                    Decimal("8000.00"),
                    2,
                )
            )
        )

        result = await calcular_promedio_ingresos_nucleo(db, 12)

        self.assertEqual(
            result,
            {"promedio": 4000.0, "cantidad_personas": 2},
        )
        db.execute.assert_awaited_once()
        sql = str(db.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn("hogar_nucleo.id =", sql)
        self.assertIn("persona.ingreso_mensual_cup >", sql)


if __name__ == "__main__":
    unittest.main()