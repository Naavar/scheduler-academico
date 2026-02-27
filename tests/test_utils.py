import unittest
from Proyecto.utils import (
    es_color_valido,
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

    # --- 1. Tests para es_color_valido ---
    def test_es_color_valido_basico(self):
        # Colores oscuros o saturados deben ser válidos
        self.assertTrue(es_color_valido((0, 0, 0)), "Negro debería ser válido")
        self.assertTrue(es_color_valido((0.5, 0.1, 0.1)), "Rojo oscuro debería ser válido")

    def test_es_color_valido_blancos(self):
        # Blanco puro y near-white (algún canal >= 0.99, todos > 0.94) → inválido
        self.assertFalse(es_color_valido((1, 1, 1)), "Blanco puro no debería ser válido")
        self.assertFalse(es_color_valido((1.0, 1.0, 0.961)), "Blanco PDF (255,255,245) no debería ser válido")
        self.assertFalse(es_color_valido((0.97, 0.97, 1.0)), "Near-white no debería ser válido")

    def test_es_color_valido_gris_claro(self):
        # Gris claro (245,245,245 → 0.961) debe ser válido: ningún canal llega a 0.99
        self.assertTrue(es_color_valido((0.961, 0.961, 0.961)), "Gris claro PDF (245,245,245) debería ser válido")
        self.assertTrue(es_color_valido((0.92, 0.92, 0.92)), "Gris medio debería ser válido")
        self.assertTrue(es_color_valido((0.95, 0.95, 0.95)), "Gris 95% debería ser válido")

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

    def test_extraer_nombre_asignatura_con_codigos(self):
        """Elimina códigos de grupo y aula, dejando solo el nombre base."""
        texto = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "Aplicaciones ofimáticas")

    def test_extraer_nombre_asignatura_con_semi(self):
        texto = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S SEMI2"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "Aplicaciones ofimáticas")

    def test_extraer_nombre_asignatura_vacio(self):
        self.assertEqual(extraer_nombre_asignatura(""), "")
        self.assertEqual(extraer_nombre_asignatura(None), "")

    def test_extraer_nombre_asignatura_codigo_grupo_incompleto(self):
        """Códigos de grupo incompletos (1CAM~) deben ser eliminados."""
        texto = "1CAM~1CAMM, 1CAM~1CAMN, 1CAM~ B21"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "")

    def test_extraer_nombre_asignatura_con_fct(self):
        """Códigos de sala tipo FCT-1 deben ser eliminados."""
        texto = "Formación en centros de trabajo 2CAM~2CAMF, 2CAM~2CMFA FCT-1"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "Formación en centros de trabajo")

    def test_extraer_nombre_asignatura_solo_fct(self):
        """Texto con solo códigos de grupo y FCT-1 debe quedar vacío."""
        texto = "2CAM~2CAMF, 2CAM~2CMFA FCT-1"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "")

    def test_extraer_nombre_asignatura_codigo_con_guion(self):
        """Códigos de grupo con guiones (CIB-R~CIB-R) deben ser eliminados."""
        texto = "CIB-R~CIB-R B01"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "")

    def test_extraer_nombre_asignatura_con_guion_y_nombre(self):
        """Nombre base se preserva con códigos con guiones."""
        texto = "Hacking ético CIB-R~CIB-R B01"
        resultado = extraer_nombre_asignatura(texto)
        self.assertEqual(resultado, "Hacking ético")

    # --- 8. Tests para textos_son_similares con nombres base diferentes ---
    def test_textos_diferentes_asignaturas_mismos_grupos(self):
        """Asignaturas con distinto nombre base pero mismos códigos de grupo
        NO deben considerarse similares (bug PROF031)."""
        t1 = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        t2 = "Sistemas operativos monopuesto 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S B23"
        self.assertFalse(textos_son_similares(t1, t2),
                         "Asignaturas con nombre base diferente no deben ser similares")

    def test_textos_misma_asignatura_diferente_aula(self):
        """La misma asignatura en aulas distintas SÍ debe ser similar."""
        t1 = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        t2 = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S B23"
        self.assertTrue(textos_son_similares(t1, t2),
                        "Misma asignatura en diferente aula debe ser similar")

    # --- 9. Tests para extraer_codigos_grupo ---
    def test_extraer_codigos_grupo_fp(self):
        texto = "Aplicaciones ofimáticas 1SSP~1SSPM, 1SSP~1SSPN, 1SSP~1S A23"
        resultado = extraer_codigos_grupo(texto)
        self.assertEqual(resultado, {"1SSP"})

    def test_extraer_codigos_grupo_especializacion(self):
        texto = "Hacking ético CIB-R~CIB-R B01"
        resultado = extraer_codigos_grupo(texto)
        self.assertEqual(resultado, {"CIB-R"})

    def test_extraer_codigos_grupo_multiples(self):
        texto = "Formación en centros de trabajo 2DAWR~2DWRF, 2DAW~2DAWX FCT-5"
        resultado = extraer_codigos_grupo(texto)
        self.assertEqual(resultado, {"2DAWR", "2DAW"})

    def test_extraer_codigos_grupo_vacio(self):
        self.assertEqual(extraer_codigos_grupo(""), set())
        self.assertEqual(extraer_codigos_grupo("GUARDIA G. TARDE"), set())

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
        """Códigos 1104 (CTVP, CPPL...) deben ser ignorados."""
        resultado = clasificar_grupos({"1104", "1DAM"})
        self.assertIn("FP", resultado)
        self.assertEqual(resultado["FP"], ["1DAM"])
        self.assertNotIn("1104", str(resultado))


if __name__ == '__main__':
    unittest.main()