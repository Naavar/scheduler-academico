"""
Constantes centralizadas del proyecto.

Todas las constantes reutilizadas entre módulos se definen aquí
para evitar duplicación y facilitar el mantenimiento.
"""

# =============================================================================
# DÍAS DE LA SEMANA
# =============================================================================

DIAS_VALIDOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
DIA_A_IDX = {d: i for i, d in enumerate(DIAS_VALIDOS)}

# =============================================================================
# NOMBRES DE ARCHIVO POR DEFECTO
# =============================================================================

DEFAULT_PDF_NAME = "HORARIOS_25_26 - Docentes_anon.pdf"
DEFAULT_JSON_NAME = "horarios_consolidados.json"
DEFAULT_RESULTS_NAME = "resultados_evaluacion.json"
DEFAULT_CONFIG_NAME = "config.json"
DEFAULT_EXPORT_EXCEL_NAME = "sesion_evaluacion.xlsx"
EXPORT_SHEET_NAME = "Evaluación"

# =============================================================================
# CONFIGURACIÓN DE HORARIOS
# =============================================================================

SESIONES_POR_DIA = 16
SEPTIMA_HORA_IDX = 10
DURACION_MINUTOS = 55
MAX_SESIONES_POR_DIA = 20
MINUTOS_POR_HORA = 60

# =============================================================================
# PESOS Y PENALIZACIONES (buscador)
# =============================================================================

PESO_SIN_SESIONES = 8
PESO_SEPTIMA_HORA = 2
PESO_RECREO = 3
PESO_HORA_NO_OBLIGATORIA = 2
PENALIZACION_MAX = 8
SCORE_DESEMPATE_MULTIPLICADOR = 100

# =============================================================================
# STRINGS PLACEHOLDER / SENTINEL
# =============================================================================

NOMBRE_DESCONOCIDO = "Desconocido"
CODIGO_NO_DISPONIBLE = "N/A"

# =============================================================================
# NIVELES EDUCATIVOS
# =============================================================================

NIVEL_ESO = "ESO"
NIVEL_BACHILLERATO = "BACHILLERATO"
NIVEL_FP = "FP"
NIVEL_ESPECIALIZACION = "ESPECIALIZACION"

NIVEL_CONFIG_ALIAS = {
    "BACHILLERATO": "BACH",
}

NIVELES_DEFAULT = ["ESO", "BACH", "FP"]

# =============================================================================
# PREFIJOS DE ESPECIALIZACIÓN
# =============================================================================

ESPECIALIZACION_PREFIJOS = {"BIG-D", "CIB-R", "VIR-V", "PYT"}

# Código administrativo a ignorar en clasificación
CODIGO_ADMINISTRATIVO_IGNORAR = "1104"

# =============================================================================
# PATRONES REGEX
# =============================================================================

REGEX_HORA = r"^\d{1,2}:\d{2}$"
REGEX_HORA_BUSCAR = r'\d{1,2}:\d{2}'
REGEX_CODIGO_GRUPO = r'\b[\w-]+~[\w-]*'
REGEX_PREFIJO_GRUPO = r'\b([\w-]+)~[\w-]*'
REGEX_CODIGO_AULA = r'\b[A-Z]\d{2}\b'
REGEX_SEMI = r'\bSEMI\d*\b'
REGEX_SALA_LAB = r'\b[A-Z]{2,}-\d+\b'
REGEX_ESO = r'^E[1-4][A-Z]$'
REGEX_DIV = r'^DIV[34]$'
REGEX_BACH = r'^B[12]'

# =============================================================================
# DETECCIÓN DE COLORES (extracción PDF)
# =============================================================================

COLOR_UMBRAL_BLANCO_MIN = 0.94
COLOR_UMBRAL_BLANCO_PURO = 0.99
COLOR_UMBRAL_GRIS_MIN = 0.9
COLOR_UMBRAL_VARIACION_MAX = 0.05
COLOR_AREA_MIN_RATIO = 0.3

# =============================================================================
# DETECCIÓN DE RECREO
# =============================================================================

RECREO_MANANA = ("11:00", "11:30")
RECREO_MEDIODIA = ("14:15", "14:25")
RECREO_TARDE = ("18:05", "18:35")
RECREO_KEYWORD = "recreo"
RECREOS_DEFAULT = [RECREO_MANANA, RECREO_MEDIODIA, RECREO_TARDE]

# =============================================================================
# SIMILITUD DE TEXTOS
# =============================================================================

SIMILITUD_MIN_RATIO = 0.7
SIMILITUD_MIN_LONGITUD = 20

# =============================================================================
# LAYOUT PDF (coordenadas de extracción)
# =============================================================================

COLUMNAS_X = {
    "Lunes": (80, 175),
    "Martes": (175, 270),
    "Miércoles": (270, 365),
    "Jueves": (365, 460),
    "Viernes": (460, 555),
}
COLUMNA_HORAS_X = (0, 80)
CABECERA_ALTURA = 130
Y_INICIO_TABLA = 145
MIN_ANCHO_LINEA = 50
MIN_SEPARACION_LINEAS = 5
ALTO_FILA_DEFAULT = 35
MIN_CROP_SIZE = 6
CROP_INSET = 2