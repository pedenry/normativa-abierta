#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unittest de resolución de ámbito territorial en AdaptadorContexto.

Encargo acotado: contrato objetivo del ajuste de la búsqueda libre actual:
 - Detectar alias con tildes y prefijos administrativos SOLO con los metadatos
   del corpus distribuible (jurisdiccion/municipio de los doc.json cargados).
 - Excluir fuentes de otra CCAA; admitir fuentes nacionales como
   complementarias cuando la consulta fija solo una localización.
 - Municipio conocido: candidatos = ese municipio, su CCAA padre según
   metadata (jurisdiccion del doc.json) y nacionales; nada más.
 - Consulta de CCAA: no admite documentos municipales que no se pidieron.
 - Varias CCAA en la consulta: unión de candidatos, no la última mención.
 - Documento explícito: precedencia del filtro; sin inferir ámbito alguno.
 - Municipio pedido explícitamente como municipal sin incorporar (incluso si
   el nombre coincide con una CCAA): sin_resultados explicado y nunca otro
   municipio.
 - Privados (distribute=False) no construyen alias en __init__ real.

Estados internos de _resolver_ambito NO se comprueban (pueden cambiar con la
corrección): se comprueba el conjunto de candidatos y la ausencia de
sustitución mediante efectos observables (resultados y páginas entregadas),
sin fijar mensajes ni trazas. "resolucion_ambito" es superficie JSON pública
documentada en la cabecera del módulo; se usa una sola vez y solo por
ausencia (documento explícito no traza ámbito). La implementación V1 está
siendo corregida: las aserciones expresan el contrato objetivo, no el
comportamiento actual; los casos que fotografían el bug pueden estar rojos
hasta que la corrección aterrice.

Rúbrica por caso (criterio -> aserción clave):
 1) alias con tilde: la consulta SIN tildes resuelve la CCAA nominal CON
    tilde por metadata; la otra CCAA queda fuera (no búsqueda global).
 2) alias con prefijo administrativo: forma completa («comunidad de …») y
    forma corta resuelven al MISMO conjunto; la otra CCAA queda fuera.
 3) nacional complementaria ante localización sola: conjunto exacto
    {CCAA mencionada, nacional}; la otra CCAA fuera; sin sustitución.
 4) consulta de CCAA: conjunto exacto {CCAA, nacional}; el doc municipal que
    declara esa jurisdicción NO entra si no se pide el municipio.
 5) municipio conocido: conjunto exacto {municipio, CCAA padre según
    metadata, nacional}; ningún otro municipio, ni el de otra CCAA.
 6) varias CCAA: unión {CCAA-A, CCAA-B, nacional}; no solo la última.
 7) documento explícito: resultados solo del documento pedido aunque la
    consulta mencione otra CCAA (sin inferencia) y sin nacionales; sin
    clave resolucion_ambito en la salida.
 8) municipal explícito sin incorporar (nombre coincide con CCAA):
    estado sin_resultados, sin páginas ni resultados, el texto conserva el
    pedido y NO aparece ningún otro municipio (sin mensaje fijado).
 9) distribute=False en carga real: no está en docs; ninguna clave de alias
    proviene de su metadata; jamás entra en resultados (el buscador recibido
    tampoco la ve: se afirman docs/filas capturadas).
 10) municipio conocido con pista municipal («ordenanza municipal»): resuelve
     con el conjunto completo del caso 5 (no cae en no-corporado).
 11) «En Villaprueba, ¿qué documentación exige la ordenanza municipal para
     una licencia?» (municipio NO incorporado): sin_resultados, sin páginas
     ni resultados y sin fallback a otra ciudad. La producción actual tiene
     el bug conocido de que «en|para» distingue mayúsculas y no detecta «En»
     inicial: LA EXPECTATIVA ES DEL CONTRATO Y NO SE AJUSTA AL BUG (roja
     hasta que la corrección de recuperación aterrice).
 12) variante minúscula «en Villaprueba…»: la misma abstención
     (sin_resultados, sin fallback); hoy es regresión verde, tras la
     corrección ambos casos deben abstenerse por igual.
 13) control del caso 11 sobre el mismo corpus: con localización conocida la
     fuente nacional (sintética, SIN jurisdiccion/municipio en doc.json)
     sigue admitida como complementaria; abstenerse con el municipio no
     incorporado no puede implementarse excluyendo nacionales.

Corpus SINTÉTICO temporal mínimo (misma forma de test_advertencias_fuentes.py):
indice/apartados.jsonl, <doc>/doc.json con jurisdiccion/municipio sintéticos,
estructura.json, paginas.json, pagina/p0001.md y apartado/p0001.md. Sin
normativa real, sin red, sin modelos; nombres e IDs son sintéticos de este
test, no del corpus real y sin valor de referencia (gold). La fuente NACIONAL
sintética declara jurisdiccion=None y municipio=None: el corpus nacional real
no declara metadato territorial y ningún clasificador se inventa aquí.

Mocks solo donde la lógica evaluada no está: crear_contadores (encs={} ->
modo aproximacion_caracteres_4, recuento determinista), buscar_bm25 (candidatos:
un apartado solo por documentos REALMENTE recibidos — intersección de las claves
de documentos y los documentos de filas, ambos ya filtrados por distribute en la
carga real — y a continuación aplica documento explícito y documentos_permitidos
como haría el motor; así un privado excluido por __init__ no puede reaparecer
por culpa del mock) y construir_lectura (abre las páginas del temporal). NO se
parchean cargar_indice, cargar_docs ni el
filtrado distribute y la construcción de alias de __init__: carga real de
fixtures. Límite declarado: el parche de buscar_bm25 asume la firma actual de
acceso.py (op.documento, op.documentos_permitidos); si la corrección altera
esa interfaz, se adapta el parche, no el contrato. El acceso a
_adaptador._alias_ambito en el caso 9 es interno y pedido por el encargo
(__init__ real); si cambia el nombre del atributo, se ajusta el acceso.

Recuento y límites: tokens_contexto en modo aproximacion_caracteres_4 es un
proxy local de texto (chars/4), no tokens de API; no mide consumo de
proveedores. Sin corpus real ni pares comparables no se calcula ahorro. La
cobertura del BM25 real, de construir_lectura real y de tiktoken queda fuera
del encargo. No se ejecutan procesos externos: la batería corre en unittest.
"""
import importlib.util
import json
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
_ACC = _cargar_modulo_privado("_acc_priv_test_ambito", RAIZ / "acceso.py")


def _cargar_adaptador_aislado():
    """Carga adaptador_contexto.py resolviendo `import acceso` a la instancia privada."""
    anterior = sys.modules.get("acceso")
    sys.modules["acceso"] = _ACC
    try:
        return _cargar_modulo_privado(
            "_adaptador_priv_test_ambito", RAIZ / "adaptador_contexto.py")
    finally:
        if anterior is None:
            sys.modules.pop("acceso", None)
        else:
            sys.modules["acceso"] = anterior


_MOD = _cargar_adaptador_aislado()


def _escribir(ruta, texto):
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)


def _doc_sintetico(doc_id, jurisdiccion=None, municipio=None, distribute=True):
    """doc.json + contenido mínimo sintético: una página y un apartado.

    Los nombres de territorio (jurisdiccion/municipio) son marcadores
    sintéticos de este test: ninguno pertenece al corpus real ni al
    vocabulario administrativo español real.
    """
    return {
        "id": doc_id,
        "distribute": distribute,
        "version": "2020-10-01",
        "sha256": "SHA-%s" % doc_id.replace("-", "").upper(),
        "url": "https://oficial.ejemplo/%s" % doc_id,
        "title": "Doc sintetico %s" % doc_id,
        "jurisdiccion": jurisdiccion,
        "municipio": municipio,
        "paginas_texto": {1: "Texto literal de pagina sintetica %s." % doc_id},
        "apartados": [{
            "apartado_id": "1.1",
            "id_tecnico": "%s-1.1" % doc_id,
            "ruta_oficial": "SINT %s 1.1" % doc_id.replace("-", " ").upper(),
            "titulo": "Apartado 1.1 de %s" % doc_id,
            "archivo": "p0001.md",
            "paginas": [1],
            "texto": "Texto literal del apartado 1.1 de %s." % doc_id,
        }],
    }


# Namespaces sintéticos de territorio usados por varios casos (metadata, no gold).
# La NACIONAL no declara territorio: jurisdiccion/municipio ausentes en doc.json,
# como en el corpus nacional real; ningún clasificador artificial con nombres demo.
_JUR_ALFA = "Comunidad de Territorio Álamo"     # con tilde: solo en metadata
_JUR_BETA = "Comunidad de Territorio Beta"
_MUN_VILLA = "Villa Betica"
_MUN_ALDEA = "Aldea Gamma"


def _docs_resultado(res):
    """Documentos presentes en los resultados del buscador (efecto observable)."""
    return {r["documento"] for r in res["recuperacion"]["resultados"]}


def _docs_paginas(res):
    """Documentos con alguna página completa entregada (efecto observable)."""
    return {p["doc"] for p in res["paginas"]}


class PruebasAmbitoBusquedaLibre(unittest.TestCase):
    """Carga real de fixtures (índice/doc.json/distribute/alias) con buscador,
    lectura y contadores parcheados; un corpus temporal por prueba."""

    # ------------------------------------------------------------- corpus

    def _corpus_sintetico(self, docs):
        """Escribe un corpus temporal mínimo y devuelve {raiz, docs}."""
        tmp = tempfile.mkdtemp(prefix="ambito-busq-")
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
                                      "url", "title", "jurisdiccion",
                                      "municipio") if k in d and d[k] is not None}
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

    def _resultado(self, corpus, doc_id):
        """Candidato sintético coherente con las fixtures (un apartado por doc)."""
        doc = corpus["docs"][doc_id]
        ap = next(iter(doc["apartados"].values()))
        docj = doc["doc_json"]
        return {
            "documento": doc_id,
            "version": docj.get("version"),
            "capa": "oficial",
            "apartado_id": ap["apartado_id"],
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

    def _montar(self, docs):
        """Corpus temporal + AdaptadorContexto con carga real y motor parcheado.

        Devuelve (corpus, adaptador, captura). El buscador parcheado recibe un
        candidato solo por documentos REALMENTE recibidos (intersección de
        claves de documentos y documentos de filas, ya filtrados por
        distribute en la carga real) y aplica el documento explícito y
        documentos_permitidos como haría el motor real: así el conjunto de
        candidatos que la implementación pasa al motor es observable por sus
        efectos (resultados/páginas), sin fijar estados internos.
        """
        corpus = self._corpus_sintetico(docs)
        captura = []

        def fake_buscar(contenido, filas, documentos, consulta, terminos, op, encs):
            doc_id = getattr(op, "documento", None)
            perm = getattr(op, "documentos_permitidos", None)
            captura.append({"doc_id": doc_id,
                            "perm": None if perm is None else set(perm),
                            "filas": [f["documento"] for f in filas],
                            "docs": set(documentos)})
            # candidatos: un apartado solo por documentos REALMENTE recibidos:
            # intersección de las claves de documentos y los documentos de
            # filas (ambos ya filtrados por distribute en la carga real). Un
            # privado excluido por __init__ no puede reaparecer por culpa del
            # mock; eso lo afirma además test_09 con la captura.
            cap_docs = set(documentos or {})
            cap_filas = {f.get("documento") for f in filas}
            visibles = cap_docs & cap_filas
            por_doc = [self._resultado(corpus, d) for d in sorted(visibles)
                       if d in corpus["docs"]]
            admitidos = por_doc
            if doc_id is not None:
                admitidos = [r for r in admitidos if r.get("documento") == doc_id]
            if perm is not None:
                permit = set(perm)
                admitidos = [r for r in admitidos if r.get("documento") in permit]
            return {"resultados": [dict(r) for r in admitidos],
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
                ("crear_contadores", lambda: ({}, "aproximacion_caracteres_4")),
                ("buscar_bm25", fake_buscar),
                ("construir_lectura", fake_lectura)):
            parche = mock.patch.object(_ACC, nombre, reemplazo)
            parche.start()
            self.addCleanup(parche.stop)
        ad = _MOD.AdaptadorContexto(str(corpus["raiz"]))
        return corpus, ad, captura

    # ------------------------------------------------------------- casos

    def test_01_alias_con_tilde_resuelve_sin_tildes(self):
        """Caso 1: consulta sin tildes resuelve la CCAA con tilde por metadata;
        la otra CCAA queda fuera (se restringió de verdad, no es global)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
        ])
        res = ad.preparar("criterios de aplicacion en territorio alamo")
        self.assertEqual(res["estado"], "ok")
        docs = _docs_resultado(res)
        self.assertIn("doc-caa-alamo", docs)
        self.assertNotIn("doc-caa-beta", docs)
        # las páginas siguen al conjunto admitido: sin entrega fuera de él
        self.assertEqual(_docs_paginas(res), docs)

    def test_02_alias_con_prefijo_equivale_forma_corta(self):
        """Caso 2: la forma completa con prefijo administrativo y la corta
        resuelven al mismo conjunto; la otra CCAA queda fuera en ambas."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
        ])
        larga = ad.preparar("criterios comunidad de territorio alamo")
        corta = ad.preparar("criterios territorio alamo")
        for res in (larga, corta):
            self.assertEqual(res["estado"], "ok")
            docs = _docs_resultado(res)
            self.assertIn("doc-caa-alamo", docs)
            self.assertNotIn("doc-caa-beta", docs)
            self.assertEqual(_docs_paginas(res), docs)
        self.assertEqual(_docs_resultado(larga), _docs_resultado(corta))

    def test_03_nacional_complementaria_con_localizacion_sola(self):
        """Caso 3: consulta que fija solo una CCAA admite a la fuente nacional
        como complementaria; la otra CCAA queda excluida."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
        ])
        res = ad.preparar("criterios de aplicacion en territorio alamo")
        self.assertEqual(res["estado"], "ok")
        esperado = {"doc-caa-alamo", "doc-nac"}
        self.assertEqual(_docs_resultado(res), esperado)
        self.assertEqual(_docs_paginas(res), esperado)

    def test_04_consulta_ccaa_no_incluye_municipio(self):
        """Caso 4: pedir la CCAA no arrastra al documento municipal que declara
        esa jurisdicción si el municipio no se mencionó."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar("criterios de aplicacion en territorio alamo")
        self.assertEqual(res["estado"], "ok")
        esperado = {"doc-caa-alamo", "doc-nac"}
        self.assertEqual(_docs_resultado(res), esperado)
        self.assertEqual(_docs_paginas(res), esperado)
        # ausencia de entrega del municipal: su texto de página literal único
        # no aparece (la cabecera puede trazar el ID como origen metadata, lo
        # que no es entrega de texto ni de resultados)
        self.assertNotIn(
            "Texto literal de pagina sintetica doc-muni-villa.",
            res["texto_contexto"])

    def test_05_municipio_conocido_conjunto_estricto(self):
        """Caso 5: municipio mencionado -> solo él, su CCAA padre según
        metadata y nacionales; ningún otro municipio, ni de otra CCAA."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
            _doc_sintetico("doc-muni-aldea", jurisdiccion=_JUR_BETA,
                           municipio=_MUN_ALDEA),
        ])
        res = ad.preparar("rehabilitacion energetica en villa betica")
        self.assertEqual(res["estado"], "ok")
        esperado = {"doc-muni-villa", "doc-caa-alamo", "doc-nac"}
        self.assertEqual(_docs_resultado(res), esperado)
        self.assertEqual(_docs_paginas(res), esperado)
        self.assertNotIn("doc-muni-aldea", _docs_resultado(res))
        self.assertNotIn("Aldea Gamma", res["texto_contexto"])

    def test_06_varias_ccaa_union_no_ultima(self):
        """Caso 6: dos CCAA mencionadas -> unión de ambas más nacionales;
        la búsqueda no queda reducida a la última mención."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
        ])
        res = ad.preparar("criterios en territorio alamo y en territorio beta")
        self.assertEqual(res["estado"], "ok")
        esperado = {"doc-caa-alamo", "doc-caa-beta", "doc-nac"}
        self.assertEqual(_docs_resultado(res), esperado)
        self.assertEqual(_docs_paginas(res), esperado)

    def test_07_documento_explicito_precedencia_sin_inferir(self):
        """Caso 7: con documento explícito, la mención territorial de otra CCAA
        no restringe ni sustituye: responde solo el documento pedido; no se
        infiere ámbito (sin resolucion_ambito) ni entran nacionales."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
        ])
        res = ad.preparar("criterios de aplicacion en territorio alamo",
                          documento="doc-caa-beta")
        self.assertEqual(res["estado"], "ok")
        self.assertEqual(_docs_resultado(res), {"doc-caa-beta"})
        self.assertEqual(_docs_paginas(res), {"doc-caa-beta"})
        self.assertNotIn("resolucion_ambito", res)

    def test_08_municipal_sin_incorporar_sin_resultados(self):
        """Caso 8: pedido municipal explícito de un municipio sin incorporar
        aunque el nombre coincida con una CCAA: sin_resultados, sin páginas ni
        resultados, y nunca otro municipio. Explicación comprobada de forma
        mínima (el texto conserva el pedido), sin fijar el mensaje exacto."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar("ordenanza municipal de territorio alamo")
        self.assertEqual(res["estado"], "sin_resultados")
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])
        # nunca otro municipio ni sustitución autonómica del pedido municipal
        self.assertNotIn("Villa Betica", res["texto_contexto"])
        self.assertNotIn("doc-muni-villa",
                         json.dumps(res["recuperacion"], ensure_ascii=False))
        self.assertIn("territorio alamo", res["texto_contexto"].lower())

    def test_09_distribute_false_no_construye_alias(self):
        """Caso 9: en __init__ real, el doc privado (distribute=False) no entra
        en docs y su metadata no genera claves de alias; jamás aparece."""
        _, ad, captura = self._montar([
            _doc_sintetico("doc-pub", jurisdiccion="Comunidad de Territorio Publico"),
            _doc_sintetico("doc-oculto", distribute=False,
                           jurisdiccion="Comunidad de Territorio Privado"),
        ])
        self.assertEqual(set(ad.docs), {"doc-pub"})
        tabla = getattr(ad, "_alias_ambito", {})  # interno pedido por el encargo
        claves = list(tabla)
        self.assertTrue(any("publico" in k for k in claves))
        self.assertFalse(any("privado" in k for k in claves))
        # la mención al nombre del privado no resuelve ámbito: búsqueda global
        # solo con lo distribuible; el oculto no existe para el adaptador
        res_priv = ad.preparar("criterios territorio privado")
        self.assertEqual(res_priv["estado"], "ok")
        self.assertEqual(_docs_resultado(res_priv), {"doc-pub"})
        res_pub = ad.preparar("criterios territorio publico")
        self.assertEqual(_docs_resultado(res_pub), {"doc-pub"})
        # el buscador REAL recibió solo lo distribuible en ambas llamadas
        # (sin depender del mock): la exclusión ocurrió en __init__
        self.assertEqual([c["docs"] for c in captura],
                         [{"doc-pub"}, {"doc-pub"}])
        self.assertEqual([c["filas"] for c in captura],
                         [["doc-pub"], ["doc-pub"]])
        self.assertEqual({f["documento"] for f in ad.filas}, {"doc-pub"})

    def test_10_municipio_conocido_con_pista_municipal_resuelve(self):
        """Caso 10 (regresión del caso 8): pista municipal con municipio
        SÍ incorporado resuelve con el conjunto completo (municipio + CCAA
        padre según metadata + nacional), no cae en sin_resultados."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar("ordenanza municipal de villa betica")
        self.assertEqual(res["estado"], "ok")
        esperado = {"doc-muni-villa", "doc-caa-alamo", "doc-nac"}
        self.assertEqual(_docs_resultado(res), esperado)
        self.assertEqual(_docs_paginas(res), esperado)

    def test_11_municipal_no_corporado_en_mayuscula_sin_fallback(self):
        """Caso 11 (regresión real): «En Villaprueba, ¿qué documentación exige
        la ordenanza municipal para una licencia?» con municipio NO incorporado
        -> sin_resultados, sin páginas, sin resultados y sin fallback a otra
        ciudad. La producción actual NO detecta «En» inicial (bug conocido:
        en|para distingue mayúsculas) y entrega búsqueda global en su lugar;
        la aserción expresa el contrato y NO se ajusta a ese bug: roja hasta
        que la corrección de recuperación aterrice."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar("En Villaprueba, ¿qué documentación exige la "
                          "ordenanza municipal para una licencia?")
        self.assertEqual(res["estado"], "sin_resultados")
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])
        # sin fallback a otra ciudad ni a otra jurisdicción (texto y JSON)
        self.assertNotIn("Villa Betica", res["texto_contexto"])
        self.assertNotIn("doc-muni-villa", res["texto_contexto"])
        self.assertNotIn("doc-muni-villa",
                         json.dumps(res["recuperacion"], ensure_ascii=False))
        self.assertNotIn("doc-caa-alamo", res["texto_contexto"])
        # la explicación conserva el lugar pedido (forma, no mensaje exacto)
        self.assertIn("villaprueba", res["texto_contexto"].lower())

    def test_12_municipal_no_corporado_minuscula_misma_abstencion(self):
        """Caso 12: variante minúscula «en Villaprueba…» -> la MISMA
        abstención del caso 11 (sin_resultados, sin páginas, sin fallback).
        Hoy es regresión verde (el patrón ya detecta «en» minúscula); tras la
        corrección mayúscula y minúscula deben abstenerse por igual."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar("en Villaprueba, ¿qué documentación exige la "
                          "ordenanza municipal para una licencia?")
        self.assertEqual(res["estado"], "sin_resultados")
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])
        self.assertNotIn("Villa Betica", res["texto_contexto"])
        self.assertNotIn("doc-muni-villa", res["texto_contexto"])
        self.assertNotIn("doc-muni-villa",
                         json.dumps(res["recuperacion"], ensure_ascii=False))
        self.assertIn("villaprueba", res["texto_contexto"].lower())

    def test_13_con_localizacion_conocida_la_nacional_se_mantiene(self):
        """Caso 13 (control del caso 11, mismo corpus): con localización
        conocida la fuente nacional —sintética, SIN jurisdiccion/municipio en
        doc.json— sigue admitida como complementaria junto a la CCAA citada;
        el conjunto es exacto y el municipio no mencionado no entra. La
        abstención del caso 11 no debe implementarse excluyendo nacionales."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar("criterios de aplicacion en territorio alamo")
        self.assertEqual(res["estado"], "ok")
        esperado = {"doc-caa-alamo", "doc-nac"}
        self.assertEqual(_docs_resultado(res), esperado)
        self.assertEqual(_docs_paginas(res), esperado)


if __name__ == "__main__":
    unittest.main()
