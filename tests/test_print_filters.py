import unittest

from app.printing.router import _filtrar_grupos_impresion


class PrintFilterTests(unittest.TestCase):
    def test_combined_profile_sex_state_and_search_filters(self):
        groups = [{
            "id": 2,
            "consejo": "Centro",
            "grupos": [
                {
                    "perfil": {"codigo": 4, "nombre": "Perfil cuatro"},
                    "nucleos": [
                        {
                            "codigo": "H-10",
                            "direccion": "Calle Norte",
                            "procede": True,
                            "personas": [
                                {"nombre": "Ana Pérez", "cedula": "123", "sexo": "F"},
                                {"nombre": "Luis Pérez", "cedula": "456", "sexo": "M"},
                            ],
                        },
                        {
                            "codigo": "H-11",
                            "direccion": "Calle Sur",
                            "procede": False,
                            "personas": [{"nombre": "Eva", "cedula": "789", "sexo": "F"}],
                        },
                    ],
                },
                {
                    "perfil": {"codigo": None, "nombre": "Sin perfil"},
                    "nucleos": [{
                        "codigo": "H-12",
                        "direccion": "Calle Norte",
                        "procede": None,
                        "personas": [{"nombre": "Nora", "cedula": "321", "sexo": None}],
                    }],
                },
            ],
        }]

        result = _filtrar_grupos_impresion(
            groups,
            perfil_codigo=4,
            sexo="F",
            estado="procede",
            busqueda="ana",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["grupos"]), 1)
        matching_nucleus = result[0]["grupos"][0]["nucleos"][0]
        self.assertEqual(matching_nucleus["codigo"], "H-10")
        self.assertEqual(len(matching_nucleus["personas"]), 2)

    def test_can_filter_unprofiled_households_with_missing_sex(self):
        groups = [{
            "grupos": [{
                "perfil": {"codigo": None, "nombre": "Sin perfil"},
                "nucleos": [{
                    "codigo": "H-12",
                    "procede": None,
                    "personas": [{"nombre": "Nora", "cedula": "321", "sexo": None}],
                }],
            }],
        }]

        result = _filtrar_grupos_impresion(
            groups,
            solo_sin_perfil=True,
            sexo="sin-sexo",
            estado="pendiente",
        )

        self.assertEqual(result[0]["grupos"][0]["nucleos"][0]["codigo"], "H-12")


if __name__ == "__main__":
    unittest.main()