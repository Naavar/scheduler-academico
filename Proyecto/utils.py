import re
from datetime import datetime, timedelta

def es_color_valido(color):
    """Filtra colores de fondo (blancos/grises claros)"""
    if not color: return False
    try:
        r, g, b = color
        return not (r > 0.9 and g > 0.9 and b > 0.9)
    except:
        return False

def colores_son_iguales(c1, c2):
    """Compara si dos colores son visualmente similares"""
    if c1 is None and c2 is None: return True
    if c1 is None or c2 is None: return False
    try:
        return all(abs(a - b) < 0.05 for a, b in zip(c1, c2))
    except:
        return False

def textos_son_similares(texto1, texto2):
    """Verifica similitud semántica entre dos textos"""
    if not texto1 or not texto2: return False
    try:
        t1, t2 = texto1.lower().strip(), texto2.lower().strip()
        if t1 == t2: return True
        if len(t1) < 20 or len(t2) < 20: return False
        min_len = min(len(t1), len(t2))
        if min_len >= 20 and t1[:20] == t2[:20]:
            palabras1, palabras2 = set(t1.split()), set(t2.split())
            comunes = palabras1 & palabras2
            total = palabras1 | palabras2
            return (len(comunes) / len(total)) >= 0.7 if total else False
    except:
        return False
    return False

def limpiar_texto(txt):
    """Elimina espacios extra y saltos de línea"""
    if not txt: return ""
    return " ".join(txt.split())

def sumar_55_minutos(hora_str):
    """Suma 55 minutos a una hora en formato HH:MM"""
    try:
        if not hora_str: return hora_str
        match = re.search(r'(\d{1,2}:\d{2})', str(hora_str))
        if not match: return hora_str
        t = datetime.strptime(match.group(1), "%H:%M")
        return (t + timedelta(minutes=55)).strftime("%H:%M")
    except:
        return hora_str

def es_hora_recreo(texto_hora, texto_celda=""):
    """Detecta si un bloque corresponde al recreo"""
    try:
        hora = str(texto_hora).lower()
        contenido = str(texto_celda).lower().strip()
        if "11:00" in hora and "11:30" in hora: return True
        if "18:05" in hora and "18:35" in hora: return True
        if contenido == "recreo": return True
        if hora.startswith('[') and hora.endswith(']'):
            coords = hora[1:-1].split('-')
            if len(coords) == 2 and (float(coords[1]) - float(coords[0])) < 25: return True
    except:
        pass
    return False