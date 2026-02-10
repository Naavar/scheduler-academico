import unittest
import sys
import os

# Ajuste de ruta para poder ejecutarlo individualmente si fuera necesario
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Proyecto.validacion import validate_schedule


class TestValidacionExtractor(unittest.TestCase):

    def test_schedule_valido_completo(self):
        """Caso ideal: Un JSON con la estructura correcta (usa 'asignatura', no 'titulo')."""
        data = {
            "profesor": {"nombre": "GARCIA, PEPE", "codigo": "5555~A1"},
            "eventos": [
                {"dia": "Lunes", "inicio": "08:00", "fin": "10:00", "asignatura": "PROGRAMACIÓN"},
                {"dia": "Martes", "inicio": "15:00", "fin": "17:00", "asignatura": "DESARROLLO WEB"}
            ]
        }
        errors = validate_schedule(data)
        self.assertEqual(len(errors), 0, f"No debería haber errores en datos válidos: {errors}")

    def test_error_profesor_incompleto(self):
        """Valida mensajes de error específicos para profesor."""
        data = {
            "profesor": {"nombre": None, "codigo": None},  # Faltan datos
            "eventos": [{"dia": "Lunes", "inicio": "08:00", "fin": "09:00", "asignatura": "CLASE"}]
        }
        errors = validate_schedule(data)

        # Comprobamos los mensajes que realmente emite validacion.py
        self.assertTrue(any("Falta nombre" in e for e in errors))
        self.assertTrue(any("Falta código" in e for e in errors))

    def test_error_sin_eventos(self):
        """Valida el aviso de lista vacía."""
        data = {
            "profesor": {"nombre": "PEPE", "codigo": "123"},
            "eventos": []
        }
        errors = validate_schedule(data)
        self.assertTrue(any("vacía" in e for e in errors))

    def test_error_dia_invalido(self):
        """El extractor solo debe permitir días en DAY_NAMES (Lunes-Viernes)."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Sábado", "inicio": "08:00", "fin": "09:00", "asignatura": "ERROR"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("día inválido" in e for e in errors))

    def test_error_horas_invertidas(self):
        """Valida que la hora de fin no sea anterior o igual a la de inicio."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "10:00", "fin": "09:00", "asignatura": "TIEMPO LOCO"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("fin <= inicio" in e for e in errors))

    def test_error_formato_hora_corrupto(self):
        """Valida el regex de horas."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "8-00", "fin": "9:00", "asignatura": "ERROR"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("formato hora inválido" in e for e in errors))

    def test_error_falta_asignatura(self):
        """Un evento sin asignatura debe ser detectado."""
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "08:00", "fin": "09:00", "asignatura": ""}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("falta asignatura" in e for e in errors))


if __name__ == '__main__':
    unittest.main()