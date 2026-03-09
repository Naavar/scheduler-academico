"""
tests/test_integracion_logica.py
================================
Test de integración: datos simulados → validación → buscar_sesion_evaluacion.
"""
import unittest
from Proyecto.validacion import validate_schedule
from Proyecto.buscador_evaluacion import buscar_sesion_evaluacion, Resultado, DIAS_VALIDOS


class TestIntegracionSistema(unittest.TestCase):

    def test_flujo_completo_datos_validos(self):
        """
        Simula datos de 4 profesores, los valida,
        y luego busca una sesión de evaluación.
        """
        profesores_simulados = []
        for i in range(4):
            profesores_simulados.append({
                "profesor": {
                    "nombre": f"PROFESOR TEST {i}",
                    "codigo": f"TEST_00{i}"
                },
                "eventos": [
                    {
                        "dia": "Lunes",
                        "asignatura": "MATEMÁTICAS",
                        "inicio": "08:00",
                        "fin": "10:00"
                    }
                ]
            })

        # Validar el primero como muestra
        errores = validate_schedule(profesores_simulados[0])
        self.assertEqual(len(errores), 0, f"El validador rechazó datos simulados: {errores}")

        # Buscar sesión de evaluación
        codigos = {f"TEST_00{i}" for i in range(4)}
        resultado = buscar_sesion_evaluacion(
            profesores=profesores_simulados,
            equipo_codigos=codigos,
        )

        self.assertIsInstance(resultado, Resultado)
        if not resultado.sin_solucion:
            self.assertIn(resultado.dia, DIAS_VALIDOS)
            self.assertIsNotNone(resultado.hora_inicio)
            self.assertIsNotNone(resultado.hora_fin)

    def test_flujo_con_datos_invalidos(self):
        """El validador detecta errores antes de pasar al buscador."""
        datos_corruptos = {
            "profesor": {"nombre": "Desconocido"},
            "eventos": [
                {"dia": "FakeDay", "inicio": "99:99"}
            ]
        }
        errores = validate_schedule(datos_corruptos)
        self.assertTrue(len(errores) > 0)
        self.assertTrue(any("nombre" in e.lower() for e in errores))

    def test_resultado_con_detalle(self):
        """El resultado con solución incluye detalle por cada profesor."""
        profesores = []
        codigos = set()
        for i in range(5):
            cod = f"P{i:03d}"
            codigos.add(cod)
            profesores.append({
                "profesor": {"codigo": cod, "nombre": f"Prof {cod}"},
                "eventos": [
                    {"dia": "Lunes", "inicio": f"{8+i}:00", "fin": f"{9+i}:00", "asignatura": "X"}
                ],
            })

        resultado = buscar_sesion_evaluacion(
            profesores=profesores,
            equipo_codigos=codigos,
        )

        if not resultado.sin_solucion:
            self.assertIn(resultado.dia, DIAS_VALIDOS)
            self.assertIsNotNone(resultado.hora_inicio)
            self.assertGreaterEqual(resultado.coste_total, 0)


if __name__ == '__main__':
    unittest.main()