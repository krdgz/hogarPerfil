import unittest
from unittest.mock import AsyncMock

from sqlalchemy.dialects import postgresql

from app import models
from app.services.nucleo_service import (
    _consulta_listado_nucleos,
    actualizar_estado_nucleo,
)


class ListingStatusTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()