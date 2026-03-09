"""
tests/test_backtracking_optimizado.py
======================================
Verifica rendimiento y diagnóstico de buscador_evaluacion.py.
"""

import time
import pytest
from typing import Set

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Proyecto.buscador_evaluacion import (
    buscar_sesion_evaluacion,
    build_indices,
    calcular_peso,
    diagnostico_sin_solucion,
    generar_candidatos,
    DIAS_VALIDOS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HORAS_BASE = [
    ("8:00", "9:00"),
    ("9:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    ("12:00", "13:00"),
    ("13:00", "14:00"),
    ("14:00", "15:00"),
]

FRANJAS_LECTIVAS = [(ini, fin) for ini, fin in HORAS_BASE if ini != "11:00"]

RECREOS = {"11:00"}

_SLOTS_OCUPADOS_COMUNES = [
    (dia, ini, fin)
    for dia in ["Lunes", "Martes"]
    for ini, fin in FRANJAS_LECTIVAS[:3]
]


def _make_profesor(codigo: str, eventos_por_dia: int = 3) -> dict:
    slots = _SLOTS_OCUPADOS_COMUNES[:eventos_por_dia * 2]
    eventos = [
        {"dia": dia, "inicio": ini, "fin": fin}
        for dia, ini, fin in slots
    ]
    return {"profesor": {"codigo": codigo, "nombre": f"Prof {codigo}"}, "eventos": eventos}


def _make_equipo(n: int, eventos_por_dia: int = 3):
    profesores = [_make_profesor(f"P{i:03d}", eventos_por_dia) for i in range(n)]
    codigos: Set[str] = {f"P{i:03d}" for i in range(n)}
    return profesores, codigos


# ---------------------------------------------------------------------------
# Test 1: Rendimiento con 50 profesores
# ---------------------------------------------------------------------------

def test_rendimiento_50_profesores():
    profesores, codigos = _make_equipo(50, eventos_por_dia=2)

    inicio = time.perf_counter()
    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
    )
    elapsed = time.perf_counter() - inicio

    print(f"\n⏱  Tiempo con 50 profesores: {elapsed:.3f}s")
    assert elapsed < 2.0, f"Tardó {elapsed:.3f}s — debe ser < 2s"
    assert not resultado.sin_solucion, "Se esperaba una solución válida"


# ---------------------------------------------------------------------------
# Test 2: Rendimiento con 50 profesores muy ocupados
# ---------------------------------------------------------------------------

def test_rendimiento_50_profesores_ocupados():
    profesores, codigos = _make_equipo(50, eventos_por_dia=4)

    inicio = time.perf_counter()
    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
    )
    elapsed = time.perf_counter() - inicio

    print(f"\n⏱  Tiempo con 50 profesores ocupados: {elapsed:.3f}s")
    assert elapsed < 2.0, f"Tardó {elapsed:.3f}s — debe ser < 2s"


# ---------------------------------------------------------------------------
# Test 3: Diagnóstico sin solución
# ---------------------------------------------------------------------------

def test_diagnostico_sin_solucion():
    profesores, codigos = _make_equipo(3, eventos_por_dia=len(HORAS_BASE))

    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
    )

    if resultado.sin_solucion:
        assert len(resultado.diagnostico_bloqueadores) > 0
        valores = [n for _, n in resultado.diagnostico_bloqueadores]
        assert valores == sorted(valores, reverse=True)
    else:
        assert resultado.diagnostico_bloqueadores == []


# ---------------------------------------------------------------------------
# Test 4: Heurística ordena candidatos
# ---------------------------------------------------------------------------

def test_heuristica_ordena_candidatos():
    profesores, codigos = _make_equipo(10, eventos_por_dia=2)
    indices = build_indices(profesores, RECREOS)
    candidatos = generar_candidatos(codigos, indices)

    assert len(candidatos) > 0, "Debe haber candidatos disponibles"

    def score_candidato(candidato):
        dia_idx, f_start, f_end = candidato
        return sum(
            calcular_peso(cod, dia_idx, f_start, indices)
            for cod in codigos
        )

    candidatos_ordenados = sorted(candidatos, key=score_candidato)
    scores = [score_candidato(s) for s in candidatos_ordenados]
    assert scores == sorted(scores)


# ---------------------------------------------------------------------------
# Test 5: Resultado con solución tiene detalle completo
# ---------------------------------------------------------------------------

def test_resultado_tiene_detalle():
    profesores = []
    codigos: Set[str] = set()
    for i in range(5):
        cod = f"P{i:03d}"
        codigos.add(cod)
        profesores.append({
            "profesor": {"codigo": cod, "nombre": f"Prof {cod}"},
            "eventos": [{"dia": "Lunes", "inicio": HORAS_BASE[i][0], "fin": HORAS_BASE[i][1]}],
        })

    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
    )

    assert not resultado.sin_solucion
    assert resultado.dia in DIAS_VALIDOS
    assert resultado.hora_inicio is not None
    assert resultado.hora_fin is not None
    assert len(resultado.detalle) == len(codigos)
    assert resultado.coste_total >= 0
    assert resultado.peor_penalizacion >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])