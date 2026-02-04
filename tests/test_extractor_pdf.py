import sys
import pytest
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Proyecto.extractor_pdf import (
    parse_teacher_header,
    fix_split_group_codes,
    compute_day_bounds,
    determine_turno,
    merge_consecutive,
    merge_continuations,
    normalize_text
)

def test_parse_teacher_header():
    res = parse_teacher_header("PÉREZ PANDRADA, PERGIO (99887766)")
    assert res["nombre"] == "PÉREZ PANDRADA, PERGIO"
    assert res["codigo"] == "99887766"

def test_normalize_text():
    assert normalize_text("  big-d~bigd-  c03  ") == "BIG-D~BIGDC03"

def test_fix_split_group_codes():
    assert fix_split_group_codes("DAW2~SGE- 01") == "DAW2~SGE01"
    assert fix_split_group_codes("RDP - DPTO INF") == "RDP - DPTO INF"

def test_compute_day_bounds():
    words = [
        {"text": "Lunes", "x0": 100, "x1": 150},
        {"text": "Martes", "x0": 200, "x1": 250},
        {"text": "Miércoles", "x0": 300, "x1": 350},
        {"text": "Jueves", "x0": 400, "x1": 450},
        {"text": "Viernes", "x0": 500, "x1": 550},
    ]
    bounds = compute_day_bounds(words)
    assert len(bounds) == 5
    assert bounds[0][2] == 175.0

@pytest.mark.parametrize("hora,esperado", [
    ("08:00", "mañana"),
    ("15:00", "tarde"),
])
def test_determine_turno(hora, esperado):
    assert determine_turno(hora) == esperado

def test_merge_consecutive():
    texts = {"Lunes": ["SISTEMAS", "SISTEMAS", ""]}
    slots = [
        {"t_ini": "08:00", "t_fin": "09:00"},
        {"t_ini": "09:00", "t_fin": "10:00"},
        {"t_ini": "10:00", "t_fin": "11:00"},
    ]
    evs = merge_consecutive(texts, slots)
    assert len(evs) == 1
    assert evs[0]["inicio"] == "08:00"
    assert evs[0]["fin"] == "10:00"

def test_merge_continuations():
    evs = [
        {"dia": "Lunes", "turno": "mañana", "inicio": "08:00", "fin": "09:00", "titulo": "PROG"},
        {"dia": "Lunes", "turno": "mañana", "inicio": "09:00", "fin": "10:00", "titulo": "B12"}
    ]
    res = merge_continuations(evs)
    assert len(res) == 1
    assert "PROG B12" in res[0]["titulo"]

def test_no_merge_distintos():
    evs = [
        {"dia": "Lunes", "turno": "mañana", "inicio": "08:00", "fin": "09:00", "titulo": "GUARDIA"},
        {"dia": "Lunes", "turno": "mañana", "inicio": "09:00", "fin": "10:00", "titulo": "REUNIÓN"}
    ]
    res = merge_continuations(evs)
    assert len(res) == 2