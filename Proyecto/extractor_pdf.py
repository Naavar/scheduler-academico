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
    if not color: return False
    r, g, b = color
    if r > 0.9 and g > 0.9 and b > 0.9:
        return False
    return True


def colores_son_iguales(c1, c2):
    if c1 is None or c2 is None:
        return False
    return all(abs(a - b) < 0.05 for a, b in zip(c1, c2))


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
    """
    Detecta las filas basándose en la posición Y de los textos de las horas.
    Mucho más fiable que las líneas gráficas.
    """
    filas = []

    # 1. Recortamos la columna de horas
    crop_horas = page.crop((COLUMNA_HORAS_X[0], 0, COLUMNA_HORAS_X[1], page.height))

    # 2. Extraemos las palabras que parecen horas (formato HH:MM)
    palabras = crop_horas.extract_words()
    horas_encontradas = []

    # Regex para detectar horas "14:25"
    patron_hora = re.compile(r'\d{1,2}:\d{2}')

    for w in palabras:
        if patron_hora.match(w['text']):
            horas_encontradas.append(w)

    # 3. Agrupamos horas que estén en la misma línea visual (inicio y fin)
    # Ejemplo: "14:25" está arriba y "15:20" un poco más abajo.
    # Necesitamos agruparlas para definir el "bloque" de la fila.

    # Ordenamos por posición vertical
    horas_encontradas.sort(key=lambda x: x['top'])

    i = 0
    while i < len(horas_encontradas) - 1:
        hora_inicio = horas_encontradas[i]

        # Buscamos la siguiente hora que esté cerca (la hora de fin)
        # Normalmente está unos 10-20 píxeles más abajo en el mismo bloque
        j = i + 1
        hora_fin = None

        while j < len(horas_encontradas):
            distancia = horas_encontradas[j]['top'] - hora_inicio['top']

            # Si está muy cerca (menos de 40px), es la hora de fin de este bloque
            if 10 < distancia < 50:
                hora_fin = horas_encontradas[j]
                break
            # Si está muy lejos, es el inicio del siguiente bloque
            elif distancia >= 50:
                break
            j += 1

        if hora_fin:
            # TENEMOS UNA FILA VÁLIDA
            # Definimos el top y bottom de la fila usando estas horas como ancla
            # Damos un poco de margen arriba y abajo
            top_fila = hora_inicio['top'] - 2
            # El bottom es un poco más abajo de la hora de fin
            bottom_fila = hora_fin['bottom'] + 2

            texto_completo = f"{hora_inicio['text']} {hora_fin['text']}"

            filas.append({
                'top': top_fila,
                'bottom': bottom_fila,
                'texto_hora': texto_completo
            })

            # Saltamos las horas que ya hemos procesado
            i = j + 1
        else:
            # Si no encontramos pareja, avanzamos
            i += 1

    return filas


def limpiar_texto(txt):
    if not txt: return ""
    return " ".join(txt.split())


def es_hora_recreo(texto_hora, texto_celda=""):
    hora = texto_hora.lower()
    contenido = texto_celda.lower()
    if "11:00" in hora and "11:30" in hora: return True
    if "18:05" in hora and "18:35" in hora: return True
    if "recreo" in contenido: return True
    return False


def extraer_info_profesor(page):
    cabecera = page.crop((0, 0, page.width, 130))
    texto_cabecera = cabecera.extract_text()
    if not texto_cabecera: return "Desconocido", "N/A"

    texto_unido = limpiar_texto(texto_cabecera)
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
        # ATENCIÓN: Pongo la página 1 para probar tu caso del Miércoles
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

                if es_hora_recreo(fila['texto_hora'], texto):
                    if bloque_actual:
                        resultado["horario"][dia].append(bloque_actual)
                        bloque_actual = None
                    continue

                es_vacia = (not texto) and (color is None)
                if es_vacia:
                    if bloque_actual:
                        resultado["horario"][dia].append(bloque_actual)
                        bloque_actual = None
                    continue

                if bloque_actual:
                    if colores_son_iguales(bloque_actual["color"], color):
                        bloque_actual["hora_fin"] = fila['texto_hora']
                        if texto and texto not in bloque_actual["raw_text"]:
                            bloque_actual["raw_text"].append(texto)
                            bloque_actual["asignatura"] = " ".join(bloque_actual["raw_text"])
                    else:
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