import pdfplumber
import re
import json
import os
import glob
from pathlib import Path

# --- IMPORTS PROPIOS ---
try:
    from validacion import validate_schedule
    # Importamos las herramientas desde el nuevo archivo utils.py
    from utils import (
        es_color_valido,
        es_color_gris_claro,
        colores_son_iguales,
        textos_son_similares,
        extraer_nombre_asignatura,
        extraer_codigos_grupo,
        clasificar_grupos,
        limpiar_texto,
        sumar_55_minutos,
        es_hora_recreo
    )
except ImportError as e:
    print(f"❌ ERROR CRÍTICO: Falta un archivo necesario ({e}). Asegúrate de tener 'utils.py' y 'validacion.py'.")
    exit()

# --- CONFIGURACIÓN ---
COLUMNAS_X = {
    "Lunes": (80, 175), "Martes": (175, 270), "Miércoles": (270, 365),
    "Jueves": (365, 460), "Viernes": (460, 555),
}
COLUMNA_HORAS_X = (0, 80)


# ==============================================================================
# LÓGICA DE EXTRACCIÓN (Ahora usa funciones de utils.py)
# ==============================================================================

def extraer_color_fondo(crop):
    try:
        if crop.width < 6 or crop.height < 6:
            crop_seguro = crop
        else:
            crop_seguro = crop.crop((2, 2, crop.width - 2, crop.height - 2), relative=True)

        area_celda = crop_seguro.width * crop_seguro.height
        # Umbral mínimo: rects deben cubrir al menos 30% del área de la celda
        # para ser considerados como fondo real (no bordes/decoraciones)
        area_minima = area_celda * 0.3 if area_celda > 0 else 100

        rects = sorted(crop_seguro.rects, key=lambda r: r['width'] * r['height'], reverse=True)
        for rect in rects:
            # Filtrar rects diminutos (bordes, decoraciones)
            rect_area = rect['width'] * rect['height']
            if rect_area < area_minima:
                continue
            c = rect.get("non_stroking_color")
            if c and es_color_valido(c): return c  # Usa función de utils

        if hasattr(crop_seguro, 'curves'):
            for curve in crop_seguro.curves:
                if curve.get("fill"):
                    c = curve.get("non_stroking_color")
                    if c and es_color_valido(c): return c  # Usa función de utils
    except Exception:
        pass
    return None


def obtener_filas_horas(page):
    try:
        filas = []
        Y_INICIO_TABLA = 145
        lineas = sorted([l['top'] for l in page.lines if l['width'] > 50])

        lineas_filtradas = []
        if lineas:
            lineas_validas = [y for y in lineas if y > Y_INICIO_TABLA]
            if not lineas_validas: return []
            lineas_filtradas.append(Y_INICIO_TABLA + 2)
            for y in lineas_validas:
                if abs(y - lineas_filtradas[-1]) > 5: lineas_filtradas.append(y)

        if lineas_filtradas:
            ultima_altura = 35
            if len(lineas_filtradas) >= 2:
                ultima_altura = lineas_filtradas[-1] - lineas_filtradas[-2]
            lineas_filtradas.append(lineas_filtradas[-1] + ultima_altura)

        crop_col_horas = page.crop((COLUMNA_HORAS_X[0], 0, COLUMNA_HORAS_X[1], page.height))
        for i in range(len(lineas_filtradas) - 1):
            top, bottom = lineas_filtradas[i], lineas_filtradas[i + 1]
            if top >= bottom: continue

            zona_hora = crop_col_horas.crop((0, top, crop_col_horas.width, bottom))
            texto = zona_hora.extract_text()
            texto_limpio = " ".join(texto.split()) if texto else ""

            if texto_limpio:
                horas = re.findall(r'\d{1,2}:\d{2}', texto_limpio)
                horas_unicas = []
                for hora in horas:
                    if not horas_unicas or hora != horas_unicas[-1]: horas_unicas.append(hora)
                if horas_unicas: texto_limpio = ' '.join(horas_unicas)

            if not texto_limpio: texto_limpio = f"[{top:.0f}-{bottom:.0f}]"
            filas.append({'top': top, 'bottom': bottom, 'texto_hora': texto_limpio})
        return filas
    except Exception as e:
        print(f"      ⚠️ Error detectando filas: {e}")
        return []


def extraer_info_profesor(page):
    try:
        cabecera = page.crop((0, 0, page.width, 130))
        texto_cabecera = cabecera.extract_text()
        if not texto_cabecera: return "Desconocido", "N/A"
        texto_unido = limpiar_texto(texto_cabecera)

        # Detectar formato anonimizado: "Profesor 001", "Profesor 123", etc.
        match_anon = re.search(r"Profesor\s+(\d{3,})", texto_unido, re.IGNORECASE)
        if match_anon:
            numero = match_anon.group(1)
            return f"Profesor {numero}", f"PROF{numero}"

        # Formato original: APELLIDOS, NOMBRE (CODIGO)
        match = re.search(r"([A-ZÁÉÍÓÚÑ, ]+)\s*\(([^)]+)\)", texto_unido)
        if match:
            nombre = match.group(1).strip().lstrip(",")
            return nombre, match.group(2).strip()

        # Fallback: generar código sintético desde el nombre
        nombre_limpio = texto_unido[:50].strip()
        codigo_sintetico = re.sub(r'[^A-Z0-9]', '', nombre_limpio.upper())[:10]
        return nombre_limpio, codigo_sintetico if codigo_sintetico else "N/A"
    except Exception:
        return "Error Lectura", "ERR"


def ajustar_bloque(bloque):
    try:
        if bloque and bloque.get("hora_inicio") == bloque.get("hora_fin"):
            # Usa función de utils
            bloque["hora_fin"] = sumar_55_minutos(bloque["hora_inicio"])
    except:
        pass
    return bloque


def procesar_pagina(page):
    horario_interno = {"profesor": "Desconocido", "codigo": "N/A", "horario": {dia: [] for dia in COLUMNAS_X}}

    try:
        horario_interno["profesor"], horario_interno["codigo"] = extraer_info_profesor(page)
        filas_horas = obtener_filas_horas(page)

        if not filas_horas: return horario_interno

        for dia, (x0, x1) in COLUMNAS_X.items():
            bloque_actual = None
            # Rastrear celdas con color sin texto para extensión hacia atrás
            celdas_vacias_con_color = []  # [(indice_fila, color)]
            for idx_fila, fila in enumerate(filas_horas):
                try:
                    bbox = (x0, fila['top'], x1, fila['bottom'])
                    celda = page.crop(bbox)
                    # Usa funciones de utils
                    texto = limpiar_texto(celda.extract_text() or "")
                    if texto.lower().startswith("recreo "): texto = texto[7:].strip()
                    color = extraer_color_fondo(celda)

                    if es_hora_recreo(fila['texto_hora'], texto):  # Utils
                        if bloque_actual:
                            ajustar_bloque(bloque_actual)
                            horario_interno["horario"][dia].append(bloque_actual)
                            bloque_actual = None
                        celdas_vacias_con_color = []  # Reset tras recreo
                        continue

                    if not texto:
                        if color is not None:
                            # Utils
                            if bloque_actual and colores_son_iguales(bloque_actual["color"], color):
                                bloque_actual["hora_fin"] = fila['texto_hora']
                            else:
                                # Cerrar bloque anterior, registrar celda vacía con color
                                if bloque_actual:
                                    ajustar_bloque(bloque_actual)
                                    if bloque_actual["asignatura"]:
                                        horario_interno["horario"][dia].append(bloque_actual)
                                    bloque_actual = None
                                celdas_vacias_con_color.append((idx_fila, color))
                        else:
                            if bloque_actual:
                                ajustar_bloque(bloque_actual)
                                if bloque_actual["asignatura"]:
                                    horario_interno["horario"][dia].append(bloque_actual)
                                bloque_actual = None
                            celdas_vacias_con_color = []  # Sin color rompe continuidad
                        continue

                    # Celda CON texto: determinar hora_inicio real
                    hora_inicio_real = fila['texto_hora']
                    hora_inicio_ext = fila['texto_hora']  # Candidato extendido hacia atrás
                    if not bloque_actual and celdas_vacias_con_color and color is not None:
                        # Extensión hacia atrás: buscar celdas vacías previas contiguas
                        # con el mismo color para encontrar el inicio candidato
                        for i in range(len(celdas_vacias_con_color) - 1, -1, -1):
                            idx_prev, color_prev = celdas_vacias_con_color[i]
                            if colores_son_iguales(color_prev, color):
                                hora_inicio_ext = filas_horas[idx_prev]['texto_hora']
                            else:
                                break
                    celdas_vacias_con_color = []  # Reset tras encontrar texto

                    if bloque_actual:
                        debe_agrupar = False
                        # Utils
                        if colores_son_iguales(bloque_actual["color"], color):
                            texto_act = bloque_actual.get("asignatura", "")
                            if color:
                                if es_color_gris_claro(color):
                                    # Gris: solo agrupar si textos son similares
                                    debe_agrupar = textos_son_similares(texto_act, texto) or texto_act == texto
                                else:
                                    # Color distintivo: agrupar solo si los textos
                                    # representan la misma asignatura.
                                    # Si alguno no tiene nombre base reconocible
                                    # (es continuación de texto partido entre filas),
                                    # confiar en el color y agrupar.
                                    base_act = extraer_nombre_asignatura(texto_act)
                                    base_new = extraer_nombre_asignatura(texto)
                                    if not base_act and not base_new:
                                        # Ambos son solo códigos → comparar directamente
                                        debe_agrupar = texto_act == texto
                                    elif not base_act or not base_new:
                                        # Uno es continuación del otro → confiar en color
                                        debe_agrupar = True
                                    else:
                                        debe_agrupar = textos_son_similares(texto_act, texto) or texto_act == texto
                            elif textos_son_similares(texto_act, texto):  # Utils
                                debe_agrupar = True

                        if debe_agrupar:
                            bloque_actual["hora_fin"] = fila['texto_hora']
                            if texto:
                                # Merge con detección de solapamiento
                                asig_actual = bloque_actual.get("asignatura", "")
                                if not asig_actual:
                                    bloque_actual["asignatura"] = texto
                                elif texto not in asig_actual:
                                    # Buscar solapamiento: sufijo de asig_actual = prefijo de texto
                                    merged = False
                                    for k in range(min(len(asig_actual), len(texto)), 4, -1):
                                        if asig_actual.endswith(texto[:k]):
                                            bloque_actual["asignatura"] = asig_actual + texto[k:]
                                            merged = True
                                            break
                                    if not merged:
                                        bloque_actual["asignatura"] = asig_actual + " " + texto
                        else:
                            if bloque_actual["asignatura"]:
                                # Para gris: revertir extensión si bloque no creció
                                # Para colores: siempre mantener extensión
                                if es_color_gris_claro(bloque_actual.get("color")):
                                    h_texto = bloque_actual.get("hora_inicio_texto", "")
                                    h_fin = bloque_actual.get("hora_fin", "")
                                    if h_texto and h_texto == h_fin:
                                        bloque_actual["hora_inicio"] = h_texto
                                ajustar_bloque(bloque_actual)
                                horario_interno["horario"][dia].append(bloque_actual)
                            bloque_actual = {"asignatura": texto, "hora_inicio": hora_inicio_ext,
                                             "hora_inicio_texto": hora_inicio_real,
                                             "hora_fin": fila['texto_hora'], "color": color,
                                             "raw_text": [texto] if texto else []}
                    else:
                        bloque_actual = {"asignatura": texto, "hora_inicio": hora_inicio_ext,
                                         "hora_inicio_texto": hora_inicio_real,
                                         "hora_fin": fila['texto_hora'],
                                         "color": color, "raw_text": [texto] if texto else []}

                except Exception:
                    continue

            if bloque_actual and bloque_actual["asignatura"]:
                # Para gris: revertir extensión si no creció. Colores: siempre mantener.
                if es_color_gris_claro(bloque_actual.get("color")):
                    h_texto = bloque_actual.get("hora_inicio_texto", "")
                    h_fin = bloque_actual.get("hora_fin", "")
                    if h_texto and h_texto == h_fin:
                        bloque_actual["hora_inicio"] = h_texto
                ajustar_bloque(bloque_actual)
                horario_interno["horario"][dia].append(bloque_actual)

        # POST-PROCESAMIENTO Y TRANSFORMACIÓN
        eventos_lista = []
        for dia in COLUMNAS_X:
            for evento in horario_interno["horario"][dia]:
                try:
                    # Saltar eventos sin asignatura (placeholders de celdas grises vacías)
                    asig = evento.get("asignatura", "")
                    if not asig:
                        continue

                    h_inicio_todas = re.findall(r'\d{1,2}:\d{2}', str(evento.get("hora_inicio", "")))
                    h_fin_todas = re.findall(r'\d{1,2}:\d{2}', str(evento.get("hora_fin", "")))

                    h_inicio_limpia = h_inicio_todas[0] if h_inicio_todas else ""
                    h_fin_limpia = h_fin_todas[-1] if h_fin_todas else ""

                    # Saltar eventos sin horas válidas
                    if not h_inicio_limpia or not h_fin_limpia:
                        continue

                    eventos_lista.append({
                        "dia": dia,
                        "asignatura": evento.get("asignatura", "Desconocida"),
                        "inicio": h_inicio_limpia,
                        "fin": h_fin_limpia
                    })
                except Exception:
                    continue

        # Extraer y clasificar grupos del profesor
        todos_los_prefijos = set()
        for evento in eventos_lista:
            todos_los_prefijos.update(extraer_codigos_grupo(evento.get("asignatura", "")))
        grupos_clasificados = clasificar_grupos(todos_los_prefijos)

        return {
            "profesor": {
                "nombre": horario_interno["profesor"],
                "codigo": horario_interno["codigo"]
            },
            "grupos": grupos_clasificados,
            "eventos": eventos_lista
        }

    except Exception as e:
        print(f"      ❌ Error crítico procesando página: {e}")
        return horario_interno


# ==============================================================================
# ORQUESTADOR
# ==============================================================================

def procesar_todo_automaticamente(carpeta_data):
    todos_los_horarios = []
    if not os.path.exists(carpeta_data):
        print(f"❌ Error crítico: La carpeta no existe: {carpeta_data}")
        return []

    patron = os.path.join(carpeta_data, "*.pdf")
    archivos_pdf = glob.glob(patron)

    if not archivos_pdf:
        print(f"⚠️ Aviso: No se encontraron archivos PDF en: {carpeta_data}")
        return []

    print(f"📂 Encontrados {len(archivos_pdf)} archivos PDF.")
    print("-" * 50)

    for ruta_pdf in archivos_pdf:
        nombre_archivo = os.path.basename(ruta_pdf)
        print(f"🔄 Procesando: {nombre_archivo} ...")

        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                if not pdf.pages:
                    print("   ⚠️ El PDF no tiene páginas.")
                    continue

                print(f"   📄 Detectadas {len(pdf.pages)} páginas.")
                for i, page in enumerate(pdf.pages):
                    try:
                        horario = procesar_pagina(page)
                        errores = validate_schedule(horario)  # Validador

                        if errores:
                            print(f"      ⚠️ Pág {i + 1} DESCARTADA por calidad insuficiente:")
                            for err in errores: print(f"         - {err}")
                        else:
                            todos_los_horarios.append(horario)

                    except Exception as e:
                        print(f"      ❌ Error en pág {i + 1}: {str(e)}")

        except Exception as e:
            print(f"   ❌ Error abriendo el archivo (posiblemente corrupto): {str(e)}")

    return todos_los_horarios


if __name__ == "__main__":
    carpeta_data = os.path.join(os.path.dirname(__file__), "..", "data")
    try:
        print("🚀 INICIANDO ESCANEO COMPLETO DE PDFs")
        horarios_consolidados = procesar_todo_automaticamente(carpeta_data)

        if horarios_consolidados:
            ruta_salida = os.path.join(carpeta_data, "horarios_consolidados.json")
            try:
                with open(ruta_salida, 'w', encoding='utf-8') as f:
                    json.dump(horarios_consolidados, f, indent=4, ensure_ascii=False)
                print("-" * 50)
                print(f"✅ ¡ÉXITO! Se han consolidado {len(horarios_consolidados)} horarios válidos.")
                print(f"💾 Resultado guardado en: {ruta_salida}")
            except IOError as e:
                print(f"❌ Error al escribir el archivo JSON final: {e}")
        else:
            print("\n⚠️ No se extrajo ningún horario válido.")
    except Exception as e:
        print(f"\n❌ Error fatal inesperado en el programa principal: {e}")