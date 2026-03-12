import re
from datetime import datetime, timedelta

def es_color_valido(color):
    """Filtra colores de fondo (blancos puros).

    Distingue gris claro de asignaturas (245,245,245 → 0.961,0.961,0.961)
    del blanco vacío (255,255,245 → 1.0,1.0,0.961) usando análisis min/max:
    - Blanco: todos los canales > 0.94 Y al menos uno casi puro (> 0.99)
    - Gris claro: todos ~0.96, ninguno llega a 0.99 → válido como asignatura
    """
    if not color: return False
    try:
        r, g, b = color
        # Es fondo blanco si todos los canales son muy altos Y alguno es ~1.0
        if min(r, g, b) > 0.94 and max(r, g, b) > 0.99:
            return False
        return True
    except:
        return False

def es_color_gris_claro(color):
    """Detecta si un color es el gris claro uniforme (reuniones/guardias).

    Gris claro: todos los canales similares (~0.96) y altos (>0.9).
    Colores de asignatura: al menos un canal es claramente diferente.
    """
    if not color: return False
    try:
        r, g, b = color
        # Gris: todos los canales > 0.9 y variación < 0.05
        return min(r, g, b) > 0.9 and (max(r, g, b) - min(r, g, b)) < 0.05
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

def extraer_nombre_asignatura(texto):
    """Extrae el nombre base de la asignatura, eliminando códigos de grupo
    (XXX~XXX o XXX~ incompletos), códigos de aula (A23, B23, C14, SEMI1,
    FCT-1...) e identificadores.

    Ejemplo:
        'Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23'
        -> 'Aplicaciones ofimáticas'
        '1CAM~1CAMM, 1CAM~1CAMN, 1CAM~ B21'
        -> ''
    """
    if not texto:
        return ""
    # Eliminar códigos de grupo (completos e incompletos): 1SSP~1SSPM, CIB-R~CIB-R, 1CAM~
    limpio = re.sub(r'\b[\w-]+~[\w-]*', '', texto)
    # Eliminar códigos de aula como A23, B23, C14
    limpio = re.sub(r'\b[A-Z]\d{2}\b', '', limpio)
    # Eliminar códigos tipo SEMI1, SEMI2
    limpio = re.sub(r'\bSEMI\d*\b', '', limpio)
    # Eliminar códigos tipo FCT-1, FCT-2 (sala/laboratorio)
    limpio = re.sub(r'\b[A-Z]{2,}-\d+\b', '', limpio)
    # Limpiar comas, puntos y espacios extra
    limpio = re.sub(r'[,\s]+', ' ', limpio).strip()
    return limpio


def textos_son_similares(texto1, texto2):
    """Verifica similitud semántica entre dos textos.

    Compara primero los nombres base de las asignaturas (sin códigos de grupo
    ni aulas). Si los nombres base son claramente distintos, devuelve False
    aunque compartan muchas palabras de código.
    """
    if not texto1 or not texto2: return False
    try:
        t1, t2 = texto1.lower().strip(), texto2.lower().strip()
        if t1 == t2: return True

        # Comparar nombres base de asignaturas (sin códigos de grupo/aula)
        base1 = extraer_nombre_asignatura(texto1).lower()
        base2 = extraer_nombre_asignatura(texto2).lower()
        if base1 and base2:
            # Quitar sufijos numéricos/romanos (I, II, III, 1, 2...) para
            # que "procesos I" y "procesos II" se consideren iguales
            base1_norm = re.sub(r'\s+(i{1,3}|iv|v|vi{0,3}|\d{1,2})$', '', base1)
            base2_norm = re.sub(r'\s+(i{1,3}|iv|v|vi{0,3}|\d{1,2})$', '', base2)
            if base1_norm != base2_norm:
                return False

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
    """Elimina espacios extra, saltos de línea y artefactos PDF (cid:X)"""
    if not txt: return ""
    # Eliminar artefactos de codificación PDF como (cid:0)
    txt = re.sub(r'\(cid:\d+\)', '', txt)
    return " ".join(txt.split())

def sumar_55_minutos(hora_str):
    """Suma 55 minutos a una hora en formato HH:MM"""
    try:
        if not hora_str: return hora_str
        # Extraer todas las horas del string
        horas_encontradas = re.findall(r'(\d{1,2}):(\d{2})', str(hora_str))
        if not horas_encontradas: return hora_str

        # Usar la primera hora encontrada
        h, m = horas_encontradas[0]
        t = datetime.strptime(f"{h}:{m}", "%H:%M")
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

# ==============================================================================
# CLASIFICACIÓN DE GRUPOS
# ==============================================================================

# Códigos conocidos de cursos de especialización
_ESPECIALIZACION_PREFIJOS = {"BIG-D", "CIB-R", "VIR-V", "PYT"}


def extraer_codigos_grupo(texto):
    """Extrae los prefijos de códigos de grupo de un texto de asignatura.

    Los códigos de grupo tienen formato XXX~YYY. Esta función extrae
    la parte antes de ~ (el prefijo) que identifica al grupo.

    Ejemplo:
        'Hacking ético CIB-R~CIB-R B01' -> {'CIB-R'}
        'Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN' -> {'1SSP'}
    """
    if not texto:
        return set()
    # Buscar todos los patrones XXX~YYY o XXX~ (incompletos)
    matches = re.findall(r'\b([\w-]+)~[\w-]*', texto)
    return set(matches)


def clasificar_grupos(prefijos):
    """Clasifica un conjunto de prefijos de grupo en categorías.

    Categorías:
        ESO: E1A-E4D, DIV3, DIV4
        BACHILLERATO: B1..., B2...
        FP: Ciclos formativos (1DAM, 2ASI, 1SMR...)
        ESPECIALIZACION: BIG-D, CIB-R, VIR-V, PYT

    Args:
        prefijos: set de strings con los prefijos (ej: {'1DAM', 'CIB-R'})

    Returns:
        dict con categorías como claves y listas de prefijos como valores.
        Solo se incluyen categorías con al menos un grupo.
    """
    resultado = {
        "ESO": [],
        "BACHILLERATO": [],
        "FP": [],
        "ESPECIALIZACION": [],
    }

    for prefijo in sorted(prefijos):
        # Saltar códigos administrativos (1104~CTVP, etc.)
        if prefijo == "1104":
            continue

        # Cursos de especialización (lista cerrada)
        if prefijo in _ESPECIALIZACION_PREFIJOS:
            resultado["ESPECIALIZACION"].append(prefijo)
        # ESO: E1A, E2B, E3C, E4D, DIV3, DIV4
        elif re.match(r'^E[1-4][A-Z]$', prefijo) or re.match(r'^DIV[34]$', prefijo):
            resultado["ESO"].append(prefijo)
        # Bachillerato: B1..., B2...
        elif re.match(r'^B[12]', prefijo):
            resultado["BACHILLERATO"].append(prefijo)
        # FP: todo lo demás (1DAM, 2ASI, 1SMR, 1FPB, etc.)
        else:
            resultado["FP"].append(prefijo)

    # Eliminar categorías vacías
    return {k: v for k, v in resultado.items() if v}
    
def es_hora_comida(texto_hora):
    """Detecta si un intervalo corresponde a la hora de comer (14:25-15:20).
    Nunca debe usarse para reuniones de evaluación.
    """
    try:
        if "14:25" in str(texto_hora):
            return True
    except:
        pass
    return False