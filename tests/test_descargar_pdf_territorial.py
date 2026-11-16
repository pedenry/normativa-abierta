# -*- coding: utf-8 -*-
"""Pruebas sinteticas de ingesta/descargar_pdf_territorial.py (sin red ni shell).
Se invoca procesar_candidato directo con red Mock. El caso de archivo corrupto
define la conducta deseada; fallara hasta que el autor corrija el descargador."""
import hashlib
import io
import json
import sys
import tempfile
import unittest
from collections import namedtuple
from itertools import count
from pathlib import Path
from unittest.mock import Mock, patch

from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ingesta"))
import descargar_pdf_territorial as dpt

CAND = {"id": "c1", "fuente_id": "f1", "url": "https://h.es/doc.pdf",
        "origen": "prueba", "texto_enlace": "enlace", "hosts_permitidos": ["h.es"]}
Uso = namedtuple("Uso", "total used free")


class TestDescargarPdfTerritorial(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.salida = Path(tmp.name) / "salida"
        self.pdf = self._pdf()
        self.sha = hashlib.sha256(self.pdf).hexdigest()
        self.red = Mock()
        self.red.descargar.return_value = (self.pdf, 200, "https://h.es/final.pdf",
                                           "application/pdf", len(self.pdf))
        self.reloj = count(1)
        p = patch.object(dpt, "ahora", side_effect=lambda: "2026-01-01T00:00:%02d+00:00" % next(self.reloj))
        p.start()
        self.addCleanup(p.stop)
        disco = patch.object(dpt.shutil, "disk_usage", return_value=Uso(0, 0, 1000 * dpt.MB))
        disco.start()
        self.addCleanup(disco.stop)

    @staticmethod
    def _pdf():
        buf = io.BytesIO(); w = PdfWriter()
        w.add_blank_page(612, 792)
        w.write(buf)
        return buf.getvalue()

    def procesar(self):
        return dpt.procesar_candidato(dict(CAND), self.salida, self.red,
                                      dpt.MAX_MB_DEFECTO * dpt.MB, False, {})

    def meta(self):
        return json.loads((self.salida / "metadata" / "c1.json").read_text(encoding="utf-8"))

    def test_descarga_crea_archivo_y_metadata(self):
        detalle, _ = self.procesar()
        self.assertEqual(detalle["estado"], "ok")
        ruta = self.salida / "archivos" / (self.sha + ".pdf")
        self.assertTrue(ruta.is_file())
        self.assertEqual(ruta.read_bytes(), self.pdf)
        meta = self.meta()
        self.assertEqual(meta["sha256"], self.sha)
        self.assertEqual(meta["bytes"], len(self.pdf))
        self.assertEqual(meta["url_final"], "https://h.es/final.pdf")
        self.red.descargar.assert_called_once()

    def test_reuso_no_llama_red_y_conserva_capture_original(self):
        self.procesar()
        original = self.meta()["capture_original"]
        self.red.reset_mock()
        detalle, _ = self.procesar()
        self.assertTrue(detalle["reuso"])
        self.red.descargar.assert_not_called()
        self.assertEqual(self.meta()["capture_original"], original)

    def test_reintento_repara_archivo_corrupto(self):
        self.procesar()
        ruta = self.salida / "archivos" / (self.sha + ".pdf")
        corrupto = b"%PDF-1.4 contenido danado no reabrible"
        ruta.write_bytes(corrupto)
        detalle, _ = self.procesar()
        self.assertEqual(detalle.get("estado"), "ok")
        self.assertEqual(detalle.get("sha256"), self.sha)
        self.assertEqual(ruta.read_bytes(), self.pdf,
                         "el reintento debe reparar con las bytes validas")
        aparte = [p for p in self.salida.rglob("*")
                  if p.is_file() and p != ruta and p.read_bytes() == corrupto]
        self.assertTrue(aparte, "el PDF corrupto debe conservarse aparte")

    def test_espacio_insuficiente_bloquea_descarga_sin_red(self):
        with patch.object(dpt.shutil, "disk_usage",
                          return_value=Uso(0, 0, 64 * dpt.MB)):
            detalle, _ = self.procesar()
        self.assertEqual(detalle["estado"], "pendiente_limite")
        self.assertIn("espacio", str(detalle.get("motivo", "")))
        self.red.descargar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
