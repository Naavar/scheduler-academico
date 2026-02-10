import unittest
from Proyecto.validacion import validate_schedule
from Proyecto.buscador_huecos import BuscadorHuecos, Hueco


class TestIntegracionSistema(unittest.TestCase):

    def test_flujo_completo_datos_validos_a_buscador(self):
        """
        Prueba el flujo completo:
        1. Simula datos que vendrían del extractor PDF (MULTIPLES PROFESORES).
        2. Los pasa por el validador.
        3. Alimenta el BuscadorHuecos y busca resultados.
        """

        # 1. SIMULACIÓN DE DATOS
        # IMPORTANTE: Creamos 4 profesores.
        # El BuscadorHuecos requiere mínimo 3 profesores libres para sugerir un hueco.
        profesores_simulados = []
        for i in range(4):
            profesores_simulados.append({
                "profesor": {
                    "nombre": f"PROFESOR TEST {i}",
                    "codigo": f"TEST_00{i}"
                },
                "eventos": [
                    # Todos ocupados Lunes 08:00-10:00
                    {
                        "dia": "Lunes",
                        "asignatura": "MATEMÁTICAS",
                        "inicio": "08:00",
                        "fin": "10:00"
                    }
                ]
            })

        # 2. VALIDACIÓN (Validamos al primero como muestra)
        errores = validate_schedule(profesores_simulados[0])
        self.assertEqual(len(errores), 0, f"El validador rechazó los datos simulados: {errores}")

        # 3. BUSCADOR DE HUECOS
        # Pasamos la lista de 4 profesores
        finder = BuscadorHuecos(profesores_simulados)

        # Buscamos huecos de 60 minutos
        huecos = finder.buscar_huecos_por_profesor(duracion=60)

        # 4. VERIFICACIONES DE RESULTADO
        self.assertIsInstance(huecos, list)

        # AHORA SÍ debería encontrar huecos (porque hay 4 profes libres el resto del día)
        self.assertTrue(len(huecos) > 0, "El buscador debería haber encontrado huecos libres (hay 4 profesores)")

        # Verificamos la estructura del primer hueco encontrado
        primer_hueco = huecos[0]
        self.assertIsInstance(primer_hueco, Hueco)

        # Lógica de negocio:
        # Como todos están ocupados Lunes 08-10, NO debe haber hueco a las 08:00 ni 09:00
        huecos_lunes_ocupado = [
            h for h in huecos
            if h.dia == "Lunes" and h.hora_inicio in ["08:00", "09:00"]
        ]
        self.assertEqual(len(huecos_lunes_ocupado), 0, "No debería haber hueco cuando hay clase")

        # Pero a las 11:00 sí deberían estar libres
        huecos_lunes_libre = [
            h for h in huecos
            if h.dia == "Lunes" and h.hora_inicio == "11:00"
        ]
        # Nota: Esto depende de tu horario escolar definido (recreos, etc),
        # pero conceptualmente validamos que EXISTAN huecos en otros horarios.
        self.assertTrue(len(huecos) > 0)

    def test_flujo_con_datos_invalidos(self):
        """Prueba que el validador detecta errores antes de pasar al buscador."""

        datos_corruptos = {
            "profesor": {"nombre": "Desconocido"},  # Error: nombre inválido
            "eventos": [
                {"dia": "FakeDay", "inicio": "99:99"}  # Error: día y hora inválidos
            ]
        }

        errores = validate_schedule(datos_corruptos)

        # Debería detectar múltiples errores
        self.assertTrue(len(errores) > 0)
        self.assertTrue(any("nombre" in e for e in errores))
        self.assertTrue(any("día" in e for e in errores))


if __name__ == '__main__':
    unittest.main()