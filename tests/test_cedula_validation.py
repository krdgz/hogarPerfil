import unittest

from pydantic import ValidationError

from app.schemas import PersonaIn


class CedulaValidationTests(unittest.TestCase):
    def test_accepts_exactly_eleven_ascii_digits_and_preserves_leading_zeroes(self):
        self.assertEqual(PersonaIn(cedula="00123112345").cedula, "00123112345")

    def test_accepts_empty_cedula(self):
        self.assertIsNone(PersonaIn(cedula="").cedula)
        self.assertIsNone(PersonaIn(cedula=None).cedula)

    def test_rejects_letters_and_non_ascii_digits(self):
        for cedula in ("desdedw1234", "１２３４５６７８９０１"):
            with self.subTest(cedula=cedula):
                with self.assertRaises(ValidationError):
                    PersonaIn(cedula=cedula)

    def test_rejects_cedulas_with_wrong_length(self):
        for cedula in ("1234567890", "123456789012"):
            with self.subTest(cedula=cedula):
                with self.assertRaises(ValidationError):
                    PersonaIn(cedula=cedula)


if __name__ == "__main__":
    unittest.main()
