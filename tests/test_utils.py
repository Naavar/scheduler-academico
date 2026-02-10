import unittest
from Proyecto.utils import (
    es_color_valido,
    colores_son_iguales,
    textos_son_similares,
    limpiar_texto,
    sumar_55_minutos,
    es_hora_recreo
)


class TestUtils(unittest.TestCase):

    # --- 1. Tests para es_color_valido ---
    def test_es_color_valido_basico(self):
        # Colores oscuros o saturados deben ser válidos
        self.assertTrue(es_color_valido((0, 0, 0)), "Negro debería ser válido")
        self.assertTrue(es_color_valido((0.5, 0.1, 0.1)), "Rojo oscuro debería ser válido")

    def test_es_color_valido_blancos(self):
        # Colores muy claros (fondo) deben ser False (r,g,b > 0.9)
        self.assertFalse(es_color_valido((1, 1, 1)), "Blanco puro no debería ser válido")
        self.assertFalse(es_color_valido((0.95, 0.95, 0.95)), "Gris muy claro no debería ser válido")

    def test_es_color_valido_errores(self):
        # Manejo de None o formatos incorrectos
        self.assertFalse(es_color_valido(None))
        self.assertFalse(es_color_valido("no es una tupla"))
        self.assertFalse(es_color_valido((1, 1)))  # Falta un canal

    # --- 2. Tests para colores_son_iguales ---
    def test_colores_iguales_exactos(self):
        c1 = (0.5, 0.5, 0.5)
        self.assertTrue(colores_son_iguales(c1, c1))
        self.assertTrue(colores_son_iguales(None, None))

    def test_colores_similares(self):
        # Diferencia menor a 0.05
        c1 = (0.50, 0.50, 0.50)
        c2 = (0.54, 0.50, 0.50)
        self.assertTrue(colores_son_iguales(c1, c2))

    def test_colores_diferentes(self):
        # Diferencia mayor o igual a 0.05
        c1 = (0.50, 0.50, 0.50)
        c2 = (0.60, 0.50, 0.50)
        self.assertFalse(colores_son_iguales(c1, c2))

    def test_colores_mixtos_none(self):
        self.assertFalse(colores_son_iguales((1, 1, 1), None))
        self.assertFalse(colores_son_iguales(None, (1, 1, 1)))

    # --- 3. Tests para textos_son_similares ---
    def test_textos_exactos(self):
        self.assertTrue(textos_son_similares("Hola Mundo", "hola mundo"))

    def test_textos_cortos_distintos(self):
        # Menos de 20 caracteres -> requiere igualdad exacta
        self.assertFalse(textos_son_similares("Matemáticas", "Matemática"),
                         "Textos cortos deben ser idénticos")

    def test_textos_largos_similares(self):
        # Más de 20 caracteres, mismo prefijo, alta similitud de palabras (Jaccard >= 0.7)
        t1 = "Programación de servicios y procesos I"
        t2 = "Programación de servicios y procesos II"
        # Prefijo "Programación de serv" (20 chars) coincide.
        # Palabras casi idénticas.
        self.assertTrue(textos_son_similares(t1, t2))

    def test_textos_largos_diferentes(self):
        # Mismo prefijo pero palabras muy distintas
        t1 = "Historia del Arte Contemporáneo del Siglo XX"
        t2 = "Historia del Arte Antiguo y Medieval en Europa"
        # Aunque "Historia del Arte " coincide, el resto cambia mucho la proporción Jaccard
        self.assertFalse(textos_son_similares(t1, t2))

    def test_textos_prefijo_distinto(self):
        # Si los primeros 20 chars son distintos, devuelve False rápido
        t1 = "Desarrollo de Interfaces Web"
        t2 = "Despliegue de Aplicaciones Web"
        self.assertFalse(textos_son_similares(t1, t2))

    # --- 4. Tests para limpiar_texto ---
    def test_limpiar_texto(self):
        entrada = "  Hola    \n   Mundo  "
        self.assertEqual(limpiar_texto(entrada), "Hola Mundo")
        self.assertEqual(limpiar_texto(None), "")

    # --- 5. Tests para sumar_55_minutos ---
    def test_sumar_55_minutos_normal(self):
        self.assertEqual(sumar_55_minutos("08:00"), "08:55")

    def test_sumar_55_minutos_cambio_hora(self):
        self.assertEqual(sumar_55_minutos("08:55"), "09:50")

    def test_sumar_55_minutos_texto_sucio(self):
        # La función usa regex para buscar HH:MM
        self.assertEqual(sumar_55_minutos("Inicio: 10:00 aprox"), "10:55")

    def test_sumar_55_minutos_invalido(self):
        # Si no encuentra formato, devuelve el original
        self.assertEqual(sumar_55_minutos("Sin hora"), "Sin hora")
        self.assertEqual(sumar_55_minutos(None), None)

    # --- 6. Tests para es_hora_recreo ---
    def test_recreo_por_hora_fija(self):
        # 11:00 y 11:30 en el texto
        self.assertTrue(es_hora_recreo("11:00 - 11:30"))
        # 18:05 y 18:35 en el texto
        self.assertTrue(es_hora_recreo("18:05 a 18:35"))

    def test_recreo_por_texto(self):
        self.assertTrue(es_hora_recreo("09:00", "  Recreo  "))
        self.assertTrue(es_hora_recreo("Any time", "RECREO"))

    def test_recreo_por_coordenadas(self):
        # Formato [y1-y2] con diferencia < 25
        self.assertTrue(es_hora_recreo("[100-120]"))  # Diff 20
        self.assertFalse(es_hora_recreo("[100-200]"))  # Diff 100 (Clase normal)

    def test_no_es_recreo(self):
        self.assertFalse(es_hora_recreo("08:00 - 09:00", "Matemáticas"))


if __name__ == '__main__':
    unittest.main()