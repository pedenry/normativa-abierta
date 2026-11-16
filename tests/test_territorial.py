# -*- coding: utf-8 -*-
"""Pruebas de ingesta/recopilar_territorial.py (stdlib, sin red, sin shell).

Comportamiento correcto esperado; un fallo de estas pruebas indica defecto del
script, no una prueba a adaptar. Ejecucion: `python -m unittest tests.test_territorial`.
"""
import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "ingesta" / "recopilar_territorial.py"
CATALOGO = ROOT / "ingesta" / "fuentes-territoriales.json"

_spec = importlib.util.spec_from_file_location("recopilar_territorial_prueba", SCRIPT)
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


class TestCatalogo(unittest.TestCase):
    def test_17_autonomias_2_ciudades_7_municipios(self):
        fuentes = json.loads(CATALOGO.read_text(encoding="utf-8"))["fuentes"]
        niveles = {}
        for f in fuentes:
            niveles[f["nivel"]] = niveles.get(f["nivel"], 0) + 1
        self.assertEqual(niveles.get("autonomia"), 17)
        self.assertEqual(niveles.get("ciudad_autonoma"), 2)
        self.assertEqual(niveles.get("municipio"), 7)
        self.assertEqual(len(fuentes), 26)


class TestPoliticaURL(unittest.TestCase):
    def test_validar_url_rechaza_http_y_host_fuera_allowlist(self):
        with self.assertRaises(rt.FalloPermanente):
            rt.validar_url("http://h.es/x", {"h.es"})
        with self.assertRaises(rt.FalloPermanente):
            rt.validar_url("https://ajeno.es/x", {"h.es"})
        self.assertEqual(rt.validar_url("https://H.es/x", {"h.es"}), "h.es")

    def test_normalizar_url_codifica_utf8_y_conserva_codificado(self):
        original = "https://h.es/normas/edificación?q=habitación&x=%C3%B1"
        esperado = "https://h.es/normas/edificaci%C3%B3n?q=habitaci%C3%B3n&x=%C3%B1"
        self.assertEqual(rt.normalizar_url(original), esperado)
        self.assertEqual(rt.normalizar_url(esperado), esperado)


class TestSalida(unittest.TestCase):
    def test_salida_fuera_de_local_rechazada(self):
        with self.assertRaises(rt.FalloConfig):
            rt.validar_salida(ROOT / "contenido")
        with self.assertRaises(rt.FalloConfig):
            rt.validar_salida(str(ROOT.parent / "otro"))
        self.assertIn(".local", rt.validar_salida(None).parts)


class TestSnapshot(unittest.TestCase):
    def test_id_con_escape_rechazado_en_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp)
            with self.assertRaises(rt.FalloConfig):
                rt.carpeta_snapshot(salida, "../escape", "20260101T000000Z")
            self.assertFalse((salida.parent / "escape").exists())


class TestRobots(unittest.TestCase):
    def test_empate_prefijo_gana_allow(self):
        self.assertTrue(rt.ruta_permitida_robots(
            [(False, "/a/"), (True, "/a/")], "/a/x"))
        self.assertTrue(rt.ruta_permitida_robots(
            [(True, "/a/"), (False, "/a/")], "/a/x"))
        self.assertFalse(rt.ruta_permitida_robots([(False, "/a/")], "/a/x"))

    def test_comodin_ancla_y_consulta(self):
        self.assertFalse(rt.ruta_permitida_robots([(False, "/priv*")], "/privado/x"))
        self.assertTrue(rt.ruta_permitida_robots([(False, "/priv*")], "/publico/x"))
        self.assertTrue(rt.ruta_permitida_robots(
            [(True, "/pub$"), (False, "/pub")], "/pub"))
        self.assertFalse(rt.ruta_permitida_robots(
            [(True, "/pub$"), (False, "/pub")], "/pub/x"))
        self.assertFalse(rt.ruta_permitida_robots([(False, "/d")], "/d?q=1"))


class TestRobots404(unittest.TestCase):
    def test_robots_404_sin_keyerror_y_permite_sitio(self):
        error = urllib.error.HTTPError(
            "https://h.es/robots.txt", 404, "Not Found", None, None)
        rastreo = rt.Rastreador(1.0, 5)
        with patch.object(rt.Rastreador, "descargar", side_effect=error):
            res = rastreo.robots_para("h.es", {"h.es"})
        self.assertEqual(res["estado"], "sin_archivo")
        self.assertTrue(res["permitido"])
        self.assertEqual(res["reglas"], [])


class TestCache(unittest.TestCase):
    def test_reanudacion_verifica_hash_y_ignora_cuerpo_corrupto(self):
        url = "https://h.es/pagina.html"
        with tempfile.TemporaryDirectory() as tmp:
            rt.Rastreador(1.0, 5, cache_raiz=tmp, reanudar=True).guardar_cache(
                url, b"contenido", 200, url, "text/html")
            datos, estado, _final, _tipo, n = rt.Rastreador(
                1.0, 5, cache_raiz=tmp, reanudar=True).leer_cache(url)
            self.assertEqual((bytes(datos), estado, n), (b"contenido", 200, 9))
            cuerpo = next(Path(tmp).rglob("*.body"))
            cuerpo.write_bytes(b"corrupto")
            self.assertIsNone(rt.Rastreador(
                1.0, 5, cache_raiz=tmp, reanudar=True).leer_cache(url))


if __name__ == "__main__":
    unittest.main()
