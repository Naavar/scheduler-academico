import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Proyecto.validacion import validate_schedule

class TestValidacionExtractor(unittest.TestCase):

    def test_schedule_valido_completo(self):
        """Caso ideal: Un JSON extraído correctamente del PDF."""
        data = {
            "profesor": {"nombre": "GARCIA, PEPE", "codigo": "5555~A1"},
            "eventos": [
                {"dia": "Lunes", "turno": "mañana", "inicio": "08:00", "fin": "10:00", "titulo": "PROGRAMACIÓN"},
                {"dia": "Martes", "turno": "tarde", "inicio": "15:00", "fin": "17:00", "titulo": "DESARROLLO WEB"}
            ]
        }
        errors = validate_schedule(data)
        self.assertEqual(len(errors), 0, f"No debería haber errores en datos válidos: {errors}")

    def test_error_profesor_incompleto(self):
        """Valida que falle si el extractor no pudo parsear bien la cabecera del profesor."""
        data = {
            "profesor": {"nombre": None, "codigo": None},
            "eventos": [{"dia": "Lunes", "inicio": "08:00", "fin": "09:00", "titulo": "CLASE"}]
        }
        errors = validate_schedule(data)
        self.assertIn("Falta profesor.nombre", errors)
        self.assertIn("Falta profesor.codigo", errors)

    def test_error_sin_eventos(self):
        """Valida que falle si no se detectó ningún evento en el PDF."""
        data = {
            "profesor": {"nombre": "PEPE", "codigo": "123"},
            "eventos": []
        }
        errors = validate_schedule(data)
        self.assertIn("No hay eventos (eventos está vacío o no es lista)", errors)

    def test_error_dia_invalido(self):
        """El extractor solo debe permitir días en DAY_NAMES definido en validacion.py."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Sábado", "inicio": "08:00", "fin": "09:00", "titulo": "ERROR"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("dia inválido: Sábado" in e for e in errors))

    def test_error_horas_invertidas(self):
        """Valida que la hora de fin no sea anterior o igual a la de inicio."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "10:00", "fin": "09:00", "titulo": "TIEMPO LOCO"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("fin <= inicio" in e for e in errors))

    def test_error_formato_hora_corrupto(self):
        """Valida si el extractor devolvió basura en las horas."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "8-00", "fin": "9:00", "titulo": "ERROR"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("formato hora inválido" in e for e in errors))

    def test_error_falta_titulo(self):
        """Un evento sin título debe ser detectado."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "08:00", "fin": "09:00", "titulo": ""}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("falta titulo" in e for e in errors))

if __name__ == '__main__':
    unittest.main()