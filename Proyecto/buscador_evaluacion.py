"""
buscador_evaluacion.py
----------------------
Sistema completo de búsqueda de sesiones de evaluación.

Integra en un único fichero:
  - Agrupador de grupos por curso desde el JSON
  - Índices de ocupación con 3 capas (real / frozen / artificial)
  - Backtracking real con deshacer entre grupos de un mismo curso
  - Congelado entre cursos para propagar bloqueos correctamente
  - Compatibilidad con la interfaz original de buscar_sesion_evaluacion

Jerarquía resuelta:
    Nivel  (ESO, FP, ESPECIALIZACION)
      └── Curso  (1º ESO, DAW, BIG-D...)
            └── Grupo  (E1A, E1B, 2DAW...)

Patrones de códigos soportados:
    ESO:           E{n}{letra}  →  E3B = 3º ESO grupo B
                   DIV{n}       →  DIV4 = Diversificación 4
    FP:            {n}{CICLO}   →  2DAW, sufijos R/M/N/X/B = subvariantes
    ESPECIALIZACION: BIG-D, CIB-R, VIR-V → cada uno es su propio ciclo
    BACH:          {n}B{letra}  →  1BA, 2BB
"""

from __future__ import annotations

import bisect
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    from Proyecto.constants import (
        DIAS_VALIDOS,
        DIA_A_IDX,
        ESPECIALIZACION_PREFIJOS,
        MINUTOS_POR_HORA,
        PENALIZACION_MAX,
        PESO_SIN_SESIONES,
        PESO_SEPTIMA_HORA,
        PESO_RECREO,
        PESO_HORA_NO_OBLIGATORIA,
        SCORE_DESEMPATE_MULTIPLICADOR,
    )
    from Proyecto.config import Config
    from Proyecto.utils import (
        clasificar_grupos,
        es_hora_recreo,
        limpiar_texto,
    )
except ImportError:
    from constants import (
        DIAS_VALIDOS,
        DIA_A_IDX,
        ESPECIALIZACION_PREFIJOS,
        MINUTOS_POR_HORA,
        PENALIZACION_MAX,
        PESO_SIN_SESIONES,
        PESO_SEPTIMA_HORA,
        PESO_RECREO,
        PESO_HORA_NO_OBLIGATORIA,
        SCORE_DESEMPATE_MULTIPLICADOR,
    )
    from config import Config
    from utils import (
        clasificar_grupos,
        es_hora_recreo,
        limpiar_texto,
    )


# ===========================================================================
# BLOQUE 1 — AGRUPADOR DE GRUPOS POR CURSO
# Usa clasificar_grupos() de utils.py para deducir la jerarquía
# Nivel → Curso → [Grupos] sin lógica hardcodeada aquí
# ===========================================================================

def agrupar_grupos_por_curso(nivel: str, grupos: List[str]) -> Dict[str, List[str]]:
    """
    Dado un nivel y lista de códigos de grupo, devuelve {nombre_curso: [grupos]}.

    Delega la clasificación en clasificar_grupos() de utils.py,
    que ya conoce los patrones ESO/FP/BACH/ESPECIALIZACION del centro.

    Ejemplos:
        nivel="ESO",  grupos=["E3A","E3B","DIV4"] → {"3º ESO": ["E3A","E3B"], "Diversificación 4": ["DIV4"]}
        nivel="FP",   grupos=["1DAW","2DAW","2DAWR"] → {"DAW": ["1DAW","2DAW","2DAWR"]}
        nivel="ESPECIALIZACION", grupos=["BIG-D"] → {"BIG-D": ["BIG-D"]}
    """
    # clasificar_grupos espera un set de prefijos y devuelve
    # {"ESO": [...], "FP": [...], "ESPECIALIZACION": [...], "BACHILLERATO": [...]}
    clasificados = clasificar_grupos(set(grupos))

    # Ahora agrupamos por curso dentro del nivel solicitado
    # Normalizamos el nombre del nivel para buscar en el dict
    nivel_norm = nivel.upper()
    if nivel_norm in ("BACH", "BACHILLERATO"):
        nivel_norm = "BACHILLERATO"
    elif nivel_norm == "ESP":
        nivel_norm = "ESPECIALIZACION"

    grupos_del_nivel = clasificados.get(nivel_norm, grupos)

    # Ahora deducir el curso de cada grupo según el nivel
    cursos: Dict[str, List[str]] = defaultdict(list)

    for g in grupos_del_nivel:
        nombre_curso = _deducir_curso(g, nivel_norm)
        cursos[nombre_curso].append(g)

    # Ordenar grupos dentro de cada curso y cursos entre sí
    def _orden_curso(nombre):
        m = re.match(r'^(\d)', nombre)
        return (0, int(m.group(1)), nombre) if m else (1, 0, nombre)

    return {k: sorted(v) for k, v in sorted(cursos.items(), key=lambda x: _orden_curso(x[0]))}


def _deducir_curso(grupo: str, nivel: str) -> str:
    """
    Deduce el nombre del curso a partir del código de grupo y el nivel.
    Usa los mismos patrones que clasificar_grupos() en utils.py.
    """
    if nivel == "ESO":
        m = re.match(r'^E(\d)[A-Z]+$', grupo)
        if m:
            return f"{m.group(1)}º ESO"
        m = re.match(r'^DIV(\d+)$', grupo)
        if m:
            return f"Diversificación {m.group(1)}"
        return grupo

    elif nivel == "FP":
        if grupo and grupo[0].isdigit():
            ciclo_raw = grupo[1:]
            # Intentar quitar sufijos conocidos para obtener el ciclo base
            for sufijo_len in (2, 1):
                if len(ciclo_raw) > sufijo_len:
                    candidato = ciclo_raw[:-sufijo_len]
                    # Si el candidato no tiene dígitos es probablemente el ciclo
                    if candidato.isalpha():
                        # Verificar que el resto (sufijo) también es alfa
                        sufijo = ciclo_raw[len(candidato):]
                        if sufijo.isalpha():
                            return candidato
            return ciclo_raw  # sin sufijo reconocible
        return grupo

    elif nivel == "BACHILLERATO":
        m = re.match(r'^(\d)B[A-Z]+$', grupo)
        if m:
            return f"{m.group(1)}º Bach"
        return grupo

    elif nivel == "ESPECIALIZACION":
        # Cada prefijo de especialización es su propio ciclo independiente
        # ESPECIALIZACION_PREFIJOS viene de utils.py: {"BIG-D","CIB-R","VIR-V","PYT"}
        if grupo in ESPECIALIZACION_PREFIJOS:
            return grupo
        # Grupo desconocido → agrupar bajo "Otros" para no perderlo
        return "Otros"

    return grupo


def construir_equipos_por_nivel(
    nivel: str,
    profesores_json: List[dict],
) -> Dict[str, Dict[str, Set[str]]]:
    """
    Dado un nivel y el JSON completo, devuelve:
    {nombre_curso: {codigo_grupo: {codigos_profesores}}}

    Ejemplo:
    {
        "3º ESO": {
            "E3A": {"PROF001", "PROF004"},
            "E3B": {"PROF001", "PROF004"},
        }
    }
    """
    todos_grupos: Set[str] = set()
    for entrada in profesores_json:
        todos_grupos.update(entrada.get("grupos", {}).get(nivel, []))

    if not todos_grupos:
        return {}

    agrupacion = agrupar_grupos_por_curso(nivel, list(todos_grupos))

    equipos: Dict[str, Dict[str, Set[str]]] = {}
    for nombre_curso, grupos_del_curso in agrupacion.items():
        equipos[nombre_curso] = {}
        for grupo in grupos_del_curso:
            equipo: Set[str] = set()
            for entrada in profesores_json:
                codigo = entrada.get("profesor", {}).get("codigo")
                if codigo and grupo in set(entrada.get("grupos", {}).get(nivel, [])):
                    equipo.add(codigo)
            if equipo:
                equipos[nombre_curso][grupo] = equipo
        if not equipos[nombre_curso]:
            del equipos[nombre_curso]

    return equipos


def niveles_en_json(profesores_json: List[dict]) -> List[str]:
    """Devuelve los niveles que tienen al menos un grupo en el JSON."""
    niveles: Set[str] = set()
    for entrada in profesores_json:
        for nivel, grupos in entrada.get("grupos", {}).items():
            if grupos:
                niveles.add(nivel)
    return sorted(niveles)


def cargar_json(ruta: str) -> List[dict]:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ===========================================================================
# BLOQUE 2 — UTILIDADES DE TIEMPO
# ===========================================================================

def hora_a_minutos(h: str) -> int:
    hh, mm = h.strip().split(":")
    return int(hh) * MINUTOS_POR_HORA + int(mm)


def minutos_a_hora(m: int) -> str:
    return f"{m // MINUTOS_POR_HORA}:{m % MINUTOS_POR_HORA:02d}"


# ===========================================================================
# BLOQUE 3 — FRANJAS HORARIAS UNITARIAS
# Se generan dinámicamente desde los propios eventos del JSON
# ===========================================================================

def construir_slots_unitarios(
    profesores: List[dict],
    recreos: Set[str],
    config=None,
) -> List[Tuple[str, str]]:
    puntos: Set[int] = set()
    for prof in profesores:
        for evento in prof.get("eventos", []):
            ini = evento.get("inicio", "").strip()
            fin = evento.get("fin", "").strip()
            if ini and fin:
                puntos.add(hora_a_minutos(ini))
                puntos.add(hora_a_minutos(fin))

    puntos_ordenados = sorted(puntos)

    recreos_min: Set[int] = set()
    if not (config and config.permitir_recreo):
        recreos_min = {hora_a_minutos(r) for r in recreos}

    # Hora de comer: 14:25-15:20
    # Se excluye cualquier franja que empiece antes de las 15:20 y termine después de las 14:25
    # Esto elimina también franjas adyacentes como 14:15-14:25 que,
    # aunque no solapan, permitirían encadenar reuniones hasta dentro del bloque de comida.
    COMIDA_INI = hora_a_minutos("14:25")
    COMIDA_FIN = hora_a_minutos("15:20")

    franjas = []
    for i in range(len(puntos_ordenados) - 1):
        ini_min = puntos_ordenados[i]
        fin_min = puntos_ordenados[i + 1]
        # Excluir si la franja toca o está dentro del bloque de comida
        toca_comida = fin_min >= COMIDA_INI and ini_min < COMIDA_FIN
        if ini_min not in recreos_min and not toca_comida:
            franjas.append((minutos_a_hora(ini_min), minutos_a_hora(fin_min)))

    return franjas


def _detectar_recreo(profesores: List[dict], config=None) -> Set[str]:
    """
    Detecta horas de recreo usando es_hora_recreo() de utils.py.
    Recorre todos los eventos de todos los profesores y marca como recreo
    los intervalos que es_hora_recreo() identifica (11:00-11:30, 18:05-18:35).
    Si config.permitir_recreo está activo, devuelve set vacío (no se filtra nada).
    """
    if config and config.permitir_recreo:
        return set()

    recreos: Set[str] = set()
    for prof in profesores:
        for evento in prof.get("eventos", []):
            ini = evento.get("inicio", "").strip()
            fin = evento.get("fin", "").strip()
            asignatura = limpiar_texto(evento.get("asignatura", ""))
            hora_str = f"{ini}-{fin}" if ini and fin else ""
            if es_hora_recreo(hora_str, asignatura):
                recreos.add(ini)
    return recreos


# ===========================================================================
# BLOQUE 4 — ÍNDICES DE OCUPACIÓN (3 CAPAS)
#
# ocupado_real       → clases del JSON        → nunca se toca
# ocupado_frozen     → reuniones ya cerradas  → no se puede deshacer
# ocupado_artificial → reuniones en curso     → el backtracking lo maneja
# ===========================================================================

@dataclass
class Indices:
    franjas: List[Tuple[str, str]]
    franja_a_idx: Dict[str, int]

    ocupado_real:       Dict[str, Set[Tuple[int, int]]] = field(default_factory=dict)
    ocupado_frozen:     Dict[str, Set[Tuple[int, int]]] = field(default_factory=dict)
    ocupado_artificial: Dict[str, Set[Tuple[int, int]]] = field(default_factory=dict)

    # Solo refleja clases reales → usado para calcular pesos/distancias
    ocupado_por_dia: Dict[str, Dict[int, List[int]]] = field(default_factory=dict)

    advertencias: List[str] = field(default_factory=list)

    def esta_ocupado(self, codigo: str, dia_idx: int, f_idx: int) -> bool:
        slot = (dia_idx, f_idx)
        return (
            slot in self.ocupado_real.get(codigo, set())
            or slot in self.ocupado_frozen.get(codigo, set())
            or slot in self.ocupado_artificial.get(codigo, set())
        )

    def bloquear(self, codigo: str, dia_idx: int, f_idx: int) -> None:
        """Bloqueo temporal durante el backtracking del curso actual."""
        self.ocupado_artificial.setdefault(codigo, set()).add((dia_idx, f_idx))

    def desbloquear(self, codigo: str, dia_idx: int, f_idx: int) -> None:
        """Deshacer bloqueo temporal (paso de backtracking)."""
        self.ocupado_artificial.get(codigo, set()).discard((dia_idx, f_idx))

    def congelar(self) -> None:
        """
        Cierra el curso actual: bloqueos temporales → frozen.
        Los cursos siguientes no podrán deshacerlos.
        Un profesor que esté en 1ºESO y 2ºESO llegará al 2ºESO
        con las horas de reunión de 1ºESO ya bloqueadas.
        """
        for codigo, slots in self.ocupado_artificial.items():
            self.ocupado_frozen.setdefault(codigo, set()).update(slots)
        self.ocupado_artificial.clear()


def build_indices(profesores: List[dict], recreos: Set[str], config=None) -> Indices:
    franjas = construir_slots_unitarios(profesores, recreos, config)
    franja_a_idx = {ini: i for i, (ini, _) in enumerate(franjas)}
    indices = Indices(franjas=franjas, franja_a_idx=franja_a_idx)

    for prof in profesores:
        codigo = prof.get("profesor", {}).get("codigo")
        if not codigo:
            indices.advertencias.append("Profesor sin código → ignorado.")
            continue

        for evento in prof.get("eventos", []):
            dia_str = evento.get("dia", "")
            ini_str = evento.get("inicio", "").strip()
            fin_str = evento.get("fin", "").strip()

            dia_idx = DIA_A_IDX.get(dia_str)
            if dia_idx is None:
                indices.advertencias.append(f"{codigo}: día '{dia_str}' no reconocido.")
                continue

            ini_min = hora_a_minutos(ini_str)
            fin_min = hora_a_minutos(fin_str)

            for f_idx, (f_ini, f_fin) in enumerate(franjas):
                if hora_a_minutos(f_ini) >= ini_min and hora_a_minutos(f_fin) <= fin_min:
                    indices.ocupado_real.setdefault(codigo, set()).add((dia_idx, f_idx))
                    indices.ocupado_por_dia.setdefault(codigo, {}).setdefault(dia_idx, [])
                    if f_idx not in indices.ocupado_por_dia[codigo][dia_idx]:
                        indices.ocupado_por_dia[codigo][dia_idx].append(f_idx)

    for codigo in indices.ocupado_por_dia:
        for dia_idx in indices.ocupado_por_dia[codigo]:
            indices.ocupado_por_dia[codigo][dia_idx].sort()

    return indices


# ===========================================================================
# BLOQUE 5 — SISTEMA DE PESOS Y PENALIZACIONES
# Peso base = distancia al evento más cercano ese día
# Sin eventos ese día → penalización máxima (8)
# ===========================================================================

def calcular_peso_base(franjas_dia: List[int], franja_idx: int) -> int:
    """
    Peso base = distancia mínima al evento más cercano ese día.
    Si no tiene sesiones → PESO_SIN_SESIONES.
    """
    if not franjas_dia:
        return PESO_SIN_SESIONES
    pos = bisect.bisect_left(franjas_dia, franja_idx)
    mejor = float("inf")
    if pos < len(franjas_dia):
        mejor = min(mejor, abs(franjas_dia[pos] - franja_idx))
    if pos > 0:
        mejor = min(mejor, abs(franjas_dia[pos - 1] - franja_idx))
    return int(mejor)


def calcular_peso(
    codigo: str,
    dia_idx: int,
    franja_idx: int,
    indices: Indices,
    config=None,
) -> int:
    """
    Tabla de pesos:
      - Sin sesiones ese día         → base = PESO_SIN_SESIONES
      - Distancia a sesión cercana   → base = distancia
      - 7ª hora (permitida)          → +PESO_SEPTIMA_HORA
      - Recreo (permitido)           → +PESO_RECREO
      - Hora no obligatoria          → +PESO_HORA_NO_OBLIGATORIA
    """
    franjas_dia = indices.ocupado_por_dia.get(codigo, {}).get(dia_idx, [])
    peso = calcular_peso_base(franjas_dia, franja_idx)

    if config is None:
        return peso

    if config.permitir_septima_hora and franja_idx in _indices_septima(indices, config):
        peso += PESO_SEPTIMA_HORA

    if config.permitir_recreo and franja_idx in _indices_recreo(indices, config):
        peso += PESO_RECREO

    if config.permitir_horas_no_obligatorias:
        ini_min = hora_a_minutos(indices.franjas[franja_idx][0])
        if ini_min in _horas_no_obligatorias(codigo, indices):
            peso += PESO_HORA_NO_OBLIGATORIA

    return peso


def _indices_recreo(indices: Indices, config) -> Set[int]:
    """Devuelve los índices de franja que caen dentro de algún recreo."""
    if config is None:
        return set()
    result = set()
    for (ini_str, fin_str) in getattr(config, "recreos", []):
        ini_min = hora_a_minutos(ini_str)
        fin_min = hora_a_minutos(fin_str)
        for idx, (f_ini, f_fin) in enumerate(indices.franjas):
            if hora_a_minutos(f_ini) >= ini_min and hora_a_minutos(f_fin) <= fin_min:
                result.add(idx)
    return result


def _indices_septima(indices: Indices, config) -> Set[int]:
    """Devuelve el índice de franja correspondiente a la séptima hora."""
    if config is None:
        return set()
    idx = config.septima_hora_idx
    if 0 <= idx < len(indices.franjas):
        return {idx}
    return set()


def _horas_no_obligatorias(codigo: str, indices: Indices) -> Set[int]:
    return set()


# ===========================================================================
# BLOQUE 6 — GENERACIÓN DE CANDIDATOS
# Slots (dia, f_start, f_end) libres para TODOS los profesores del equipo
# Consulta las 3 capas de ocupación
# ===========================================================================

def generar_candidatos(
    equipo_codigos: Set[str],
    indices: Indices,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
    config=None,
) -> List[Tuple[int, int, int]]:
    dias_idx = (
        [DIA_A_IDX[d] for d in dias_disponibles if d in DIA_A_IDX]
        if dias_disponibles
        else list(range(len(DIAS_VALIDOS)))
    )

    franjas_prohibidas: Set[int] = set()
    if config is not None:
        if not config.permitir_septima_hora:
            franjas_prohibidas.update(_indices_septima(indices, config))
        if not config.permitir_recreo:
            franjas_prohibidas |= _indices_recreo(indices, config)

    candidatos = []
    n_franjas = len(indices.franjas)

    for dia_idx in dias_idx:
        for f_start in range(n_franjas):
            if f_start in franjas_prohibidas:
                continue
            minutos_acumulados = 0
            for f_end in range(f_start, n_franjas):
                if f_end in franjas_prohibidas:
                    break
                if any(indices.esta_ocupado(cod, dia_idx, f_end) for cod in equipo_codigos):
                    break
                ini_min = hora_a_minutos(indices.franjas[f_end][0])
                fin_min = hora_a_minutos(indices.franjas[f_end][1])
                minutos_acumulados += fin_min - ini_min
                if duracion_minutos == 0 or minutos_acumulados >= duracion_minutos:
                    candidatos.append((dia_idx, f_start, f_end))
                    if duracion_minutos == 0:
                        break

    return candidatos


# ===========================================================================
# BLOQUE 7 — DATACLASSES DE RESULTADO
# ===========================================================================

@dataclass
class DetalleProfesor:
    codigo: str
    nombre: str
    penalizacion: int
    sesion_ocupada_mas_cercana: Optional[Tuple[str, str]]
    tiene_eventos_ese_dia: bool


@dataclass
class Resultado:
    sin_solucion: bool = False
    dia: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    coste_total: Optional[int] = None
    peor_penalizacion: Optional[int] = None
    es_recreo: bool = False
    es_septima: bool = False
    detalle: List[DetalleProfesor] = field(default_factory=list)
    explicacion: str = ""
    diagnostico_bloqueadores: List[Tuple[str, int]] = field(default_factory=list)


# ===========================================================================
# BLOQUE 8 — BÚSQUEDA DEL MEJOR SLOT PARA UN GRUPO
# Igual que el original pero usando esta_ocupado() en candidatos
# ===========================================================================

def diagnostico_sin_solucion(
    equipo_codigos: Set[str],
    indices: Indices,
) -> List[Tuple[str, int]]:
    diagnostico: Dict[str, int] = {}
    for dia_idx in range(len(DIAS_VALIDOS)):
        for f_idx in range(len(indices.franjas)):
            for cod in equipo_codigos:
                if indices.esta_ocupado(cod, dia_idx, f_idx):
                    diagnostico[cod] = diagnostico.get(cod, 0) + 1
    return sorted(diagnostico.items(), key=lambda x: -x[1])


def find_best_slot(
    profesores: List[dict],
    equipo_codigos: Set[str],
    indices: Indices,
    config=None,
    penalizacion_max: int = PENALIZACION_MAX,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
) -> Resultado:
    nombre_por_codigo = {
        p["profesor"]["codigo"]: p["profesor"].get("nombre", p["profesor"]["codigo"])
        for p in profesores
    }
    equipo_lista = sorted(equipo_codigos)
    candidatos = generar_candidatos(equipo_codigos, indices, dias_disponibles, duracion_minutos, config)

    if not candidatos:
        ranking = diagnostico_sin_solucion(equipo_codigos, indices)
        return Resultado(
            sin_solucion=True,
            explicacion="No existe ningún slot libre común para todos los profesores.",
            diagnostico_bloqueadores=[
                (nombre_por_codigo.get(cod, cod), n) for cod, n in ranking
            ],
        )

    def score_estimado(c):
        dia_idx, f_start, _ = c
        total = sum(calcular_peso(cod, dia_idx, f_start, indices, config) for cod in equipo_lista)
        peor  = max(calcular_peso(cod, dia_idx, f_start, indices, config) for cod in equipo_lista)
        return (total, peor, dia_idx * SCORE_DESEMPATE_MULTIPLICADOR + f_start)

    candidatos_ordenados = sorted(candidatos, key=score_estimado)
    INF = float("inf")
    mejor_score = (INF, INF, INF)
    mejor_slot = None
    mejor_detalle = []

    for candidato in candidatos_ordenados:
        dia_idx, f_start, f_end = candidato
        suma_parcial, max_parcial = 0, 0
        detalle_actual = []
        podado = False

        for cod in equipo_lista:
            pen = calcular_peso(cod, dia_idx, f_start, indices, config)
            suma_parcial += pen
            max_parcial = max(max_parcial, pen)

            franjas_dia = indices.ocupado_por_dia.get(cod, {}).get(dia_idx, [])
            cercana_idx = None
            if franjas_dia:
                pos = bisect.bisect_left(franjas_dia, f_start)
                mejor_dist = INF
                for cp in [pos, pos - 1]:
                    if 0 <= cp < len(franjas_dia):
                        dist = abs(franjas_dia[cp] - f_start)
                        if dist < mejor_dist:
                            mejor_dist, cercana_idx = dist, franjas_dia[cp]

            detalle_actual.append(DetalleProfesor(
                codigo=cod,
                nombre=nombre_por_codigo.get(cod, cod),
                penalizacion=pen,
                sesion_ocupada_mas_cercana=indices.franjas[cercana_idx] if cercana_idx is not None else None,
                tiene_eventos_ese_dia=bool(franjas_dia),
            ))

            mejor_coste, mejor_peor, _ = mejor_score
            if suma_parcial > mejor_coste or (suma_parcial == mejor_coste and max_parcial >= mejor_peor):
                podado = True
                break

        if not podado:
            score_actual = (suma_parcial, max_parcial, dia_idx * SCORE_DESEMPATE_MULTIPLICADOR + f_start)
            if score_actual < mejor_score:
                mejor_score = score_actual
                mejor_slot = candidato
                mejor_detalle = detalle_actual

    if mejor_slot is None:
        return Resultado(sin_solucion=True, explicacion="No se encontró slot válido.")

    coste_final, peor_final, _ = mejor_score
    dia_idx_final, f_start_final, f_end_final = mejor_slot

    es_recreo = es_septima = False
    if config:
        es_recreo  = config.permitir_recreo and f_start_final in _indices_recreo(indices, config)
        es_septima = config.permitir_septima_hora and f_start_final in _indices_septima(indices, config)

    return Resultado(
        sin_solucion=False,
        dia=DIAS_VALIDOS[dia_idx_final],
        hora_inicio=indices.franjas[f_start_final][0],
        hora_fin=indices.franjas[f_end_final][1],
        coste_total=coste_final,
        peor_penalizacion=peor_final,
        es_recreo=es_recreo,
        es_septima=es_septima,
        detalle=mejor_detalle,
    )


# ===========================================================================
# BLOQUE 9 — HELPERS DE BLOQUEO/DESBLOQUEO PARA BACKTRACKING
# ===========================================================================

def _franjas_en_rango(indices: Indices, resultado: Resultado) -> List[int]:
    ini_min = hora_a_minutos(resultado.hora_inicio)
    fin_min = hora_a_minutos(resultado.hora_fin)
    return [
        f_idx for f_idx, (f_ini, f_fin) in enumerate(indices.franjas)
        if hora_a_minutos(f_ini) < fin_min and hora_a_minutos(f_fin) > ini_min
    ]


def _bloquear_resultado(indices: Indices, resultado: Resultado) -> None:
    if resultado.sin_solucion:
        return
    dia_idx = DIA_A_IDX[resultado.dia]
    for f_idx in _franjas_en_rango(indices, resultado):
        for det in resultado.detalle:
            indices.bloquear(det.codigo, dia_idx, f_idx)


def _desbloquear_resultado(indices: Indices, resultado: Resultado) -> None:
    if resultado.sin_solucion:
        return
    dia_idx = DIA_A_IDX[resultado.dia]
    for f_idx in _franjas_en_rango(indices, resultado):
        for det in resultado.detalle:
            indices.desbloquear(det.codigo, dia_idx, f_idx)


# ===========================================================================
# BLOQUE 10 — BACKTRACKING ENTRE GRUPOS DE UN CURSO
#
# Para cada grupo prueba todos los candidatos en orden de coste.
# Al asignar uno → bloquea en ocupado_artificial.
# Explora recursivamente el resto de grupos.
# Si no mejora → deshace (desbloquea) y prueba el siguiente candidato.
# Al terminar el curso → congelar() mueve artificial → frozen.
# Los cursos siguientes heredan esos bloqueos y no pueden deshacerlos.
# ===========================================================================

def _construir_resultado_desde_candidato(
    candidato: Tuple[int, int, int],
    equipo_lista: List[str],
    nombre_por_codigo: Dict[str, str],
    indices: Indices,
    config=None,
) -> Resultado:
    dia_idx, f_start, f_end = candidato
    coste, peor = 0, 0
    detalle = []

    for cod in equipo_lista:
        pen = calcular_peso(cod, dia_idx, f_start, indices, config)
        coste += pen
        peor = max(peor, pen)
        franjas_dia = indices.ocupado_por_dia.get(cod, {}).get(dia_idx, [])
        detalle.append(DetalleProfesor(
            codigo=cod,
            nombre=nombre_por_codigo.get(cod, cod),
            penalizacion=pen,
            sesion_ocupada_mas_cercana=None,
            tiene_eventos_ese_dia=bool(franjas_dia),
        ))

    es_recreo = es_septima = False
    if config:
        es_recreo  = config.permitir_recreo and f_start in _indices_recreo(indices, config)
        es_septima = config.permitir_septima_hora and f_start in _indices_septima(indices, config)

    return Resultado(
        sin_solucion=False,
        dia=DIAS_VALIDOS[dia_idx],
        hora_inicio=indices.franjas[f_start][0],
        hora_fin=indices.franjas[f_end][1],
        coste_total=coste,
        peor_penalizacion=peor,
        es_recreo=es_recreo,
        es_septima=es_septima,
        detalle=detalle,
    )


def backtracking_grupos(
    grupos_pendientes: List[dict],
    profesores: List[dict],
    indices: Indices,
    asignaciones: Dict[str, Resultado],
    mejor_global: dict,
    config=None,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
    limite_tiempo: float = 30.0,
    _inicio: Optional[float] = None,
) -> None:
    """
    Backtracking real sobre los grupos de un curso.

    grupos_pendientes : [{"nombre": "E3A", "equipo": {"PROF001", ...}}, ...]
    asignaciones      : resultados parciales de esta rama
    mejor_global      : {"coste": int, "asignaciones": dict} — mejor completa encontrada
    """
    if _inicio is None:
        _inicio = time.time()

    # Límite de tiempo → devuelve el mejor parcial encontrado hasta ahora
    if time.time() - _inicio > limite_tiempo:
        return

    # CASO BASE: todos los grupos asignados → comparar con mejor global
    if not grupos_pendientes:
        coste_total = sum(
            r.coste_total for r in asignaciones.values() if r.coste_total is not None
        )
        if coste_total < mejor_global.get("coste", float("inf")):
            mejor_global["coste"] = coste_total
            mejor_global["asignaciones"] = dict(asignaciones)
        return

    grupo_actual = grupos_pendientes[0]
    resto        = grupos_pendientes[1:]
    equipo_lista = sorted(grupo_actual["equipo"])

    nombre_por_codigo = {
        p["profesor"]["codigo"]: p["profesor"].get("nombre", p["profesor"]["codigo"])
        for p in profesores
    }

    # Generar candidatos válidos dado el estado actual del índice
    candidatos = generar_candidatos(
        grupo_actual["equipo"], indices, dias_disponibles, duracion_minutos, config
    )

    if not candidatos:
        return  # rama muerta, no hay hueco → subir sin actualizar mejor_global

    # Ordenar por coste estimado para explorar primero los más prometedores
    def score(c):
        dia_idx, f_start, _ = c
        total = sum(calcular_peso(cod, dia_idx, f_start, indices, config) for cod in equipo_lista)
        peor  = max(calcular_peso(cod, dia_idx, f_start, indices, config) for cod in equipo_lista)
        return (total, peor, dia_idx * 100 + f_start)

    for candidato in sorted(candidatos, key=score):
        resultado = _construir_resultado_desde_candidato(
            candidato, equipo_lista, nombre_por_codigo, indices, config
        )

        # PODA: coste parcial ya supera al mejor global → saltar
        coste_acumulado = sum(
            r.coste_total for r in asignaciones.values() if r.coste_total is not None
        )
        if coste_acumulado + resultado.coste_total >= mejor_global.get("coste", float("inf")):
            continue

        # 1. DECIDIR
        asignaciones[grupo_actual["nombre"]] = resultado
        _bloquear_resultado(indices, resultado)

        # 2. EXPLORAR
        backtracking_grupos(
            grupos_pendientes=resto,
            profesores=profesores,
            indices=indices,
            asignaciones=asignaciones,
            mejor_global=mejor_global,
            config=config,
            dias_disponibles=dias_disponibles,
            duracion_minutos=duracion_minutos,
            limite_tiempo=limite_tiempo,
            _inicio=_inicio,
        )

        # 3. DESHACER ← aquí está la diferencia real con el sistema anterior
        del asignaciones[grupo_actual["nombre"]]
        _desbloquear_resultado(indices, resultado)


# ===========================================================================
# BLOQUE 11 — SESIÓN DE EVALUACIÓN (ORQUESTADOR)
#
# Construye el índice una sola vez.
# Para cada nivel elegido por el usuario:
#   Lee el JSON → agrupa por curso → backtracking por curso → congela
# Los profesores que cruzan niveles llegan al siguiente con sus horas bloqueadas.
# ===========================================================================

class SesionEvaluacion:
    """
    Uso:
        sesion = SesionEvaluacion(profesores_json, config)
        resultados = sesion.resolver_nivel("ESO", dias=["Lunes","Martes"])
        resultados = sesion.resolver_nivel("FP")
    """

    def __init__(self, profesores_json: List[dict], config=None):
        self.profesores = profesores_json
        self.config = config
        recreos = _detectar_recreo(profesores_json, config)
        # Índice compartido durante toda la sesión
        self.indices = build_indices(profesores_json, recreos, config)
        # Acumula todos los resultados: {nivel: {curso: {grupo: Resultado}}}
        self.resultados: Dict[str, Dict[str, Dict[str, Resultado]]] = {}

    def resolver_nivel(
        self,
        nivel: str,
        dias_disponibles: Optional[List[str]] = None,
        duracion_minutos: int = 0,
        limite_tiempo: float = 30.0,
    ) -> Dict[str, Dict[str, Resultado]]:
        """
        Resuelve todos los cursos del nivel elegido por el usuario.

        Orden:
          1. Agrupa grupos por curso desde el JSON
          2. Para cada curso: backtracking entre sus grupos
          3. Congela: los bloqueos pasan a frozen para los cursos siguientes

        Un profesor en 1ºESO y 2ºESO llega al 2ºESO con las horas
        de las reuniones de 1ºESO ya bloqueadas e intocables.
        """
        equipos = construir_equipos_por_nivel(nivel, self.profesores)

        if not equipos:
            return {}

        resultados_nivel: Dict[str, Dict[str, Resultado]] = {}

        for nombre_curso, grupos_dict in equipos.items():

            # Convertir a lista de dicts para el backtracking
            grupos = [
                {"nombre": codigo_grupo, "equipo": equipo}
                for codigo_grupo, equipo in grupos_dict.items()
            ]

            # Los grupos más restringidos (menos candidatos) van primero
            # → mejor poda, menos ramas exploradas
            grupos = sorted(
                grupos,
                key=lambda g: len(generar_candidatos(
                    g["equipo"], self.indices, dias_disponibles, duracion_minutos, self.config
                ))
            )

            mejor_global: dict = {"coste": float("inf"), "asignaciones": {}}

            backtracking_grupos(
                grupos_pendientes=grupos,
                profesores=self.profesores,
                indices=self.indices,
                asignaciones={},
                mejor_global=mejor_global,
                config=self.config,
                dias_disponibles=dias_disponibles,
                duracion_minutos=duracion_minutos,
                limite_tiempo=limite_tiempo,
            )

            if mejor_global["asignaciones"]:
                resultados_nivel[nombre_curso] = mejor_global["asignaciones"]
            else:
                resultados_nivel[nombre_curso] = {
                    g["nombre"]: Resultado(
                        sin_solucion=True,
                        explicacion=f"Sin solución para {g['nombre']} en {nombre_curso}",
                    )
                    for g in grupos
                }

            # Congelar: cierra este curso
            # Los bloqueos artificiales pasan a frozen y son intocables
            # para todos los cursos y niveles que vengan después
            self.indices.congelar()

        self.resultados[nivel] = resultados_nivel
        return resultados_nivel

    def resumen(self) -> None:
        for nivel, cursos in self.resultados.items():
            print(f"\n{'='*50}\nNIVEL: {nivel}\n{'='*50}")
            for curso, grupos in cursos.items():
                print(f"\n  {curso}:")
                for grupo, r in grupos.items():
                    if r.sin_solucion:
                        print(f"    {grupo}: ❌ SIN SOLUCIÓN")
                    else:
                        print(f"    {grupo}: {r.dia} {r.hora_inicio}–{r.hora_fin} (coste={r.coste_total})")


# ===========================================================================
# BLOQUE 12 — COMPATIBILIDAD CON LA INTERFAZ ORIGINAL
# buscar_sesion_evaluacion sigue funcionando igual que antes
# ===========================================================================

def buscar_sesion_evaluacion(
    profesores: List[dict],
    equipo_codigos: Set[str],
    config=None,
    penalizacion_max: int = PENALIZACION_MAX,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
    resultados_previos: Optional[Dict[str, "Resultado"]] = None,
) -> Resultado:
    """
    Interfaz original para búsqueda de un único grupo.
    Para múltiples grupos con backtracking usar SesionEvaluacion.
    """
    recreos = _detectar_recreo(profesores, config)
    indices = build_indices(profesores, recreos, config)

    if resultados_previos:
        for resultado in resultados_previos.values():
            if not resultado.sin_solucion and resultado.hora_inicio:
                dia_idx = DIA_A_IDX.get(resultado.dia)
                if dia_idx is None:
                    continue
                ini_min = hora_a_minutos(resultado.hora_inicio)
                fin_min = hora_a_minutos(resultado.hora_fin)
                for f_idx, (f_ini, f_fin) in enumerate(indices.franjas):
                    if hora_a_minutos(f_ini) < fin_min and hora_a_minutos(f_fin) > ini_min:
                        for det in resultado.detalle:
                            indices.ocupado_frozen.setdefault(
                                det.codigo, set()
                            ).add((dia_idx, f_idx))

    return find_best_slot(
        profesores=profesores,
        equipo_codigos=equipo_codigos,
        indices=indices,
        config=config,
        penalizacion_max=penalizacion_max,
        dias_disponibles=dias_disponibles,
        duracion_minutos=duracion_minutos,
    )