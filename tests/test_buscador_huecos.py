import unittest
import sys
import os
from typing import List, Dict, Any

# --- CONFIGURACIÓN DE RUTAS (MAGIC FIX) ---
# 1. Obtenemos la ruta de la carpeta actual (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Subimos un nivel para obtener la raíz del proyecto (Proyecto_Horarios/)
project_root = os.path.dirname(current_dir)
# 3. Añadimos la raíz al sistema para que Python vea la carpeta 'Proyecto'
sys.path.insert(0, project_root)

# --- IMPORTACIÓN CORREGIDA SEGÚN TU ESTRUCTURA ---
# Importamos desde el archivo 'buscador_huecos.py' que está dentro de la carpeta 'Proyecto'
from Proyecto.buscador_huecos import BuscadorHuecos, Hueco, clave_num_profesores


class TestHueco(unittest.TestCase):
    """Pruebas para la dataclass Hueco y funciones auxiliares."""

    def test_propiedades_hueco(self):
        hueco = Hueco(
            dia="Lunes",
            hora_inicio="08:00",
            hora_fin="09:00",
            profesores_disponibles=["Ana", "Beto", "Carla"]
        )
        self.assertEqual(hueco.num_profesores, 3)
        self.assertEqual(hueco.dia, "Lunes")

    def test_clave_ordenacion(self):
        h1 = Hueco("L", "08:00", "09:00", ["A", "B"])
        h2 = Hueco("L", "09:00", "10:00", ["A", "B", "C"])
        # h2 debe ser mayor que h1
        self.assertGreater(clave_num_profesores(h2), clave_num_profesores(h1))


class TestBuscadorHuecosBase(unittest.TestCase):
    """Clase base con utilidades para generar datos de prueba."""

    def crear_profesor(self, nombre: str, eventos: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "profesor": {"nombre": nombre, "email": f"{nombre}@test.com"},
            "eventos": eventos
        }

    def setUp(self):
        # Configuración por defecto: 4 profesores para superar el umbral de 3
        # Profesor 1: Libre todo el día
        self.p1 = self.crear_profesor("P1", [])

        # Profesor 2: Ocupado de 08:00 a 10:00 el Lunes
        self.p2 = self.crear_profesor("P2", [
            {"dia": "Lunes", "inicio": "08:00", "fin": "10:00", "asignatura": "X"}
        ])

        # Profesor 3: Ocupado tarde el Lunes
        self.p3 = self.crear_profesor("P3", [
            {"dia": "Lunes", "inicio": "15:00", "fin": "16:00", "asignatura": "Y"}
        ])

        # Profesor 4: Libre todo el día
        self.p4 = self.crear_profesor("P4", [])

        self.datos_base = [self.p1, self.p2, self.p3, self.p4]
        self.buscador = BuscadorHuecos(self.datos_base)


class TestBuscadorUtils(TestBuscadorHuecosBase):
    """Pruebas de métodos utilitarios y configuración inicial."""

    def test_conversiones_tiempo(self):
        # 07:00 empieza el día. 7*60 = 420 min
        self.assertEqual(self.buscador.hora_a_min("07:00"), 420)
        self.assertEqual(self.buscador.hora_a_min("10:30"), 630)

        self.assertEqual(self.buscador.min_a_hora(420), "07:00")
        self.assertEqual(self.buscador.min_a_hora(630), "10:30")

    def test_precalcular_horas(self):
        # Verificar que la lista de horas se genera correctamente
        self.assertEqual(self.buscador.horas[0], "07:00")
        self.assertEqual(self.buscador.horas[-1], "22:00")
        # El slot es de 5 min
        self.assertEqual(self.buscador.horas[1], "07:05")

    def test_hueco_pertenece_a_turno(self):
        # Mañana: Inicio < 14:15
        self.assertTrue(self.buscador._hueco_pertenece_a_turno("08:00", "09:00", "mañana"))
        self.assertTrue(self.buscador._hueco_pertenece_a_turno("14:10", "15:10", "mañana"))
        self.assertFalse(self.buscador._hueco_pertenece_a_turno("14:15", "15:15", "mañana"))

        # Tarde: Inicio >= 14:15
        self.assertTrue(self.buscador._hueco_pertenece_a_turno("14:15", "15:15", "tarde"))
        self.assertTrue(self.buscador._hueco_pertenece_a_turno("18:00", "19:00", "tarde"))
        self.assertFalse(self.buscador._hueco_pertenece_a_turno("10:00", "11:00", "tarde"))


class TestDisponibilidad(TestBuscadorHuecosBase):
    """Pruebas de la construcción de la matriz de disponibilidad."""

    def test_matriz_construccion(self):
        # P2 está ocupado Lunes 08:00 - 10:00
        # Indices: 08:00 es (480-420)/5 = 12. 10:00 es (600-420)/5 = 36.
        # Rango [12, 36)

        matriz_lunes = self.buscador.disponibilidad["Lunes"]

        # P1 (índice 0) está libre
        self.assertTrue(matriz_lunes[0][12])

        # P2 (índice 1) está ocupado
        self.assertFalse(matriz_lunes[1][12])  # 08:00
        self.assertFalse(matriz_lunes[1][35])  # 09:55
        self.assertTrue(matriz_lunes[1][11])  # 07:55 (antes del evento)
        self.assertTrue(matriz_lunes[1][36])  # 10:00 (fin del evento)

    def test_eventos_fuera_de_rango(self):
        # Evento que termina antes de que empiece el día escolar
        p_madrugador = self.crear_profesor("Madrugador", [
            {"dia": "Lunes", "inicio": "05:00", "fin": "06:00", "asig": "Gym"}
        ])
        # Evento que empieza después del fin
        p_nocturno = self.crear_profesor("Nocturno", [
            {"dia": "Lunes", "inicio": "23:00", "fin": "23:30", "asig": "Party"}
        ])

        buscador = BuscadorHuecos([p_madrugador, p_nocturno, self.p1, self.p4])  # 4 profs
        matriz = buscador.disponibilidad["Lunes"]

        # Deben estar libres en horario escolar (7-22)
        self.assertTrue(all(matriz[0]))
        self.assertTrue(all(matriz[1]))

    def test_evento_parcial(self):
        # Evento que empieza antes de las 7 y termina a las 07:10
        p_borde = self.crear_profesor("Borde", [
            {"dia": "Lunes", "inicio": "06:50", "fin": "07:10", "asig": "X"}
        ])
        buscador = BuscadorHuecos([p_borde, self.p1, self.p4, self.p2])
        matriz = buscador.disponibilidad["Lunes"]

        # 07:00 y 07:05 ocupados. 07:10 libre.
        self.assertFalse(matriz[0][0])  # 07:00
        self.assertFalse(matriz[0][1])  # 07:05
        self.assertTrue(matriz[0][2])  # 07:10


class TestBusquedaLogica(TestBuscadorHuecosBase):
    """Pruebas de la búsqueda de huecos (métodos públicos)."""

    def test_buscar_huecos_simple(self):
        # Buscar hueco de 60 mins el Lunes
        huecos = self.buscador.buscar_huecos_por_profesor(duracion=60, filtro_dia="Lunes")

        # Verificaciones
        self.assertTrue(len(huecos) > 0)
        primer_hueco = huecos[0]

        # Buscar un hueco a las 12:00 (todos libres)
        huecos_12 = [h for h in huecos if h.hora_inicio == "12:00"]
        if huecos_12:
            self.assertEqual(huecos_12[0].num_profesores, 4)

        # Buscar un hueco a las 08:00 (P2 ocupado, deben quedar 3: P1, P3, P4)
        huecos_08 = [h for h in huecos if h.hora_inicio == "08:00"]
        if huecos_08:
            self.assertEqual(huecos_08[0].num_profesores, 3)
            self.assertNotIn("P2", huecos_08[0].profesores_disponibles)

    def test_filtro_turno_manana(self):
        huecos = self.buscador.buscar_huecos_por_profesor(duracion=60, turno="mañana", filtro_dia="Lunes")
        for h in huecos:
            # Debe empezar antes de las 14:15
            min_inicio = self.buscador.hora_a_min(h.hora_inicio)
            self.assertLess(min_inicio, self.buscador.hora_a_min("14:15"))

    def test_filtro_turno_tarde(self):
        huecos = self.buscador.buscar_huecos_por_profesor(duracion=60, turno="tarde", filtro_dia="Lunes")
        for h in huecos:
            # Debe empezar a partir de las 14:15
            min_inicio = self.buscador.hora_a_min(h.hora_inicio)
            self.assertGreaterEqual(min_inicio, self.buscador.hora_a_min("14:15"))

    def test_filtro_rango_horario(self):
        # Solo buscar entre 10:00 y 11:00
        huecos = self.buscador.buscar_huecos_por_profesor(
            duracion=60,
            hora_min="10:00",
            hora_max="11:00",
            filtro_dia="Lunes"
        )
        for h in huecos:
            self.assertGreaterEqual(h.hora_inicio, "10:00")
            self.assertLessEqual(h.hora_inicio, "11:00")

    def test_buscar_huecos_n(self):
        res = self.buscador.buscar_huecos_n(duracion=30, n=2)
        self.assertEqual(len(res), 2)
        # Deben estar ordenados
        self.assertGreaterEqual(res[0].num_profesores, res[1].num_profesores)

    def test_buscar_hueco_comun_encontrado(self):
        res = self.buscador.buscar_hueco_comun(duracion=30)
        self.assertIsNotNone(res)
        self.assertIn("dia", res)
        self.assertIn("profesores_disponibles", res)

    def test_poda_insuficientes_candidatos(self):
        profes = [self.p1, self.p4]  # Solo 2 profes, ambos libres
        buscador_small = BuscadorHuecos(profes)

        # Aunque están libres, son menos de 3, el algoritmo debería podar y retornar vacío
        huecos = buscador_small.buscar_huecos_por_profesor(duracion=60)
        self.assertEqual(len(huecos), 0, "Debería retornar lista vacía por la regla de <3 candidatos")

    def test_backtracking_resultado_vacio(self):
        # Caso imposible: rango de búsqueda absurdo
        huecos = self.buscador.buscar_huecos_por_profesor(
            duracion=60,
            hora_min="21:55",
            hora_max="22:00"
        )
        self.assertEqual(len(huecos), 0)


if __name__ == '__main__':
    unittest.main()