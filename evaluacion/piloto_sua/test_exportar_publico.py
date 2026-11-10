# -*- coding: utf-8 -*-
"""Pruebas de exportar_publico.py sin red, claves, API ni corpus: fixtures sinteticos.
Ejecutar (Codex): python -m unittest discover -s evaluacion/piloto_sua -p "test_*.py".
IDs claramente ficticios (vs_sintetico0001...) para falsos positivos gitleaks cero."""
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import exportar_publico as ex

SHA = "a" * 64
RUTA_W = r"C:\Users\sintetica\doc.pdf"
RUN = "S01-r1-adaptador"


def escribe_json(ruta, dato):
    ruta.write_text(json.dumps(dato, ensure_ascii=False), encoding="utf-8")


def huellas(dir_raiz):
    return {str(p.relative_to(dir_raiz)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(dir_raiz.rglob("*")) if p.is_file()}


class Saneo(unittest.TestCase):
    def test_sha_run_id_y_numeros_intactos(self):
        s = ex.sanear({"sha": SHA, "run_id": RUN, "usage": {"input": 123, "cache": 10}, "n": 168})
        self.assertEqual(s, {"sha": SHA, "run_id": RUN, "usage": {"input": 123, "cache": 10}, "n": 168})

    def test_borra_opacos_y_ids(self):
        compuesto = "id resp_sintetico0001 y file-sintetico0001"
        s = ex.sanear({"request_id": "req_sintetico0001", "billing": {"payer": "sintetico"},
                       "creados": {"vector_store_id": "vs_sintetico0001"}, "otro": compuesto})
        self.assertNotIn("request_id", s)
        self.assertNotIn("billing", s)
        self.assertEqual(s["creados"], {})
        self.assertNotIn("resp_", s["otro"])
        self.assertNotIn("file-", s["otro"])

    def test_rutas_completas_e_incrustadas(self):
        s = ex.sanear({"a": RUTA_W, "b": "/home/sintetica/doc.pdf", "d": "/Users/sintetica/doc.pdf",
                       "c": "ver " + RUTA_W + " fin"})
        self.assertEqual(s["a"], "[ruta local omitida]")
        self.assertEqual(s["b"], "[ruta local omitida]")
        self.assertNotIn("/Users/", s["d"])
        self.assertEqual(s["c"], "ver [ruta local omitida] fin")


class Manifest(unittest.TestCase):
    def test_hashes_codigo_y_conservados(self):
        m = {"python": "3", "fuente": {"ruta": RUTA_W, "url": "https://ejemplo.invalid/d.pdf", "sha256": SHA},
             "hashes": {"cliente_api.py": SHA}, "config": {"split": "evaluacion"},
             "slots": [{"id": RUN}], "pdfs": {"S01": SHA}, "creados": {"vector_store_id": "vs_sintetico0001"}}
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            escribe_json(base / "manifest.json", m)
            e = ex.exportar_manifest(base / "manifest.json")
        self.assertNotIn("hashes", e)
        self.assertNotIn("python", e)
        self.assertEqual([x for x in e["hashes_codigo"] if x["archivo"] == "cliente_api.py"][0]["sha256"], SHA)
        self.assertEqual(e["fuente"]["sha256"], SHA)
        self.assertIn("url", e["fuente"])
        self.assertNotIn("ruta", e["fuente"])
        self.assertEqual(e["creados"], {})
        self.assertEqual(e["pdfs"]["S01"], SHA)

    def test_codigo_sha256_dev_a_lista(self):
        dev = {"fase": "desarrollo",
               "codigo_sha256": {"cliente_api.py": SHA, "solicitudes.py": "b" * 64},
               "archivos_sha256": {"generar_fixtures.py": "c" * 64}}
        ambos = {"hashes": {"ejecutar.py": SHA}, "codigo_sha256": {"solicitudes.py": "b" * 64}}
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            escribe_json(base / "dev.json", dev)
            e = ex.exportar_manifest(base / "dev.json")
            escribe_json(base / "ambos.json", ambos)
            e2 = ex.exportar_manifest(base / "ambos.json")
        self.assertEqual(e["codigo_sha256"], [{"archivo": "cliente_api.py", "sha256": SHA},
                                              {"archivo": "solicitudes.py", "sha256": "b" * 64}])
        self.assertEqual(e["archivos_sha256"], [{"archivo": "generar_fixtures.py", "sha256": "c" * 64}])
        self.assertNotIn("hashes", e2)
        self.assertEqual(e2["hashes_codigo"], [{"archivo": "ejecutar.py", "sha256": SHA}])
        self.assertEqual(e2["codigo_sha256"], [{"archivo": "solicitudes.py", "sha256": "b" * 64}])


class Respuesta(unittest.TestCase):
    def test_reducida_preserva_normativo_y_quita_opacos(self):
        texto = json.dumps({"estado": "cumple", "cita_proyecto": "doc p2", "adjunto": RUTA_W}, ensure_ascii=False)
        resp = {"id": "resp_sintetico0001", "model": "modelo-sintetico", "status": "completed",
                "usage": {"input": 123, "output": 45}, "encrypted_content": "opaco-sintetico-borrar",
                "output": [{"id": "rs_sintetico0001", "type": "reasoning", "summary": []},
                           {"id": "msg_sintetico0001", "type": "message", "role": "assistant",
                            "content": [{"type": "output_text", "text": texto, "annotations": []}]},
                           {"id": "fs_sintetico0001", "type": "file_search_call", "status": "completed",
                            "queries": ["consulta sin datos"], "results": [
                                {"file_id": "file-sintetico0001", "filename": "d.pdf", "score": 0.9, "text": "cota 1,25 m"}]}]}
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            escribe_json(base / "r.json", resp)
            e = ex.reducir_respuesta(base / "r.json")
        self.assertNotIn("id", e)
        self.assertNotIn("encrypted_content", e)
        self.assertEqual(e["usage"], {"input": 123, "output": 45})
        tipos = [o.get("type") for o in e["output"]]
        self.assertNotIn("reasoning", tipos)
        msg = e["output"][tipos.index("message")]
        self.assertEqual(msg["role"], "assistant")
        dato = json.loads(msg["content"][0]["text"])
        self.assertEqual(dato["estado"], "cumple")
        self.assertEqual(dato["cita_proyecto"], "doc p2")
        self.assertNotIn("sintetica", json.dumps(e))
        fs = e["output"][tipos.index("file_search_call")]
        self.assertEqual(fs["status"], "completed")
        self.assertEqual(fs["queries"], ["consulta sin datos"])
        self.assertEqual(fs["results"], [{"filename": "d.pdf", "score": 0.9, "text": "cota 1,25 m"}])


class Ejecutar(unittest.TestCase):
    def test_exporta_lista_autorizada_y_no_altera_origen(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            origen = base / "evaluacion-sintetica"
            origen.mkdir()
            filas = [{"run_id": RUN, "usage": {"input": 123, "output": 45, "cache": 10},
                      "coste_usd": 0.012345, "gastado_sesion": 0.012345, "gastado_total": 0.2},
                     {"run_id": "S01-r2-adaptador", "usage": {"input": 7, "output": 8, "cache": 0},
                      "coste_usd": 0.000007, "gastado_sesion": 0.012352, "gastado_total": 0.212345}]
            (origen / "consumo.jsonl").write_text(
                "\n".join(json.dumps(f, ensure_ascii=False) for f in filas) + "\n", encoding="utf-8")
            escribe_json(origen / "manifest.json", {"modelo": "m", "hashes": {"x.py": SHA}})
            escribe_json(origen / "S01-r1.response.json", {"model": "m", "status": "completed", "output": []})
            escribe_json(origen / "S01.recuperacion.json", {"estado": "ok", "texto_contexto": "/home/sintetica/x"})
            escribe_json(origen / "S01-r1.request.json", {"x": 1})
            escribe_json(origen / "recursos.json", {"vector_stores": {
                "vs_sintetico0001": {"estado": "borrado"}}, "files": {"file-sintetico0001": {"estado": "borrado"}}})
            escribe_json(origen / "error_http_500.json", {})
            escribe_json(origen / "cleanup.json", {})
            (origen / "api_llamadas.jsonl").write_text("{}\n", encoding="utf-8")
            antes = huellas(origen)
            cierre = ex.exportar_run(origen, base / "salida" / "evaluacion-sintetica")
            self.assertEqual(huellas(origen), antes)
            self.assertEqual(sorted(p.name for p in (base / "salida" / "evaluacion-sintetica").iterdir()),
                             ["S01-r1.response.json", "S01.recuperacion.json", "cierre_publico.json",
                              "consumo.jsonl", "manifest.json"])
            self.assertEqual(cierre["conteo"], {"manifest": 1, "consumo_filas": 2, "respuestas": 1, "recuperaciones": 1})
            self.assertEqual(cierre["recursos_estados"], {"vector_stores": {"borrado": 1}, "files": {"borrado": 1}})
            texto = (base / "salida" / "evaluacion-sintetica" / "cierre_publico.json").read_text(encoding="utf-8")
            self.assertNotIn("vs_", texto)
            self.assertNotIn("file-", texto)
            self.assertNotIn("/home/", texto)
            costes = cierre["costes_observados"]
            self.assertEqual(costes["coste_run_usd"], 0.012352)
            self.assertEqual(costes["coste_acumulado_observado_usd"], 0.212345)
            segunda = json.loads((base / "salida" / "evaluacion-sintetica" / "consumo.jsonl")
                                 .read_text(encoding="utf-8").splitlines()[1])
            self.assertEqual(segunda["coste_usd"], 0.000007)
            self.assertEqual(segunda["run_id"], "S01-r2-adaptador")


class Main(unittest.TestCase):
    def ejecutar(self, origen, destino):
        argv = ["exportar_publico.py", "--origen", str(origen), "--destino", str(destino)]
        with mock.patch.object(sys, "argv", argv):
            ex.main()

    def test_rechaza_destino_invalido(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            origen = base / "res"
            origen.mkdir()
            archivo = base / "salida.txt"
            archivo.write_text("x", encoding="utf-8")
            with self.assertRaises(SystemExit) as c:
                self.ejecutar(origen, archivo)
            self.assertIn("archivo", str(c.exception))
            no_vacio = base / "salida2"
            no_vacio.mkdir()
            (no_vacio / "a.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(SystemExit) as c:
                self.ejecutar(origen, no_vacio)
            self.assertIn("nuevo o vacio", str(c.exception))
            vacio = base / "vacio"
            vacio.mkdir()
            with self.assertRaises(SystemExit) as c:
                self.ejecutar(vacio, vacio)
            self.assertIn("origen", str(c.exception))
            origen2 = base / "res2"
            origen2.mkdir()
            (origen2 / "dentro").mkdir()
            with self.assertRaises(SystemExit) as c:
                self.ejecutar(origen2, origen2 / "dentro")
            self.assertIn("origen", str(c.exception))

    def test_camino_feliz(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            run = base / "res" / "evaluacion-sintetica"
            run.mkdir(parents=True)
            filas = [{"run_id": RUN, "usage": {"input": 1, "output": 2}, "gastado_total": 0.1}]
            (run / "consumo.jsonl").write_text(
                "\n".join(json.dumps(f) for f in filas) + "\n", encoding="utf-8")
            escribe_json(run / "manifest.json", {"modelo": "m"})
            escribe_json(run / "S01-r1.response.json", {"model": "m", "status": "completed", "output": []})
            escribe_json(run / "S01-r1.request.json", {"x": 1})
            destino = base / "salida"
            self.ejecutar(run.parent, destino)
            salid = destino / "evaluacion-sintetica"
            self.assertTrue((destino / "manifest_export.json").is_file())
            raiz = json.loads((destino / "manifest_export.json").read_text(encoding="utf-8"))
            self.assertTrue(raiz["originales_preservados"])
            self.assertEqual(raiz["runs"]["evaluacion-sintetica"]["consumo_filas"], 1)
            self.assertTrue((salid / "S01-r1.response.json").is_file())
            self.assertFalse((salid / "S01-r1.request.json").exists())


if __name__ == "__main__":
    unittest.main()
