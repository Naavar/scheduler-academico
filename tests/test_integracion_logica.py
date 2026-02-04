import unittest
from Proyecto.extractor_pdf import extract_schedule
from Proyecto.validacion import validate_schedule
from Proyecto.buscador_huecos import BuscadorHuecos


class TestIntegracionSistema(unittest.TestCase):
    def test_flujo_completo_extractor_a_buscador(self):
        resultado_extractor = extract_schedule("data/HORARIO.pdf")

        errores = validate_schedule(resultado_extractor)
        self.assertEqual(len(errores), 0, f"El extractor generó datos inválidos: {errores}")

        finder = BuscadorHuecos([resultado_extractor])
        huecos = finder.buscar_huecos_por_profesor(duracion=60)

        self.assertIsInstance(huecos, list)
        if len(huecos) > 0:
            self.assertIn("dia", huecos[0].__dict__)