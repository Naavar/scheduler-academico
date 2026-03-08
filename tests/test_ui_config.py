import pytest
from Proyecto.config import Config, todos_dias
from app import build_config_from_params


def test_devuelve_config():
    resultado = build_config_from_params("ESO", todos_dias, 4, 7, False, False, False)
    assert resultado.hora_recreo == 4
    assert resultado.sesiones_por_dia == 7

def test_nivel_y_dias_se_guardan():
    dias = ["Lunes", "Martes"]
    config = build_config_from_params("BACH", dias, 4, 7, False, False, False)
    assert config.dias_disponibles_por_nivel["BACH"] == dias

def test_hora_recreo_se_aplica():
    config = build_config_from_params("ESO", todos_dias, 3, 7, False, False, False)
    assert config.hora_recreo == 3

def test_sesiones_por_dia_se_aplica():
    config = build_config_from_params("ESO", todos_dias, 4, 6, False, False, False)
    assert config.sesiones_por_dia == 6

def test_permitir_septima_hora_true():
    config = build_config_from_params("ESO", todos_dias, 4, 7, True, False, False)
    assert config.permitir_septima_hora is True

def test_permitir_recreo_true():
    config = build_config_from_params("ESO", todos_dias, 4, 7, False, True, False)
    assert config.permitir_recreo is True

def test_permitir_horas_no_obligatorias_true():
    config = build_config_from_params("ESO", todos_dias, 4, 7, False, False, True)
    assert config.permitir_horas_no_obligatorias is True

def test_todos_false_por_defecto():
    config = build_config_from_params("FP", todos_dias, 4, 7, False, False, False)
    assert config.permitir_septima_hora is False
    assert config.permitir_recreo is False
    assert config.permitir_horas_no_obligatorias is False

def test_hora_recreo_invalida_lanza_error():
    with pytest.raises(ValueError):
        build_config_from_params("ESO", todos_dias, 99, 7, False, False, False)

def test_distintos_niveles_no_se_mezclan():
    config1 = build_config_from_params("ESO", ["Lunes"], 4, 7, False, False, False)
    config2 = build_config_from_params("BACH", ["Martes"], 4, 7, False, False, False)
    assert "ESO" not in config2.dias_disponibles_por_nivel