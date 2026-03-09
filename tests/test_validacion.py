"""
tests/test_validacion.py
=========================
Tests para Proyecto/validacion.py.
"""
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Proyecto.validacion import validate_schedule, hhmm_to_minutes


class TestValidacionExtractor(unittest.TestCase):

    def test_schedule_valido_completo(self):
        """Caso ideal: Un JSON con la estructura correcta (usa 'asignatura')."""
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
            "profesor": {"nombre": None, "codigo": None},
            "eventos": [{"dia": "Lunes", "inicio": "08:00", "fin": "09:00", "asignatura": "CLASE"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("Falta nombre" in e for e in errors))

    def test_error_sin_eventos(self):
        """Valida el aviso de lista vacía."""
        data = {
            "profesor": {"nombre": "PEPE", "codigo": "123"},
            "eventos": []
        }
        errors = validate_schedule(data)
        self.assertTrue(any("vacía" in e for e in errors))

    def test_error_dia_invalido(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Sábado", "inicio": "08:00", "fin": "09:00", "asignatura": "ERROR"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("día inválido" in e for e in errors))

    def test_error_horas_invertidas(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "10:00", "fin": "09:00", "asignatura": "TIEMPO LOCO"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("fin <= inicio" in e for e in errors))

    def test_error_formato_hora_corrupto(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "8-00", "fin": "9:00", "asignatura": "ERROR"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("formato hora inválido" in e for e in errors))

    def test_error_falta_asignatura(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "08:00", "fin": "09:00", "asignatura": ""}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("falta asignatura" in e for e in errors))

    # --- Tests adicionales para cobertura ---

    def test_hhmm_to_minutes_normal(self):
        self.assertEqual(hhmm_to_minutes("08:00"), 480)
        self.assertEqual(hhmm_to_minutes("14:30"), 870)

    def test_hhmm_to_minutes_invalido(self):
        self.assertEqual(hhmm_to_minutes("invalid"), -1)
        self.assertEqual(hhmm_to_minutes("abc:def"), -1)

    def test_profesor_no_es_dict(self):
        data = {"profesor": "string_invalido", "eventos": []}
        errors = validate_schedule(data)
        self.assertTrue(any("objeto" in e for e in errors))

    def test_eventos_no_es_lista(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": "no_lista"
        }
        errors = validate_schedule(data)
        self.assertTrue(any("lista" in e for e in errors))

    def test_evento_sin_inicio_ni_fin(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": None, "fin": None, "asignatura": "X"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("falta hora" in e for e in errors))

    def test_evento_horas_iguales(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [{"dia": "Lunes", "inicio": "8:00", "fin": "8:00", "asignatura": "X"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("fin <= inicio" in e for e in errors))

    def test_profesor_anonimizado_valido(self):
        data = {
            "profesor": {"nombre": "Profesor 001", "codigo": "PROF001"},
            "eventos": [{"dia": "Lunes", "inicio": "8:00", "fin": "9:00", "asignatura": "X"}]
        }
        errors = validate_schedule(data)
        self.assertEqual(len(errors), 0)

    def test_profesor_desconocido(self):
        data = {
            "profesor": {"nombre": "Desconocido", "codigo": "N/A"},
            "eventos": [{"dia": "Lunes", "inicio": "8:00", "fin": "9:00", "asignatura": "X"}]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("nombre" in e.lower() for e in errors))

    def test_multiples_eventos_mixtos(self):
        data = {
            "profesor": {"nombre": "A", "codigo": "B"},
            "eventos": [
                {"dia": "Lunes", "inicio": "8:00", "fin": "9:00", "asignatura": "OK"},
                {"dia": "Sabado", "inicio": "8:00", "fin": "9:00", "asignatura": "MAL DIA"},
                {"dia": "Lunes", "inicio": "10:00", "fin": "9:00", "asignatura": "MAL HORA"},
            ]
        }
        errors = validate_schedule(data)
        self.assertTrue(any("día inválido" in e for e in errors))
        self.assertTrue(any("fin <= inicio" in e for e in errors))


if __name__ == '__main__':
    unittest.main()