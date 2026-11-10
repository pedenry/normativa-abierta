"""Pruebas del piloto SUA sin red: red y entorno simulados con unittest.mock; la clave nunca es real.
Ejecutar (Codex): python -m unittest discover -s evaluacion/piloto_sua -p "test_*.py" (discover inserta la carpeta en sys.path)."""
import base64, json, os, tempfile, unittest
from pathlib import Path
from unittest import mock
AQUI = Path(__file__).resolve().parent
import cliente_api, solicitudes
CASOS = json.loads((AQUI / "casos.json").read_text(encoding="utf-8"))["casos"]
PDF = b"%PDF-1.4 piloto-sintetico-test\n"
ENV = {"OPENAI_API_KEY": "sk-dummy-solo-pruebas"}

class PlanAB(unittest.TestCase):
    def test_casos_12_con_4_dev_y_8_eval(self):
        self.assertEqual(len(CASOS), 12)
        self.assertEqual([c["split"] for c in CASOS].count("desarrollo"), 4)
        self.assertEqual([c["split"] for c in CASOS].count("evaluacion"), 8)
    def test_8casos_x_3reps_x_2_dan_48_slots_ids_unicos_y_brazos_alternados(self):
        ocho = [{"id": f"T{i:02d}"} for i in range(8)]
        plan = solicitudes.planificar(ocho, 3)
        self.assertEqual(len(plan), 48)
        self.assertEqual(len({p["id"] for p in plan}), 48)
        pares = {}
        for p in plan:
            pares.setdefault((p["caso"]["id"], p["repeticion"]), []).append(p["brazo"])
        self.assertEqual(len(pares), 24)
        self.assertTrue(all(sorted(v) == ["adaptador", "pdf_indexado"] for v in pares.values()))
        self.assertTrue(all(pares[(c["id"], r)][0] != pares[(c["id"], r + 1)][0] for c in ocho for r in (1, 2)))
        self.assertEqual(sum(1 for p in plan if p["brazo"] == "adaptador"), 24)

class Solicitud(unittest.TestCase):
    def _caso(self):
        caso = dict(CASOS[0])
        caso["datos_plano"] = {"elemento": "Pasillo", "anchura_libre_m": 9.99}
        caso["valor_secreto"] = "XSECRETO999"
        return caso
    def test_brazos_comparten_modelo_esquema_prompt_input_comun_y_mismos_bytes_pdf(self):
        a = solicitudes.construir_solicitud(self._caso(), PDF, "adaptador", contexto={"estado": "ok", "texto_contexto": "ctx"})
        b = solicitudes.construir_solicitud(self._caso(), PDF, "pdf_indexado", vector_id="vs_x")
        self.assertEqual((a["model"], a["text"], a["input"][0]), (b["model"], b["text"], b["input"][0]))
        self.assertEqual(a["text"]["format"]["type"], "json_schema")
        self.assertEqual(a["input"][1]["content"][:2], b["input"][1]["content"][:2])
        b64 = "data:application/pdf;base64," + base64.b64encode(PDF).decode("ascii")
        self.assertTrue(all(c["input"][1]["content"][1]["file_data"] == b64 for c in (a, b)))
    def test_candidate_solo_anade_contexto_y_baseline_filtra_version_2010(self):
        caso = self._caso(); caso["version"] = "2010-03-11"
        a = solicitudes.construir_solicitud(caso, PDF, "adaptador", contexto={"estado": "ok", "texto_contexto": "ctx-unico"})
        b = solicitudes.construir_solicitud(caso, PDF, "pdf_indexado", vector_id="vs_x")
        self.assertNotIn("tools", a)
        self.assertEqual(len(a["input"][1]["content"]), 3)
        self.assertIn("contexto_estado: ok", a["input"][1]["content"][2]["text"])
        self.assertEqual([f["value"] for f in b["tools"][0]["filters"]["filters"] if f["key"] == "version"], ["2010-03-11"])
    def test_datos_plano_y_valor_secreto_inyectados_no_aparecen_en_solicitud(self):
        for brazo in ("adaptador", "pdf_indexado"):
            cuerpo = solicitudes.construir_solicitud(self._caso(), PDF, brazo, contexto={"estado": "s", "texto_contexto": "t"}, vector_id="vs_x")
            texto = json.dumps(cuerpo)
            self.assertTrue(all(s not in texto for s in ("datos_plano", "valor_secreto", "XSECRETO999", "9.99")))

class Cliente(unittest.TestCase):
    def _cliente(self, tmp):
        return cliente_api.ClienteAPI(Path(tmp))
    def test_sanear_quita_base64_preserva_hash_y_longitud_sin_mutar_body(self):
        original = "data:application/pdf;base64,QUJDRA=="
        cuerpo = {"input": [{"content": [{"type": "input_file", "file_data": original}]}]}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, ENV):
            fd = self._cliente(tmp)._sanear(cuerpo)["input"][0]["content"][0]["file_data"]
        self.assertNotIn("base64,", json.dumps(fd))
        self.assertEqual(fd["longitud"], len(original))
        self.assertRegex(fd["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(cuerpo["input"][0]["content"][0]["file_data"], original)
    def test_contabilizar_total_1100_no_1550_y_coste_con_file_search(self):
        resp = {"usage": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100,
                "input_tokens_details": {"cached_tokens": 400}, "output_tokens_details": {"reasoning_tokens": 50}},
                "output": [{"type": "file_search_call"}]}
        esperado = (600 * 0.75 + 400 * 0.075 + 100 * 4.5) / 1e6 + 0.0025
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, ENV):
            c = self._cliente(tmp)
            coste = c._contabilizar("R1", resp, 1.2)
            fila = json.loads(c.ruta_consumo.read_text(encoding="utf-8").strip())
        self.assertAlmostEqual(coste, esperado, places=9)
        self.assertAlmostEqual(c.gastado_sesion, esperado, places=9)
        self.assertEqual((fila["usage"]["total_input_mas_output"], fila["file_search_calls"]), (1100, 1))
        self.assertNotEqual(fila["usage"]["total_input_mas_output"], 1550)
        self.assertEqual(fila["coste_usd"], round(esperado, 6))
    def test_guarda_presupuesto_bloquea_antes_de_request(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, ENV):
            c = self._cliente(tmp)
            c.gastado_sesion = 3.8  # 0.5 reserva + 0 previo + 3.8 = 4.3 > presupuesto 4.0
            with mock.patch.object(c, "request") as req, self.assertRaisesRegex(RuntimeError, "reserva"):
                c.respuesta({"model": "m", "input": []}, "run-bloqueado")
            req.assert_not_called()
    def test_limpiar_solo_ids_registrados_continua_tras_fallo_y_deja_estado_y_logs(self):
        def fake(method, path, body=None):
            llamadas.append(f"{method} {path}")
            if path.endswith("vs-1"): raise RuntimeError("boom")
            return {}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, ENV):
            c = self._cliente(tmp)
            c.ruta_log.write_text("linea-log-previa\n", encoding="utf-8")
            c.recursos = {"vector_stores": {"vs-1": {"estado": "creado"}, "vs-2": {"estado": "creado"}},
                          "files": {"f-1": {"estado": "creado"}}}
            llamadas = []
            with mock.patch.object(c, "request", side_effect=fake):
                res = c.limpiar()
            self.assertEqual(llamadas, ["DELETE /vector_stores/vs-1", "DELETE /vector_stores/vs-2", "DELETE /files/f-1"])
            self.assertEqual(res, {"vs-1": "error:RuntimeError", "vs-2": "borrado", "f-1": "borrado"})
            estados = json.loads(c.ruta_recursos.read_text(encoding="utf-8"))["vector_stores"]
            self.assertEqual((estados["vs-1"]["estado"], estados["vs-2"]["estado"]), ("error_borrado:RuntimeError", "borrado"))
            self.assertIn("linea-log-previa\n", c.ruta_log.read_text(encoding="utf-8"))
    def test_multipart_valido_purpose_assistants_y_bytes_pdf(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, ENV):
            c = self._cliente(tmp)
            with mock.patch.object(c, "_enviar", return_value={"id": "file-123"}) as envio:
                out = c._upload_multipart("file", "proyecto.pdf", PDF, {"purpose": "assistants"})
            req, endpoint = envio.call_args[0]
            self.assertEqual((out, endpoint, req.method), ({"id": "file-123"}, "POST /files (multipart)", "POST"))
            self.assertEqual([type(req.data), type(req.get_header("Content-type"))], [bytes, str])
            limite = req.get_header("Content-type").split("boundary=", 1)[1]
            self.assertTrue(req.data.startswith(f"--{limite}\r\n".encode()) and req.data.endswith(f"--{limite}--\r\n".encode()))
            self.assertIn(b'name="purpose"\r\n\r\nassistants', req.data)
            self.assertIn(b'filename="proyecto.pdf"', req.data)
            self.assertIn(PDF, req.data)

# Archivos: normativa-abierta/evaluacion/piloto_sua/test_piloto.py (nuevo; 10 pruebas, sin red ni clave real).
# Ejecucion externa (Codex; aqui no se ejecuto nada): unittest discover en evaluacion/piloto_sua con 10 pruebas pasando.
# Fixtures PDF y referencia.md existen; el test no necesita leer el gold.
