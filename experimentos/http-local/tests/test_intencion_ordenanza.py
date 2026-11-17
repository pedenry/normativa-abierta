"""Regresión de intención municipal sobre el adaptador real.

Corpus temporal y buscador/lectura sintéticos del helper de aclaración.
La resolución de ámbito es real; las abstenciones no deben buscar evidencia.
"""
import unittest

import test_aclaracion as F


class PruebasIntencionOrdenanza(unittest.TestCase):
    def setUp(self):
        ayuda = F.PruebasAclaracionSinUbicacion()
        self.addCleanup(ayuda.doCleanups)
        _, self.ad, self.captura = ayuda._montar([
            F._doc_sintetico("doc-nacional"),
            F._doc_sintetico("doc-region", jurisdiccion="Region Demo"),
            F._doc_sintetico("doc-municipio", jurisdiccion="Region Demo",
                             municipio="Municipio Demo"),
        ])

    def _sin_fuente(self, consulta):
        salida = self.ad.preparar(consulta)
        self.assertEqual(salida["estado"], "sin_resultados")
        self.assertEqual(salida["resolucion_ambito"]["estado"], "municipal_no_corporado")
        self.assertEqual(salida["paginas"], [])
        self.assertEqual(salida["recuperacion"]["resultados"], [])
        self.assertFalse(salida.get("aclaracion"))
        self.assertFalse(self.captura)

    def test_ordenanza_explicita_no_se_suple_con_la_comunidad(self):
        for ordenanza in ("la ordenanza municipal", "las ordenanzas municipales"):
            with self.subTest(ordenanza=ordenanza):
                self._sin_fuente("En Region Demo, que documentacion exige " +
                                 ordenanza + " para solicitar una licencia de obras?")

    def test_nombre_desconocido_tras_de_y_del(self):
        for enlace in ("de", "del"):
            with self.subTest(enlace=enlace):
                self._sin_fuente("Segun la ordenanza municipal " + enlace +
                                 " Ciudad Ausente, que documentacion necesito?")

    def test_competencia_y_cesion_no_piden_ordenanza_local(self):
        for consulta in (
            "En Region Demo, en que supuestos se subroga el consejo en la competencia urbanistica municipal?",
            "En Region Demo, que porcentaje de cesion de aprovechamiento corresponde al ayuntamiento?",
        ):
            with self.subTest(consulta=consulta):
                ambito = self.ad._resolver_ambito(consulta)
                self.assertEqual(ambito["estado"], "resuelto")
                self.assertEqual(set(ambito["documentos_permitidos"]),
                                 {"doc-nacional", "doc-region"})

    def test_municipio_incorporado_sigue_resolviendose_despues_de_abstenerse(self):
        self._sin_fuente("Segun la ordenanza municipal de Ciudad Ausente, que documentacion necesito?")
        ambito = self.ad._resolver_ambito("Segun la ordenanza municipal de Municipio Demo, que documentacion necesito?")
        self.assertEqual(ambito["estado"], "resuelto")
        self.assertIn("doc-municipio", ambito["documentos_permitidos"])
        self.assertIn("doc-region", ambito["documentos_permitidos"])


if __name__ == "__main__":
    unittest.main()
