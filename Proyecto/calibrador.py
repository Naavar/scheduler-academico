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
        # A veces aparece "11:30 11:30 12:25" en lugar de "11:30 12:25"
        if texto_limpio:
            # Normalizar espacios múltiples
            texto_limpio = ' '.join(texto_limpio.split())

            # Eliminar duplicados de horas (formato HH:MM)
            # Encontrar todas las horas en formato HH:MM
            horas = re.findall(r'\d{1,2}:\d{2}', texto_limpio)

            # Eliminar duplicados consecutivos manteniendo el orden
            horas_unicas = []
            for hora in horas:
                if not horas_unicas or hora != horas_unicas[-1]:
                    horas_unicas.append(hora)

            # Reconstruir el texto con horas únicas
            if horas_unicas:
                texto_limpio = ' '.join(horas_unicas)

        # CAMBIO: Agregar TODAS las filas, incluso sin texto de hora
        # Si no hay texto, usar un placeholder con las coordenadas
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

    # Recreos por hora conocida
    if "11:00" in hora and "11:30" in hora: return True
    if "18:05" in hora and "18:35" in hora: return True

    # Solo si la celda ÚNICAMENTE contiene "recreo" (sin otro contenido)
    if contenido == "recreo": return True

    # Si es un placeholder (sin texto de hora) con tamaño muy pequeño, probablemente es recreo
    if hora.startswith('[') and hora.endswith(']'):
        # Extraer las coordenadas del placeholder [top-bottom]
        try:
            coords = hora[1:-1].split('-')
            if len(coords) == 2:
                top = float(coords[0])
                bottom = float(coords[1])
                altura = bottom - top
                # Si la altura es menor a 25px, probablemente es un recreo
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


def procesar_horario(pdf_path):
    resultado = {
        "profesor": "",
        "codigo": "",
        "horario": {dia: [] for dia in COLUMNAS_X}
    }

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[3]  # Estamos leyendo la página 2

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

                # Limpiar "recreo" si aparece al inicio del texto (artefacto del PDF)
                if texto.lower().startswith("recreo "):
                    texto = texto[7:].strip()  # Eliminar "recreo " (7 caracteres)

                color = extraer_color_fondo(celda)

                if es_hora_recreo(fila['texto_hora'], texto):
                    if bloque_actual:
                        resultado["horario"][dia].append(bloque_actual)
                        bloque_actual = None
                    continue

                # --- NUEVA LÓGICA ---
                # Si NO hay texto pero SÍ hay color, intentar agrupar con bloque anterior
                if not texto:
                    if color is not None:
                        # Hay color pero no texto
                        if bloque_actual and colores_son_iguales(bloque_actual["color"], color):
                            # Extender el bloque actual (misma celda coloreada continúa)
                            bloque_actual["hora_fin"] = fila['texto_hora']
                        else:
                            # No hay bloque previo o es de otro color
                            # Crear un bloque placeholder que será completado después
                            if bloque_actual:
                                resultado["horario"][dia].append(bloque_actual)

                            bloque_actual = {
                                "asignatura": "",  # Será completado cuando aparezca texto
                                "hora_inicio": fila['texto_hora'],
                                "hora_fin": fila['texto_hora'],
                                "color": color,
                                "raw_text": []
                            }
                    else:
                        # No hay color ni texto, finalizar bloque
                        if bloque_actual:
                            resultado["horario"][dia].append(bloque_actual)
                            bloque_actual = None
                    continue

                if bloque_actual:
                    # Verificar si debe agruparse con el bloque actual
                    debe_agrupar = False

                    if colores_son_iguales(bloque_actual["color"], color):
                        # Si ambos tienen color (no None)
                        if color is not None:
                            # Verificar si los textos son muy diferentes (textos cortos < 20 chars)
                            # En ese caso, NO agrupar aunque tengan el mismo color
                            texto_actual = bloque_actual["asignatura"]
                            if len(texto) < 20 and len(texto_actual) < 20 and texto != texto_actual:
                                # Textos cortos y diferentes, NO agrupar
                                debe_agrupar = False
                            else:
                                # Textos largos o similares, agrupar
                                debe_agrupar = True
                        # Si ambos son None (sin color), verificar similitud de texto
                        elif textos_son_similares(bloque_actual["asignatura"], texto):
                            debe_agrupar = True

                    if debe_agrupar:
                        bloque_actual["hora_fin"] = fila['texto_hora']
                        if texto and texto not in bloque_actual["raw_text"]:
                            bloque_actual["raw_text"].append(texto)
                            bloque_actual["asignatura"] = " ".join(bloque_actual["raw_text"])
                    else:
                        # Antes de crear nuevo bloque, verificar si el actual tiene texto
                        # Si no tiene texto (placeholder), no guardarlo
                        if bloque_actual["asignatura"]:  # Solo guardar si tiene contenido
                            resultado["horario"][dia].append(bloque_actual)

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
                # Solo guardar si tiene contenido (no es un placeholder vacío)
                if bloque_actual["asignatura"]:
                    resultado["horario"][dia].append(bloque_actual)

    return resultado


if __name__ == "__main__":
    import os

    ruta_pdf = os.path.join(os.path.dirname(__file__), "..", "data", "HORARIOS_25_26 - Docentes IA.pdf")
    if os.path.exists(ruta_pdf):
        print(f"Procesando: {ruta_pdf} ...")
        res = procesar_horario(ruta_pdf)
        print(json.dumps(res, indent=4, ensure_ascii=False))