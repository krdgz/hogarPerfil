import unittest

from app.services.nucleo_service import edad_en_anos_desde_ci, normalizar_rango_edad


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


class RangoEdadTests(unittest.TestCase):
    def test_normalizar_rango_edad_incluye_limites_inferior_y_superior(self):
        self.assertEqual(normalizar_rango_edad("0", "5"), (0, 5))

    def test_normalizar_rango_edad_siempre_ordena_limites(self):
        self.assertEqual(normalizar_rango_edad("12", "3"), (3, 12))

    def test_normalizar_rango_edad_ignora_valores_invalidos(self):
        self.assertEqual(normalizar_rango_edad("abc", ""), (None, None))


if __name__ == "__main__":
    unittest.main()
