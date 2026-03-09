import json
import os
import tempfile
import pytest
from Proyecto.config import Config, todos_dias


# --- Valores por defecto ---

def test_hora_recreo_default():
    assert Config().hora_recreo == 4

def test_sesiones_por_dia_default():
    assert Config().sesiones_por_dia == 7

def test_permitir_septima_hora_default():
    assert Config().permitir_septima_hora is False

def test_permitir_recreo_default():
    assert Config().permitir_recreo is False

def test_permitir_horas_no_obligatorias_default():
    assert Config().permitir_horas_no_obligatorias is False

def test_dias_disponibles_por_nivel_default_vacio():
    assert Config().dias_disponibles_por_nivel == {}

def test_instancias_no_comparten_dict():
    c1 = Config()
    c2 = Config()
    c1.dias_disponibles_por_nivel["ESO"] = ["Lunes"]
    assert "ESO" not in c2.dias_disponibles_por_nivel


# --- Serialización ---

def test_to_dict_devuelve_dict():
    assert isinstance(Config().to_dict(), dict)

def test_to_dict_tiene_todos_los_campos():
    campos = {"hora_recreo", "sesiones_por_dia", "permitir_septima_hora",
              "permitir_recreo", "permitir_horas_no_obligatorias", "dias_disponibles_por_nivel"}
    assert campos == set(Config().to_dict().keys())

def test_to_json_es_json_valido():
    assert isinstance(json.loads(Config().to_json()), dict)


# --- Round-trip ---

def test_from_dict_round_trip():
    c = Config(hora_recreo=3, sesiones_por_dia=6, permitir_recreo=True)
    assert Config.from_dict(c.to_dict()).to_dict() == c.to_dict()

def test_from_json_round_trip():
    c = Config(permitir_septima_hora=True, permitir_horas_no_obligatorias=True)
    assert Config.from_json(c.to_json()).to_dict() == c.to_dict()

def test_round_trip_con_dias_por_nivel():
    c = Config(dias_disponibles_por_nivel={"ESO": ["Lunes", "Miércoles"]})
    assert Config.from_json(c.to_json()).dias_disponibles_por_nivel == {"ESO": ["Lunes", "Miércoles"]}


# --- Guardado y carga en fichero ---

def test_guardar_y_cargar():
    c = Config(hora_recreo=2, permitir_recreo=True)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        ruta = f.name
    try:
        c.guardar(ruta)
        cargada = Config.cargar(ruta)
        assert cargada.hora_recreo == 2
        assert cargada.permitir_recreo is True
    finally:
        os.unlink(ruta)


# --- Validaciones ---

def test_hora_recreo_fuera_de_rango_lanza_error():
    with pytest.raises(ValueError):
        Config(hora_recreo=99)

def test_hora_recreo_cero_lanza_error():
    with pytest.raises(ValueError):
        Config(hora_recreo=0)

def test_sesiones_por_dia_cero_lanza_error():
    with pytest.raises(ValueError):
        Config(sesiones_por_dia=0)

def test_sesiones_por_dia_excesivo_lanza_error():
    with pytest.raises(ValueError):
        Config(sesiones_por_dia=21)

def test_hora_recreo_igual_a_sesiones_es_valido():
    c = Config(hora_recreo=7, sesiones_por_dia=7)
    assert c.hora_recreo == 7


# --- get_dias_nivel ---

def test_get_dias_nivel_devuelve_todos_si_no_existe():
    assert Config().get_dias_nivel("ESO") == todos_dias

def test_get_dias_nivel_devuelve_los_configurados():
    c = Config(dias_disponibles_por_nivel={"ESO": ["Lunes", "Martes"]})
    assert c.get_dias_nivel("ESO") == ["Lunes", "Martes"]