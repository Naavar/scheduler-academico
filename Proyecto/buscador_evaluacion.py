from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    from config import Config
except ImportError:
    Config = None  # type: ignore


DIAS_VALIDOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
DIA_A_IDX = {d: i for i, d in enumerate(DIAS_VALIDOS)}


# ---------------------------------------------------------------------------
# Utilidades de tiempo
# ---------------------------------------------------------------------------

def hora_a_minutos(h: str) -> int:
    hh, mm = h.strip().split(":")
    return int(hh) * 60 + int(mm)


def minutos_a_hora(m: int) -> str:
    return f"{m // 60}:{m % 60:02d}"


# ---------------------------------------------------------------------------
# Construcción de franjas horarias unitarias
# ---------------------------------------------------------------------------

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

    permitir_recreo = config.permitir_recreo if config else False
    recreos_min: Set[int] = set()
    if not permitir_recreo:
        recreos_min = {hora_a_minutos(r) for r in recreos}

    franjas = []
    for i in range(len(puntos_ordenados) - 1):
        ini_min = puntos_ordenados[i]
        fin_min = puntos_ordenados[i + 1]
        if ini_min not in recreos_min:
            franjas.append((minutos_a_hora(ini_min), minutos_a_hora(fin_min)))

    # No recortamos franjas porque si se han detectado trozos pequeños (20 min, 30 min)
    # la longitud de franjas puede ser > 10, y truncarlas a 6 (sesiones_por_dia - 1)
    # destruiría toda la tarde y media mañana.
    
    return franjas


# ---------------------------------------------------------------------------
# Índices de ocupación
# ---------------------------------------------------------------------------

@dataclass
class Indices:
    franjas: List[Tuple[str, str]]
    franja_a_idx: Dict[str, int]
    ocupado: Dict[str, Set[Tuple[int, int]]] = field(default_factory=dict)
    ocupado_por_dia: Dict[str, Dict[int, List[int]]] = field(default_factory=dict)
    advertencias: List[str] = field(default_factory=list)


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

            if codigo not in indices.ocupado:
                indices.ocupado[codigo] = set()
                indices.ocupado_por_dia[codigo] = {}

            for f_idx, (f_ini, f_fin) in enumerate(franjas):
                f_ini_min = hora_a_minutos(f_ini)
                f_fin_min = hora_a_minutos(f_fin)
                if f_ini_min >= ini_min and f_fin_min <= fin_min:
                    indices.ocupado[codigo].add((dia_idx, f_idx))
                    if dia_idx not in indices.ocupado_por_dia[codigo]:
                        indices.ocupado_por_dia[codigo][dia_idx] = []
                    if f_idx not in indices.ocupado_por_dia[codigo][dia_idx]:
                        indices.ocupado_por_dia[codigo][dia_idx].append(f_idx)

    for codigo in indices.ocupado_por_dia:
        for dia_idx in indices.ocupado_por_dia[codigo]:
            indices.ocupado_por_dia[codigo][dia_idx].sort()

    return indices


# ---------------------------------------------------------------------------
# Sistema de pesos
# ---------------------------------------------------------------------------

def calcular_peso_base(franjas_dia: List[int], franja_idx: int) -> int:
    """
    Peso base = distancia mínima al evento más cercano ese día.
    Si no tiene sesiones → 8.
    """
    if not franjas_dia:
        return 8
    pos = bisect.bisect_left(franjas_dia, franja_idx)
    mejor_dist = float("inf")
    if pos < len(franjas_dia):
        mejor_dist = min(mejor_dist, abs(franjas_dia[pos] - franja_idx))
    if pos > 0:
        mejor_dist = min(mejor_dist, abs(franjas_dia[pos - 1] - franja_idx))
    return int(mejor_dist)


def calcular_peso(
    codigo: str,
    dia_idx: int,
    franja_idx: int,
    indices: Indices,
    config=None,
) -> int:
    """
    Tabla de pesos:
      - Sin sesiones ese día         → base = 8
      - Distancia a sesión cercana   → base = distancia
      - 7ª hora (permitida)          → +2
      - Recreo (permitido)           → +3
      - Hora no obligatoria          → +2
    """
    franjas_dia = indices.ocupado_por_dia.get(codigo, {}).get(dia_idx, [])
    peso = calcular_peso_base(franjas_dia, franja_idx)

    if config is None:
        return peso

    if config.permitir_septima_hora and franja_idx == config.sesiones_por_dia - 1:
        peso += 2

    recreo_idx = _indice_recreo(indices, config)
    if config.permitir_recreo and recreo_idx is not None and franja_idx == recreo_idx:
        peso += 3

    if config.permitir_horas_no_obligatorias:
        horas_no_obl = _horas_no_obligatorias(codigo, indices)
        ini_min = hora_a_minutos(indices.franjas[franja_idx][0])
        if ini_min in horas_no_obl:
            peso += 2

    return peso


def _indice_recreo(indices: Indices, config) -> Optional[int]:
    if config is None:
        return None
    recreo_pos = config.hora_recreo - 1
    if 0 <= recreo_pos < len(indices.franjas):
        return recreo_pos
    return None


def _horas_no_obligatorias(codigo: str, indices: Indices) -> Set[int]:
    # TODO: leer del JSON cuando esté disponible
    return set()


def _detectar_recreo(profesores: List[dict], config=None) -> Set[str]:
    """
    Deshabilitado: La detección dinámica falla con solapamientos de turnos
    y borra slots reales de clase. Es mejor usar config.hora_recreo.
    """
    return set()


# ---------------------------------------------------------------------------
# Generación de candidatos
# ---------------------------------------------------------------------------

def generar_candidatos(
    equipo_codigos: Set[str],
    indices: Indices,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
) -> List[Tuple[int, int, int]]:
    dias_idx = (
        [DIA_A_IDX[d] for d in dias_disponibles if d in DIA_A_IDX]
        if dias_disponibles
        else list(range(len(DIAS_VALIDOS)))
    )

    candidatos = []
    n_franjas = len(indices.franjas)

    for dia_idx in dias_idx:
        for f_start in range(n_franjas):
            minutos_acumulados = 0
            for f_end in range(f_start, n_franjas):
                if any(
                    (dia_idx, f_end) in indices.ocupado.get(cod, set())
                    for cod in equipo_codigos
                ):
                    break
                ini_min = hora_a_minutos(indices.franjas[f_end][0])
                fin_min = hora_a_minutos(indices.franjas[f_end][1])
                minutos_acumulados += fin_min - ini_min
                if duracion_minutos == 0 or minutos_acumulados >= duracion_minutos:
                    candidatos.append((dia_idx, f_start, f_end))
                    if duracion_minutos == 0:
                        break

    return candidatos


# ---------------------------------------------------------------------------
# Diagnóstico sin solución
# ---------------------------------------------------------------------------

def diagnostico_sin_solucion(
    equipo_codigos: Set[str],
    indices: Indices,
) -> List[Tuple[str, int]]:
    slots_calendario = [
        (dia_idx, f_idx)
        for dia_idx in range(len(DIAS_VALIDOS))
        for f_idx in range(len(indices.franjas))
    ]
    diagnostico: Dict[str, int] = {}
    for slot in slots_calendario:
        for cod in equipo_codigos:
            if slot in indices.ocupado.get(cod, set()):
                diagnostico[cod] = diagnostico.get(cod, 0) + 1
    return sorted(diagnostico.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------------------
# Dataclasses de resultado
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Backtracking principal
# ---------------------------------------------------------------------------

def find_best_slot(
    profesores: List[dict],
    equipo_codigos: Set[str],
    indices: Indices,
    config=None,
    penalizacion_max: int = 8,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
) -> Resultado:
    nombre_por_codigo = {
        p["profesor"]["codigo"]: p["profesor"].get("nombre", p["profesor"]["codigo"])
        for p in profesores
    }
    equipo_lista = sorted(equipo_codigos)
    candidatos = generar_candidatos(equipo_codigos, indices, dias_disponibles, duracion_minutos)

    if not candidatos:
        ranking = diagnostico_sin_solucion(equipo_codigos, indices)
        return Resultado(
            sin_solucion=True,
            explicacion="No existe ningún slot libre común para todos los profesores.",
            diagnostico_bloqueadores=[
                (nombre_por_codigo.get(cod, cod), n) for cod, n in ranking
            ],
        )

    def score_estimado(candidato):
        dia_idx, f_start, _ = candidato
        total = sum(calcular_peso(cod, dia_idx, f_start, indices, config) for cod in equipo_lista)
        peor  = max(calcular_peso(cod, dia_idx, f_start, indices, config) for cod in equipo_lista)
        return (total, peor, dia_idx * 100 + f_start)

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
                mejor_dist = float("inf")
                for cp in [pos, pos - 1]:
                    if 0 <= cp < len(franjas_dia):
                        dist = abs(franjas_dia[cp] - f_start)
                        if dist < mejor_dist:
                            mejor_dist, cercana_idx = dist, franjas_dia[cp]

            sesion_cercana = indices.franjas[cercana_idx] if cercana_idx is not None else None
            detalle_actual.append(DetalleProfesor(
                codigo=cod,
                nombre=nombre_por_codigo.get(cod, cod),
                penalizacion=pen,
                sesion_ocupada_mas_cercana=sesion_cercana,
                tiene_eventos_ese_dia=bool(franjas_dia),
            ))

            mejor_coste, mejor_peor, _ = mejor_score
            if suma_parcial > mejor_coste or (
                suma_parcial == mejor_coste and max_parcial >= mejor_peor
            ):
                podado = True
                break

        if not podado:
            score_actual = (suma_parcial, max_parcial, dia_idx * 100 + f_start)
            if score_actual < mejor_score:
                mejor_score = score_actual
                mejor_slot = candidato
                mejor_detalle = detalle_actual

    coste_final, peor_final, _ = mejor_score
    dia_idx_final, f_start_final, f_end_final = mejor_slot
    ini = indices.franjas[f_start_final][0]
    fin = indices.franjas[f_end_final][1]

    es_recreo = False
    es_septima = False
    if config:
        recreo_idx = _indice_recreo(indices, config)
        es_recreo  = config.permitir_recreo and recreo_idx == f_start_final
        es_septima = config.permitir_septima_hora and f_start_final == config.sesiones_por_dia - 1

    return Resultado(
        sin_solucion=False,
        dia=DIAS_VALIDOS[dia_idx_final],
        hora_inicio=ini,
        hora_fin=fin,
        coste_total=coste_final,
        peor_penalizacion=peor_final,
        es_recreo=es_recreo,
        es_septima=es_septima,
        detalle=mejor_detalle,
    )


# ---------------------------------------------------------------------------
# Bloqueo de slots ya asignados (anti-solapamiento entre cursos)  ← NUEVO
# ---------------------------------------------------------------------------

def bloquear_slots_asignados(
    indices: Indices,
    resultados_previos: Dict[str, "Resultado"],
) -> Indices:
    """
    Marca como ocupados todos los slots que abarca una reunión asignada
    a los profesores que participaron en ella.
    """
    for curso, resultado in resultados_previos.items():
        if resultado.sin_solucion or not resultado.hora_inicio or not resultado.hora_fin:
            continue

        dia_idx = DIA_A_IDX.get(resultado.dia)
        if dia_idx is None:
            continue

        ini_min = hora_a_minutos(resultado.hora_inicio)
        fin_min = hora_a_minutos(resultado.hora_fin)

        franjas_a_bloquear = []
        for f_idx, (f_ini, f_fin) in enumerate(indices.franjas):
            f_i_min = hora_a_minutos(f_ini)
            f_f_min = hora_a_minutos(f_fin)
            # si hay solapamiento estricto en el tiempo
            if f_i_min < fin_min and f_f_min > ini_min:
                franjas_a_bloquear.append(f_idx)

        for detalle in resultado.detalle:
            codigo = detalle.codigo

            if codigo not in indices.ocupado:
                indices.ocupado[codigo] = set()
                indices.ocupado_por_dia[codigo] = {}

            for f_idx in franjas_a_bloquear:
                indices.ocupado[codigo].add((dia_idx, f_idx))
                if dia_idx not in indices.ocupado_por_dia[codigo]:
                    indices.ocupado_por_dia[codigo][dia_idx] = []
                if f_idx not in indices.ocupado_por_dia[codigo][dia_idx]:
                    indices.ocupado_por_dia[codigo][dia_idx].append(f_idx)
                    indices.ocupado_por_dia[codigo][dia_idx].sort()

    return indices


# ---------------------------------------------------------------------------
# Función de entrada pública
# ---------------------------------------------------------------------------

def buscar_sesion_evaluacion(
    profesores: List[dict],
    equipo_codigos: Set[str],
    config=None,
    penalizacion_max: int = 8,
    dias_disponibles: Optional[List[str]] = None,
    duracion_minutos: int = 0,
    resultados_previos: Optional[Dict[str, "Resultado"]] = None,  # ← NUEVO
) -> Resultado:
    """
    Punto de entrada principal.

    El recreo se detecta automáticamente del JSON (gap >= 30 min).
    Si se pasan resultados_previos, los slots ya asignados a otros cursos
    se bloquean antes de buscar, evitando que un profesor coincida en
    dos reuniones a la vez.
    """
    recreos = _detectar_recreo(profesores, config)
    indices = build_indices(profesores, recreos, config)

    if resultados_previos:
        indices = bloquear_slots_asignados(indices, resultados_previos)  # ← NUEVO

    return find_best_slot(
        profesores,
        equipo_codigos,
        indices,
        config=config,
        penalizacion_max=penalizacion_max,
        dias_disponibles=dias_disponibles,
        duracion_minutos=duracion_minutos,
    )