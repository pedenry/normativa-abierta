#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_libres.py — 4 pruebas unitarias sintéticas e independientes del evaluador
de búsqueda libre territorial (territorial/ejecutar_libres.py).

Sin modelos, sin red y sin corpus real: cada prueba construye en un directorio
temporal propio un contenido mínimo (doc.json + páginas pNNNN.md) y un resultado
sintético con la misma forma JSON que emite AdaptadorContexto.preparar, y evalúa
la lógica pura de _registro_caso y _resumen. No se ejecuta el motor ni el
adaptador real.

Cubre:
1) test_gold_ajeno_no_acredita — una página válida de OTRO documento no acredita
   el gold aunque coincida el número de página; queda trazada como documento no
   esperado y el acierto falla por gold faltante (ámbito compatible: mismo CCAA).
2) test_mezcla_ambito_invalida_acierto — una fuente de OTRA CCAA junto al gold
   marca ámbito mezcla_ambito (documentos_ambito_incompatible por caso y
   resumen), invalida el acierto aunque el gold esté presente y fuerza exit 1;
   resolucion_ambito del motor se conserva tal cual y las páginas no se filtran.
   Incluye subcaso homónimo: fuente municipal con el mismo municipio pero de
   otra CCAA también es incompatible (con caso.jurisdiccion declarada se exige
   también jurisdicción coincidente).
3) test_nacional_complementaria_permitida — una fuente nacional (doc.json sin
   jurisdicción ni municipio, p. ej. un REBT) junto al gold NO es incompatible:
   ámbito compatible, acierto posible y exit 0.
4) test_metadata_incoherente — doc.json con distribute false o con versión
   declarada distinta a la usada por el motor genera incidencia
   metadata_incoherente, integridad_ok False y acierto False.
5) test_carpeta_legacy_consistente — carpeta legacy cuyo nombre no empieza por
   la fecha (p. ej. sin-fecha__<hash>) con doc.json coherente (id, version,
   version_dir==nombre de carpeta, distribute True): metadata_ok y página
   aceptada por el helper local; variantes con version declarada distinta o
   version_dir que no coincide con el nombre de carpeta: rechazadas
   (metadata_incoherente + ruta_fuera_documento_edicion), integridad False,
   acierto False y exit 1 con gold presente.
6) test_alternativa_propia_validada_adjudica — con --alternativas (opt-in), una
   adjudicación posterior de la MISMA edición, página ya devuelta y verificada
   (ruta/sha/texto/metadata_ok) admite el caso por adjudicación MANTIENDO los
   faltantes originales del gold; resumen_original (gold exclusivo) exit 1 y
   resumen adjudicado separa aciertos_gold_exacto de aciertos_adjudicados sin
   fingir cobertura gold exacta; la MISMA página de OTRO documento de la MISMA
   CCAA devuelta ANTES no provoca falso negativo (fila por pagina+doc+version).
7) test_alternativa_incoherente_no_acredita — variantes que NO acreditan: doc
   distinto del esperado (caso rechazado en el helper), sha incorrecto, archivo
   incorrecto y texto ausente del contexto real (evidencia rechazada con motivo,
   acierto False, exit 1 adjudicado); y contrato de entrada: hash de fixture
   distinto, posterior_a_resultados != true o esquema incorrecto -> ValueError;
   entrada con consulta distinta -> rechazo visible (sin aceptación silenciosa).

Límite: pruebas de la lógica del evaluador con datos sintéticos; no acreditan el
comportamiento del motor real ni la calidad de la recuperación.
Uso: python -m unittest evaluacion.regresion_recuperacion.test_libres (desde la raíz)
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA / "territorial"))
import ejecutar_libres as lib  # noqa: E402  (lógica pura; no arranca el motor)


def _fabricar_contenido(td, docs):
    """docs: {doc: {"version": ..., "carpeta": nombre_fisico opcional,
    "version_dir": declarado opcional, "jurisdiccion": ..., "municipio": ...,
    "distribute": bool, "paginas": {n: texto}}} -> {("doc", n): texto}.
    Por defecto la carpeta es <version>__test y el doc.json declara
    version_dir igual al nombre de la carpeta (como el corpus real)."""
    textos = {}
    for doc, cfg in docs.items():
        ver = cfg["version"]
        nombre = cfg.get("carpeta") or ("%s__test" % ver)
        d = td / "docs" / doc / nombre
        (d / "pagina").mkdir(parents=True)
        dj = {"id": doc, "version": cfg.get("version_declarada", ver),
              "version_dir": cfg.get("version_dir", nombre),
              "distribute": cfg.get("distribute", True),
              "jurisdiccion": cfg.get("jurisdiccion"), "municipio": cfg.get("municipio")}
        (d / "doc.json").write_text(json.dumps(dj, ensure_ascii=False), encoding="utf-8")
        for n, texto in (cfg.get("paginas") or {}).items():
            (d / "pagina" / ("p%04d.md" % n)).write_text(texto, encoding="utf-8")
            textos[(doc, n)] = texto
    return textos


def _pagina(doc, ver, n, texto, motivo="primaria", vdir=None):
    vdir = vdir or ("%s__test" % ver)
    return {"doc": doc, "version": ver, "pagina": n, "motivo": motivo,
            "archivo": "docs/%s/%s/pagina/p%04d.md" % (doc, vdir, n),
            "texto_sha256": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            "etiqueta_impresa": None, "url_fuente": None}


def _res(paginas, textos, resolucion_ambito=None):
    """Resultado sintético con la forma de la salida real del adaptador."""
    partes = [textos[(p["doc"], p["pagina"])] for p in paginas]
    return {"estado": "ok", "consulta": "consulta sintética", "documento": None,
            "version": None, "texto_contexto": "\n".join(partes) + "\n",
            "paginas": list(paginas), "recuperacion": {"resultados": []},
            "tokens_contexto": 10, "excedido": False,
            "resolucion_ambito": resolucion_ambito}


def _caso(jur="Andalucía", mun=None, doc="D1", ver="2026-01-01", pags=(26,)):
    return {"id": "L-X", "consulta": "consulta sintética",
            "esperado_documento": doc, "esperada_version": ver,
            "esperadas_paginas": list(pags), "jurisdiccion": jur, "municipio": mun}


class TestEvaluadorLibres(unittest.TestCase):

    def test_gold_ajeno_no_acredita(self):
        """Página válida de otro documento (misma CCAA) no acredita el gold."""
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado."}},
                "D2": {"version": "2026-02-02", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto valido de otro documento andaluz."}}})
            caso = _caso()
            res = _res([_pagina("D2", "2026-02-02", 26, textos[("D2", 26)])], textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["contexto"], [])
            self.assertEqual(reg["cobertura"]["faltantes"], [26])
            self.assertIn("D2", reg["documentos_no_esperados"])
            self.assertEqual(reg["ambito"]["estado"], "compatible")  # mismo CCAA
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 1)
            self.assertEqual(resumen["aciertos"], [])

    def test_mezcla_ambito_invalida_acierto(self):
        """Otra CCAA junto al gold: mezcla marcada, acierto inválido, exit 1."""
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado."}},
                "D3": {"version": "2026-03-03", "jurisdiccion": "Cataluña",
                       "paginas": {7: "Texto de una ley de otra comunidad."}}})
            caso = _caso()
            amb_motor = {"estado": "no_resuelto", "consulta_original": "consulta sintética",
                         "territorios": [], "nombres_no_resueltos": [],
                         "documentos_permitidos": None, "notas": ["sintético"]}
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)]),
                        _pagina("D3", "2026-03-03", 7, textos[("D3", 7)], motivo="auxiliar")],
                       textos, resolucion_ambito=amb_motor)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["contexto"], [26])  # gold presente
            self.assertEqual(len(reg["paginas"]), 2)  # sin filtrar páginas
            self.assertEqual(reg["ambito"]["estado"], "mezcla_ambito")
            self.assertIn("D3|2026-03-03", reg["ambito"]["documentos_ambito_incompatible"])
            # resolucion_ambito del motor se conserva TAL CUAL, sin interpretar.
            self.assertEqual(reg["busqueda"]["resolucion_ambito"], amb_motor)
            self.assertFalse(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 1)
            self.assertEqual(resumen["ambito"]["casos_mezcla_ambito"], ["L-X"])
            self.assertIn("D3|2026-03-03",
                          resumen["ambito"]["documentos_ambito_incompatible"])
        # Subcaso homónimo: fuente municipal con el MISMO municipio pero de otra
        # CCAA -> incompatible aunque el municipio coincida; el gold municipal
        # (municipio y jurisdicción coincidentes) sigue siendo compatible.
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "municipio": "Málaga",
                       "paginas": {26: "Texto del gold municipal malagueño esperado."}},
                "DM": {"version": "2026-06-06", "jurisdiccion": "Cataluña",
                       "municipio": "Málaga",
                       "paginas": {5: "Ordenanza de una ciudad homonima de otra comunidad."}}})
            caso = _caso(jur="Andalucía", mun="Málaga")
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)]),
                        _pagina("DM", "2026-06-06", 5, textos[("DM", 5)], motivo="auxiliar")],
                       textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["contexto"], [26])  # gold presente
            self.assertEqual(reg["ambito"]["estado"], "mezcla_ambito")
            self.assertIn("DM|2026-06-06",
                          reg["ambito"]["documentos_ambito_incompatible"])
            self.assertNotIn("D1|2026-01-01",
                             reg["ambito"]["documentos_ambito_incompatible"])
            self.assertFalse(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 1)
            self.assertIn("DM|2026-06-06",
                          resumen["ambito"]["documentos_ambito_incompatible"])

    def test_nacional_complementaria_permitida(self):
        """Fuente nacional (sin jurisdicción ni municipio) junto al gold: permitida."""
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado."}},
                "DN": {"version": "2026-04-04", "jurisdiccion": None,
                       "municipio": None,
                       "paginas": {3: "Texto nacional complementario sin jurisdiccion."}}})
            caso = _caso()
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)]),
                        _pagina("DN", "2026-04-04", 3, textos[("DN", 3)], motivo="auxiliar")],
                       textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["ambito"]["estado"], "compatible")
            self.assertEqual(reg["ambito"]["documentos_ambito_incompatible"], [])
            doc_nac = [d for d in reg["documentos"] if d["documento"] == "DN"][0]
            self.assertEqual(doc_nac["tipo_ambito"], "nacional")
            self.assertIs(doc_nac["ambito_compatible"], True)
            self.assertTrue(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 0)
            self.assertEqual(resumen["aciertos"], ["L-X"])

    def test_metadata_incoherente(self):
        """doc.json con distribute false o versión declarada distinta: detectado."""
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D4": {"version": "2026-05-05", "jurisdiccion": "Andalucía",
                       "distribute": False,
                       "paginas": {26: "Texto del gold de un doc no distribuible."}}})
            caso = _caso(doc="D4", ver="2026-05-05")
            res = _res([_pagina("D4", "2026-05-05", 26, textos[("D4", 26)])], textos)
            reg = lib._registro_caso(caso, res, td)
            tipos = [i["tipo"] for i in reg["integridad_incidencias"]]
            self.assertIn("metadata_incoherente", tipos)
            detalles = [i["detalle"] for i in reg["integridad_incidencias"]]
            self.assertIn("distribute_false", detalles)
            self.assertFalse(reg["integridad_ok"])
            self.assertFalse(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 1)
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D5": {"version": "2025-05-05", "version_declarada": "2025-01-01",
                       "jurisdiccion": "Andalucía",
                       "paginas": {12: "Texto con version declarada distinta."}}})
            caso = _caso(doc="D5", ver="2025-05-05", pags=(12,))
            res = _res([_pagina("D5", "2025-05-05", 12, textos[("D5", 12)])], textos)
            reg = lib._registro_caso(caso, res, td)
            detalles = [i["detalle"] for i in reg["integridad_incidencias"]
                        if i["tipo"] == "metadata_incoherente"]
            self.assertIn("version_declarada_distinta", detalles)
            self.assertFalse(reg["integridad_ok"])
            self.assertFalse(lib._acierto(reg))

    def test_carpeta_legacy_consistente(self):
        """Carpeta legacy (nombre sin fecha) con metadata coherente: aceptada;
        variantes con version declarada distinta o version_dir incorrecto:
        rechazadas. Reproduce el falso positivo con DB-HS-oficial
        (sin-fecha__<hash> declarando version 2022-06-14)."""
        # PASS: legacy declara id/version/version_dir/distribute coherentes
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado."}},
                "DL": {"version": "2022-06-14", "carpeta": "sin-fecha__abc123",
                       "jurisdiccion": None, "municipio": None,
                       "paginas": {3: "Texto nacional de carpeta legacy coherente."}}})
            caso = _caso()
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)]),
                        _pagina("DL", "2022-06-14", 3, textos[("DL", 3)],
                                motivo="auxiliar", vdir="sin-fecha__abc123")], textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["contexto"], [26])
            self.assertEqual(reg["integridad_incidencias"], [])
            self.assertTrue(reg["integridad_ok"])
            doc_l = [d for d in reg["documentos"] if d["documento"] == "DL"][0]
            self.assertTrue(doc_l["metadata"]["metadata_ok"])
            self.assertEqual(doc_l["metadata"]["carpeta"], "sin-fecha__abc123")
            self.assertEqual(doc_l["tipo_ambito"], "nacional")
            self.assertIs(doc_l["ambito_compatible"], True)
            self.assertEqual(reg["ambito"]["estado"], "compatible")
            self.assertTrue(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 0)
            self.assertEqual(resumen["aciertos"], ["L-X"])
        # FAIL version: la carpeta declara OTRA versión distinta a la reclamada;
        # ninguna carpeta afirma la edición pedida -> doc_json_ausente y la
        # ruta queda fuera (no hay carpeta válida para esa edición).
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado."}},
                "DL": {"version": "2022-01-01", "carpeta": "sin-fecha__def456",
                       "jurisdiccion": None,
                       "paginas": {3: "Texto de legacy que declara version distinta."}}})
            caso = _caso()
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)]),
                        _pagina("DL", "2022-06-14", 3, textos[("DL", 3)],
                                motivo="auxiliar", vdir="sin-fecha__def456")], textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["contexto"], [26])  # gold presente
            tipos = [i["tipo"] for i in reg["integridad_incidencias"]]
            self.assertIn("metadata_incoherente", tipos)
            self.assertIn("ruta_fuera_documento_edicion", tipos)
            detalles = [i["detalle"] for i in reg["integridad_incidencias"]
                        if i["tipo"] == "metadata_incoherente"]
            self.assertIn("doc_json_ausente", detalles)
            self.assertFalse(reg["integridad_ok"])
            self.assertFalse(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 1)
        # FAIL version_dir: la carpeta declara un version_dir que NO es su
        # nombre -> no es candidata estricta ni para metadata ni para ruta.
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado."}},
                "DL": {"version": "2022-06-14", "carpeta": "sin-fecha__ghi789",
                       "version_dir": "sin-fecha__otro",
                       "jurisdiccion": None,
                       "paginas": {3: "Texto de legacy con version_dir erroneo."}}})
            caso = _caso()
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)]),
                        _pagina("DL", "2022-06-14", 3, textos[("DL", 3)],
                                motivo="auxiliar", vdir="sin-fecha__ghi789")], textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["contexto"], [26])  # gold presente
            tipos = [i["tipo"] for i in reg["integridad_incidencias"]]
            self.assertIn("metadata_incoherente", tipos)
            self.assertIn("ruta_fuera_documento_edicion", tipos)
            detalles = [i["detalle"] for i in reg["integridad_incidencias"]
                        if i["tipo"] == "metadata_incoherente"]
            self.assertIn("version_dir_distinto", detalles)
            self.assertFalse(reg["integridad_ok"])
            self.assertFalse(lib._acierto(reg))
            resumen, codigo = lib._resumen([reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo, 1)

    def test_alternativa_propia_validada_adjudica(self):
        """Opt-in --alternativas: adjudicación posterior de la MISMA edición,
        página ya devuelta y verificada, admite el caso MANTENIENDO los faltantes
        originales; gold exclusivo (resumen_original) exit 1; adjudicado separa
        gold exacto de adjudicado sin fingir cobertura gold. Si ANTES de la
        página correcta aparece la MISMA página de OTRO documento de la MISMA
        CCAA (ambas íntegras y con metadata válida), la fila se localiza por
        pagina+doc+version y la alternativa correcta se admite igualmente."""
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado.",
                                   7: "Texto alternativo verificado en la misma edicion."}}})
            caso = _caso()
            # Respuesta REAL: solo p7 (la p26 del gold no fue devuelta).
            p7 = _pagina("D1", "2026-01-01", 7, textos[("D1", 7)], motivo="auxiliar")
            res = _res([p7], textos)
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["faltantes"], [26])
            resumen_original, codigo_original = lib._resumen(
                [reg], {"esperado": {}, "casos": [caso]})
            self.assertEqual(codigo_original, 1)  # gold exclusivo: fallo
            self.assertEqual(resumen_original["aciertos"], [])
            alt = {"esquema": lib.ESQUEMA_ALTERNATIVAS,
                   "revision": {"fecha": "2026-11-16", "motivo": "revision sintetica posterior",
                                "posterior_a_resultados": True},
                   "fixture_sha256": "f" * 64,
                   "casos": [{"id": "L-X", "consulta": caso["consulta"],
                              "documento": "D1", "version": "2026-01-01",
                              "adjudicacion": "REF-SIN-1",
                              "paginas": [{"pagina": p7["pagina"], "archivo": p7["archivo"],
                                           "texto_sha256": p7["texto_sha256"]}]}],
                   "casos_rechazados": []}
            apl, regs = lib._aplicar_alternativas([reg], {"casos": [caso]}, alt)
            self.assertIs(regs[0], reg)  # helper anota en el mismo registro
            self.assertEqual(reg["cobertura"]["faltantes"], [26])  # gold intacto
            self.assertEqual(reg["cobertura"]["contexto"], [])  # no se finge gold
            self.assertEqual(reg["evidencias_alternativas_validas"],
                             [{"pagina": 7, "archivo": p7["archivo"],
                               "texto_sha256": p7["texto_sha256"], "adjudicacion": "REF-SIN-1"}])
            self.assertTrue(reg["adjudicacion_posterior"]["validada"])
            self.assertEqual(apl["casos_adjudicados"],
                             [{"id": "L-X", "adjudicacion": "REF-SIN-1", "paginas": [7]}])
            self.assertEqual(apl["evidencias_validas"], 1)
            self.assertEqual(apl["evidencias_rechazadas"], [])
            self.assertTrue(lib._acierto(reg))  # gold completo O adjudicacion validada
            resumen_adj, codigo_adj = lib._resumen(
                [reg], {"esperado": {}, "casos": [caso]}, adjudicacion_activa=True)
            self.assertEqual(codigo_adj, 0)
            self.assertEqual(resumen_adj["aciertos"], ["L-X"])
            self.assertEqual(resumen_adj["aciertos_gold_exacto"], [])
            self.assertEqual([a["id"] for a in resumen_adj["aciertos_adjudicados"]], ["L-X"])
            self.assertEqual(resumen_adj["cobertura_contexto"], 0)  # gold exacto intacto
            self.assertEqual(resumen_adj["cobertura_alternativa"], 1)
        # La MISMA página (7) de OTRO documento de la MISMA CCAA (D2, Andalucía)
        # aparece ANTES que la página correcta de D1; ambas íntegras y con
        # metadata válida. La alternativa correcta (D1 p7) debe admitirse
        # (fila localizada por pagina+doc+version) y los faltantes originales
        # del gold (p26, nunca devuelta) se mantienen.
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {7: "Texto alternativo verificado en la misma edicion."}},
                "D2": {"version": "2026-02-02", "jurisdiccion": "Andalucía",
                       "paginas": {7: "Texto de OTRO documento andaluz con la misma pagina."}}})
            caso = _caso()
            p7_d2 = _pagina("D2", "2026-02-02", 7, textos[("D2", 7)], motivo="auxiliar")
            p7_d1 = _pagina("D1", "2026-01-01", 7, textos[("D1", 7)], motivo="auxiliar")
            res = _res([p7_d2, p7_d1], textos)  # la p7 ajena aparece PRIMERO
            reg = lib._registro_caso(caso, res, td)
            self.assertEqual(reg["cobertura"]["faltantes"], [26])
            self.assertEqual(reg["cobertura"]["contexto"], [])  # no se finge gold
            self.assertTrue(reg["integridad_ok"])  # ambas páginas íntegras
            self.assertEqual(reg["ambito"]["estado"], "compatible")  # misma CCAA
            alt = {"esquema": lib.ESQUEMA_ALTERNATIVAS,
                   "revision": {"fecha": "2026-11-16", "motivo": "revision sintetica posterior",
                                "posterior_a_resultados": True},
                   "fixture_sha256": "f" * 64,
                   "casos": [{"id": "L-X", "consulta": caso["consulta"],
                              "documento": "D1", "version": "2026-01-01",
                              "adjudicacion": "REF-SIN-2",
                              "paginas": [{"pagina": p7_d1["pagina"],
                                           "archivo": p7_d1["archivo"],
                                           "texto_sha256": p7_d1["texto_sha256"]}]}],
                   "casos_rechazados": []}
            apl, regs = lib._aplicar_alternativas([reg], {"casos": [caso]}, alt)
            self.assertIs(regs[0], reg)
            self.assertEqual(reg["cobertura"]["faltantes"], [26])  # gold intacto
            self.assertEqual(reg["evidencias_alternativas_validas"],
                             [{"pagina": 7, "archivo": p7_d1["archivo"],
                               "texto_sha256": p7_d1["texto_sha256"],
                               "adjudicacion": "REF-SIN-2"}])
            self.assertTrue(reg["adjudicacion_posterior"]["validada"])
            self.assertEqual(apl["evidencias_validas"], 1)
            self.assertEqual(apl["evidencias_rechazadas"], [])
            self.assertEqual(apl["casos_adjudicados"],
                             [{"id": "L-X", "adjudicacion": "REF-SIN-2", "paginas": [7]}])
            self.assertTrue(lib._acierto(reg))
            resumen_adj, codigo_adj = lib._resumen(
                [reg], {"esperado": {}, "casos": [caso]}, adjudicacion_activa=True)
            self.assertEqual(codigo_adj, 0)
            self.assertEqual(resumen_adj["aciertos_gold_exacto"], [])
            self.assertEqual([a["id"] for a in resumen_adj["aciertos_adjudicados"]], ["L-X"])
            self.assertEqual(resumen_adj["cobertura_alternativa"], 1)

    def test_alternativa_incoherente_no_acredita(self):
        """Variantes que NO acreditan: doc distinto del esperado (caso rechazado),
        sha incorrecto, archivo incorrecto y texto ausente del contexto real;
        contrato de entrada: hash distinto, posterior_a_resultados != true o
        esquema incorrecto -> ValueError; consulta distinta -> rechazo visible."""
        # doc distinto del esperado: el helper rechaza el caso entero
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {7: "Texto alternativo de D1 en la misma edicion."}},
                "D2": {"version": "2026-02-02", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto de OTRO documento devuelto por error."}}})
            caso = _caso()
            res = _res([_pagina("D1", "2026-01-01", 7, textos[("D1", 7)], motivo="auxiliar"),
                        _pagina("D2", "2026-02-02", 26, textos[("D2", 26)])], textos)
            reg = lib._registro_caso(caso, res, td)
            p7 = _pagina("D1", "2026-01-01", 7, textos[("D1", 7)])
            alt_doc_malo = {"esquema": lib.ESQUEMA_ALTERNATIVAS,
                            "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": True},
                            "fixture_sha256": "f" * 64,
                            "casos": [{"id": "L-X", "consulta": caso["consulta"],
                                       "documento": "D2", "version": "2026-02-02",
                                       "adjudicacion": "REF-MAL",
                                       "paginas": [{"pagina": p7["pagina"], "archivo": p7["archivo"],
                                                    "texto_sha256": p7["texto_sha256"]}]}],
                            "casos_rechazados": []}
            apl, _ = lib._aplicar_alternativas([reg], {"casos": [caso]}, alt_doc_malo)
            self.assertEqual(apl["casos_adjudicados"], [])
            self.assertEqual(apl["casos_no_adjudicados"][0]["motivo"], "doc_distinto_del_esperado")
            self.assertNotIn("adjudicacion_posterior", reg)
            self.assertFalse(lib._acierto(reg))
        # sha incorrecto y archivo incorrecto: evidencia rechazada, no acredita
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {7: "Texto alternativo verificado en la misma edicion."}}})
            caso = _caso()
            p7 = _pagina("D1", "2026-01-01", 7, textos[("D1", 7)], motivo="auxiliar")
            reg = lib._registro_caso(caso, _res([p7], textos), td)
            base = {"id": "L-X", "consulta": caso["consulta"], "documento": "D1",
                    "version": "2026-01-01", "adjudicacion": "REF-X"}
            alt_sha = {"esquema": lib.ESQUEMA_ALTERNATIVAS,
                       "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": True},
                       "fixture_sha256": "f" * 64,
                       "casos": [dict(base, paginas=[{"pagina": 7, "archivo": p7["archivo"],
                                                      "texto_sha256": "0" * 64}])],
                       "casos_rechazados": []}
            apl, _ = lib._aplicar_alternativas([reg], {"casos": [caso]}, alt_sha)
            self.assertEqual(apl["evidencias_validas"], 0)
            self.assertEqual(apl["evidencias_rechazadas"][0]["motivo"], "sha_distinto")
            self.assertFalse(reg["adjudicacion_posterior"]["validada"])
            self.assertFalse(lib._acierto(reg))
            resumen_adj, codigo_adj = lib._resumen(
                [reg], {"esperado": {}, "casos": [caso]}, adjudicacion_activa=True)
            self.assertEqual(codigo_adj, 1)
            alt_arch = {"esquema": lib.ESQUEMA_ALTERNATIVAS,
                        "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": True},
                        "fixture_sha256": "f" * 64,
                        "casos": [dict(base, paginas=[{"pagina": 7,
                                                       "archivo": "docs/D1/2026-01-01__test/pagina/p9999.md",
                                                       "texto_sha256": p7["texto_sha256"]}])],
                        "casos_rechazados": []}
            apl2, _ = lib._aplicar_alternativas([reg], {"casos": [caso]}, alt_arch)
            self.assertEqual(apl2["evidencias_rechazadas"][0]["motivo"], "archivo_distinto")
            self.assertFalse(lib._acierto(reg))
        # texto ausente del contexto real: la página devuelta con sha correcto
        # pero sin su texto en texto_contexto no acredita
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            textos = _fabricar_contenido(td, {
                "D1": {"version": "2026-01-01", "jurisdiccion": "Andalucía",
                       "paginas": {26: "Texto del gold andaluz esperado.",
                                   7: "Texto alternativo que NO entra en el contexto."}}})
            caso = _caso()
            res = _res([_pagina("D1", "2026-01-01", 26, textos[("D1", 26)])], textos)
            p7 = _pagina("D1", "2026-01-01", 7, textos[("D1", 7)], motivo="auxiliar")
            res["paginas"].append(p7)  # devuelta pero su texto NO está en ctx
            reg = lib._registro_caso(caso, res, td)
            alt_txt = {"esquema": lib.ESQUEMA_ALTERNATIVAS,
                       "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": True},
                       "fixture_sha256": "f" * 64,
                       "casos": [{"id": "L-X", "consulta": caso["consulta"], "documento": "D1",
                                  "version": "2026-01-01", "adjudicacion": "REF-T",
                                  "paginas": [{"pagina": 7, "archivo": p7["archivo"],
                                               "texto_sha256": p7["texto_sha256"]}]}],
                       "casos_rechazados": []}
            apl, _ = lib._aplicar_alternativas([reg], {"casos": [caso]}, alt_txt)
            self.assertEqual(apl["evidencias_rechazadas"][0]["motivo"], "texto_ausente_en_contexto")
            self.assertFalse(reg["adjudicacion_posterior"]["validada"])
            self.assertFalse(lib._acierto(reg))
            resumen_adj, codigo_adj = lib._resumen(
                [reg], {"esperado": {}, "casos": [caso]}, adjudicacion_activa=True)
            self.assertEqual(codigo_adj, 1)
        # contrato de entrada: hash, posterior_a_resultados, esquema y consulta
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)
            caso = _caso()
            datos = {"casos": [dict(caso)]}
            entrada = {"id": "L-X", "consulta": caso["consulta"], "documento": "D1",
                       "version": "2026-01-01", "adjudicacion": "REF-OK",
                       "paginas": [{"pagina": 7, "archivo": "docs/D1/2026-01-01__test/pagina/p0007.md",
                                    "texto_sha256": "a" * 64}]}
            alt_path = td / "alt.json"
            alt_path.write_text(json.dumps({
                "esquema": "alternativas-evidencia/1",
                "revision": {"fecha": "2026-11-16", "motivo": "revision", "posterior_a_resultados": True},
                "fixture_sha256": "f" * 64, "casos": [entrada]}), encoding="utf-8")
            with self.assertRaises(ValueError):  # hash de fixture distinto
                lib._cargar_alternativas(alt_path, "0" * 64, datos)
            ok = lib._cargar_alternativas(alt_path, "f" * 64, datos)
            self.assertEqual(len(ok["casos"]), 1)
            self.assertEqual(ok["casos"][0]["id"], "L-X")
            alt_path.write_text(json.dumps({
                "esquema": "alternativas-evidencia/1",
                "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": False},
                "fixture_sha256": "f" * 64, "casos": [entrada]}), encoding="utf-8")
            with self.assertRaises(ValueError):  # no declara adjudicacion posterior
                lib._cargar_alternativas(alt_path, "f" * 64, datos)
            alt_path.write_text(json.dumps({
                "esquema": "otro-esquema/9",
                "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": True},
                "fixture_sha256": "f" * 64, "casos": [entrada]}), encoding="utf-8")
            with self.assertRaises(ValueError):  # esquema incorrecto
                lib._cargar_alternativas(alt_path, "f" * 64, datos)
            alt_path.write_text(json.dumps({
                "esquema": "alternativas-evidencia/1",
                "revision": {"fecha": "2026-11-16", "motivo": "m", "posterior_a_resultados": True},
                "fixture_sha256": "f" * 64,
                "casos": [dict(entrada, consulta="OTRA CONSULTA DISTINTA")]}), encoding="utf-8")
            rechazada = lib._cargar_alternativas(alt_path, "f" * 64, datos)
            self.assertEqual(rechazada["casos"], [])
            self.assertEqual(rechazada["casos_rechazados"][0]["motivo"], "consulta_distinta")


if __name__ == "__main__":
    unittest.main()
