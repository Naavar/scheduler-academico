import pdfplumber
import re
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE COORDENADAS ---
COLUMNAS_X = {
    "Lunes": (80, 175),
    "Martes": (175, 270),
    "Miércoles": (270, 365),
    "Jueves": (365, 460),
    "Viernes": (460, 555),
}
COLUMNA_HORAS_X = (0, 80)


def es_color_valido(color):
    """Filtra colores de fondo (blancos/grises claros)"""
    if not color: return False
    r, g, b = color
    if r > 0.9 and g > 0.9 and b > 0.9:
        return False
    return True


def colores_son_iguales(c1, c2):
    # Si ambos son None, se consideran iguales
    if c1 is None and c2 is None:
        return True
    # Si solo uno es None, son diferentes
    if c1 is None or c2 is None:
        return False
    return all(abs(a - b) < 0.05 for a, b in zip(c1, c2))


def textos_son_similares(texto1, texto2):
    """
    Verifica si dos textos representan la misma asignatura.
    Útil para bloques sin color que deben agruparse.
    """
    if not texto1 or not texto2:
        return False

    # Normalizar textos
    t1 = texto1.lower().strip()
    t2 = texto2.lower().strip()

    # Si son idénticos
    if t1 == t2:
        return True

    # Para textos cortos (menos de 20 caracteres), deben ser idénticos
    if len(t1) < 20 or len(t2) < 20:
        return False

    # Para textos más largos, verificar si comparten un prefijo significativo
    # Pero también verificar que no sean completamente diferentes
    min_len = min(len(t1), len(t2))

    # Comparar primeros 20 caracteres (más estricto que antes)
    if min_len >= 20 and t1[:20] == t2[:20]:
        # Verificar que al menos el 70% de las palabras coincidan
        palabras1 = set(t1.split())
        palabras2 = set(t2.split())
        comunes = palabras1 & palabras2
        total = palabras1 | palabras2

        if len(total) > 0:
            similitud = len(comunes) / len(total)
            return similitud >= 0.7

    return False


def extraer_color_fondo(crop):
    if crop.width < 6 or crop.height < 6:
        crop_seguro = crop
    else:
        crop_seguro = crop.crop((2, 2, crop.width - 2, crop.height - 2), relative=True)

    rects = crop_seguro.rects
    color_encontrado = None

    if rects:
        rects.sort(key=lambda r: r['width'] * r['height'], reverse=True)
        for rect in rects:
            c = rect.get("non_stroking_color")
            if c and es_color_valido(c):
                color_encontrado = c
                break

    if not color_encontrado and hasattr(crop_seguro, 'curves'):
        for curve in crop_seguro.curves:
            if curve.get("fill"):
                c = curve.get("non_stroking_color")
                if c and es_color_valido(c):
                    color_encontrado = c
                    break
    return color_encontrado


def obtener_filas_horas(page):
    filas = []
    Y_INICIO_TABLA = 145

    lineas = [l['top'] for l in page.lines if l['width'] > 50]
    lineas.sort()

    lineas_filtradas = []
    if lineas:
        lineas_validas = [y for y in lineas if y > Y_INICIO_TABLA]
        if not lineas_validas: return []

        lineas_filtradas.append(Y_INICIO_TABLA + 2)
        for y in lineas_validas:
            if abs(y - lineas_filtradas[-1]) > 5:
                lineas_filtradas.append(y)

    if lineas_filtradas:
        if len(lineas_filtradas) >= 2:
            ultima_altura = lineas_filtradas[-1] - lineas_filtradas[-2]
        else:
            ultima_altura = 35

        linea_final_virtual = lineas_filtradas[-1] + ultima_altura
        lineas_filtradas.append(linea_final_virtual)

    crop_col_horas = page.crop((COLUMNA_HORAS_X[0], 0, COLUMNA_HORAS_X[1], page.height))

    for i in range(len(lineas_filtradas) - 1):
        top = lineas_filtradas[i]
        bottom = lineas_filtradas[i + 1]

        zona_hora = crop_col_horas.crop((0, top, crop_col_horas.width, bottom))
        texto = zona_hora.extract_text()
        texto_limpio = texto.replace('\n', ' ').strip() if texto else ""

        # Limpiar duplicaciones en el texto de hora
        if texto_limpio:
            texto_limpio = ' '.join(texto_limpio.split())
            horas = re.findall(r'\d{1,2}:\d{2}', texto_limpio)
            horas_unicas = []
            for hora in horas:
                if not horas_unicas or hora != horas_unicas[-1]:
                    horas_unicas.append(hora)
            if horas_unicas:
                texto_limpio = ' '.join(horas_unicas)

        if not texto_limpio:
            texto_limpio = f"[{top:.0f}-{bottom:.0f}]"

        filas.append({
            'top': top,
            'bottom': bottom,
            'texto_hora': texto_limpio
        })

    return filas


def limpiar_texto(txt):
    if not txt: return ""
    return " ".join(txt.split())


def es_hora_recreo(texto_hora, texto_celda=""):
    hora = texto_hora.lower()
    contenido = texto_celda.lower().strip()

    if "11:00" in hora and "11:30" in hora: return True
    if "18:05" in hora and "18:35" in hora: return True
    if contenido == "recreo": return True

    if hora.startswith('[') and hora.endswith(']'):
        try:
            coords = hora[1:-1].split('-')
            if len(coords) == 2:
                top = float(coords[0])
                bottom = float(coords[1])
                altura = bottom - top
                if altura < 25:
                    return True
        except:
            pass

    return False


def extraer_info_profesor(page):
    cabecera = page.crop((0, 0, page.width, 130))
    texto_cabecera = cabecera.extract_text()
    if not texto_cabecera:
        return "Desconocido", "N/A"
    texto_unido = limpiar_texto(texto_cabecera)
    match = re.search(r"([A-ZÁÉÍÓÚÑ, ]+)\s*\(([^)]+)\)", texto_unido)
    if match:
        nombre = match.group(1).strip()
        if nombre.startswith(","): nombre = nombre[1:].strip()
        codigo = match.group(2).strip()
        return nombre, codigo
    return texto_unido, "N/A"


def sumar_55_minutos(hora_str):
    try:
        # Extraer hora en formato HH:MM
        match = re.search(r'(\d{1,2}:\d{2})', hora_str)
        if not match: return hora_str

        hora_obj = datetime.strptime(match.group(1), "%H:%M")
        nueva_hora = hora_obj + timedelta(minutes=55)
        return nueva_hora.strftime("%H:%M")
    except Exception as e:
        # En caso de error, devolver la hora original
        return hora_str


def ajustar_bloque(bloque):
    """
    Ajusta la hora_fin si es igual a la hora_inicio sumando 55 minutos.
    """
    if bloque and bloque.get("hora_inicio") == bloque.get("hora_fin"):
        bloque["hora_fin"] = sumar_55_minutos(bloque["hora_inicio"])
    return bloque


def procesar_pagina(page):
    """
    Procesa una página individual y devuelve el horario de un profesor.
    """
    horario = {
        "profesor": "",
        "codigo": "",
        "horario": {dia: [] for dia in COLUMNAS_X}
    }

    nombre, codigo = extraer_info_profesor(page)
    horario["profesor"] = nombre
    horario["codigo"] = codigo

    filas_horas = obtener_filas_horas(page)

    for dia, (x0, x1) in COLUMNAS_X.items():
        bloque_actual = None

        for fila in filas_horas:
            bbox = (x0, fila['top'], x1, fila['bottom'])
            celda = page.crop(bbox)

            texto_raw = celda.extract_text() or ""
            texto = limpiar_texto(texto_raw)

            if texto.lower().startswith("recreo "):
                texto = texto[7:].strip()

            color = extraer_color_fondo(celda)

            if es_hora_recreo(fila['texto_hora'], texto):
                if bloque_actual:
                    # Ajustar antes de guardar
                    ajustar_bloque(bloque_actual)
                    horario["horario"][dia].append(bloque_actual)
                    bloque_actual = None
                continue

            if not texto:
                if color is not None:
                    if bloque_actual and colores_son_iguales(bloque_actual["color"], color):
                        bloque_actual["hora_fin"] = fila['texto_hora']
                    else:
                        if bloque_actual:
                            # Ajustar antes de guardar
                            ajustar_bloque(bloque_actual)
                            horario["horario"][dia].append(bloque_actual)
                        bloque_actual = {
                            "asignatura": "",
                            "hora_inicio": fila['texto_hora'],
                            "hora_fin": fila['texto_hora'],
                            "color": color,
                            "raw_text": []
                        }
                else:
                    if bloque_actual:
                        # Ajustar antes de guardar
                        ajustar_bloque(bloque_actual)
                        horario["horario"][dia].append(bloque_actual)
                        bloque_actual = None
                continue

            if bloque_actual:
                debe_agrupar = False

                if colores_son_iguales(bloque_actual["color"], color):
                    if color is not None:
                        texto_actual = bloque_actual["asignatura"]
                        if len(texto) < 20 and len(texto_actual) < 20 and texto != texto_actual:
                            debe_agrupar = False
                        else:
                            debe_agrupar = True
                    elif textos_son_similares(bloque_actual["asignatura"], texto):
                        debe_agrupar = True

                if debe_agrupar:
                    bloque_actual["hora_fin"] = fila['texto_hora']
                    if texto and texto not in bloque_actual["raw_text"]:
                        bloque_actual["raw_text"].append(texto)
                        bloque_actual["asignatura"] = " ".join(bloque_actual["raw_text"])
                else:
                    if bloque_actual["asignatura"]:
                        # Ajustar antes de guardar
                        ajustar_bloque(bloque_actual)
                        horario["horario"][dia].append(bloque_actual)

                    bloque_actual = {
                        "asignatura": texto,
                        "hora_inicio": fila['texto_hora'],
                        "hora_fin": fila['texto_hora'],
                        "color": color,
                        "raw_text": [texto] if texto else []
                    }
            else:
                bloque_actual = {
                    "asignatura": texto,
                    "hora_inicio": fila['texto_hora'],
                    "hora_fin": fila['texto_hora'],
                    "color": color,
                    "raw_text": [texto] if texto else []
                }

        if bloque_actual:
            if bloque_actual["asignatura"]:
                # Ajustar antes de guardar el último bloque
                ajustar_bloque(bloque_actual)
                horario["horario"][dia].append(bloque_actual)

    return horario


def procesar_pdf(pdf_path, paginas=None):
    """
    Procesa un PDF completo.

    Args:
        pdf_path: Ruta al archivo PDF
        paginas: Lista de números de página a procesar (base 0). Si es None, procesa todas.
                 Ejemplos: [0, 1, 2] o None

    Returns:
        Lista de horarios (uno por cada página procesada)
    """
    horarios = []

    with pdfplumber.open(pdf_path) as pdf:
        # Determinar qué páginas procesar
        if paginas is None:
            paginas_a_procesar = range(len(pdf.pages))
        else:
            paginas_a_procesar = paginas

        for num_pagina in paginas_a_procesar:
            if num_pagina < len(pdf.pages):
                print(f"  Procesando página {num_pagina + 1}...")
                page = pdf.pages[num_pagina]
                horario = procesar_pagina(page)

                # Solo agregar si tiene información válida
                if horario["profesor"] != "Desconocido" or any(
                        len(bloques) > 0 for bloques in horario["horario"].values()
                ):
                    horarios.append(horario)
            else:
                print(f"  ⚠️  Página {num_pagina + 1} no existe en el PDF")

    return horarios


def procesar_multiples_pdfs(rutas_pdfs, paginas_por_pdf=None):
    """
    Procesa múltiples archivos PDF.

    Args:
        rutas_pdfs: Lista de rutas a archivos PDF
        paginas_por_pdf: Diccionario {ruta_pdf: [lista_paginas]} o None para procesar todas
                        Ejemplo: {"pdf1.pdf": [0, 1], "pdf2.pdf": None}

    Returns:
        Lista consolidada de todos los horarios
    """
    todos_los_horarios = []

    for ruta_pdf in rutas_pdfs:
        if not os.path.exists(ruta_pdf):
            print(f"⚠️  Archivo no encontrado: {ruta_pdf}")
            continue

        print(f"\nProcesando: {ruta_pdf}")

        # Obtener páginas específicas para este PDF
        paginas = None
        if paginas_por_pdf and ruta_pdf in paginas_por_pdf:
            paginas = paginas_por_pdf[ruta_pdf]

        horarios = procesar_pdf(ruta_pdf, paginas)
        todos_los_horarios.extend(horarios)

        print(f"  ✓ {len(horarios)} horario(s) extraído(s)")

    return todos_los_horarios


def guardar_json(horarios, ruta_salida):
    """Guarda los horarios en un archivo JSON."""
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(horarios, f, indent=4, ensure_ascii=False)
    print(f"\n✓ JSON guardado en: {ruta_salida}")


if __name__ == "__main__":
    # ========== CONFIGURACIÓN ==========

    # Opción 1: Procesar UN PDF con MÚLTIPLES PÁGINAS
    ruta_pdf = os.path.join(os.path.dirname(__file__), "..", "data", "HORARIOS_25_26 - Docentes IA.pdf")

    # Especificar páginas (base 0): None = todas, o lista como [0, 1, 2, 3]
    # Ejemplo: primeras 5 páginas = [0, 1, 2, 3, 4]
    paginas_a_procesar = None  # Cambia a [0, 1, 2] para procesar solo las primeras 3 páginas

    if os.path.exists(ruta_pdf):
        print(f"Procesando PDF: {ruta_pdf}")
        horarios = procesar_pdf(ruta_pdf, paginas=paginas_a_procesar)

        # Mostrar en consola
        print("\n" + "=" * 80)
        print(f"TOTAL DE HORARIOS EXTRAÍDOS: {len(horarios)}")
        print("=" * 80)
        print(json.dumps(horarios, indent=4, ensure_ascii=False))

        # Guardar en archivo JSON
        ruta_salida = os.path.join(os.path.dirname(__file__), "..", "data", "horarios_consolidados.json")
        guardar_json(horarios, ruta_salida)
    else:
        print(f"❌ Archivo no encontrado: {ruta_pdf}")

    # ========== Opción 2: Procesar MÚLTIPLES PDFs ==========
    # Descomenta esto para usar múltiples PDFs
    """
    pdfs = [
        os.path.join(os.path.dirname(__file__), "..", "data", "HORARIOS_1.pdf"),
        os.path.join(os.path.dirname(__file__), "..", "data", "HORARIOS_2.pdf"),
    ]

    # Configurar páginas específicas por PDF (opcional)
    config_paginas = {
        pdfs[0]: [0, 1, 2],  # Primeras 3 páginas del primer PDF
        pdfs[1]: None,       # Todas las páginas del segundo PDF
    }

    horarios = procesar_multiples_pdfs(pdfs, paginas_por_pdf=config_paginas)

    print(f"\nTOTAL DE HORARIOS: {len(horarios)}")

    # Guardar resultado
    ruta_salida = os.path.join(os.path.dirname(__file__), "..", "data", "todos_los_horarios.json")
    guardar_json(horarios, ruta_salida)
    """