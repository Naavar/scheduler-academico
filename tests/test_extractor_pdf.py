import unittest
import os
from unittest.mock import MagicMock, patch
from Proyecto.extractor_pdf import (
    extraer_info_profesor,
    ajustar_bloque,
    procesar_pagina,
    obtener_filas_horas,
    COLUMNAS_X
)


class TestExtractorPDF(unittest.TestCase):

    # 1. TEST PARA EXTRAER EL NOMBRE DEL PROFESOR
    def test_extraer_info_profesor(self):
        """Prueba que se extrae correctamente el nombre y código del encabezado."""
        mock_page = MagicMock()
        mock_crop = MagicMock()

        # Simulamos que el PDF tiene este texto en la cabecera
        mock_crop.extract_text.return_value = "PEREZ GARCIA, JUAN (INF_01)"
        mock_page.crop.return_value = mock_crop

        nombre, codigo = extraer_info_profesor(mock_page)

        self.assertEqual(nombre, "PEREZ GARCIA, JUAN")
        self.assertEqual(codigo, "INF_01")

    # 2. TEST PARA AJUSTAR BLOQUES (Lógica de 55 minutos)
    @patch('Proyecto.extractor_pdf.sumar_55_minutos')
    def test_ajustar_bloque(self, mock_sumar):
        """Si hora_inicio == hora_fin, debe sumar 55 minutos."""
        # Simulamos la función de utils
        mock_sumar.return_value = "09:55"

        bloque = {
            "asignatura": "PROG",
            "hora_inicio": "09:00",
            "hora_fin": "09:00"
        }

        resultado = ajustar_bloque(bloque)

        self.assertEqual(resultado["hora_fin"], "09:55")
        mock_sumar.assert_called_with("09:00")

    # 3. TEST DE CONSTANTES
    def test_constantes_columnas(self):
        """Verifica que las coordenadas de los días están definidas."""
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        for dia in dias:
            self.assertIn(dia, COLUMNAS_X)
            # Verifica que sea una tupla (x_inicio, x_fin)
            self.assertIsInstance(COLUMNAS_X[dia], tuple)
            self.assertTrue(COLUMNAS_X[dia][0] < COLUMNAS_X[dia][1])

    # 4. TEST INTEGRAL SIMULADO (Procesar página completa)
    @patch('Proyecto.extractor_pdf.extraer_info_profesor')
    @patch('Proyecto.extractor_pdf.obtener_filas_horas')
    def test_procesar_pagina_estructura(self, mock_filas, mock_info):
        """
        Simula una página completa para verificar que devuelve
        la estructura JSON correcta.
        """
        # Configuración de Mocks
        mock_info.return_value = ("PROFESOR TEST", "COD123")

        # Simulamos que el PDF detectó 1 fila de hora
        mock_filas.return_value = [
            {'top': 100, 'bottom': 150, 'texto_hora': '08:00'}
        ]

        mock_page = MagicMock()
        mock_page.width = 600
        mock_page.height = 800

        # Simulamos la extracción de texto de una celda
        # Haremos que devuelva texto vacío para que no falle lógica compleja de colores
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = ""
        mock_page.crop.return_value = mock_crop

        # Ejecución
        resultado = procesar_pagina(mock_page)

        # Verificaciones
        self.assertIsInstance(resultado, dict)
        self.assertIn("profesor", resultado)
        self.assertIn("eventos", resultado)
        self.assertEqual(resultado["profesor"]["nombre"], "PROFESOR TEST")
        self.assertIsInstance(resultado["eventos"], list)

    # 5. TEST CON ARCHIVO REAL (Si existe)
    def test_procesar_pdf_real_si_existe(self):
        """
        Intenta abrir el archivo data/HORARIO.pdf real si existe.
        Este test es útil para integración real.
        """
        # Construye la ruta al archivo real basándose en la ubicación del test
        base_dir = os.path.dirname(os.path.abspath(__file__))  # carpeta tests/
        pdf_path = os.path.join(base_dir, "..", "data", "HORARIO.pdf")

        if os.path.exists(pdf_path):
            import pdfplumber
            # Solo abrimos para ver si la función procesar_pagina no explota
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if pdf.pages:
                        page = pdf.pages[0]
                        resultado = procesar_pagina(page)

                        # Debe devolver al menos la estructura básica
                        self.assertIn("profesor", resultado)
                        self.assertIn("eventos", resultado)

                        # Si el PDF tiene contenido, verifica tipos
                        if resultado["eventos"]:
                            evento = resultado["eventos"][0]
                            self.assertIn("dia", evento)
                            self.assertIn("asignatura", evento)
            except Exception as e:
                self.fail(f"El procesamiento del PDF real falló con error: {e}")
        else:
            print(f"\n⚠️ Salteando test de archivo real: No se encontró {pdf_path}")


if __name__ == '__main__':
    unittest.main()