from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


DIAS_VALIDOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
DIA_A_IDX = {d: i for i, d in enumerate(DIAS_VALIDOS)}


def hora_a_minutos(h: str) -> int:
    hh, mm = h.strip().split(":")
    return int(hh) * 60 + int(mm)


def construir_slots_unitarios(profesores: List[dict], recreos: Set[str]) -> List[Tuple[str, str]]:
    puntos: Set[int] = set()
    for prof in profesores:
        for evento in prof.get("eventos", []):
            ini = evento.get("inicio", "").strip()
            fin = evento.get("fin", "").strip()
            if ini and fin:
                puntos.add(hora_a_minutos(ini))
                puntos.add(hora_a_minutos(fin))

    puntos_ordenados = sorted(puntos)
    recreos_min = {hora_a_minutos(r) for r in recreos}

    franjas = []
    for i in range(len(puntos_ordenados) - 1):
        ini_min = puntos_ordenados[i]
        fin_min = puntos_ordenados[i + 1]
        if ini_min not in recreos_min:
            ini_str = f"{ini_min // 60}:{ini_min % 60:02d}"
            fin_str = f"{fin_min // 60}:{fin_min % 60:02d}"
            franjas.append((ini_str, fin_str))

    return franjas


@dataclass
class Indices:
    franjas: List[Tuple[str, str]]
    franja_a_idx: Dict[str, int]
    ocupado: Dict[str, Set[Tuple[int, int]]] = field(default_factory=dict)
    ocupado_por_dia: Dict[str, Dict[int, List[int]]] = field(default_factory=dict)
    advertencias: List[str] = field(default_factory=list)


def build_indices(profesores: List[dict], recreos: Set[str]) -> Indices:
    franjas = construir_slots_unitarios(profesores, recreos)
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


def penalizacion(
    codigo: str,
    dia_idx: int,
    franja_idx: int,
    indices: Indices,
    penalizacion_max: int = 7,
) -> Tuple[int, Optional[int]]:
    franjas_dia = indices.ocupado_por_dia.get(codigo, {}).get(dia_idx, [])

    if not franjas_dia:
        return penalizacion_max, None

    pos = bisect.bisect_left(franjas_dia, franja_idx)
    mejor_dist = float("inf")
    cercana = None

    if pos < len(franjas_dia):
        dist = abs(franjas_dia[pos] - franja_idx)
        if dist < mejor_dist:
            mejor_dist, cercana = dist, franjas_dia[pos]

    if pos > 0:
        dist = abs(franjas_dia[pos - 1] - franja_idx)
        if dist < mejor_dist:
            mejor_dist, cercana = dist, franjas_dia[pos - 1]

    return int(mejor_dist), cercana


def generar_candidatos(
    equipo_codigos: Set[str],
    indices: Indices,
) -> List[Tuple[int, int]]:
    slots_calendario = [
        (dia_idx, f_idx)
        for dia_idx in range(len(DIAS_VALIDOS))
        for f_idx in range(len(indices.franjas))
    ]
    return [
        slot for slot in slots_calendario
        if all(
            slot not in indices.ocupado.get(cod, set())
            for cod in equipo_codigos
        )
    ]


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
    detalle: List[DetalleProfesor] = field(default_factory=list)
    explicacion: str = ""


def find_best_slot(
    profesores: List[dict],
    equipo_codigos: Set[str],
    indices: Indices,
    penalizacion_max: int = 7,
) -> Resultado:
    nombre_por_codigo = {
        p["profesor"]["codigo"]: p["profesor"]["nombre"]
        for p in profesores
    }
    equipo_lista = sorted(equipo_codigos)
    candidatos = generar_candidatos(equipo_codigos, indices)

    if not candidatos:
        return Resultado(
            sin_solucion=True,
            explicacion="No existe ningún slot libre común para todos los profesores.",
        )

    def score(slot):
        dia_idx, f_idx = slot
        total, peor = 0, 0
        for cod in equipo_lista:
            pen, _ = penalizacion(cod, dia_idx, f_idx, indices, penalizacion_max)
            total += pen
            peor = max(peor, pen)
        return (total, peor, dia_idx * 100 + f_idx)

    candidatos_ordenados = sorted(candidatos, key=score)

    INF = float("inf")
    mejor_score = (INF, INF, INF)
    mejor_slot = None
    mejor_detalle = []

    for slot in candidatos_ordenados:
        dia_idx, f_idx = slot
        suma_parcial, max_parcial = 0, 0
        detalle_actual = []
        podado = False

        for cod in equipo_lista:
            pen, cercana_idx = penalizacion(cod, dia_idx, f_idx, indices, penalizacion_max)
            suma_parcial += pen
            max_parcial = max(max_parcial, pen)

            sesion_cercana = None
            if cercana_idx is not None:
                sesion_cercana = indices.franjas[cercana_idx]

            detalle_actual.append(DetalleProfesor(
                codigo=cod,
                nombre=nombre_por_codigo.get(cod, cod),
                penalizacion=pen,
                sesion_ocupada_mas_cercana=sesion_cercana,
                tiene_eventos_ese_dia=(cercana_idx is not None),
            ))

            mejor_coste, mejor_peor, _ = mejor_score
            if suma_parcial > mejor_coste:
                podado = True
                break
            if suma_parcial == mejor_coste and max_parcial >= mejor_peor:
                podado = True
                break

        if not podado:
            score_actual = (suma_parcial, max_parcial, dia_idx * 100 + f_idx)
            if score_actual < mejor_score:
                mejor_score = score_actual
                mejor_slot = slot
                mejor_detalle = detalle_actual

    coste_final, peor_final, _ = mejor_score
    dia_idx_final, f_idx_final = mejor_slot
    ini, fin = indices.franjas[f_idx_final]

    return Resultado(
        sin_solucion=False,
        dia=DIAS_VALIDOS[dia_idx_final],
        hora_inicio=ini,
        hora_fin=fin,
        coste_total=coste_final,
        peor_penalizacion=peor_final,
        detalle=mejor_detalle,
    )


def buscar_sesion_evaluacion(
    profesores: List[dict],
    equipo_codigos: Set[str],
    recreos: Set[str],
    penalizacion_max: int = 7,
) -> Resultado:
    indices = build_indices(profesores, recreos)
    return find_best_slot(profesores, equipo_codigos, indices, penalizacion_max)