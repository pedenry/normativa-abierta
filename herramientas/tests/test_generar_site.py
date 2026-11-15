"""Regresiones del visor con corpus sintético: no red ni documentos privados."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1] / "generar_site.py"
spec = importlib.util.spec_from_file_location("generar_site", MODULE)
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)


class GenerarSiteTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = self.root / "contenido"
        self.content.mkdir()
        (self.content / "fichas").mkdir()

    def json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def document(self, identifier="DB-SUA-oficial", public=True, boe=False):
        pdf = b"%PDF-1.4\nsynthetic fixture\n"
        digest = hashlib.sha256(pdf).hexdigest()
        version_dir = "2022-06-14__" + digest[:12]
        directory = self.content / "docs" / identifier / version_dir
        meta = {"id": identifier, "code": identifier, "title": "Título <script>alert(1)</script>",
                "version": "2022-06-14", "version_dir": version_dir,
                "scope": "Seguridad utilización y accesibilidad", "layer": "asociada" if boe else "oficial",
                "sha256": digest, "distribute": public, "conteos": {"paginas": 1, "apartados": 1},
                "url": "https://www.boe.es/ejemplo.pdf", "landing": "https://www.boe.es/ejemplo",
                "advertencias": ["Consolidado meramente informativo, sin valor oficial."] if boe else [],
                "metodo_segmentacion": "pagina_fisica" if boe else "toc+lineas",
                "capturado_en_utc": "2026-11-15T00:00:00Z"}
        self.json(directory / "doc.json", meta)
        self.json(self.content / "fichas" / (identifier + ".json"), meta)
        if not public:
            # Falta PDF y el contenido no es JSON válido. No se debe abrir.
            (directory / "apartado").mkdir()
            (directory / "apartado" / "secreto.json").write_text("NO LEER PRIVADO", encoding="utf-8")
            return directory, meta
        (directory / "fuente.pdf").write_bytes(pdf)
        (directory / "pagina").mkdir()
        (directory / "pagina" / "p0001.md").write_text("Texto <img src=x onerror=alert(1)> & literal", encoding="utf-8")
        info = {"id_tecnico": "p0001" if boe else "a0001", "titulo": "Título original",
                "ruta_semantica": "Página física 1" if boe else "Fragmento de PDF p1"}
        item = {**info, "paginas": [1], "texto": "Literal <b>sin formato</b>"} if boe else {
            "apartado": info, "paginas": [1], "texto": "Literal <b>sin formato</b>"}
        name = "p0001" if boe else "a0001__titulo-original"
        self.json(directory / "apartado" / (name + ".json"), item)
        (directory / "apartado" / (name + ".md")).write_text(item["texto"], encoding="utf-8")
        return directory, meta

    def test_routes_and_both_segment_schemas(self):
        _, legacy = self.document()
        _, boe = self.document("BOE-A-2002-18099", boe=True)
        outputs, report = site.prepare(self.content)
        for meta, segment in ((legacy, "a0001"), (boe, "p0001")):
            stem = site.slug(meta["id"] + "-" + meta["version_dir"])
            self.assertIn(f"site/doc/{stem}.html", outputs)
            self.assertIn(f"site/pagina/{stem}__p0001.html", outputs)
            self.assertIn(f"site/apartado/{stem}__{segment}.html", outputs)
        self.assertIn("site/materia/sua.html", outputs)
        self.assertEqual((report["documentos"], report["apartados"], report["paginas_fuente_html"]), (2, 2, 2))
        self.assertEqual(report["enlaces_rotos"], 0)
        self.assertEqual(report["links_fuera_raiz"], 0)

    def test_restricted_body_not_read_or_published(self):
        self.document()
        self.document("PRIVADO", public=False)
        outputs, report = site.prepare(self.content)
        self.assertEqual(report["documentos"], 1)
        self.assertEqual(report["fichas"], 2)
        self.assertFalse(any("privado-" in route for route in outputs))
        self.assertNotIn("NO LEER PRIVADO", "".join(outputs.values()))
        self.assertIn("solo ficha y enlace", outputs["site/fichas.html"])

    def test_literal_escape_metadata_warnings_and_source_links(self):
        _, meta = self.document("BOE-A-2002-18099", boe=True)
        outputs, _ = site.prepare(self.content)
        for route, value in outputs.items():
            if route.startswith(("site/doc/", "site/pagina/", "site/apartado/")):
                self.assertIn("Consolidado meramente informativo", value)
                self.assertIn("No es una jerarquía de artículos", value)
                self.assertIn("Basado en datos de la", value)
                self.assertIn("Fuente de los datos:", value)
                self.assertIn(meta["sha256"], value)
                self.assertIn("2022-06-14", value)
                self.assertIn("2026-11-15T00:00:00Z", value)
                self.assertIn('href="https://www.boe.es/ejemplo"', value)
                self.assertNotIn("<script>", value)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", "".join(outputs.values()))
        self.assertEqual(site.link("javascript:alert(1)", "enlace"), "enlace")
        self.assertEqual(site.link("//malicioso.example", "enlace"), "enlace")

    def test_warning_types_are_not_iterated_as_characters(self):
        doc = {"meta": {"advertencias": "TEXTO NO ES LISTA", "nota_capa": None}}
        rendered = site.warnings(doc)
        self.assertNotIn("<li>T</li>", rendered)
        self.assertNotIn("TEXTO NO ES LISTA", rendered)
        doc["meta"]["advertencias"] = ["Aviso", {"html": "<script>"}, "Aviso", 14]
        rendered = site.warnings(doc)
        self.assertEqual(rendered.count("<li>Aviso</li>"), 1)
        self.assertNotIn("<script>", rendered)

    def test_legacy_boe_id_gets_attribution_and_consolidation_notice(self):
        directory, _ = self.document("RITE-asociada")
        (directory / "pagina" / "p0001.md").write_text("LEGISLACIÓN CONSOLIDADA\nTexto", encoding="utf-8")
        outputs, _ = site.prepare(self.content)
        for route, value in outputs.items():
            if route.startswith(("site/doc/", "site/pagina/", "site/apartado/")):
                self.assertIn("Basado en datos de la", value)
                self.assertIn("Consolidado meramente informativo, sin valor oficial", value)

    def test_guide_credits_from_permission_evidence_are_preserved_whole(self):
        directory, meta = self.document("GUIA-ejemplo")
        credits = "Autoras: Persona A y Persona B. " + "Créditos completos. " * 180
        meta.update({"url": "https://www.codigotecnico.org/guia.pdf", "landing": None, "creditos": None,
                     "license_evidence": [{"page": 1, "permission_text": "Se permite reproducir citando autores.",
                                           "credits_page_text": credits}]})
        self.json(directory / "doc.json", meta)
        outputs, _ = site.prepare(self.content)
        for route, value in outputs.items():
            if route.startswith(("site/doc/", "site/pagina/", "site/apartado/")):
                self.assertIn(credits, value)
                self.assertIn("Se permite reproducir citando autores.", value)
                self.assertIn("fuente.pdf#page=1", value)

    def test_hash_mismatch_fails_before_writes(self):
        directory, _ = self.document()
        (directory / "fuente.pdf").write_bytes(b"%PDF- changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            site.prepare(self.content)
        self.assertFalse((self.root / "candidato").exists())

    def test_determinism_and_candidate_isolation(self):
        self.document()
        first, report1 = site.prepare(self.content)
        second, report2 = site.prepare(self.content)
        self.assertEqual(first, second)
        self.assertEqual(report1, report2)
        candidate = self.root / "candidato"
        site.write_candidate(first, candidate, self.content)
        before = {p.relative_to(candidate).as_posix(): p.read_bytes() for p in candidate.rglob("*") if p.is_file()}
        site.write_candidate(second, candidate, self.content)
        after = {p.relative_to(candidate).as_posix(): p.read_bytes() for p in candidate.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        with self.assertRaises(ValueError):
            site.write_candidate(first, self.root, self.content)
        foreign = candidate / "ajeno.txt"
        foreign.write_text("preservar", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ajenos"):
            site.write_candidate(first, candidate, self.content)
        self.assertEqual(foreign.read_text(), "preservar")

    def test_validator_checks_paths_and_fragment_targets(self):
        outputs = {"index.html": '<a href="site/a.html#bien">bien</a>',
                   "site/a.html": '<h1 id="bien">A</h1><a href="../index.html">inicio</a>'}
        self.assertEqual(site.validate_links(outputs, self.content)["enlaces_rotos"], 0)
        outputs["site/a.html"] += '<a href="../../privado.txt">fuera</a><a href="#ausente">mal</a>'
        result = site.validate_links(outputs, self.content)
        self.assertEqual(result["links_fuera_raiz"], 1)
        self.assertEqual(result["enlaces_rotos"], 1)

    def test_symlink_source_file_is_rejected(self):
        directory, _ = self.document()
        page = directory / "pagina" / "p0001.md"
        target = self.root / "outside.txt"
        target.write_text("secreto", encoding="utf-8")
        page.unlink()
        try:
            page.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("El sistema no permite symlinks en esta sesión")
        with self.assertRaisesRegex(ValueError, "simbólicos"):
            site.prepare(self.content)


if __name__ == "__main__":
    unittest.main()
