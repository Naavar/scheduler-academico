"""
tests/test_ui_config.py
========================
Tests para la función build_config_from_params de app.py.
Se usa un helper local para evitar la dependencia de streamlit.
"""
import pytest
from Proyecto.config import Config, todos_dias


def _build_config(nivel, dias, hora_recreo,
                  permitir_septima_hora, permitir_recreo,
                  permitir_horas_no_obligatorias):
    """Replica la lógica de build_config_from_params de app.py sin streamlit."""
    return Config(
        hora_recreo=hora_recreo,
        sesiones_por_dia=7,
        permitir_septima_hora=permitir_septima_hora,
        permitir_recreo=permitir_recreo,
        permitir_horas_no_obligatorias=permitir_horas_no_obligatorias,
        dias_disponibles_por_nivel={nivel: dias},
    )


def test_devuelve_config():
    resultado = _build_config("ESO", todos_dias, 4, False, False, False)
    assert resultado.hora_recreo == 4
    assert resultado.sesiones_por_dia == 7


def test_nivel_y_dias_se_guardan():
    dias = ["Lunes", "Martes"]
    config = _build_config("BACH", dias, 4, False, False, False)
    assert config.dias_disponibles_por_nivel["BACH"] == dias


def test_hora_recreo_se_aplica():
    config = _build_config("ESO", todos_dias, 3, False, False, False)
    assert config.hora_recreo == 3


def test_permitir_septima_hora_true():
    config = _build_config("ESO", todos_dias, 4, True, False, False)
    assert config.permitir_septima_hora is True


def test_permitir_recreo_true():
    config = _build_config("ESO", todos_dias, 4, False, True, False)
    assert config.permitir_recreo is True


def test_permitir_horas_no_obligatorias_true():
    config = _build_config("ESO", todos_dias, 4, False, False, True)
    assert config.permitir_horas_no_obligatorias is True


def test_todos_false_por_defecto():
    config = _build_config("FP", todos_dias, 4, False, False, False)
    assert config.permitir_septima_hora is False
    assert config.permitir_recreo is False
    assert config.permitir_horas_no_obligatorias is False


def test_hora_recreo_invalida_lanza_error():
    with pytest.raises(ValueError):
        _build_config("ESO", todos_dias, 99, False, False, False)


def test_distintos_niveles_no_se_mezclan():
    config1 = _build_config("ESO", ["Lunes"], 4, False, False, False)
    config2 = _build_config("BACH", ["Martes"], 4, False, False, False)
    assert "ESO" not in config2.dias_disponibles_por_nivel