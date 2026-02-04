import unittest
from buscador_huecos import BuscadorHuecos


class TestBuscadorHuecos(unittest.TestCase):
    def test_basic_overlap(self):
        # 2 Professors
        # Prof A: Busy Mon 08:00-10:00
        # Prof B: Busy Mon 09:00-11:00
        # Expected Hueco: Mon 11:00 (Both free)
        
        data = [
            {
                "profesor": {"nombre": "Prof A", "codigo": "A"},
                "eventos": [
                    {"dia": "Lunes", "inicio": "07:00", "fin": "10:00", "titulo": "C1"}
                ]
            },
            {
                "profesor": {"nombre": "Prof B", "codigo": "B"},
                "eventos": [
                    {"dia": "Lunes", "inicio": "07:00", "fin": "11:00", "titulo": "C2"}
                ]
            }
        ]
        
        finder = BuscadorHuecos(data)
        result = finder.buscar_hueco_comun(duracion=60)
        
        print("\nResult Test 1:", result)
        self.assertIsNotNone(result)
        self.assertEqual(result["dia"], "Lunes")
        # Best common slot starts at 11:00 because before that at least 1 is busy
        # 8-9: A busy
        # 9-10: A & B busy
        # 10-11: B busy
        # 11-12: Both Free!
        self.assertEqual(result["hora_inicio"], "11:00")
        self.assertEqual(result["num_profesores"], 2)
        self.assertIn("Prof A", result["profesores_disponibles"])
        self.assertIn("Prof B", result["profesores_disponibles"])

    def test_find_best_partial(self):
        # Prof A: Busy all day Lunes
        # Prof B: Free all day Lunes
        # Expected: Any slot on Lunes with 1 prof (B)
        data = [
            {
                "profesor": {"nombre": "Prof A", "codigo": "A"},
                "eventos": [
                    {"dia": "Lunes", "inicio": "07:00", "fin": "22:00", "titulo": "Full"}
                ]
            },
            {
                "profesor": {"nombre": "Prof B", "codigo": "B"},
                "eventos": []
            }
        ]
        finder = BuscadorHuecos(data)
        finder.dias = ["Lunes"]
        result = finder.buscar_hueco_comun(duracion=60)
        print("\nResult Test 2:", result)
        self.assertEqual(result["num_profesores"], 1)
        self.assertEqual(result["profesores_disponibles"], ["Prof B"])


if __name__ == '__main__':
    unittest.main()
