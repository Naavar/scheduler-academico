"""
tests/test_utils.py
===================
Tests para todas las funciones de Proyecto/utils.py.
"""
import unittest
from Proyecto.utils import (
    es_color_valido,
    es_color_gris_claro,
    colores_son_iguales,
    textos_son_similares,
    extraer_nombre_asignatura,
    extraer_codigos_grupo,
    clasificar_grupos,
    limpiar_texto,
    sumar_55_minutos,
    es_hora_recreo
)


class TestUtils(unittest.TestCase):

    # --- 1. es_color_valido ---
    def test_es_color_valido_basico(self):
        self.assertTrue(es_color_valido((0, 0, 0)))
        self.assertTrue(es_color_valido((0.5, 0.1, 0.1)))

    def test_es_color_valido_blancos(self):
        self.assertFalse(es_color_valido((1, 1, 1)))
        self.assertFalse(es_color_valido((1.0, 1.0, 0.961)))
        self.assertFalse(es_color_valido((0.97, 0.97, 1.0)))

    def test_es_color_valido_gris_claro_valido(self):
        """Gris claro (245,245,245 → 0.961): ningún canal llega a 0.99 → válido."""
        self.assertTrue(es_color_valido((0.961, 0.961, 0.961)))
        self.assertTrue(es_color_valido((0.92, 0.92, 0.92)))
        self.assertTrue(es_color_valido((0.95, 0.95, 0.95)))

    def test_es_color_valido_errores(self):
        self.assertFalse(es_color_valido(None))
        self.assertFalse(es_color_valido("no es una tupla"))
        self.assertFalse(es_color_valido((1, 1)))

    # --- 2. es_color_gris_claro ---
    def test_es_color_gris_claro_positivo(self):
        self.assertTrue(es_color_gris_claro((0.96, 0.96, 0.96)))
        self.assertTrue(es_color_gris_claro((0.95, 0.95, 0.95)))

    def test_es_color_gris_claro_color_saturado(self):
        self.assertFalse(es_color_gris_claro((0.5, 0.1, 0.1)))

    def test_es_color_gris_claro_none(self):
        self.assertFalse(es_color_gris_claro(None))

    # --- 3. colores_son_iguales ---
    def test_colores_iguales_exactos(self):
        c1 = (0.5, 0.5, 0.5)
        self.assertTrue(colores_son_iguales(c1, c1))
        self.assertTrue(colores_son_iguales(None, None))

    def test_colores_similares(self):
        c1 = (0.50, 0.50, 0.50)
        c2 = (0.54, 0.50, 0.50)
        self.assertTrue(colores_son_iguales(c1, c2))

    def test_colores_diferentes(self):
        c1 = (0.50, 0.50, 0.50)
        c2 = (0.60, 0.50, 0.50)
        self.assertFalse(colores_son_iguales(c1, c2))

    def test_colores_mixtos_none(self):
        self.assertFalse(colores_son_iguales((1, 1, 1), None))
        self.assertFalse(colores_son_iguales(None, (1, 1, 1)))

    def test_colores_iguales_tipos_incompatibles(self):
        self.assertFalse(colores_son_iguales("rojo", (1, 0, 0)))

    # --- 4. textos_son_similares ---
    def test_textos_exactos(self):
        self.assertTrue(textos_son_similares("Hola Mundo", "hola mundo"))

    def test_textos_cortos_distintos(self):
        self.assertFalse(textos_son_similares("Matemáticas", "Matemática"))

    def test_textos_largos_similares(self):
        t1 = "Programación de servicios y procesos I"
        t2 = "Programación de servicios y procesos II"
        self.assertTrue(textos_son_similares(t1, t2))

    def test_textos_largos_diferentes(self):
        t1 = "Historia del Arte Contemporáneo del Siglo XX"
        t2 = "Historia del Arte Antiguo y Medieval en Europa"
        self.assertFalse(textos_son_similares(t1, t2))

    def test_textos_prefijo_distinto(self):
        t1 = "Desarrollo de Interfaces Web"
        t2 = "Despliegue de Aplicaciones Web"
        self.assertFalse(textos_son_similares(t1, t2))

    def test_textos_similares_none(self):
        self.assertFalse(textos_son_similares(None, "algo"))
        self.assertFalse(textos_son_similares("algo", None))
        self.assertFalse(textos_son_similares(None, None))

    def test_textos_similares_vacios(self):
        self.assertFalse(textos_son_similares("", "algo"))
        self.assertFalse(textos_son_similares("algo", ""))

    def test_textos_diferentes_asignaturas_mismos_grupos(self):
        """Asignaturas con distinto nombre base pero mismos códigos de grupo."""
        t1 = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        t2 = "Sistemas operativos monopuesto 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S B23"
        self.assertFalse(textos_son_similares(t1, t2))

    def test_textos_misma_asignatura_diferente_aula(self):
        t1 = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        t2 = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S B23"
        self.assertTrue(textos_son_similares(t1, t2))

    # --- 5. extraer_nombre_asignatura ---
    def test_extraer_nombre_asignatura_con_codigos(self):
        texto = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        self.assertEqual(extraer_nombre_asignatura(texto), "Aplicaciones ofimáticas")

    def test_extraer_nombre_asignatura_con_semi(self):
        texto = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S SEMI2"
        self.assertEqual(extraer_nombre_asignatura(texto), "Aplicaciones ofimáticas")

    def test_extraer_nombre_asignatura_vacio(self):
        self.assertEqual(extraer_nombre_asignatura(""), "")
        self.assertEqual(extraer_nombre_asignatura(None), "")

    def test_extraer_nombre_asignatura_codigo_grupo_incompleto(self):
        texto = "1CAM~1CAMM, 1CAM~1CAMN, 1CAM~ B21"
        self.assertEqual(extraer_nombre_asignatura(texto), "")

    def test_extraer_nombre_asignatura_con_fct(self):
        texto = "Formación en centros de trabajo 2CAM~2CAMF, 2CAM~2CMFA FCT-1"
        self.assertEqual(extraer_nombre_asignatura(texto), "Formación en centros de trabajo")

    def test_extraer_nombre_asignatura_solo_fct(self):
        texto = "2CAM~2CAMF, 2CAM~2CMFA FCT-1"
        self.assertEqual(extraer_nombre_asignatura(texto), "")

    def test_extraer_nombre_asignatura_codigo_con_guion(self):
        texto = "CIB-R~CIB-R B01"
        self.assertEqual(extraer_nombre_asignatura(texto), "")

    def test_extraer_nombre_asignatura_con_guion_y_nombre(self):
        texto = "Hacking ético CIB-R~CIB-R B01"
        self.assertEqual(extraer_nombre_asignatura(texto), "Hacking ético")

    # --- 6. limpiar_texto ---
    def test_limpiar_texto(self):
        self.assertEqual(limpiar_texto("  Hola    \n   Mundo  "), "Hola Mundo")
        self.assertEqual(limpiar_texto(None), "")

    def test_limpiar_texto_cadena_vacia(self):
        self.assertEqual(limpiar_texto(""), "")

    def test_limpiar_texto_tabs(self):
        self.assertEqual(limpiar_texto("A\tB"), "A B")

    # --- 7. sumar_55_minutos ---
    def test_sumar_55_minutos_normal(self):
        self.assertEqual(sumar_55_minutos("08:00"), "08:55")

    def test_sumar_55_minutos_cambio_hora(self):
        self.assertEqual(sumar_55_minutos("08:55"), "09:50")

    def test_sumar_55_minutos_texto_sucio(self):
        self.assertEqual(sumar_55_minutos("Inicio: 10:00 aprox"), "10:55")

    def test_sumar_55_minutos_invalido(self):
        self.assertEqual(sumar_55_minutos("Sin hora"), "Sin hora")
        self.assertEqual(sumar_55_minutos(None), None)

    def test_sumar_55_minutos_cadena_vacia(self):
        self.assertEqual(sumar_55_minutos(""), "")

    def test_sumar_55_minutos_multiples_horas(self):
        self.assertEqual(sumar_55_minutos("8:00 - 9:00"), "08:55")

    # --- 8. es_hora_recreo ---
    def test_recreo_por_hora_fija(self):
        self.assertTrue(es_hora_recreo("11:00 - 11:30"))
        self.assertTrue(es_hora_recreo("18:05 a 18:35"))

    def test_recreo_por_texto(self):
        self.assertTrue(es_hora_recreo("09:00", "  Recreo  "))
        self.assertTrue(es_hora_recreo("Any time", "RECREO"))

    def test_recreo_por_coordenadas(self):
        self.assertTrue(es_hora_recreo("[100-120]"))
        self.assertFalse(es_hora_recreo("[100-200]"))

    def test_no_es_recreo(self):
        self.assertFalse(es_hora_recreo("08:00 - 09:00", "Matemáticas"))

    def test_es_hora_recreo_coordenadas_invalidas(self):
        self.assertFalse(es_hora_recreo("[abc-def]"))

    def test_es_hora_recreo_texto_generico(self):
        self.assertFalse(es_hora_recreo("12:00 13:00", "Matemáticas"))

    # --- 9. extraer_codigos_grupo ---
    def test_extraer_codigos_grupo_fp(self):
        texto = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        self.assertEqual(extraer_codigos_grupo(texto), {"1SSP"})

    def test_extraer_codigos_grupo_especializacion(self):
        texto = "Hacking ético CIB-R~CIB-R B01"
        self.assertEqual(extraer_codigos_grupo(texto), {"CIB-R"})

    def test_extraer_codigos_grupo_multiples(self):
        texto = "Formación en centros de trabajo 2DAWR~2DWRF, 2DAW~2DAWX FCT-5"
        self.assertEqual(extraer_codigos_grupo(texto), {"2DAWR", "2DAW"})

    def test_extraer_codigos_grupo_vacio(self):
        self.assertEqual(extraer_codigos_grupo(""), set())
        self.assertEqual(extraer_codigos_grupo("GUARDIA G. TARDE"), set())

    # --- 10. clasificar_grupos ---
    def test_clasificar_grupos_fp(self):
        resultado = clasificar_grupos({"1DAM", "2ASI", "1SMR"})
        self.assertIn("FP", resultado)
        self.assertEqual(sorted(resultado["FP"]), ["1DAM", "1SMR", "2ASI"])

    def test_clasificar_grupos_eso(self):
        resultado = clasificar_grupos({"E1A", "E2B", "DIV3"})
        self.assertIn("ESO", resultado)
        self.assertEqual(sorted(resultado["ESO"]), ["DIV3", "E1A", "E2B"])

    def test_clasificar_grupos_bachillerato(self):
        resultado = clasificar_grupos({"B1BSO", "B2AC"})
        self.assertIn("BACHILLERATO", resultado)
        self.assertEqual(sorted(resultado["BACHILLERATO"]), ["B1BSO", "B2AC"])

    def test_clasificar_grupos_especializacion(self):
        resultado = clasificar_grupos({"CIB-R", "BIG-D", "PYT"})
        self.assertIn("ESPECIALIZACION", resultado)
        self.assertEqual(sorted(resultado["ESPECIALIZACION"]), ["BIG-D", "CIB-R", "PYT"])

    def test_clasificar_grupos_mixto(self):
        resultado = clasificar_grupos({"1DAM", "E1A", "CIB-R", "B1BSO"})
        self.assertIn("FP", resultado)
        self.assertIn("ESO", resultado)
        self.assertIn("ESPECIALIZACION", resultado)
        self.assertIn("BACHILLERATO", resultado)

    def test_clasificar_grupos_ignora_administrativos(self):
        resultado = clasificar_grupos({"1104", "1DAM"})
        self.assertIn("FP", resultado)
        self.assertEqual(resultado["FP"], ["1DAM"])
        self.assertNotIn("1104", str(resultado))


if __name__ == '__main__':
    unittest.main()