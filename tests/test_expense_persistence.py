import unittest
from unittest.mock import AsyncMock, Mock

from app import models
from app.schemas import GastoIn, NucleoIn
from app.services.nucleo_service import _guardar_nucleo


class ExpensePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def _saved_expenses(self, gasto):
        db = AsyncMock()
        db.add = Mock()
        db.scalar.return_value = None
        data = NucleoIn(
            codigo="TEST-1",
            provincia_id=1,
            municipio_id=1,
            consejo_popular_id=1,
            zona_residencia_id=1,
            gastos=[gasto],
        )
        hogar = models.HogarNucleo(id=1, codigo="TEST-1")

        await _guardar_nucleo(db, data, hogar=hogar)

        return [
            call.args[0]
            for call in db.add.call_args_list
            if isinstance(call.args[0], models.GastoHogar)
        ]

    async def test_persists_importance_order_without_amount(self):
        gastos = await self._saved_expenses(
            GastoIn(tipo_gasto_id=1, orden_importancia=2)
        )

        self.assertEqual(len(gastos), 1)
        self.assertEqual(gastos[0].monto_cup, 0)
        self.assertEqual(gastos[0].orden_importancia, 2)

    async def test_skips_expense_without_amount_or_importance_order(self):
        gastos = await self._saved_expenses(GastoIn(tipo_gasto_id=1))

        self.assertEqual(gastos, [])


if __name__ == "__main__":
    unittest.main()