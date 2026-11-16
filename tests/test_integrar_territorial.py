# -*- coding: utf-8 -*-
"""Pruebas sinteticas de ingesta/integrar_territorial.py (sin red ni shell). Un
fallo indica defecto del script; la segunda tanda define la conducta deseada."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "ingesta" / "integrar_territorial.py"
LIC = "territorial-2026-11-16.json"


def _pdf_una_pagina(texto):
    stream = ("BT /F1 12 Tf 72 720 Td (%s) Tj ET" % texto).encode("latin-1")
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream)]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


class TestIntegrarTerritorial(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.contenido = self.tmp / "contenido"
        self.pdf_bytes = _pdf_una_pagina("Texto ordenanza municipal de prueba pagina uno")
        self.pdf = self.tmp / "datos" / "doc.pdf"
        self.evid = self.tmp / "datos" / "bop.html"
        self.pdf.parent.mkdir(parents=True)
        self.pdf.write_bytes(self.pdf_bytes)
        self.evid.write_text("<html>Evidencia oficial BOP</html>", encoding="utf-8")
        self.evid_sha = hashlib.sha256(self.evid.read_bytes()).hexdigest()

    def fuente(self, id_):
        return {"id": id_, "titulo": "Ordenanza " + id_,
                "disposicion": "Ordenanza municipal", "jurisdiccion": "local",
                "materia": "Urbanismo", "municipio": "Test",
                "version": "2026-01-15", "version_label_literal": "TXT-2026",
                "fecha_publicacion": "2026-01-15", "creditos": "Ayuntamiento de Test",
                "capturado_en_utc": "2026-11-16T10:00:00Z", "paginas_fisicas": 1,
                "url_pdf": "https://ejemplo.test/bop.pdf", "url_fuente": "https://ejemplo.test/ficha",
                "ruta_pdf": str(self.pdf),
                "sha256_pdf": hashlib.sha256(self.pdf_bytes).hexdigest(),
                "reutilizacion": {"estado": "APROBADA", "base_juridica": "Interes publico",
                                  "alcance": "Publicacion integra del boletin",
                                  "revision_por": "Revision documental",
                                  "evidencia_url": "https://ejemplo.test/ev",
                                  "evidencia_ruta_local": str(self.evid),
                                  "evidencia_sha256": self.evid_sha}}

    def correr(self, fuentes, nombre="fuentes.json"):
        p = self.tmp / "entrada" / nombre
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"fuentes": fuentes}, ensure_ascii=False),
                     encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), "--origen", str(p),
                               "--contenido", str(self.contenido)],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", shell=False)

    def snapshot(self):
        return {str(p.relative_to(self.tmp)): hashlib.sha256(p.read_bytes()).hexdigest()
                for base in (self.contenido, self.tmp / "licencias")
                for p in base.rglob("*") if p.is_file()}

    def sin_corpus(self):
        c = self.contenido
        self.assertFalse(any((c / x).exists() for x in ("docs", "fichas", "indice/apartados.jsonl", "manifest_publico.json")))

    def bloquea(self, fuentes, nombre="fuentes.json"):
        r = self.correr(fuentes, nombre)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ERROR preflight", r.stderr)
        self.assertNotIn("SyntaxError", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_sin_aprobada_bloquea_sin_corpus(self):
        f = self.fuente("doc-a")
        f["reutilizacion"]["estado"] = "PENDIENTE"
        self.bloquea([f])
        self.sin_corpus()

    def test_hash_evidencia_o_pdf_distinto_bloquea(self):
        f = self.fuente("doc-a")
        f["reutilizacion"]["evidencia_sha256"] = "0" * 64
        self.bloquea([f], "f1.json")
        self.sin_corpus()
        f2 = self.fuente("doc-b")
        f2["sha256_pdf"] = "0" * 64
        self.bloquea([f2], "f2.json")
        self.sin_corpus()

    def test_lote_mixto_no_deja_buena_parcial(self):
        mala = self.fuente("doc-mala")
        mala["paginas_fisicas"] = 2
        self.bloquea([self.fuente("doc-buena"), mala])
        self.sin_corpus()
        self.assertFalse((self.contenido / "docs" / "doc-buena").exists())

    def test_integracion_valida_genera_salidas(self):
        f = self.fuente("doc-a")
        self.assertEqual(self.correr([f]).returncode, 0)
        vdir = self.contenido / "docs" / "doc-a" / ("2026-01-15__" + f["sha256_pdf"][:12])
        self.assertEqual((vdir / "fuente.pdf").read_bytes(), self.pdf_bytes)
        pagina = (vdir / "pagina" / "p0001.md").read_text(encoding="utf-8")
        self.assertIn("ordenanza municipal", pagina.lower())
        self.assertTrue((vdir / "apartado" / "p0001.json").is_file())
        ficha = json.loads((self.contenido / "fichas" / "doc-a.json").read_text("utf-8"))
        self.assertEqual(ficha["title"], "Ordenanza doc-a")
        fila = json.loads((self.contenido / "indice" / "apartados.jsonl").read_text("utf-8").splitlines()[0])
        self.assertEqual(fila["documento"], "doc-a")
        lic = json.loads((self.tmp / "licencias" / LIC).read_text("utf-8"))
        self.assertEqual([d["id"] for d in lic["documentos"]], ["doc-a"])

    def test_reejecucion_mismo_id_hash_no_cambia_bytes(self):
        f = self.fuente("doc-a")
        self.assertEqual(self.correr([f]).returncode, 0)
        antes = self.snapshot()
        self.assertEqual(self.correr([f], "reintento.json").returncode, 0)
        self.assertEqual(antes, self.snapshot())

    def test_segunda_tanda_otro_id_conserva_evidencia(self):
        self.assertEqual(self.correr([self.fuente("doc-a")], "f1.json").returncode, 0)
        self.assertEqual(self.correr([self.fuente("doc-b")], "f2.json").returncode, 0)
        lic = json.loads((self.tmp / "licencias" / LIC).read_text("utf-8"))
        ids = [d["id"] for d in lic["documentos"]]
        self.assertIn("doc-a", ids, "licencias pierde la primera tanda")
        self.assertIn("doc-b", ids)
        val = json.loads((self.contenido / "validacion" / LIC).read_text("utf-8"))
        vids = [v["id"] for v in val["fuentes"]]
        self.assertIn("doc-a", vids, "validacion pierde la primera tanda")
        self.assertIn("doc-b", vids)
