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
        colores_son_iguales,
        textos_son_similares,
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

        rects = sorted(crop_seguro.rects, key=lambda r: r['width'] * r['height'], reverse=True)
        for rect in rects:
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
        texto_unido = limpiar_texto(texto_cabecera)  # Usa función de utils
        match = re.search(r"([A-ZÁÉÍÓÚÑ, ]+)\s*\(([^)]+)\)", texto_unido)
        if match:
            nombre = match.group(1).strip().lstrip(",")
            return nombre, match.group(2).strip()
        return texto_unido[:50], "N/A"
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
            for fila in filas_horas:
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
                        continue

                    if not texto:
                        if color is not None:
                            # Utils
                            if bloque_actual and colores_son_iguales(bloque_actual["color"], color):
                                bloque_actual["hora_fin"] = fila['texto_hora']
                            else:
                                if bloque_actual:
                                    ajustar_bloque(bloque_actual)
                                    horario_interno["horario"][dia].append(bloque_actual)
                                bloque_actual = {"asignatura": "", "hora_inicio": fila['texto_hora'],
                                                 "hora_fin": fila['texto_hora'], "color": color, "raw_text": []}
                        else:
                            if bloque_actual:
                                ajustar_bloque(bloque_actual)
                                horario_interno["horario"][dia].append(bloque_actual)
                                bloque_actual = None
                        continue

                    if bloque_actual:
                        debe_agrupar = False
                        # Utils
                        if colores_son_iguales(bloque_actual["color"], color):
                            if color:
                                texto_act = bloque_actual.get("asignatura", "")
                                debe_agrupar = not (len(texto) < 20 and len(texto_act) < 20 and texto != texto_act)
                            elif textos_son_similares(bloque_actual.get("asignatura", ""), texto):  # Utils
                                debe_agrupar = True

                        if debe_agrupar:
                            bloque_actual["hora_fin"] = fila['texto_hora']
                            if texto and texto not in bloque_actual["raw_text"]:
                                bloque_actual["raw_text"].append(texto)
                                bloque_actual["asignatura"] = " ".join(bloque_actual["raw_text"])
                        else:
                            if bloque_actual["asignatura"]:
                                ajustar_bloque(bloque_actual)
                                horario_interno["horario"][dia].append(bloque_actual)
                            bloque_actual = {"asignatura": texto, "hora_inicio": fila['texto_hora'],
                                             "hora_fin": fila['texto_hora'], "color": color,
                                             "raw_text": [texto] if texto else []}
                    else:
                        bloque_actual = {"asignatura": texto, "hora_inicio": fila['texto_hora'],
                                         "hora_fin": fila['texto_hora'],
                                         "color": color, "raw_text": [texto] if texto else []}

                except Exception:
                    continue

            if bloque_actual and bloque_actual["asignatura"]:
                ajustar_bloque(bloque_actual)
                horario_interno["horario"][dia].append(bloque_actual)

        # POST-PROCESAMIENTO Y TRANSFORMACIÓN
        eventos_lista = []
        for dia in COLUMNAS_X:
            for evento in horario_interno["horario"][dia]:
                try:
                    h_inicio_todas = re.findall(r'\d{1,2}:\d{2}', str(evento.get("hora_inicio", "")))
                    h_fin_todas = re.findall(r'\d{1,2}:\d{2}', str(evento.get("hora_fin", "")))

                    h_inicio_limpia = h_inicio_todas[0] if h_inicio_todas else evento.get("hora_inicio", "")
                    h_fin_limpia = h_fin_todas[-1] if h_fin_todas else evento.get("hora_fin", "")

                    eventos_lista.append({
                        "dia": dia,
                        "asignatura": evento.get("asignatura", "Desconocida"),
                        "inicio": h_inicio_limpia,
                        "fin": h_fin_limpia
                    })
                except Exception:
                    continue

        return {
            "profesor": {
                "nombre": horario_interno["profesor"],
                "codigo": horario_interno["codigo"]
            },
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