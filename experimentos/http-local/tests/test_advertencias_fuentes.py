#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unittest de advertencias de fuentes (doc.json) en AdaptadorContexto.

Encargo acotado: contrato "advertencias list[str] + nota_capa str de cada
documento que BM25 selecciona, deduplicadas por documento en texto_contexto y
recuperacion.advertencias, contando el presupuesto final".

Corpus SINTÉTICO temporal en formato mínimo (sin normativa real, sin red, sin
API, sin llamadas a modelos): indice/apartados.jsonl, <doc>/doc.json,
<doc>/estructura.json, <doc>/paginas.json, <doc>/pagina/p0001.md y
<doc>/apartado/p0001.md. Los textos son marcadores sintéticos sin relación con
normativa real ni respuestas de evaluación.

Rúbrica por caso (criterio -> aserción clave):
 1) dos resultados del mismo documento: el aviso aparece UNA vez por documento
    en recuperacion.advertencias y UNA vez en texto_contexto (marcador
    exclusivo del aviso; la página se entrega literal y aparte); nota_capa
    igual a un aviso previo no se duplica.
 2) dos documentos con el mismo aviso: cada entrada lleva el ID del documento;
    metadatos de resultados y páginas intactos; ningún aviso del tercer
    documento no seleccionado por BM25.
 3) el aviso cuenta en el presupuesto final: frontera exacta sobre
    tokens_contexto en modo determinista (encs={} -> aproximacion_caracteres_4,
    misma fórmula ceil(len/4) de _salida): presupuesto exacto -> ok; uno menos
    -> presupuesto_excedido con texto sin recortes.
 4) edición solicitada ausente -> version_no_disponible: sin páginas, sin
    resultados, sin sustitución de contenido y sin exponer los avisos del doc,
    aunque doc.json tenga advertencias; el buscador no llega a llamarse.
 5) tipos inesperados en advertencias/nota_capa (dict, int, None, "", list):
    sin excepción y sin serializar dicts en texto_contexto ni recuperacion.
 6) doc.json con distribute=False sigue excluido (carga REAL de fixtures):
    no entra en docs/filas, su aviso no aparece y --documento devuelve
    documento_no_disponible con "Documentos disponibles: doc-ok".

Límites de la muestra: buscar_bm25, construir_lectura y crear_contadores están
parcheados (resultados/página sintéticos; contadores {} y modo
aproximacion_caracteres_4). NO están parcheados cargar_indice, cargar_docs ni
el filtrado distribute de AdaptadorContexto, que cargan los fixtures reales
del temporal. El recuento chars/4 es un proxy local de texto, no tokens de
API; no mide consumo de proveedores. Cobertura pendiente (fuera del encargo):
BM25 real, construir_lectura real y tiktoken.

Aislamiento: acceso.py y adaptador_contexto.py se cargan con importlib bajo
nombres privados y sys.modules["acceso"] se restaura al valor previo, para no
compartir estado global con test_seguridad_http (que instala un stub en
sys.modules["acceso"]), tanto si esa suite corre antes como después.
"""
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent  # experimentos/http-local


def _cargar_modulo_privado(nombre, ruta):
    """Carga un módulo por ruta con importlib sin dejar rastro en sys.modules."""
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.modules.pop(nombre, None)
    return modulo


# Instancia privada de acceso.py: distinta de cualquier 'acceso' global o stub;
# sobre ella se aplican los parches por prueba.
_ACC = _cargar_modulo_privado("_acc_priv_test_advertencias", RAIZ / "acceso.py")


def _cargar_adaptador_aislado():
    """Carga adaptador_contexto.py resolviendo `import acceso` a la instancia privada."""
    anterior = sys.modules.get("acceso")
    sys.modules["acceso"] = _ACC
    try:
        return _cargar_modulo_privado(
            "_adaptador_priv_test_advertencias", RAIZ / "adaptador_contexto.py")
    finally:
        if anterior is None:
            sys.modules.pop("acceso", None)
        else:
            sys.modules["acceso"] = anterior


_MOD = _cargar_adaptador_aislado()


def _escribir(ruta, texto):
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)


class PruebasAdvertenciasFuentes(unittest.TestCase):
    """Carga real de fixtures (indice/doc.json/distribute) con buscador,
    lectura y contadores parcheados; un corpus temporal independiente por prueba."""

    # ------------------------------------------------------------- corpus

    def _corpus_sintetico(self, docs):
        """Escribe un corpus temporal mínimo y devuelve {raiz, docs}.

        Cada especificación: id, distribute, version, sha256, url, title,
        advertencias, nota_capa (según el caso), paginas_texto ({n: texto})
        y apartados ([{apartado_id, id_tecnico, ruta_oficial, titulo,
        archivo, paginas, texto}]).
        """
        tmp = tempfile.mkdtemp(prefix="adv-fuentes-")
        self.addCleanup(shutil.rmtree, tmp, True)
        raiz = Path(tmp).resolve()
        (raiz / "indice").mkdir(parents=True)
        lineas = []
        salida = {"raiz": raiz, "docs": {}}
        for d in docs:
            doc_id = d["id"]
            base = raiz / doc_id
            (base / "pagina").mkdir(parents=True)
            (base / "apartado").mkdir(parents=True)
            docj = {k: d[k] for k in ("id", "distribute", "version", "sha256",
                                      "url", "title", "advertencias", "nota_capa")
                    if k in d}
            docj.setdefault("code", "DB-SINTETICO")
            docj.setdefault("layer", "oficial")
            _escribir(base / "doc.json",
                      json.dumps(docj, ensure_ascii=False, indent=1) + "\n")
            _escribir(base / "estructura.json",
                      json.dumps({"nodos": []}, ensure_ascii=False) + "\n")
            pags_meta = [{"pagina": p, "archivo": "pagina/p%04d.md" % p}
                         for p in sorted(d.get("paginas_texto") or {})]
            _escribir(base / "paginas.json",
                      json.dumps({"paginas": pags_meta}, ensure_ascii=False) + "\n")
            for p, texto_pg in (d.get("paginas_texto") or {}).items():
                _escribir(base / "pagina" / ("p%04d.md" % p), texto_pg)
            apartados = {}
            for a in d["apartados"]:
                _escribir(base / "apartado" / a["archivo"], a["texto"])
                apartados[a["apartado_id"]] = dict(a, texto_literal=a["texto"])
                lineas.append(json.dumps({
                    "id_tecnico": a["id_tecnico"],
                    "documento": doc_id,
                    "doc_json": "%s/doc.json" % doc_id,
                    "apartado_id": a["apartado_id"],
                    "archivo": "%s/apartado/%s" % (doc_id, a["archivo"]),
                    "capa": "oficial",
                    "version": docj.get("version"),
                    "titulo": a["titulo"],
                    "paginas": list(a.get("paginas") or []),
                }, ensure_ascii=False))
            salida["docs"][doc_id] = {"doc_json": docj, "apartados": apartados}
        _escribir(raiz / "indice" / "apartados.jsonl", "\n".join(lineas) + "\n")
        return salida

    def _resultado(self, corpus, doc_id, apartado_id):
        """Resultado sintético coherente con las fixtures del corpus."""
        doc = corpus["docs"][doc_id]
        ap = doc["apartados"][apartado_id]
        docj = doc["doc_json"]
        return {
            "documento": doc_id,
            "version": docj.get("version"),
            "capa": "oficial",
            "apartado_id": apartado_id,
            "id_tecnico": ap["id_tecnico"],
            "ruta_oficial": ap.get("ruta_oficial"),
            "titulo": ap.get("titulo"),
            "codigo": docj.get("code"),
            "archivo": "%s/apartado/%s" % (doc_id, ap["archivo"]),
            "paginas": list(ap.get("paginas") or [1]),
            "pagina": None,
            "tablas": [],
            "referencias": [],
            "etiquetas_impresas": None,
            "puntuacion_bm25": 1.234,
            "hallada": True,
            "cita": {"texto": ap["texto_literal"]},
            "texto_integro": ap["texto_literal"],
            "contexto": {},
        }

    def _montar(self, docs, selecciones):
        """Corpus temporal + AdaptadorContexto parcheado.

        Devuelve (corpus, adaptador, captura); captura registra los argumentos
        de cada llamada al buscador parcheado (filas/docs ya filtradas por la
        carga real de fixtures y el filtro distribute).
        """
        corpus = self._corpus_sintetico(docs)
        resultados = [self._resultado(corpus, d, a) for d, a in selecciones]
        captura = []

        def fake_buscar(contenido, filas, documentos, consulta, terminos, op, encs):
            captura.append({"filas": list(filas), "docs": dict(documentos),
                            "contenido": str(contenido)})
            return {"resultados": [dict(r) for r in resultados],
                    "omitidos": [], "advertencias": [],
                    "terminos": list(terminos), "ambito_capa": "oficial+asociada"}

        def fake_lectura(contenido, filas, documentos, opt, encs):
            pag = getattr(opt, "pagina", None)
            if pag:
                p = int(pag)
                ruta = Path(contenido) / opt.documento / "pagina" / ("p%04d.md" % p)
                texto_pg = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
                return {"pagina": {"pagina": p, "texto": texto_pg,
                                   "etiqueta_impresa": None,
                                   "archivo": "%s/pagina/p%04d.md" % (opt.documento, p)},
                        "contexto": {}}
            return {"pagina": {}, "contexto": {}}

        for nombre, reemplazo in (
                ("crear_contadores",
                 lambda: ({}, "aproximacion_caracteres_4")),
                ("buscar_bm25", fake_buscar),
                ("construir_lectura", fake_lectura)):
            parche = mock.patch.object(_ACC, nombre, reemplazo)
            parche.start()
            self.addCleanup(parche.stop)
        ad = _MOD.AdaptadorContexto(str(corpus["raiz"]))
        return corpus, ad, captura

    # ------------------------------------------------------------- casos

    def test_aviso_una_vez_por_documento_y_nota_capa_deduplicada(self):
        """Caso 1: dos resultados del mismo doc; aviso una vez en recuperacion
        y texto; nota_capa repetida con el aviso no se duplica."""
        aviso = "AVISO-EXCLUSIVO-UNO: advertencia sintetica de la fuente."
        pagina = "Texto literal de pagina sintetica UNO."
        docs = [{
            "id": "doc-uno", "distribute": True, "version": "2020-10-01",
            "sha256": "SHA-UNO", "url": "https://oficial.ejemplo/uno",
            "title": "Doc uno sintetico",
            "advertencias": [aviso],
            "nota_capa": aviso,  # repetida con el aviso: debe deduplicarse
            "paginas_texto": {1: pagina},
            "apartados": [
                {"apartado_id": "1.1", "id_tecnico": "doc-uno-1.1",
                 "ruta_oficial": "DB 1.1", "titulo": "Apartado 1.1",
                 "archivo": "p0001.md", "paginas": [1],
                 "texto": "Texto literal del apartado 1.1."},
                {"apartado_id": "1.2", "id_tecnico": "doc-uno-1.2",
                 "ruta_oficial": "DB 1.2", "titulo": "Apartado 1.2",
                 "archivo": "p0002.md", "paginas": [1],
                 "texto": "Texto literal del apartado 1.2."},
            ],
        }]
        corpus, ad, _ = self._montar(docs, [("doc-uno", "1.1"), ("doc-uno", "1.2")])
        res = ad.preparar("consulta sintetica uno")
        self.assertEqual(res["estado"], "ok")
        rec = res["recuperacion"]
        self.assertEqual([r["id_tecnico"] for r in rec["resultados"]],
                         ["doc-uno-1.1", "doc-uno-1.2"])
        self.assertEqual(rec["advertencias"], ["documento doc-uno: %s" % aviso])
        texto = res["texto_contexto"]
        self.assertEqual(texto.count("AVISO-EXCLUSIVO-UNO"), 1)
        # la página se entrega literal y aparte; el marcador del aviso es exclusivo
        self.assertIn(pagina, texto)
        self.assertEqual(len(res["paginas"]), 1)
        pg = res["paginas"][0]
        self.assertEqual(pg["doc"], "doc-uno")
        self.assertEqual(pg["pagina"], 1)
        self.assertEqual(pg["sha256"], "SHA-UNO")
        self.assertEqual(pg["url_fuente"], "https://oficial.ejemplo/uno")
        self.assertEqual(pg["texto_sha256"],
                         hashlib.sha256(pagina.encode("utf-8")).hexdigest())

    def test_mismo_aviso_dos_documentos_con_id_y_tercero_excluido(self):
        """Caso 2: dos documentos con el mismo aviso, identificados con ID y sin
        perder metadatos; el tercer documento no seleccionado no aporta avisos."""
        compartido = "AVISO-COMPARTIDO: advertencia sintetica identica en dos fuentes."
        pagina_a = "Texto literal de pagina sintetica A."
        pagina_b = "Texto literal de pagina sintetica B."

        def doc_base(doc_id, sha, titulo, apartados):
            return {"id": doc_id, "distribute": True, "version": "2020-10-01",
                    "sha256": sha, "url": "https://oficial.ejemplo/%s" % doc_id,
                    "title": titulo, "apartados": apartados}

        docs = [
            dict(doc_base("doc-a", "SHA-A", "Doc A sintetico",
                          [{"apartado_id": "1.1", "id_tecnico": "doc-a-1.1",
                            "ruta_oficial": "DB A 1.1", "titulo": "Apartado A 1.1",
                            "archivo": "p0001.md", "paginas": [1],
                            "texto": "Texto literal del apartado A 1.1."}]),
                 advertencias=[compartido], paginas_texto={1: pagina_a}),
            dict(doc_base("doc-b", "SHA-B", "Doc B sintetico",
                          [{"apartado_id": "1.1", "id_tecnico": "doc-b-1.1",
                            "ruta_oficial": "DB B 1.1", "titulo": "Apartado B 1.1",
                            "archivo": "p0001.md", "paginas": [1],
                            "texto": "Texto literal del apartado B 1.1."}]),
                 advertencias=[compartido], paginas_texto={1: pagina_b}),
            dict(doc_base("doc-c", "SHA-C", "Doc C sintetico",
                          [{"apartado_id": "1.1", "id_tecnico": "doc-c-1.1",
                            "ruta_oficial": "DB C 1.1", "titulo": "Apartado C 1.1",
                            "archivo": "p0001.md", "paginas": [1],
                            "texto": "Texto literal del apartado C 1.1."}]),
                 advertencias=["AVISO-TERCERO-NO-SELECCIONADO"],
                 paginas_texto={1: "Texto literal de pagina sintetica C."}),
        ]
        corpus, ad, _ = self._montar(docs, [("doc-a", "1.1"), ("doc-b", "1.1")])
        res = ad.preparar("consulta sintetica dos")
        self.assertEqual(res["estado"], "ok")
        rec = res["recuperacion"]
        self.assertEqual(rec["advertencias"],
                         ["documento doc-a: %s" % compartido,
                          "documento doc-b: %s" % compartido])
        texto = res["texto_contexto"]
        self.assertEqual(texto.count("AVISO-COMPARTIDO"), 2)
        self.assertIn(pagina_a, texto)
        self.assertIn(pagina_b, texto)
        # el tercer documento no fue seleccionado por BM25: nada suyo
        self.assertNotIn("AVISO-TERCERO-NO-SELECCIONADO", texto)
        self.assertNotIn("doc-c", texto)
        volcado = json.dumps(rec, ensure_ascii=False)
        self.assertNotIn("AVISO-TERCERO-NO-SELECCIONADO", volcado)
        self.assertNotIn("doc-c", volcado)
        # metadatos de ambos documentos intactos (de fixtures reales y sintéticos)
        self.assertEqual({r["documento"] for r in rec["resultados"]},
                         {"doc-a", "doc-b"})
        por_doc = {r["documento"]: r for r in rec["resultados"]}
        self.assertEqual(por_doc["doc-a"]["id_tecnico"], "doc-a-1.1")
        self.assertEqual(por_doc["doc-b"]["id_tecnico"], "doc-b-1.1")
        self.assertEqual([p["doc"] for p in res["paginas"]], ["doc-a", "doc-b"])
        self.assertEqual(res["paginas"][0]["sha256"], "SHA-A")
        self.assertEqual(res["paginas"][1]["sha256"], "SHA-B")

    def test_aviso_cuenta_en_presupuesto_frontera_exacta(self):
        """Caso 3: el aviso cuenta en el presupuesto final del texto de respuesta;
        frontera con presupuesto exacto (ok) y uno menos (presupuesto_excedido,
        texto sin recortes), con recuento determinista."""
        aviso = ("AVISO-PRESUPUESTO: advertencia sintetica que debe contar en el "
                 "presupuesto final del texto de respuesta.")
        pagina = "Texto literal de pagina sintetica PRES."
        docs = [{"id": "doc-pres", "distribute": True, "version": "2020-10-01",
                 "sha256": "SHA-PRES", "url": "https://oficial.ejemplo/pres",
                 "title": "Doc presupuesto sintetico", "advertencias": [aviso],
                 "paginas_texto": {1: pagina},
                 "apartados": [{"apartado_id": "1.1", "id_tecnico": "doc-pres-1.1",
                                "ruta_oficial": "DB PRES 1.1", "titulo": "Apartado 1.1",
                                "archivo": "p0001.md", "paginas": [1],
                                "texto": "Texto literal del apartado de frontera."}]}]
        corpus, ad, _ = self._montar(docs, [("doc-pres", "1.1")])
        holgado = ad.preparar("consulta frontera", presupuesto_tokens=10 ** 6)
        self.assertEqual(holgado["estado"], "ok")
        # recuento determinista (proxy chars/4, encs={}); misma fórmula de _salida
        self.assertEqual(holgado["modo_tokens"], "aproximacion_caracteres_4")
        texto = holgado["texto_contexto"]
        self.assertIn(aviso, texto)   # el aviso está dentro del texto contado
        self.assertIn(pagina, texto)
        limite = max(1, math.ceil(len(texto) / 4.0))
        self.assertEqual(holgado["tokens_contexto"], limite)
        exacto = ad.preparar("consulta frontera", presupuesto_tokens=limite)
        menos = ad.preparar("consulta frontera", presupuesto_tokens=limite - 1)
        self.assertEqual(exacto["estado"], "ok")
        self.assertFalse(exacto["excedido"])
        self.assertEqual(exacto["tokens_contexto"], limite)
        self.assertEqual(exacto["texto_contexto"], texto)
        self.assertEqual(menos["estado"], "presupuesto_excedido")
        self.assertTrue(menos["excedido"])
        self.assertEqual(menos["tokens_contexto"], limite)
        self.assertEqual(menos["limite_tokens"], limite - 1)
        # sin recortes: el mismo texto, con aviso y página literal
        self.assertEqual(menos["texto_contexto"], texto)
        self.assertIn(aviso, menos["texto_contexto"])
        self.assertIn(pagina, menos["texto_contexto"])

    def test_version_ausente_sin_paginas_ni_sustitucion(self):
        """Caso 4: edición solicitada ausente -> version_no_disponible; sin
        páginas, resultados ni sustitución, aunque doc.json tenga avisos."""
        aviso = "AVISO-VERSION-AUSENTE: advertencia que no debe exponerse sin edicion valida."
        pagina = "Texto literal de pagina sintetica X."
        docs = [{"id": "doc-x", "distribute": True, "version": "2020-10-01",
                 "sha256": "SHA-X", "url": "https://oficial.ejemplo/x",
                 "title": "Doc X sintetico", "advertencias": [aviso],
                 "paginas_texto": {1: pagina},
                 "apartados": [{"apartado_id": "1.1", "id_tecnico": "doc-x-1.1",
                                "ruta_oficial": "DB X 1.1", "titulo": "Apartado X 1.1",
                                "archivo": "p0001.md", "paginas": [1],
                                "texto": "Texto literal del apartado X 1.1."}]}]
        corpus, ad, captura = self._montar(docs, [("doc-x", "1.1")])
        res = ad.preparar("consulta version", documento="doc-x",
                          version="1999-01-01")
        self.assertEqual(res["estado"], "version_no_disponible")
        self.assertEqual(res["documento"], "doc-x")
        self.assertEqual(res["version"], "1999-01-01")
        self.assertEqual(res["versiones_disponibles"], ["2020-10-01"])
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])
        self.assertEqual(res["recuperacion"]["advertencias"],
                         ["versión no disponible: 1999-01-01"])
        texto = res["texto_contexto"]
        self.assertIn("ESTADO version_no_disponible", texto)
        self.assertIn("Versiones disponibles: 2020-10-01", texto)
        # aunque doc.json tiene avisos: ni avisos ni contenido sustituido
        self.assertNotIn("AVISO-VERSION-AUSENTE", texto)
        self.assertNotIn(pagina, texto)
        self.assertNotIn("AVISO-VERSION-AUSENTE",
                         json.dumps(res["recuperacion"], ensure_ascii=False))
        self.assertEqual(captura, [])  # el buscador no llega a llamarse

    def test_tipos_inesperados_sin_excepcion_ni_dicts(self):
        """Caso 5: tipos inesperados en advertencias/nota_capa no lanzan
        excepción ni serializan dicts en texto ni recuperacion."""
        docs = [{"id": "doc-tipos", "distribute": True, "version": "2020-10-01",
                 "sha256": "SHA-TIPOS", "url": "https://oficial.ejemplo/tipos",
                 "title": "Doc tipos sintetico",
                 "advertencias": ["AVISO-VALIDO-TIPOS", {"no_serializar_dict": True},
                                  42, None, "", ["lista"]],
                 "nota_capa": {"nota": "no serializar"},
                 "paginas_texto": {1: "Texto literal de pagina sintetica TIPOS."},
                 "apartados": [{"apartado_id": "1.1", "id_tecnico": "doc-tipos-1.1",
                                "ruta_oficial": "DB TIPOS 1.1",
                                "titulo": "Apartado TIPOS", "archivo": "p0001.md",
                                "paginas": [1],
                                "texto": "Texto literal del apartado TIPOS."}]}]
        corpus, ad, _ = self._montar(docs, [("doc-tipos", "1.1")])
        res = ad.preparar("consulta tipos")  # no debe lanzar excepción
        self.assertEqual(res["estado"], "ok")
        rec = res["recuperacion"]
        self.assertEqual(rec["advertencias"],
                         ["documento doc-tipos: AVISO-VALIDO-TIPOS"])
        texto = res["texto_contexto"]
        self.assertEqual(texto.count("AVISO-VALIDO-TIPOS"), 1)
        # ni dicts serializados (JSON) ni repr de dicts en el texto
        self.assertNotIn("{", texto)
        self.assertNotIn("no_serializar_dict", texto)
        self.assertNotIn("no_serializar_dict", json.dumps(rec, ensure_ascii=False))

    def test_distribute_false_excluido(self):
        """Caso 6: doc.json con distribute=False sigue excluido de la carga real;
        su aviso no aparece y --documento devuelve documento_no_disponible."""
        docs = [
            {"id": "doc-ok", "distribute": True, "version": "2020-10-01",
             "sha256": "SHA-OK", "url": "https://oficial.ejemplo/ok",
             "title": "Doc ok sintetico", "advertencias": ["AVISO-OK-EXCLUSIVO"],
             "paginas_texto": {1: "Texto literal de pagina sintetica OK."},
             "apartados": [{"apartado_id": "1.1", "id_tecnico": "doc-ok-1.1",
                            "ruta_oficial": "DB OK 1.1", "titulo": "Apartado OK 1.1",
                            "archivo": "p0001.md", "paginas": [1],
                            "texto": "Texto literal del apartado OK 1.1."}]},
            {"id": "doc-oculto", "distribute": False, "version": "2020-10-01",
             "sha256": "SHA-OCULTO", "url": "https://oficial.ejemplo/oculto",
             "title": "Doc oculto sintetico",
             "advertencias": ["AVISO-OCULTO-EXCLUIDO"],
             "paginas_texto": {1: "Texto literal de pagina sintetica OCULTA."},
             "apartados": [{"apartado_id": "1.1", "id_tecnico": "doc-oculto-1.1",
                            "ruta_oficial": "DB OCULTO 1.1", "titulo": "Apartado oculto",
                            "archivo": "p0001.md", "paginas": [1],
                            "texto": "Texto literal del apartado oculto."}]},
        ]
        corpus, ad, captura = self._montar(docs, [("doc-ok", "1.1")])
        # filtrado distribute REAL en la carga (no parcheado)
        self.assertEqual(set(ad.docs), {"doc-ok"})
        self.assertEqual([f["documento"] for f in ad.filas], ["doc-ok"])
        res = ad.preparar("consulta exclusion")
        self.assertEqual(res["estado"], "ok")
        texto = res["texto_contexto"]
        self.assertEqual(texto.count("AVISO-OK-EXCLUSIVO"), 1)
        self.assertNotIn("AVISO-OCULTO-EXCLUIDO", texto)
        self.assertNotIn("doc-oculto", texto)
        # y por filtro directo sigue inaccesible
        res2 = ad.preparar("consulta exclusion", documento="doc-oculto")
        self.assertEqual(res2["estado"], "documento_no_disponible")
        self.assertEqual(res2["recuperacion"]["resultados"], [])
        self.assertEqual(res2["paginas"], [])
        self.assertIn("Documentos disponibles: doc-ok", res2["texto_contexto"])
        self.assertNotIn("AVISO-OCULTO-EXCLUIDO", res2["texto_contexto"])
        # el buscador parcheado solo recibió el corpus distribuible
        self.assertEqual(len(captura), 1)
        self.assertEqual([f["documento"] for f in captura[0]["filas"]], ["doc-ok"])
        self.assertEqual(set(captura[0]["docs"]), {"doc-ok"})


if __name__ == "__main__":
    unittest.main()
