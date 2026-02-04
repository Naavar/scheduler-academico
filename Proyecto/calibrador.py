import pdfplumber
import re
import json

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
    """Compara colores con tolerancia"""
    if c1 is None or c2 is None:
        return False
    return all(abs(a - b) < 0.05 for a, b in zip(c1, c2))


def extraer_color_fondo(crop):
    """Busca el color evitando bordes"""
    if crop.width < 6 or crop.height < 6:
        crop_seguro = crop
    else:
        # relative=True es vital
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
    """Detecta filas y recupera la última hora si falta la línea de cierre"""
    filas = []
    Y_INICIO_TABLA = 145

    lineas = [l['top'] for l in page.lines if l['width'] > 50]
    lineas.sort()

    lineas_filtradas = []
    if lineas:
        lineas_validas = [y for y in lineas if y > Y_INICIO_TABLA]
        if not lineas_validas: return []

        # Forzamos inicio de tabla
        lineas_filtradas.append(Y_INICIO_TABLA + 2)

        for y in lineas_validas:
            if abs(y - lineas_filtradas[-1]) > 5:
                lineas_filtradas.append(y)

    # Lógica para recuperar la última hora (20:25 - 21:20) si el PDF no tiene línea final
    if len(lineas_filtradas) > 2:
        alturas = [lineas_filtradas[i + 1] - lineas_filtradas[i] for i in range(len(lineas_filtradas) - 1)]
        altura_media = sum(alturas) / len(alturas)
        posible_nueva_linea = lineas_filtradas[-1] + altura_media

        crop_test = page.crop((COLUMNA_HORAS_X[0], lineas_filtradas[-1], COLUMNA_HORAS_X[1], posible_nueva_linea))
        txt = crop_test.extract_text()
        if txt and any(c.isdigit() for c in txt):
            lineas_filtradas.append(posible_nueva_linea)

    crop_col_horas = page.crop((COLUMNA_HORAS_X[0], 0, COLUMNA_HORAS_X[1], page.height))

    for i in range(len(lineas_filtradas) - 1):
        top = lineas_filtradas[i]
        bottom = lineas_filtradas[i + 1]

        zona_hora = crop_col_horas.crop((0, top, crop_col_horas.width, bottom))
        texto = zona_hora.extract_text()
        texto_limpio = texto.replace('\n', ' ').strip() if texto else ""

        if texto_limpio:
            filas.append({
                'top': top,
                'bottom': bottom,
                'texto_hora': texto_limpio
            })
    return filas


def limpiar_texto(txt):
    if not txt: return ""
    return " ".join(txt.split())


def es_celda_recreo(texto_hora, texto_celda=""):
    """
    Devuelve True si es recreo por hora O si el texto contiene 'recreo'.
    """
    hora = texto_hora.lower()
    contenido = texto_celda.lower()

    # 1. Filtro por palabra clave (LO QUE HAS PEDIDO)
    if "recreo" in contenido:
        return True

    # 2. Filtro por hora (backup)
    if "11:00" in hora and "11:30" in hora: return True
    if "18:05" in hora and "18:35" in hora: return True

    return False


def extraer_info_profesor(page):
    cabecera = page.crop((0, 0, page.width, 130))
    texto_cabecera = cabecera.extract_text()
    if not texto_cabecera: return "Desconocido", "N/A"

    texto_unido = limpiar_texto(texto_cabecera)
    # Regex para: NOMBRE APELLIDOS (CODIGO)
    match = re.search(r"([A-ZÁÉÍÓÚÑ, ]+)\s*\(([^)]+)\)", texto_unido)

    if match:
        nombre = match.group(1).strip()
        if nombre.startswith(","): nombre = nombre[1:].strip()
        codigo = match.group(2).strip()
        return nombre, codigo
    return texto_unido, "N/A"


def procesar_horario(pdf_path):
    resultado = {
        "profesor": "",
        "codigo": "",
        "horario": {dia: [] for dia in COLUMNAS_X}
    }

    with pdfplumber.open(pdf_path) as pdf:
        # ATENCIÓN: Aquí eliges la página. [0] es la primera.
        page = pdf.pages[1]

        nombre, codigo = extraer_info_profesor(page)
        resultado["profesor"] = nombre
        resultado["codigo"] = codigo

        filas_horas = obtener_filas_horas(page)

        for dia, (x0, x1) in COLUMNAS_X.items():
            bloque_actual = None

            for fila in filas_horas:
                bbox = (x0, fila['top'], x1, fila['bottom'])
                celda = page.crop(bbox)

                texto_raw = celda.extract_text() or ""
                texto = limpiar_texto(texto_raw)
                color = extraer_color_fondo(celda)

                # --- FILTRO ANTI-RECREO ---
                # Si pone "recreo" o es la hora del recreo -> SALTAR
                if es_celda_recreo(fila['texto_hora'], texto):
                    if bloque_actual:
                        resultado["horario"][dia].append(bloque_actual)
                        bloque_actual = None
                    continue

                    # Si hay texto, NO es vacía (aunque no tenga color)
                # Esto recupera las reuniones sin fondo de color
                es_vacia = (not texto) and (color is None)

                if es_vacia:
                    if bloque_actual:
                        resultado["horario"][dia].append(bloque_actual)
                        bloque_actual = None
                    continue

                # LÓGICA DE AGRUPACIÓN
                if bloque_actual:
                    if colores_son_iguales(bloque_actual["color"], color):
                        # EXTENDER BLOQUE
                        bloque_actual["hora_fin"] = fila['texto_hora']
                        # Unimos texto si es nuevo
                        if texto and texto not in bloque_actual["raw_text"]:
                            bloque_actual["raw_text"].append(texto)
                            bloque_actual["asignatura"] = " ".join(bloque_actual["raw_text"])
                    else:
                        # CERRAR Y EMPEZAR NUEVO
                        resultado["horario"][dia].append(bloque_actual)
                        bloque_actual = None

                if bloque_actual is None:
                    bloque_actual = {
                        "asignatura": texto,
                        "hora_inicio": fila['texto_hora'],
                        "hora_fin": fila['texto_hora'],
                        "color": color,
                        "raw_text": [texto] if texto else []
                    }

            if bloque_actual:
                resultado["horario"][dia].append(bloque_actual)

    return resultado


if __name__ == "__main__":
    import os

    ruta_pdf = os.path.join(os.path.dirname(__file__), "..", "data", "HORARIOS_25_26 - Docentes IA.pdf")
    if os.path.exists(ruta_pdf):
        print(f"Procesando: {ruta_pdf} ...")
        res = procesar_horario(ruta_pdf)
        print(json.dumps(res, indent=4, ensure_ascii=False))