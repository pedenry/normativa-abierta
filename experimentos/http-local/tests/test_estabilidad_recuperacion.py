#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_estabilidad_recuperacion.py — contratos de filtrado y estabilidad de
respuesta del buscador REAL.

Encargo acotado (solo pruebas; sin modificar acceso.py, adaptador_contexto.py ni
el corpus): ejercita buscar_bm25 REAL y AdaptadorContexto REAL (sin parchear
BM25, ranking, carga de fixtures ni construir_lectura) sobre corpus sintéticos
mínimos y temporales, aislados por prueba. Sin red, sin API, sin corpus real y
sin respuestas fijas: no se hardcodea ningún documento real (p. ej. REBT103)
como respuesta; los resultados se obtienen ejecutando el buscador y los textos
son marcadores sintéticos sin relación con normativa.

Rúbrica por caso (criterio -> aserción clave):
 1) FILTRADO por documento (el IDF es GLOBAL sobre todas las filas
    indexadas): al añadir 80 documentos excluidos por el filtro (40 capa
    «guias» + 40 con materia ajena) que contienen el término, ningún excluido
    aparece en resultados; los seleccionados son del documento acotado y
    legibles (texto íntegro con el término); repetir la MISMA consulta sobre
    el MISMO corpus reproduce la respuesta (ranking y puntuaciones). Entre
    colecciones distintas la puntuación PUEDE variar: el IDF global es diseño
    declarado; no se exige invariancia estadística entre colecciones.
 2) FILTRADO por alias/código: igual que 1 acotando por el código del doc;
    además el prefijo del código NO casará (pertenencia exacta, sin
    subcadenas).
 3) FILTRADO por materia: al añadir 40 documentos con el término y materia
    excluida por el filtro: sin fuga, contenido legible y misma respuesta en
    repetición del mismo corpus.
 4) FILTRADO por capa: por defecto solo sale el doc oficial aunque se añadan
    40 guías con ambos términos (repetición estable); capa explícita
    «asociada» devuelve la asociada y no la oficial; capa «todas» recupera
    guías: la omisión es el filtro, no el índice.
 5) Sin filas elegibles: la consulta solo casaba en una capa excluida por
    defecto -> sin excepción, estructura normal (resultados=[], omitidos=[],
    aviso «Sin coincidencias para los términos dados.», ámbito y terminos
    declarados) y, con capa «todas», sí se encuentra: la omisión era el
    filtro, no el índice.
 6) Filtro matéria: query con término común a dos docs; op.materia exacta
    devuelve solo la fila de esa materia y excluye la otra (ambas direcciones).
 7) Capa: por defecto («oficial+asociada») se excluyen filas capa «guias»
    aunque casen; capa «todas» las incluye (ambito_capa == «todas»); capa
    «guias» exacta devuelve solo esa capa.
 8) Consulta SIN filtro sigue encontrando documentos AÑADIDOS al corpus
    (guarda contra un fix que dejara fuera del índice lo nuevo).
 9) Desempate estable: textos idénticos -> puntuación idéntica y orden
    determinista (documento, id_tecnico); reejecución idéntica.
10) Tokens numéricos exactos: «103» solo casa el doc con el token «103» y no
    el que contiene «1030» (y a la inversa), sin bonus de frase (len<=6).
11) Parámetros: «ventilacion con h=3 m» separa h=3; los términos efectivos no
    incluyen «3»: un doc lleno de «3» queda fuera; traza y literal intactos.
12) Navegación: encabezado literal de navegacion_fuente.json (>=2 palabras,
    página verificada) contenido en la consulta resuelve página real
    (en_cuerpo); sin el encabezado en la consulta -> navegacion None. La
    fixture contiene el encabezado literal COMPLETO (incluido el prefijo,
    p. ej. «Apartado: ...») en el texto de la página: _titulo_sin_codigo no
    elimina ese prefijo, así que sin él en_cuerpo=False correctamente.
13) Adaptador, edición inexistente: version_no_disponible sin sustitución
    (sin páginas, resultados, avisos ni textos del doc) y versiones
    disponibles listadas.
14) Adaptador, presupuesto exacto/bajo: frontera con ceil(len/4) (proxy
    chars/4, encs vacíos forzados en la instancia); presupuesto exacto -> ok;
    uno menos -> presupuesto_excedido con el MISMO texto sin recortes
    (preservación de página literal y aviso del doc.json).
15) Adaptador, privados fuera de estadísticas: añadir documentos
    distribute=False con el término NO cambia resultados, puntuaciones ni
    texto_contexto del corpus público; este invariante SÍ es contrato porque
    el filtrado distribute ocurre ANTES del IDF global en AdaptadorContexto.

Límites de la muestra: corpus sintético mínimo (indice/apartados.jsonl,
doc.json, estructura.json, paginas.json, pagina/pXXXX.md, apartado/*.md);
notas/footnotes auxiliares, tablas, multi-página y tiktoken real quedan fuera.
El recuento chars/4 es proxy local de texto, no tokens de API ni consumo de
proveedores; no se mide gasto. Las puntuaciones se comparan entre ejecuciones
del mismo motor (no valores absolutos ni esperados fijos), de modo que la
presencia o ausencia de snowballstemmer no afecta.

Estado del encargo (registrado sin ocultar fallos): el ajuste que adelantaba
el filtrado antes de las estadísticas globales se REVERTIÓ exactamente tras el
contraste con gold INDEPENDIENTE: en las consultas 46 y 149 el diseño global
declarado sostiene 13/14 referencias y la variante local cae a 11/14 (perdía
REBT103 y 109 en dos consultas precisas), pese a ser estable. La variación de
puntuación al crecer la colección era diseño declarado, no bug. El gold real
no se modifica; no se tunearon textos ni páginas para pasar. El gap SUA
preexistente queda pendiente; cualquier conclusión de degradación o mejora
global corresponde a la ejecución contra el gold, fuera del alcance de esta
suite (aquí solo contratos de motor y adaptador).

Aislamiento: acceso.py y adaptador_contexto.py se cargan con importlib bajo
nombres privados propios y sys.modules["acceso"] se restaura al valor previo,
para no compartir estado global con otras suites (que cargan o parchean
«acceso»), tanto si corren antes como después.

Ejecución: python test_estabilidad_recuperacion.py -v   (desde tests/)
            python -m unittest discover -s tests -p "test_estabilidad_recuperacion.py" -v
"""
import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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


# Instancia privada de acceso.py: motor real, sin parche de BM25 ni ranking.
_ACC = _cargar_modulo_privado("_acc_priv_test_estabilidad", RAIZ / "acceso.py")


def _cargar_adaptador_aislado():
    """Carga adaptador_contexto.py resolviendo `import acceso` a la instancia privada."""
    anterior = sys.modules.get("acceso")
    sys.modules["acceso"] = _ACC
    try:
        return _cargar_modulo_privado(
            "_adaptador_priv_test_estabilidad", RAIZ / "adaptador_contexto.py")
    finally:
        if anterior is None:
            sys.modules.pop("acceso", None)
        else:
            sys.modules["acceso"] = anterior


_MOD = _cargar_adaptador_aislado()


def _escribir(ruta, texto):
    ruta.write_text(texto, encoding="utf-8", newline="\n")


def _pares(res):
    """[(id_tecnico, puntuacion_bm25)] en el orden devuelto por el motor."""
    return [(r["id_tecnico"], r["puntuacion_bm25"]) for r in res["resultados"]]


class PruebasEstabilidadRecuperacion(unittest.TestCase):
    """Buscador real sobre corpus temporales aislados; cero mock.patch."""

    # ------------------------------------------------------------ corpus

    def _corpus(self, docs):
        """Escribe un corpus temporal mínimo y devuelve {raiz, filas, docs} REALES."""
        tmp = tempfile.mkdtemp(prefix="estab-recup-")
        self.addCleanup(shutil.rmtree, tmp, True)
        raiz = Path(tmp).resolve()
        (raiz / "indice").mkdir(parents=True)
        lineas = []
        for d in docs:
            doc_id = d["id"]
            base = raiz / doc_id
            (base / "pagina").mkdir(parents=True)
            (base / "apartado").mkdir(parents=True)
            docj = {
                "id": doc_id, "code": d["codigo"],
                "layer": d.get("capa", "oficial"),
                "scope": d.get("materia", "pruebas sinteticas"),
                "version": d.get("version", "2020-10-01"),
                "sha256": "SHA-" + doc_id,
                "distribute": d.get("distribute", True),
                "url": "https://oficial.ejemplo/" + doc_id,
                "title": d["title"],
                "advertencias": list(d.get("advertencias") or []),
            }
            if d.get("nota_capa"):
                docj["nota_capa"] = d["nota_capa"]
            _escribir(base / "doc.json",
                      json.dumps(docj, ensure_ascii=False) + "\n")
            entradas = []
            for i, ap in enumerate(d["apartados"], 1):
                archivo = ap.get("archivo", "ap%02d.md" % i)
                entradas.append({
                    "id_tecnico": ap["id_tecnico"], "titulo": ap["titulo"],
                    "nivel": 2, "paginas": list(ap.get("paginas") or [1]),
                    "archivo": "apartado/" + archivo,
                    "ruta_oficial": ap.get("ruta_oficial", "DB %d.%d" % (1, i)),
                })
            _escribir(base / "estructura.json",
                      json.dumps({"apartados": entradas}, ensure_ascii=False) + "\n")
            paginas_meta = []
            for p, texto_pg in (d.get("paginas") or {1: "Pagina sintetica sin mas."}).items():
                _escribir(base / "pagina" / ("p%04d.md" % p), texto_pg)
                paginas_meta.append({"n": p, "pagina": p,
                                     "archivo": "pagina/p%04d.md" % p,
                                     "etiqueta_impresa": "p. %d" % p})
            _escribir(base / "paginas.json",
                      json.dumps({"paginas": paginas_meta}, ensure_ascii=False) + "\n")
            if d.get("navegacion"):
                _escribir(base / "navegacion_fuente.json",
                          json.dumps({"nodos": d["navegacion"]}, ensure_ascii=False) + "\n")
            for i, ap in enumerate(d["apartados"], 1):
                archivo = ap.get("archivo", "ap%02d.md" % i)
                _escribir(base / "apartado" / archivo, ap["texto"])
                lineas.append(json.dumps({
                    "id_tecnico": ap["id_tecnico"], "apartado_id": ap["id_tecnico"],
                    "documento": doc_id, "doc_json": doc_id + "/doc.json",
                    "archivo": doc_id + "/apartado/" + archivo,
                    "capa": docj["layer"], "version": docj["version"],
                    "titulo": ap["titulo"], "paginas": list(ap.get("paginas") or [1]),
                    "nivel": 2, "estructura": doc_id + "/estructura.json",
                    "codigo": docj["code"], "materia": docj["scope"],
                    "ruta_oficial": "DB %d.%d" % (1, i),
                }, ensure_ascii=False))
        _escribir(raiz / "indice" / "apartados.jsonl", "\n".join(lineas) + "\n")
        filas = _ACC.cargar_indice(raiz)
        return {"raiz": raiz, "filas": filas, "docs": _ACC.cargar_docs(raiz, filas)}

    @staticmethod
    def _extras(i, capa, prefijo, titulo):
        """Documento excluido típico para la prueba de independencia."""
        return {
            "id": "doc-%s-%02d" % (prefijo, i), "codigo": "%s-%02d" % (prefijo, i),
            "capa": capa, "materia": "materia-ajena" if capa == "oficial" else "sobrantes",
            "title": titulo % i,
            "apartados": [{"id_tecnico": "1.1",
                           "titulo": (titulo + " apartado") % i,
                           "texto": "Ventilacion pasillos rutina relleno extendido marcador %02d."
                                    % i}],
        }

    # ------------------------------------------------------------ ejecución

    def _buscar(self, corpus, consulta, **overrides):
        op = SimpleNamespace(
            max=overrides.pop("max", 5), presupuesto=100000, expandir=0,
            documento=overrides.pop("documento", None),
            capa=overrides.pop("capa", None),
            materia=overrides.pop("materia", None))
        terminos = [t for t in re.split(r"[\s,;]+", consulta) if len(t) > 1]
        return _ACC.buscar_bm25(corpus["raiz"], corpus["filas"], corpus["docs"],
                                consulta, terminos, op, {})

    def _adaptador(self, corpus):
        ad = _MOD.AdaptadorContexto(str(corpus["raiz"]))
        # Determinismo de recuento: proxy chars/4 local, sin tiktoken (no es uso de API).
        ad.encs = {}
        ad.modo_contadores = "aproximacion_caracteres_4"
        return ad

    # ------------------------------------------------------------ 1-4 filtrado y repetición

    def test_filtro_documento_sin_fuga_y_repetible(self):
        """Caso 1 (filtrado; el IDF es global sobre filas indexadas): al
        añadir 80 documentos excluidos con el término, ningún excluido sale;
        los seleccionados son del doc acotado y legibles; repetir la MISMA
        consulta sobre el MISMO corpus reproduce la respuesta. No se exige
        invariancia estadística entre colecciones (variar la puntuación al
        crecer la colección es diseño declarado del IDF global)."""
        base = {
            "id": "doc-base", "codigo": "DB-SYN-77", "capa": "oficial",
            "title": "Doc base sintetico unico",
            "apartados": [
                {"id_tecnico": "1.1", "titulo": "Apartado base higiene",
                 "texto": "Regla sintetica de ventilacion e higiene en pasillos comunes."},
                {"id_tecnico": "1.2", "titulo": "Apartado base extra",
                 "texto": "Ventilacion ventilacion ventilacion sin higiene declarada."},
            ]}
        corpus_a = self._corpus([dict(base)])
        self.assertEqual(len(corpus_a["filas"]), 2)
        res_a = self._buscar(corpus_a, "ventilacion higiene", documento="doc-base")
        res_a2 = self._buscar(corpus_a, "ventilacion higiene", documento="doc-base")
        pares_a = _pares(res_a)
        self.assertEqual(pares_a, _pares(res_a2))  # mismo corpus -> misma respuesta
        self.assertEqual({r["documento"] for r in res_a["resultados"]}, {"doc-base"})
        self.assertTrue(pares_a and all(s > 0 for _, s in pares_a))
        for r in res_a["resultados"]:
            self.assertIn("ventilacion", r["texto_integro"].lower())
        ampliado = [dict(base)] + [
            self._extras(i, "guias", "gui", "Guia rellena %02d") for i in range(40)
        ] + [self._extras(i, "oficial", "aj", "Apartado ajeno %02d") for i in range(40)]
        corpus_b = self._corpus(ampliado)
        self.assertEqual(len(corpus_b["filas"]), 82)  # los excluidos SÍ están indexados
        res_b = self._buscar(corpus_b, "ventilacion higiene", documento="doc-base")
        res_b2 = self._buscar(corpus_b, "ventilacion higiene", documento="doc-base")
        self.assertEqual(_pares(res_b), _pares(res_b2))
        # sin fuga: solo el doc acotado, con contenido legible del término
        self.assertEqual({r["documento"] for r in res_b["resultados"]}, {"doc-base"})
        for r in res_b["resultados"]:
            self.assertIn("ventilacion", r["texto_integro"].lower())

    def test_filtro_alias_sin_fuga_y_repetible(self):
        """Caso 2: mismo contrato acotando por el código (alias); el prefijo
        del código NO casará nada (pertenencia exacta, sin subcadenas)."""
        base = {
            "id": "doc-base", "codigo": "DB-SYN-77", "capa": "oficial",
            "title": "Doc base sintetico unico",
            "apartados": [
                {"id_tecnico": "1.1", "titulo": "Apartado base higiene",
                 "texto": "Regla sintetica de ventilacion e higiene en pasillos comunes."},
                {"id_tecnico": "1.2", "titulo": "Apartado base extra",
                 "texto": "Ventilacion ventilacion ventilacion sin higiene declarada."},
            ]}
        corpus_a = self._corpus([dict(base)])
        res_a = self._buscar(corpus_a, "ventilacion", documento="DB-SYN-77")
        res_a2 = self._buscar(corpus_a, "ventilacion", documento="DB-SYN-77")
        self.assertEqual(_pares(res_a), _pares(res_a2))  # mismo corpus -> misma respuesta
        self.assertGreaterEqual(len(res_a["resultados"]), 1)
        self.assertEqual({r["documento"] for r in res_a["resultados"]}, {"doc-base"})
        for r in res_a["resultados"]:
            self.assertIn("ventilacion", r["texto_integro"].lower())
        vacio = self._buscar(corpus_a, "ventilacion", documento="DB-SYN")
        self.assertEqual(vacio["resultados"], [])
        ampliado = [dict(base)] + [
            self._extras(i, "guias", "gui", "Guia rellena %02d") for i in range(40)
        ] + [self._extras(i, "oficial", "aj", "Apartado ajeno %02d") for i in range(40)]
        corpus_b = self._corpus(ampliado)
        res_b = self._buscar(corpus_b, "ventilacion", documento="DB-SYN-77")
        res_b2 = self._buscar(corpus_b, "ventilacion", documento="DB-SYN-77")
        self.assertEqual(_pares(res_b), _pares(res_b2))
        self.assertGreaterEqual(len(res_b["resultados"]), 1)
        self.assertEqual({r["documento"] for r in res_b["resultados"]}, {"doc-base"})
        for r in res_b["resultados"]:
            self.assertIn("ventilacion", r["texto_integro"].lower())

    def test_filtro_materia_sin_fuga_y_repetible(self):
        """Caso 3 (filtrado por materia): al añadir 40 documentos con el
        término y materia excluida, ningún excluido sale; los seleccionados
        son de la materia acotada y legibles; repetición del mismo corpus
        reproduce la respuesta (sin invariancia entre colecciones)."""
        base = {
            "id": "doc-mat-base", "codigo": "MB-1", "materia": "incendios",
            "title": "Doc materia base sintetico",
            "apartados": [
                {"id_tecnico": "1.1", "titulo": "Apartado base higiene",
                 "texto": "Regla sintetica de ventilacion e higiene en pasillos comunes."},
                {"id_tecnico": "1.2", "titulo": "Apartado base extra",
                 "texto": "Ventilacion ventilacion ventilacion sin higiene declarada."},
            ]}
        corpus_a = self._corpus([dict(base)])
        res_a = self._buscar(corpus_a, "ventilacion higiene", materia="incendios")
        res_a2 = self._buscar(corpus_a, "ventilacion higiene", materia="incendios")
        self.assertEqual(_pares(res_a), _pares(res_a2))  # mismo corpus -> misma respuesta
        self.assertEqual({r["documento"] for r in res_a["resultados"]},
                         {"doc-mat-base"})
        self.assertTrue(_pares(res_a) and all(s > 0 for _, s in _pares(res_a)))
        for r in res_a["resultados"]:
            self.assertIn("ventilacion", r["texto_integro"].lower())
        ampliado = [dict(base)] + [
            self._extras(i, "oficial", "aj", "Apartado ajeno %02d") for i in range(40)]
        corpus_b = self._corpus(ampliado)
        self.assertEqual(len(corpus_b["filas"]), 42)  # materia ajena indexada igualmente
        res_b = self._buscar(corpus_b, "ventilacion higiene", materia="incendios")
        res_b2 = self._buscar(corpus_b, "ventilacion higiene", materia="incendios")
        self.assertEqual(_pares(res_b), _pares(res_b2))
        self.assertEqual({r["documento"] for r in res_b["resultados"]},
                         {"doc-mat-base"})
        for r in res_b["resultados"]:
            self.assertIn("ventilacion", r["texto_integro"].lower())

    def test_filtro_capa_sin_fuga_defecto_y_asociada(self):
        """Caso 4 (filtrado por capa): por defecto solo sale el doc oficial
        aunque se añadan 40 guías con ambos términos (repetición estable);
        capa explícita «asociada» devuelve la asociada y no la oficial; capa
        «todas» recupera guías (la omisión es el filtro, no el índice)."""
        doc_ofi = {"id": "doc-cap-ofi", "codigo": "CA-1", "capa": "oficial",
                   "title": "Doc capa oficial sintetico",
                   "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado oficial",
                                  "texto": "Sentencia del termino ofitermo en el oficio."}]}
        doc_aso = {"id": "doc-cap-aso", "codigo": "CB-1", "capa": "asociada",
                   "title": "Doc capa asociada sintetico",
                   "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado asociado",
                                  "texto": "Sentencia del termino asociadotermo en el anexo."}]}
        corpus_a = self._corpus([dict(doc_ofi), dict(doc_aso)])
        guias = []
        for i in range(40):
            extra = self._extras(i, "guias", "gui", "Guia de capa %02d")
            # las guías añadidas contienen AMBOS términos (estresa cualquier fuga).
            extra["apartados"][0]["texto"] = (
                "Sentencia del termino ofitermo y asociadotermo en guia %02d." % i)
            guias.append(extra)
        corpus_b = self._corpus([dict(doc_ofi), dict(doc_aso)] + guias)
        self.assertEqual(len(corpus_a["filas"]), 2)
        self.assertEqual(len(corpus_b["filas"]), 42)
        for corpus in (corpus_a, corpus_b):
            # por defecto: solo el oficial, contenido legible y repetición estable
            defecto = self._buscar(corpus, "ofitermo")
            defecto2 = self._buscar(corpus, "ofitermo")
            self.assertEqual(_pares(defecto), _pares(defecto2))
            self.assertEqual({r["documento"] for r in defecto["resultados"]},
                             {"doc-cap-ofi"})
            self.assertNotIn("doc-cap-aso",
                             {r["documento"] for r in defecto["resultados"]})
            self.assertNotIn("doc-gui-00",
                             {r["documento"] for r in defecto["resultados"]})
            for r in defecto["resultados"]:
                self.assertIn("ofitermo", r["texto_integro"].lower())
            # capa explícita asociada: la asociada, no la oficial, invariante
            asociada = self._buscar(corpus, "asociadotermo", capa="asociada")
            asociada2 = self._buscar(corpus, "asociadotermo", capa="asociada")
            self.assertEqual(_pares(asociada), _pares(asociada2))
            self.assertEqual({r["documento"] for r in asociada["resultados"]},
                             {"doc-cap-aso"})
            for r in asociada["resultados"]:
                self.assertIn("asociadotermo", r["texto_integro"].lower())
        # y con capa «todas» sí aparecen las guías añadidas
        todas = self._buscar(corpus_b, "ofitermo asociadotermo", capa="todas")
        self.assertEqual(todas["ambito_capa"], "todas")
        self.assertIn("doc-gui-00",
                      {r["documento"] for r in todas["resultados"]})

    def test_sin_filas_elegibles_estructura_normal(self):
        """Caso 5: consulta que solo casaba en capa excluida por defecto ->
        sin excepción, estructura normal sin resultados; con capa «todas» sí
        encuentra, evidenciando que la omisión era el filtro, no el índice."""
        corpus = self._corpus([
            {"id": "doc-guias-unica", "codigo": "GU-1", "capa": "guias",
             "materia": "sobrantes", "title": "Guia unica sintetica",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado guiado",
                            "texto": "Contenido del termino guiadotermo en la guia."}]},
        ])
        self.assertEqual({f["capa"] for f in corpus["filas"]}, {"guias"})
        res = self._buscar(corpus, "guiadotermo")  # por defecto: nada elegible
        self.assertEqual(res["resultados"], [])
        self.assertEqual(res["omitidos"], [])
        self.assertEqual(res["ambito_capa"], "oficial+asociada")
        self.assertIn("Sin coincidencias para los términos dados.",
                      res["advertencias"])
        self.assertTrue(res["terminos"])  # términos declarados, sin stema fija
        self.assertEqual(res["presupuesto"]["limite"], 100000)
        self.assertEqual(res["presupuesto"]["modo_tokens"],
                         "aproximacion_caracteres_4")
        # la misma consulta con capa «todas» sí encuentra: filtro, no índice
        todas = self._buscar(corpus, "guiadotermo", capa="todas")
        self.assertEqual([r["documento"] for r in todas["resultados"]],
                         ["doc-guias-unica"])
        self.assertGreater(todas["resultados"][0]["puntuacion_bm25"], 0)

    # ------------------------------------------------------------ 6-12 filtros y motor

    def test_filtro_materia_exacta_en_dos_direcciones(self):
        corpus = self._corpus([
            {"id": "doc-mat-a", "codigo": "MAT-A", "materia": "incendios",
             "title": "Apartado incendios sintetico",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado alumbrado A",
                            "texto": "Medida de alumbrado medellamada sintetica."}]},
            {"id": "doc-mat-b", "codigo": "MAT-B", "materia": "instalaciones",
             "title": "Apartado instalaciones sintetico",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado alumbrado B",
                            "texto": "Medida de alumbrado fugas declaradas."}]},
        ])
        self.assertEqual(len(corpus["filas"]), 2)
        solo_a = self._buscar(corpus, "alumbrado", materia="incendios")
        self.assertEqual({r["documento"] for r in solo_a["resultados"]}, {"doc-mat-a"})
        solo_b = self._buscar(corpus, "alumbrado", materia="instalaciones")
        self.assertEqual({r["documento"] for r in solo_b["resultados"]}, {"doc-mat-b"})
        self.assertGreater(solo_a["resultados"][0]["puntuacion_bm25"], 0)

    def test_capa_defecto_excluye_guias_y_todas_incluye(self):
        corpus = self._corpus([
            {"id": "doc-ofi", "codigo": "OFI-1", "capa": "oficial",
             "title": "Norma oficial sintetica",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado official",
                            "texto": "Pendiente revisable rotulo oficial del anexo."}]},
            {"id": "doc-guias", "codigo": "GUI-1", "capa": "guias",
             "materia": "sobrantes", "title": "Guia orientativa sintetica",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado orientativo",
                            "texto": "Pendiente revisable rotulo orientativo de la guia."}]},
        ])
        capas_filas = {f["capa"] for f in corpus["filas"]}
        self.assertEqual(capas_filas, {"oficial", "guias"})  # premisa: guias indexadas
        defecto = self._buscar(corpus, "revisable")
        self.assertEqual(defecto["ambito_capa"], "oficial+asociada")
        self.assertEqual({r["documento"] for r in defecto["resultados"]}, {"doc-ofi"})
        self.assertNotIn("doc-guias", {r["documento"] for r in defecto["resultados"]})
        con_guias = self._buscar(corpus, "orientativo")
        self.assertEqual(con_guias["resultados"], [])  # solo la capa guias casaba
        todas = self._buscar(corpus, "orientativo", capa="todas")
        self.assertEqual(todas["ambito_capa"], "todas")
        self.assertEqual({r["documento"] for r in todas["resultados"]}, {"doc-guias"})
        exacta = self._buscar(corpus, "revisable", capa="guias")
        self.assertEqual({r["documento"] for r in exacta["resultados"]}, {"doc-guias"})

    def test_sin_filtro_encuentra_documentos_anadidos(self):
        corpus = self._corpus([
            {"id": "doc-viejo", "codigo": "VIE-1",
             "title": "Doc viejo sintetico",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado viejo",
                            "texto": "Contenido antiguo estable del corpus base."}]},
            {"id": "doc-nuevo", "codigo": "NUE-1",
             "title": "Doc nuevo sintetico",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado nuevo",
                            "texto": "Marcador marcanuevo del doc añadido al corpus."}]},
        ])
        res = self._buscar(corpus, "marcanuevo")
        self.assertGreaterEqual(len(res["resultados"]), 1)
        self.assertEqual(res["resultados"][0]["documento"], "doc-nuevo")
        self.assertGreater(res["resultados"][0]["puntuacion_bm25"], 0)

    def test_desempate_estable_y_reproducible(self):
        texto = "Texto identico de desempate estable marcador parejo QZ."
        iguales = {"id_tecnico": "1.1", "titulo": "Apartado parejo", "texto": texto}
        corpus = self._corpus([
            {"id": "doc-empate-a", "codigo": "DB-EMP", "title": "Doc empate A",
             "apartados": [dict(iguales), dict(iguales, id_tecnico="1.2")]},
            {"id": "doc-empate-z", "codigo": "DB-ZEMP", "title": "Doc empate Z",
             "apartados": [dict(iguales)]},
        ])
        primera = self._buscar(corpus, "desempate parejo")
        pares_1 = _pares(primera)
        self.assertEqual(len(pares_1), 3)
        self.assertGreater(pares_1[0][1], 0)
        self.assertEqual([i for i, _ in pares_1], ["1.1", "1.2", "1.1"])
        self.assertEqual([r["documento"] for r in primera["resultados"]],
                         ["doc-empate-a", "doc-empate-a", "doc-empate-z"])
        # mismos textos -> misma puntuación exacta y desempate (documento, id)
        puntajes = [s for _, s in pares_1]
        self.assertEqual(puntajes[0], puntajes[1])
        self.assertEqual(puntajes[0], puntajes[2])
        segunda = self._buscar(corpus, "desempate parejo")
        self.assertEqual(_pares(segunda), pares_1)  # reproducible entre llamadas

    def test_tokens_numericos_exactos_sin_subcadenas(self):
        corpus = self._corpus([
            {"id": "doc-num-a", "codigo": "NUM-A", "title": "Doc banda centena",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado centena",
                            "texto": "La banda 103 cubre el margen sureste."}]},
            {"id": "doc-num-b", "codigo": "NUM-B", "title": "Doc banda millar",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado millar",
                            "texto": "La banda 1030 cubre el margen noroeste."}]},
        ])
        por_103 = self._buscar(corpus, "103")
        self.assertEqual({r["documento"] for r in por_103["resultados"]},
                         {"doc-num-a"})
        self.assertGreater(por_103["resultados"][0]["puntuacion_bm25"], 0)
        por_1030 = self._buscar(corpus, "1030")
        self.assertEqual({r["documento"] for r in por_1030["resultados"]},
                         {"doc-num-b"})
        self.assertGreater(por_1030["resultados"][0]["puntuacion_bm25"], 0)

    def test_parametros_separados_no_contaminan_busqueda(self):
        corpus = self._corpus([
            {"id": "doc-tema", "codigo": "TEM-1", "title": "Doc ventilacion sintetica",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado ventilacion",
                            "texto": "La ventilacion minima exige caudal constante."}]},
            {"id": "doc-num", "codigo": "MAG-1", "title": "Doc numeros sueltos",
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado numeros",
                            "texto": "El fanal 3 marca el anexo 33 y otra vez 3."}]},
        ])
        res = self._buscar(corpus, "ventilacion con h=3 m")
        self.assertEqual({r["documento"] for r in res["resultados"]}, {"doc-tema"})
        self.assertGreater(len(res["parametros_aportados"]), 0)
        p = res["parametros_aportados"][0]
        self.assertEqual(p["variable"], "h")
        self.assertEqual(p["valor"], "3")
        self.assertIsNone(p["unidad"])
        self.assertEqual(p["literal"], "h=3")
        self.assertEqual(res["consulta_tematica"], "ventilacion con m")
        self.assertEqual(res["consulta_operacion"], "")
        self.assertEqual(res["traza_consulta"][0]["literal"], "h=3")

    def test_navegacion_encabezado_resuelve_y_negativa(self):
        corpus = self._corpus([
            {"id": "doc-nav", "codigo": "NAV-1", "title": "Manual sintetico de senales",
             "navegacion": [{"pagina": 1, "pagina_verificada": True,
                             "titulo_literal": "Apartado: Seccion despeje",
                             "ruta_literal": "1/a", "id_navegacion": "nav-1"}],
             "paginas": {1: "Apartado: Seccion despeje: encabezado literal "
                         "completo de la pagina sintetica."},
             "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado despeje",
                            "texto": "Regla de seccion despeje del anexo sintetico."}]},
        ])
        con_nav = self._buscar(corpus, "manual de senales apartado: seccion despeje")
        nav = con_nav["navegacion"]
        self.assertIsNotNone(nav)
        self.assertEqual(nav["documento"], "doc-nav")
        self.assertEqual(nav["pagina"], 1)
        self.assertEqual(nav["titulo_literal"], "Apartado: Seccion despeje")
        self.assertTrue(nav["en_cuerpo"])
        self.assertIn("seccion despeje", nav["consulta_clave"])
        sin_nav = self._buscar(corpus, "manual de senales")
        self.assertIsNone(sin_nav["navegacion"])

    # ------------------------------------------------------------ 13-15 adaptador

    def test_adaptador_edicion_inexistente_sin_sustitucion(self):
        pagina = "Texto literal de la pagina de la edicion sintetica."
        corpus = self._corpus([{
            "id": "doc-ed", "codigo": "ED-1", "version": "2020-10-01",
            "title": "Doc ediciones sintetico",
            "advertencias": ["AVISO-EDICION-AUSENTE: solo edicion 2020-10-01."],
            "paginas": {1: pagina},
            "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado edicion",
                           "texto": "Texto literal del apartado de la edicion 2020."}],
        }])
        ad = self._adaptador(corpus)
        res = ad.preparar("edicion sintetica inexistente", documento="doc-ed",
                          version="1999-01-01")
        self.assertEqual(res["estado"], "version_no_disponible")
        self.assertEqual(res["documento"], "doc-ed")
        self.assertEqual(res["version"], "1999-01-01")
        self.assertEqual(res["versiones_disponibles"], ["2020-10-01"])
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])
        texto = res["texto_contexto"]
        self.assertIn("ESTADO version_no_disponible", texto)
        self.assertIn("No se sustituye por otra versión", texto)
        self.assertIn("Versiones disponibles: 2020-10-01", texto)
        # sin sustitución: nada del contenido ni avisos del documento
        self.assertNotIn("Texto literal", texto)
        self.assertNotIn(pagina, texto)
        self.assertNotIn("AVISO-EDICION-AUSENTE", texto)
        self.assertNotIn("AVISO-EDICION-AUSENTE",
                         json.dumps(res["recuperacion"], ensure_ascii=False))

    def test_adaptador_presupuesto_exacto_y_bajo_preservacion(self):
        aviso = "AVISO-PRESUPUESTO-ED: advertencia sintetica que cuenta en el presupuesto final."
        pagina = "Texto literal de la pagina de frontera del presupuesto."
        corpus = self._corpus([{
            "id": "doc-pres", "codigo": "PRE-1", "title": "Doc presupuesto sintetico",
            "advertencias": [aviso], "paginas": {1: pagina},
            "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado frontera",
                           "texto": "Texto literal del apartado de frontera sintetica."}],
        }])
        ad = self._adaptador(corpus)
        holgado = ad.preparar("frontera presupuesto sintetica",
                              presupuesto_tokens=10 ** 6)
        self.assertEqual(holgado["estado"], "ok")
        self.assertEqual(holgado["modo_tokens"], "aproximacion_caracteres_4")
        texto = holgado["texto_contexto"]
        self.assertIn(aviso, texto)
        self.assertIn(pagina, texto)
        limite = max(1, math.ceil(len(texto) / 4.0))
        self.assertEqual(holgado["tokens_contexto"], limite)
        exacto = ad.preparar("frontera presupuesto sintetica",
                             presupuesto_tokens=limite)
        self.assertEqual(exacto["estado"], "ok")
        self.assertFalse(exacto["excedido"])
        self.assertEqual(exacto["texto_contexto"], texto)  # estable entre llamadas
        bajo = ad.preparar("frontera presupuesto sintetica",
                           presupuesto_tokens=limite - 1)
        self.assertEqual(bajo["estado"], "presupuesto_excedido")
        self.assertTrue(bajo["excedido"])
        self.assertEqual(bajo["tokens_contexto"], limite)
        self.assertEqual(bajo["limite_tokens"], limite - 1)
        # preservación: sin recortes, página literal y aviso intactos
        self.assertEqual(bajo["texto_contexto"], texto)
        self.assertIn(pagina, bajo["texto_contexto"])
        self.assertIn(aviso, bajo["texto_contexto"])
        self.assertEqual(len(bajo["paginas"]), 1)
        self.assertEqual(bajo["paginas"][0]["pagina"], 1)
        self.assertEqual(bajo["paginas"][0]["texto_sha256"],
                         hashlib.sha256(pagina.encode("utf-8")).hexdigest())

    def test_adaptador_privados_distribute_false_no_alteran_publico(self):
        """Caso 15 (contrato del adaptador, sin parches): añadir documentos
        distribute=False con el término NO cambia resultados, puntuaciones ni
        texto_contexto del corpus público; el filtrado distribute ocurre
        ANTES del IDF global (AdaptadorContexto.__init__), a diferencia del
        filtro documento/capa/materia, que es posterior por diseño."""
        publico = {
            "id": "doc-publico", "codigo": "PUB-1", "capa": "oficial",
            "title": "Doc publico sintetico",
            "paginas": {1: "Pagina del apartado del doc publico sintetico."},
            "apartados": [
                {"id_tecnico": "1.1", "titulo": "Apartado publico uno",
                 "texto": "Contenido publico del termino publitarmo en el apartado uno."},
                {"id_tecnico": "1.2", "titulo": "Apartado publico dos",
                 "texto": "Publitarmo repetido en el apartado dos del doc publico."},
            ]}
        ad_a = self._adaptador(self._corpus([dict(publico)]))
        res_a = ad_a.preparar("publitarmo publico", max_resultados=5)
        self.assertEqual(res_a["estado"], "ok")
        pares_a = [(r["id_tecnico"], r["puntuacion_bm25"])
                   for r in res_a["recuperacion"]["resultados"]]
        self.assertGreaterEqual(len(pares_a), 2)
        self.assertTrue(all(s > 0 for _, s in pares_a))
        privados = [{
            "id": "doc-priv-%02d" % i, "codigo": "PR-%02d" % i,
            "capa": "oficial", "materia": "privada", "distribute": False,
            "title": "Doc privado %02d" % i,
            "apartados": [{"id_tecnico": "1.1", "titulo": "Apartado privado",
                           "texto": "Publitarmo publitarmo publitarmo en privado %02d "
                                    "para estresar el IDF si se filtrara tarde." % i}],
        } for i in range(25)]
        corpus_b = self._corpus([dict(publico)] + privados)
        self.assertEqual(len(corpus_b["filas"]), 27)  # públicos + privados indexados
        ad_b = self._adaptador(corpus_b)
        res_b = ad_b.preparar("publitarmo publico", max_resultados=5)
        self.assertEqual(res_b["estado"], "ok")
        pares_b = [(r["id_tecnico"], r["puntuacion_bm25"])
                   for r in res_b["recuperacion"]["resultados"]]
        self.assertEqual(pares_b, pares_a)  # resultados y puntuaciones idénticos
        self.assertEqual(res_b["texto_contexto"], res_a["texto_contexto"])
        volcado = json.dumps(res_b["recuperacion"], ensure_ascii=False)
        self.assertNotIn("doc-priv", volcado)
        self.assertNotIn("doc-priv", res_b["texto_contexto"])


if __name__ == "__main__":
    unittest.main()
