"""
tests/test_extractor_pdf.py
===========================
Tests para Proyecto/extractor_pdf.py.
"""
import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch
from Proyecto.extractor_pdf import (
    extraer_color_fondo,
    extraer_info_profesor,
    ajustar_bloque,
    obtener_filas_horas,
    procesar_pagina,
    procesar_todo_automaticamente,
    COLUMNAS_X,
    COLUMNA_HORAS_X,
)


class TestExtractorPDF(unittest.TestCase):

    # --- extraer_info_profesor ---

    def test_extraer_info_profesor_formato_normal(self):
        mock_page = MagicMock()
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = "PEREZ GARCIA, JUAN (INF_01)"
        mock_page.crop.return_value = mock_crop
        nombre, codigo = extraer_info_profesor(mock_page)
        self.assertEqual(nombre, "PEREZ GARCIA, JUAN")
        self.assertEqual(codigo, "INF_01")

    def test_extraer_info_profesor_anonimizado(self):
        """Formato 'Profesor 001' debe devolver código PROF001."""
        mock_page = MagicMock()
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = "Profesor 001"
        mock_page.crop.return_value = mock_crop
        nombre, codigo = extraer_info_profesor(mock_page)
        self.assertEqual(nombre, "Profesor 001")
        self.assertEqual(codigo, "PROF001")

    def test_extraer_info_profesor_sin_texto(self):
        mock_page = MagicMock()
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = None
        mock_page.crop.return_value = mock_crop
        nombre, codigo = extraer_info_profesor(mock_page)
        self.assertEqual(nombre, "Desconocido")
        self.assertEqual(codigo, "N/A")

    def test_extraer_info_profesor_fallback_sin_parentesis(self):
        """Nombre sin paréntesis: genera código sintético."""
        mock_page = MagicMock()
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = "LOPEZ MARTINEZ"
        mock_page.crop.return_value = mock_crop
        nombre, codigo = extraer_info_profesor(mock_page)
        self.assertEqual(nombre, "LOPEZ MARTINEZ")
        self.assertEqual(codigo, "LOPEZMARTI")

    def test_extraer_info_profesor_excepcion(self):
        mock_page = MagicMock()
        mock_page.crop.side_effect = Exception("boom")
        nombre, codigo = extraer_info_profesor(mock_page)
        self.assertEqual(nombre, "Error Lectura")
        self.assertEqual(codigo, "ERR")

    # --- ajustar_bloque ---

    @patch('Proyecto.extractor_pdf.sumar_55_minutos')
    def test_ajustar_bloque_misma_hora(self, mock_sumar):
        mock_sumar.return_value = "09:55"
        bloque = {"asignatura": "X", "hora_inicio": "09:00", "hora_fin": "09:00"}
        resultado = ajustar_bloque(bloque)
        self.assertEqual(resultado["hora_fin"], "09:55")
        mock_sumar.assert_called_with("09:00")

    def test_ajustar_bloque_horas_diferentes(self):
        bloque = {"asignatura": "X", "hora_inicio": "09:00", "hora_fin": "10:00"}
        resultado = ajustar_bloque(bloque)
        self.assertEqual(resultado["hora_fin"], "10:00")

    def test_ajustar_bloque_none(self):
        self.assertIsNone(ajustar_bloque(None))

    def test_ajustar_bloque_vacio(self):
        bloque = {}
        resultado = ajustar_bloque(bloque)
        self.assertEqual(resultado, {})

    # --- extraer_color_fondo ---

    def test_extraer_color_fondo_celda_con_rects(self):
        mock_crop = MagicMock()
        mock_crop.width = 100
        mock_crop.height = 40
        inner = MagicMock()
        inner.width = 96
        inner.height = 36
        # El rect debe ser > 30% del área de la celda interna
        inner.rects = [
            {"width": 96, "height": 36, "non_stroking_color": (0.5, 0.3, 0.8)}
        ]
        inner.curves = []
        mock_crop.crop.return_value = inner
        color = extraer_color_fondo(mock_crop)
        self.assertEqual(color, (0.5, 0.3, 0.8))

    def test_extraer_color_fondo_rect_diminuto(self):
        """Rect demasiado pequeño (< 30% del area) debe ser ignorado."""
        mock_crop = MagicMock()
        mock_crop.width = 100
        mock_crop.height = 40
        inner = MagicMock()
        inner.width = 96
        inner.height = 36
        # Area interna = 96*36 = 3456. Area minima 30% = 1037. Rect area = 5*5 = 25
        inner.rects = [
            {"width": 5, "height": 5, "non_stroking_color": (0.5, 0.5, 0.5)}
        ]
        inner.curves = []
        mock_crop.crop.return_value = inner
        color = extraer_color_fondo(mock_crop)
        self.assertIsNone(color)

    def test_extraer_color_fondo_celda_blanca(self):
        mock_crop = MagicMock()
        mock_crop.width = 100
        mock_crop.height = 40
        inner = MagicMock()
        inner.width = 96
        inner.height = 36
        inner.rects = [
            {"width": 96, "height": 36, "non_stroking_color": (1.0, 1.0, 1.0)}
        ]
        inner.curves = []
        mock_crop.crop.return_value = inner
        color = extraer_color_fondo(mock_crop)
        self.assertIsNone(color)

    def test_extraer_color_fondo_sin_rects_con_curves(self):
        mock_crop = MagicMock()
        mock_crop.width = 100
        mock_crop.height = 40
        inner = MagicMock()
        inner.width = 96
        inner.height = 36
        inner.rects = []
        inner.curves = [{"fill": True, "non_stroking_color": (0.3, 0.7, 0.2)}]
        mock_crop.crop.return_value = inner
        color = extraer_color_fondo(mock_crop)
        self.assertEqual(color, (0.3, 0.7, 0.2))

    def test_extraer_color_fondo_sin_nada(self):
        mock_crop = MagicMock()
        mock_crop.width = 100
        mock_crop.height = 40
        inner = MagicMock()
        inner.width = 96
        inner.height = 36
        inner.rects = []
        inner.curves = []
        mock_crop.crop.return_value = inner
        color = extraer_color_fondo(mock_crop)
        self.assertIsNone(color)

    def test_extraer_color_fondo_excepcion(self):
        mock_crop = MagicMock()
        mock_crop.width = 100
        mock_crop.height = 40
        mock_crop.crop.side_effect = Exception("crash")
        color = extraer_color_fondo(mock_crop)
        self.assertIsNone(color)

    # --- obtener_filas_horas ---

    def test_obtener_filas_horas_sin_lineas(self):
        mock_page = MagicMock()
        mock_page.lines = []
        mock_page.height = 800
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = ""
        mock_page.crop.return_value = mock_crop
        filas = obtener_filas_horas(mock_page)
        self.assertEqual(filas, [])

    def test_obtener_filas_horas_excepcion(self):
        mock_page = MagicMock()
        mock_page.lines = None
        filas = obtener_filas_horas(mock_page)
        self.assertEqual(filas, [])

    # --- procesar_pagina ---

    @patch('Proyecto.extractor_pdf.extraer_info_profesor')
    @patch('Proyecto.extractor_pdf.obtener_filas_horas')
    def test_procesar_pagina_estructura(self, mock_filas, mock_info):
        mock_info.return_value = ("PROFESOR TEST", "COD123")
        mock_filas.return_value = [
            {'top': 100, 'bottom': 150, 'texto_hora': '08:00'}
        ]
        mock_page = MagicMock()
        mock_page.width = 600
        mock_page.height = 800
        mock_crop = MagicMock()
        mock_crop.extract_text.return_value = ""
        mock_page.crop.return_value = mock_crop
        resultado = procesar_pagina(mock_page)
        self.assertIsInstance(resultado, dict)
        self.assertIn("profesor", resultado)
        self.assertIn("eventos", resultado)
        self.assertIn("grupos", resultado)
        self.assertEqual(resultado["profesor"]["nombre"], "PROFESOR TEST")

    @patch('Proyecto.extractor_pdf.extraer_info_profesor')
    @patch('Proyecto.extractor_pdf.obtener_filas_horas')
    def test_procesar_pagina_sin_filas(self, mock_filas, mock_info):
        """Con 0 filas de hora, devuelve el dict interno (sin 'eventos')."""
        mock_info.return_value = ("PROF", "COD")
        mock_filas.return_value = []
        mock_page = MagicMock()
        mock_page.width = 600
        mock_page.height = 800
        resultado = procesar_pagina(mock_page)
        self.assertIsInstance(resultado, dict)
        self.assertEqual(resultado["profesor"], "PROF")
        # Devuelve formato interno con 'horario', no 'eventos'
        self.assertIn("horario", resultado)

    # --- procesar_todo_automaticamente ---

    def test_procesar_todo_carpeta_inexistente(self):
        result = procesar_todo_automaticamente("/ruta/que/no/existe")
        self.assertEqual(result, [])

    def test_procesar_todo_carpeta_sin_pdfs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = procesar_todo_automaticamente(tmpdir)
            self.assertEqual(result, [])

    def test_procesar_todo_con_pdf_corrupto(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ruta = os.path.join(tmpdir, "corrupto.pdf")
            with open(ruta, "w") as f:
                f.write("esto no es un PDF")
            result = procesar_todo_automaticamente(tmpdir)
            self.assertEqual(result, [])

    # --- Constantes ---

    def test_constantes_columnas(self):
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        for dia in dias:
            self.assertIn(dia, COLUMNAS_X)
            self.assertIsInstance(COLUMNAS_X[dia], tuple)
            self.assertTrue(COLUMNAS_X[dia][0] < COLUMNAS_X[dia][1])

    def test_columna_horas(self):
        self.assertEqual(COLUMNA_HORAS_X, (0, 80))

    # --- Test con archivo real (si existe) ---

    def test_procesar_pdf_real_si_existe(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(base_dir, "..", "data", "HORARIO.pdf")
        if os.path.exists(pdf_path):
            import pdfplumber
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if pdf.pages:
                        page = pdf.pages[0]
                        resultado = procesar_pagina(page)
                        self.assertIn("profesor", resultado)
                        self.assertIn("eventos", resultado)
                        if resultado["eventos"]:
                            evento = resultado["eventos"][0]
                            self.assertIn("dia", evento)
                            self.assertIn("asignatura", evento)
            except Exception as e:
                self.fail(f"El procesamiento del PDF real falló: {e}")
        else:
            print(f"\n⚠️ Salteando test de archivo real: No se encontró {pdf_path}")


if __name__ == '__main__':
    unittest.main()