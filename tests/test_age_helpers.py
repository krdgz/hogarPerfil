import unittest

from app.services.nucleo_service import edad_en_anos_desde_ci


class EdadDesdeCiTests(unittest.TestCase):
    def test_edad_en_anos_desde_ci_cubano_recién_nacido(self):
        self.assertEqual(edad_en_anos_desde_ci("26010112345"), 0)

    def test_edad_en_anos_desde_ci_cubano_nino_entre_0_y_3(self):
        self.assertEqual(edad_en_anos_desde_ci("23010112345"), 3)

    def test_edad_en_anos_desde_ci_cubano_adolescente_entre_8_y_13(self):
        self.assertEqual(edad_en_anos_desde_ci("13010112345"), 13)

    def test_edad_en_anos_desde_ci_datos_vacios(self):
        self.assertIsNone(edad_en_anos_desde_ci(""))
        self.assertIsNone(edad_en_anos_desde_ci(None))


if __name__ == "__main__":
    unittest.main()
