import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pdfplumber
from extractor_pdf import extraer_color_fondo, obtener_filas_horas, COLUMNAS_X
from utils import limpiar_texto, es_color_valido, es_color_gris_claro

pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "HORARIOS_25_26 - Docentes_anon.pdf")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[101]  # Prof 102
    filas = obtener_filas_horas(page)
    
    dia = "Viernes"
    x0, x1 = COLUMNAS_X[dia]
    print("=== Prof 102 %s ===" % dia)
    print("Column x range: %s - %s" % (x0, x1))
    print()
    
    # Show all rows
    for fila in filas:
        bbox = (x0, fila["top"], x1, fila["bottom"])
        celda = page.crop(bbox)
        texto = limpiar_texto(celda.extract_text() or "")
        color = extraer_color_fondo(celda)
        hora = fila["texto_hora"]
        print("  Hora: %-20s top=%-6.1f bot=%-6.1f | Texto: %-50s | Color: %s" % (
            hora, fila["top"], fila["bottom"], texto[:50], str(color)[:30] if color else "None"))
    
    print("\n=== Colored rects in Viernes column ===")
    # Find ALL rects in the Viernes column area
    # Get the full page area for this column
    full_bbox = (x0, 0, x1, page.height)
    col_crop = page.crop(full_bbox)
    for rect in col_crop.rects:
        c = rect.get("non_stroking_color")
        if c and es_color_valido(c):
            area = rect['width'] * rect['height']
            if area > 100:  # Skip tiny decorations
                print("  Rect: top=%-6.1f bot=%-6.1f h=%-5.1f w=%-5.1f color=%s" % (
                    rect['top'], rect['bottom'], rect['height'], rect['width'], str(c)[:30]))
