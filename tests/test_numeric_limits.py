import unittest

from pydantic import ValidationError

from app.schemas import DiversidadIn, GastoIn


class NumericLimitsTests(unittest.TestCase):
    def test_accepts_expense_importance_bounds(self):
        for value in (1, 3):
            with self.subTest(value=value):
                self.assertEqual(
                    GastoIn(tipo_gasto_id=1, orden_importancia=value).orden_importancia,
                    value,
                )

    def test_rejects_expense_importance_outside_bounds(self):
        for value in (0, 4):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    GastoIn(tipo_gasto_id=1, orden_importancia=value)

    def test_accepts_food_frequency_bounds(self):
        for value in (0, 7):
            with self.subTest(value=value):
                self.assertEqual(
                    DiversidadIn(
                        grupo_alimento_id=1,
                        frecuencia_semanal_dias=value,
                    ).frecuencia_semanal_dias,
                    value,
                )

    def test_rejects_food_frequency_outside_bounds(self):
        for value in (-1, 8):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    DiversidadIn(
                        grupo_alimento_id=1,
                        frecuencia_semanal_dias=value,
                    )


if __name__ == "__main__":
    unittest.main()