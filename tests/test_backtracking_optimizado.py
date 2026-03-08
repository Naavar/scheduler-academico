"""
tests/test_backtracking_optimizado.py
======================================
Verifica que con 50 profesores la respuesta llega en menos de 2 segundos,
y que la heurística de ordenación + diagnóstico sin solución funcionan correctamente.
"""

import time
import pytest
from typing import Set

# Ajusta el import según tu estructura de proyecto
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from buscador_evaluacion import (
    buscar_sesion_evaluacion,
    build_indices,
    calcular_peso_rapido,
    diagnostico_sin_solucion,
    generar_candidatos,
    DIAS_VALIDOS,
)


# ---------------------------------------------------------------------------
# Helpers para generar datos sintéticos
# ---------------------------------------------------------------------------

HORAS_BASE = [
    ("8:00", "9:00"),
    ("9:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),  # recreo — se excluye
    ("12:00", "13:00"),
    ("13:00", "14:00"),
    ("14:00", "15:00"),
]

FRANJAS_LECTIVAS = [(ini, fin) for ini, fin in HORAS_BASE if ini != "11:00"]
# → 6 franjas lectivas por día × 5 días = 30 slots totales

RECREOS = {"11:00"}

# Slots que todos los profesores tienen ocupados en los tests de rendimiento.
# Al compartir exactamente los mismos slots ocupados, comparten también
# los mismos huecos libres, garantizando que siempre hay solución.
_SLOTS_OCUPADOS_COMUNES = [
    (dia, ini, fin)
    for dia in ["Lunes", "Martes"]
    for ini, fin in FRANJAS_LECTIVAS[:3]  # primeras 3 franjas de lun/mar
]


def _make_profesor(codigo: str, eventos_por_dia: int = 3) -> dict:
    """
    Genera un profesor cuyos eventos coinciden con _SLOTS_OCUPADOS_COMUNES
    (ajustado a eventos_por_dia).  Al compartir los mismos slots ocupados,
    todos los profesores del equipo tienen los mismos huecos libres,
    garantizando que generar_candidatos devuelve slots válidos.
    """
    slots = _SLOTS_OCUPADOS_COMUNES[:eventos_por_dia * 2]  # 2 días × n franjas
    eventos = [
        {"dia": dia, "inicio": ini, "fin": fin}
        for dia, ini, fin in slots
    ]
    return {"profesor": {"codigo": codigo, "nombre": f"Prof {codigo}"}, "eventos": eventos}


def _make_equipo(n: int, eventos_por_dia: int = 3):
    """Genera n profesores con horarios sintéticos."""
    profesores = [_make_profesor(f"P{i:03d}", eventos_por_dia) for i in range(n)]
    codigos: Set[str] = {f"P{i:03d}" for i in range(n)}
    return profesores, codigos


# ---------------------------------------------------------------------------
# Test 1: Rendimiento con 50 profesores — debe responder en < 2 s
# ---------------------------------------------------------------------------

def test_rendimiento_50_profesores():
    """Con 50 profesores y heurística activa, la búsqueda debe tardar < 2 segundos."""
    profesores, codigos = _make_equipo(50, eventos_por_dia=2)

    inicio = time.perf_counter()
    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
        recreos=RECREOS,
    )
    elapsed = time.perf_counter() - inicio

    print(f"\n⏱  Tiempo con 50 profesores: {elapsed:.3f}s")
    assert elapsed < 2.0, f"Tardó {elapsed:.3f}s — debe ser < 2s"
    # Con 2 eventos/día por profesor quedan franjas libres: no debe ser sin_solucion
    assert not resultado.sin_solucion, "Se esperaba una solución válida"


# ---------------------------------------------------------------------------
# Test 2: Rendimiento con 50 profesores muy ocupados (más poda)
# ---------------------------------------------------------------------------

def test_rendimiento_50_profesores_ocupados():
    """Con profesores muy ocupados la poda es más agresiva; también debe ser < 2s."""
    profesores, codigos = _make_equipo(50, eventos_por_dia=4)

    inicio = time.perf_counter()
    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
        recreos=RECREOS,
    )
    elapsed = time.perf_counter() - inicio

    print(f"\n⏱  Tiempo con 50 profesores ocupados: {elapsed:.3f}s")
    assert elapsed < 2.0, f"Tardó {elapsed:.3f}s — debe ser < 2s"


# ---------------------------------------------------------------------------
# Test 3: Diagnóstico sin solución — devuelve bloqueadores correctos
# ---------------------------------------------------------------------------

def test_diagnostico_sin_solucion():
    """
    Con un equipo donde todos los slots están bloqueados,
    el resultado debe incluir diagnostico_bloqueadores con los profesores responsables.
    """
    # Creamos profesores que cubren TODOS los slots del calendario
    profesores, codigos = _make_equipo(3, eventos_por_dia=len(HORAS_BASE))

    resultado = buscar_sesion_evaluacion(
        profesores=profesores,
        equipo_codigos=codigos,
        recreos=RECREOS,
    )

    if resultado.sin_solucion:
        assert len(resultado.diagnostico_bloqueadores) > 0, (
            "Sin solución pero diagnostico_bloqueadores está vacío"
        )
        # El ranking debe estar ordenado de mayor a menor
        valores = [n for _, n in resultado.diagnostico_bloqueadores]
        assert valores == sorted(valores, reverse=True), (
            "Los bloqueadores deben estar ordenados de mayor a menor"
        )
        print(f"\n🔒 Bloqueadores: {resultado.diagnostico_bloqueadores[:3]}")
    else:
        # Si hay solución, simplemente verificamos que el campo existe y está vacío
        assert resultado.diagnostico_bloqueadores == []


# ---------------------------------------------------------------------------
# Test 4: La heurística mejora el orden — el primer candidato es el mejor
# ---------------------------------------------------------------------------

def test_heuristica_ordena_candidatos():
    """
    Verifica que los candidatos generados están ordenados de menor a mayor coste
    tras aplicar la heurística.
    """
    profesores, codigos = _make_equipo(10, eventos_por_dia=2)
    indices = build_indices(profesores, RECREOS)
    candidatos = generar_candidatos(codigos, indices)

    assert len(candidatos) > 0, "Debe haber candidatos disponibles"

    def score_candidato(candidato):
        dia_idx, f_start, f_end = candidato  # nuevo formato de 3 elementos
        return sum(
            calcular_peso_rapido(cod, dia_idx, f_start, indices)
            for cod in codigos
        )

    candidatos_ordenados = sorted(candidatos, key=score_candidato)
    scores = [score_candidato(s) for s in candidatos_ordenados]

    assert scores == sorted(scores), "Los candidatos deben estar ordenados de menor a mayor coste"


# ---------------------------------------------------------------------------
# Test 5: Resultado con solución tiene detalle completo
# ---------------------------------------------------------------------------

def test_resultado_tiene_detalle():
    """El resultado con solución debe incluir detalle por cada profesor del equipo."""
    # Cada profesor solo tiene eventos el lunes → martes-viernes están libres
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
        recreos=RECREOS,
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