#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unittest del contrato de ACLARACIÓN por falta de ubicación en AdaptadorContexto.

Encargo acotado (evaluación-normativa, 2026-11-16): contrato objetivo acordado con la
producción (encargada a otro especialista). 10 pruebas sintéticas, import aislado como
test_ambito.py (acceso.py y adaptador_contexto.py cargados por ruta en instancias
privadas, sin contaminar sys.modules):

 1) territorial sin lugar ACLARA: consulta del encargo sin ciudad/CCAA/doc/edición ->
    estado aclaracion_necesaria, sin páginas ni resultados.
 2) nacionales técnicas NO aclara: consulta técnica tipo SUA/REBT -> estado ok con
    resultados; nunca clave aclaración.
 3) 'suelo' técnico (humedad / cableado eléctrico bajo el suelo) NO es falso positivo:
    el disparador de aclaración no puede ser la mera presencia de «suelo».
 4) documento explícito: PRECEDENCIA — con documento pedido, la consulta sin lugar
    responde el documento y no aclara; sin inferencia de ámbito (sin resolucion_ambito).
 5) territorio ya especificado (CCAA o municipio): no aclara, responde.
 6) la respuesta de aclaración NO llama BM25 ni filtra documentos (simulación con
    captura): el buscador parcheado no recibe ninguna llamada y las filas globales
    quedan intactas.
 7) estado serializable con pregunta/campos/presupuesto: json.dumps completo,
    pregunta y campos_requeridos válidos, presupuesto respetado (excedido False,
    tokens_contexto dentro del presupuesto).
 8) campos_requeridos subconjunto específico: consulta de ámbito autonómico pide
    SOLO campos dentro de {comunidad_autonoma} (no municipio).
 9) campos_requeridos para consultas «ambos»: subconjunto no vacío de
    {comunidad_autonoma, municipio}.
10) la aclaración NO inventa territorio: pregunta/contexto sin ningún nombre
    territorial del corpus (jurisdiccion/municipio sintéticos del doc.json).
11) campos por tipo de consulta (revisión del contrato de evaluación, rúbrica v2 de
    evaluación: IGUALDAD de campos, no subconjunto): «estatal y autonómica …
    clasificación del suelo» aclara SOLO CA (no asume respuesta estatal sola);
    «cesión de aprovechamiento … ayuntamiento» aclara SOLO CA (el ayuntamiento es
    receptor de la cesión, no el lugar consultado: SIN municipio adicional);
    «marco normativo … licencia de obras» aclara AMBOS (CA+municipio).

Las aserciones expresan el CONTRATO OBJETIVO, no el comportamiento actual: la
producción actual aún no emite aclaracion_necesaria, así que los casos 1, 6, 7, 8, 9,
10 y 11 están ROJOS hasta que la corrección aterrice; los casos 2, 3, 4 y 5 son verdes
hoy y deben seguirlo (guarda contra falsos positivos y precedencia). No se ajusta
ninguna expectativa al bug.

Corpus SINTÉTICO temporal mínimo (misma forma de test_ambito.py):
indice/apartados.jsonl, doc.json con jurisdiccion/municipio sintéticos, estructura.json,
paginas.json, pagina/p0001.md y apartado/p0001.md. Sin normativa real, sin red, sin
modelos; los nombres de territorio son marcadores sintéticos de este test (no del corpus
real, sin valor de referencia/gold). La fuente NACIONAL sintética declara
jurisdiccion=None y municipio=None, como el corpus nacional real.

Mocks solo donde la lógica evaluada no está (misma disciplina que test_ambito.py):
crear_contadores (encs={} -> modo aproximacion_caracteres_4, recuento determinista),
buscar_bm25 (candidatos por documentos REALMENTE recibidos, con captura de llamadas y de
los filtros documento/documentos_permitidos como los aplicaría el motor) y
construir_lectura (abre las páginas del temporal). NO se parchean cargar_indice,
cargar_docs ni el filtrado distribute de __init__: carga real de fixtures. Límite
declarado: el parche de buscar_bm25 asume la firma actual de acceso.py (op.documento,
op.documentos_permitidos); si la corrección altera esa interfaz, se adapta el parche, no
el contrato.

Recuento y límites: tokens_contexto en modo aproximacion_caracteres_4 es un proxy local
de texto (chars/4), no tokens de API; no hay usage de API ni desglose entrada/salida/
caché. Sin corpus real ni pares comparables no se calcula ahorro. Cobertura del BM25
real y de tiktoken fuera del encargo. No se ejecutan procesos externos: la batería corre
en unittest.
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
_ACC = _cargar_modulo_privado("_acc_priv_test_aclaracion", RAIZ / "acceso.py")


def _cargar_adaptador_aislado():
    """Carga adaptador_contexto.py resolviendo `import acceso` a la instancia privada."""
    anterior = sys.modules.get("acceso")
    sys.modules["acceso"] = _ACC
    try:
        return _cargar_modulo_privado(
            "_adaptador_priv_test_aclaracion", RAIZ / "adaptador_contexto.py")
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

    Los nombres de territorio (jurisdiccion/municipio) son marcadores sintéticos de
    este test: ninguno pertenece al corpus real ni al vocabulario administrativo
    español real.
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


# Namespaces sintéticos de territorio (metadata, no gold; sin corpus real).
_JUR_ALFA = "Comunidad de Territorio Álamo"
_JUR_BETA = "Comunidad de Territorio Beta"
_MUN_VILLA = "Villa Betica"

# Consultas EXACTAS del fixture casos-sin-ubicacion.json (encargo 2026-11-16).
_Q_SIN_LUGAR_DOC = "¿Qué documentación debo presentar para solicitar una licencia de obras?"
_Q_CCAA = "¿Cuándo se considera suelo urbano consolidado y cuándo no consolidado?"
_Q_AMBOS = "¿En qué momento se considera iniciado el procedimiento de solicitud de licencia urbanística?"
_Q_LOCAL = "Quiero abrir un local: ¿licencia de actividad o declaración responsable?"
_Q_NACIONAL = "Pendiente transversal máxima de rampas en itinerario accesible"
_Q_HUMEDAD = "¿Cómo se protege de la humedad el suelo de la vivienda?"
_Q_ELECTRICO = "¿Dónde debe ir embutido el cableado eléctrico bajo el suelo?"
# Subcasos de la revisión del contrato de evaluación (rúbrica v2: IGUALDAD de campos).
_Q_ESTATAL_AUTONOMICA = ("¿Qué normativa estatal y autonómica se aplica a la "
                         "clasificación del suelo?")
_Q_CESION = "¿Qué porcentaje de cesión de aprovechamiento corresponde al ayuntamiento?"
_Q_MARCO_LICENCIA = "¿Qué marco normativo regula la tramitación de una licencia de obras?"
# Segunda tanda del mismo encargo (2026-11-16): relación/conexión y escala estatal.
_Q_RELACION = "Qué elementos conecta el colector de retorno de un circuito hidráulico"
_Q_RELACION_TERRITORIO = ("¿Qué elementos conecta el colector de retorno de un "
                          "circuito hidráulico en territorio álamo?")
_Q_ESTADO_LICENCIA = "¿Qué normativa regula el estado de mi licencia de obras?"
_Q_NORMA_ESTADO = "¿Qué norma del Estado regula las situaciones básicas del suelo?"


def _normalizar(texto):
    import unicodedata
    plano = unicodedata.normalize("NFKD", str(texto or ""))
    plano = "".join(c for c in plano if not unicodedata.combining(c)).casefold()
    return plano


def _docs_resultado(res):
    """Documentos presentes en los resultados del buscador (efecto observable)."""
    return {r["documento"] for r in res["recuperacion"]["resultados"]}


class PruebasAclaracionSinUbicacion(unittest.TestCase):
    """Carga real de fixtures (índice/doc.json/distribute) con buscador, lectura y
    contadores parcheados; un corpus temporal por prueba; captura de llamadas BM25."""

    # ------------------------------------------------------------- corpus

    def _corpus_sintetico(self, docs):
        """Escribe un corpus temporal mínimo y devuelve {raiz, docs}."""
        tmp = tempfile.mkdtemp(prefix="aclaracion-sin-ubicacion-")
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
        candidato solo por documentos REALMENTE recibidos y aplica documento
        explícito y documentos_permitidos como haría el motor; toda llamada queda
        capturada para poder afirmar que la aclaración no busca ni filtra.
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

    def test_01_territorial_sin_lugar_aclara(self):
        """Caso 1 (CONTRATO, rojo hasta que la corrección aterrice): consulta del
        encargo sin ciudad/CCAA/doc/edición -> estado aclaracion_necesaria con
        aclaración no vacía y CERO páginas/resultados (una aclaración que entrega
        páginas o responde ok no es acierto)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar(_Q_SIN_LUGAR_DOC)
        self.assertEqual(res["estado"], "aclaracion_necesaria")
        acl = res.get("aclaracion")
        self.assertIsInstance(acl, dict)
        self.assertIsInstance(acl.get("pregunta"), str)
        self.assertTrue(acl.get("pregunta", "").strip())
        campos = acl.get("campos_requeridos")
        self.assertIsInstance(campos, list)
        self.assertTrue(campos)
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])

    def test_02_nacional_tecnico_no_aclara(self):
        """Caso 2 (guarda, verde hoy): consulta técnica nacional (sin documento ni
        lugar en su texto) NO dispara aclaración: estado ok con resultados."""
        _, ad, _ = self._montar([_doc_sintetico("doc-nac")])
        res = ad.preparar(_Q_NACIONAL, None, None, 20000, 2)
        self.assertEqual(res["estado"], "ok")
        self.assertFalse(res.get("aclaracion"))
        self.assertTrue(res["recuperacion"]["resultados"])

    def test_03_suelo_tecnico_sin_falso_positivo(self):
        """Caso 3 (guarda, verde hoy): «suelo de la vivienda» (humedad) y «cableado
        eléctrico bajo el suelo» contienen la palabra «suelo» pero son consultas
        técnicas: NO falso positivo de aclaración; se busca y se responde ok."""
        _, ad, _ = self._montar([_doc_sintetico("doc-nac")])
        for consulta in (_Q_HUMEDAD, _Q_ELECTRICO):
            res = ad.preparar(consulta, None, None, 20000, 2)
            self.assertEqual(res["estado"], "ok", consulta)
            self.assertFalse(res.get("aclaracion"), consulta)
            self.assertTrue(res["recuperacion"]["resultados"], consulta)

    def test_04_documento_explicito_precedencia(self):
        """Caso 4 (guarda, verde hoy): con documento explícito, la consulta sin lugar
        responde SOLO el documento pedido; sin aclaración y sin inferencia de ámbito
        (sin resolucion_ambito)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar(_Q_SIN_LUGAR_DOC, documento="doc-nac")
        self.assertEqual(res["estado"], "ok")
        self.assertEqual(_docs_resultado(res), {"doc-nac"})
        self.assertFalse(res.get("aclaracion"))
        self.assertNotIn("resolucion_ambito", res)

    def test_05_territorio_ya_especificado_no_aclara(self):
        """Caso 5 (guarda, verde hoy): con CCAA o municipio ya especificado en la
        consulta NO hay aclaración: se responde con el conjunto de ámbito propio
        (CCAA + nacionales; municipio + CCAA padre + nacionales)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res_caa = ad.preparar("criterios de aplicacion en territorio alamo")
        self.assertEqual(res_caa["estado"], "ok")
        self.assertFalse(res_caa.get("aclaracion"))
        self.assertIn("doc-caa-alamo", _docs_resultado(res_caa))
        res_mun = ad.preparar("ordenanza municipal de villa betica")
        self.assertEqual(res_mun["estado"], "ok")
        self.assertFalse(res_mun.get("aclaracion"))
        self.assertIn("doc-muni-villa", _docs_resultado(res_mun))

    def test_06_aclaracion_no_llama_bm25_ni_filtra(self):
        """Caso 6 (CONTRATO, rojo hasta la corrección): la respuesta de aclaración NO
        llama al buscador (captura vacía) y NO filtra documentos: las filas globales
        del adaptador quedan intactas y no se entrega ningún resultado ni página."""
        _, ad, captura = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar(_Q_SIN_LUGAR_DOC, None, None, 20000, 2)
        self.assertEqual(res["estado"], "aclaracion_necesaria")
        # BM25 jamás fue invocado para esta consulta (captura vacía)
        self.assertEqual(captura, [])
        # nada entregado
        self.assertEqual(res["paginas"], [])
        self.assertEqual(res["recuperacion"]["resultados"], [])
        # sin filtrado de documentos: la carga global sigue completa
        self.assertEqual(set(ad.docs),
                         {"doc-nac", "doc-caa-alamo", "doc-muni-villa"})
        self.assertEqual({f["documento"] for f in ad.filas},
                         {"doc-nac", "doc-caa-alamo", "doc-muni-villa"})

    def test_07_estado_serializable_pregunta_campos_presupuesto(self):
        """Caso 7 (CONTRATO, rojo hasta la corrección): la respuesta de aclaración es
        JSON-serializable completa, con pregunta (cadena no vacía), campos_requeridos
        (lista de cadenas) y presupuesto respetado (excedido False y
        tokens_contexto dentro del presupuesto con presupuesto reducido)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
        ])
        res = ad.preparar(_Q_AMBOS, None, None, 500, 2)
        json.dumps(res, ensure_ascii=False)  # serializable, no lanza
        self.assertEqual(res["estado"], "aclaracion_necesaria")
        acl = res["aclaracion"]
        self.assertIsInstance(acl.get("pregunta"), str)
        self.assertTrue(acl.get("pregunta", "").strip())
        campos = acl.get("campos_requeridos")
        self.assertIsInstance(campos, list)
        self.assertTrue(all(isinstance(x, str) for x in campos))
        self.assertTrue(campos)
        self.assertIs(res.get("excedido"), False)
        tokens = res.get("tokens_contexto")
        if tokens is not None:
            self.assertIsInstance(tokens, int)
            self.assertLessEqual(tokens, 500)

    def test_08_campos_solo_comunidad_autonoma(self):
        """Caso 8 (CONTRATO, rojo hasta la corrección): consulta cuyo único campo
        requerido por contrato es la CCAA -> campos_requeridos subconjunto NO vacío
        de {comunidad_autonoma}; no pide municipio ni otros campos."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
        ])
        res = ad.preparar(_Q_CCAA, None, None, 20000, 2)
        self.assertEqual(res["estado"], "aclaracion_necesaria")
        campos = res["aclaracion"]["campos_requeridos"]
        self.assertTrue(campos)
        self.assertTrue(set(campos) <= {"comunidad_autonoma"},
                        "campos fuera de contrato: %r" % campos)
        self.assertNotIn("municipio", campos)

    def test_09_campos_ambos_subconjunto(self):
        """Caso 9 (CONTRATO, rojo hasta la corrección): consulta «ambos» -> campos
        subconjunto NO vacío de {comunidad_autonoma, municipio}; ningún campo fuera
        del vocabulario territorial (p. ej. provincia, documento, barrio)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar(_Q_AMBOS, None, None, 20000, 2)
        self.assertEqual(res["estado"], "aclaracion_necesaria")
        campos = res["aclaracion"]["campos_requeridos"]
        self.assertTrue(campos)
        self.assertTrue(set(campos) <= {"comunidad_autonoma", "municipio"},
                        "campos fuera de contrato: %r" % campos)

    def test_10_aclaracion_no_inventa_territorio(self):
        """Caso 10 (CONTRATO, rojo hasta la corrección): la aclaración PREGUNTA el
        lugar, no lo rellena: ni la pregunta ni el texto de contexto contienen
        ningún nombre territorial del corpus (sintético: CCAA alfa/beta, municipio)."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        res = ad.preparar(_Q_LOCAL, None, None, 20000, 2)
        self.assertEqual(res["estado"], "aclaracion_necesaria")
        texto = _normalizar(res["aclaracion"].get("pregunta")) + "\n" \
            + _normalizar(res.get("texto_contexto"))
        for nombre in (_JUR_ALFA, _JUR_BETA, _MUN_VILLA):
            self.assertNotIn(_normalizar(nombre), texto,
                             "la aclaracion inventa el territorio %r" % nombre)
        self.assertEqual(res["paginas"], [])

    def test_11_campos_requeridos_por_tipo_de_consulta(self):
        """Caso 11 (CONTRATO, rojo hasta la corrección; rúbrica v2 de evaluación:
        IGUALDAD de campos, no subconjunto). Tres subcasos de la revisión:
        a) «¿Qué normativa estatal y autonómica se aplica a la clasificación del
           suelo?» aclara SOLO CA: no puede asumir respuesta estatal sola ni
           devolver páginas;
        b) «¿Qué porcentaje de cesión de aprovechamiento corresponde al
           ayuntamiento?» aclara SOLO CA: el ayuntamiento es el RECEPTOR de la
           cesión, no el lugar consultado; la regla es autonómica y NO pide
           municipio adicional;
        c) «¿Qué marco normativo regula la tramitación de una licencia de obras?»
           aclara AMBOS (comunidad_autonoma + municipio).
        Cada aclaración: pregunta no vacía, campos sin duplicados, cero páginas y
        cero resultados."""
        _, ad, _ = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        subcasos = (
            (_Q_ESTATAL_AUTONOMICA, {"comunidad_autonoma"}),
            (_Q_CESION, {"comunidad_autonoma"}),
            (_Q_MARCO_LICENCIA, {"comunidad_autonoma", "municipio"}),
        )
        for consulta, campos_esp in subcasos:
            res = ad.preparar(consulta, None, None, 20000, 2)
            self.assertEqual(res["estado"], "aclaracion_necesaria", consulta)
            acl = res.get("aclaracion")
            self.assertIsInstance(acl, dict, consulta)
            self.assertTrue(str(acl.get("pregunta") or "").strip(), consulta)
            campos = acl.get("campos_requeridos")
            self.assertIsInstance(campos, list, consulta)
            # IGUALDAD v2: todos los campos requeridos, sin extras ni duplicados
            self.assertEqual(len(campos), len(set(campos)),
                             "duplicados en %r (%s)" % (campos, consulta))
            self.assertEqual(set(campos), campos_esp,
                             "%s -> campos %r != %r"
                             % (consulta, campos, sorted(campos_esp)))
            self.assertEqual(res["paginas"], [], consulta)
            self.assertEqual(res["recuperacion"]["resultados"], [], consulta)

    def test_12_relacion_vista_enfocada_doc_y_territorio(self):
        """Caso 12 (CONTRATO): relación de OTRA entidad (entidad sintética,
        sin LGA ni IDs reales). Automática (sin documento ni ubicación):
        BM25 recibe la vista enfocada «…colector de retorno», la consulta
        original se conserva y se exponen vista_busqueda y traza. Con
        documento explícito NO enfoca. Con territorio resuelto SOLO opera
        la vista geográfica existente (cola contextual conservada)."""
        vista_esp = "Qué elementos conecta el colector de retorno"
        _, ad, captura = self._montar([
            _doc_sintetico("doc-nac"),
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        consultas_bm25 = []
        previa = _ACC.buscar_bm25

        def con_consulta(contenido, filas, documentos, consulta, terminos,
                         op, encs):
            consultas_bm25.append(consulta)
            return previa(contenido, filas, documentos, consulta, terminos,
                          op, encs)

        envol = mock.patch.object(_ACC, "buscar_bm25", con_consulta)
        envol.start()
        self.addCleanup(envol.stop)
        # a) automática: vista enfocada al buscador, original conservada
        res = ad.preparar(_Q_RELACION)
        self.assertEqual(res["estado"], "ok")
        self.assertEqual(consultas_bm25[-1], vista_esp)
        self.assertEqual(res["consulta"], _Q_RELACION)
        self.assertEqual(res["vista_busqueda"], vista_esp)
        self.assertTrue(any(vista_esp in a
                            for a in res["recuperacion"]["advertencias"]))
        self.assertNotIn("resolucion_ambito", res)
        # b) documento explícito: precedencia, sin enfoque
        res_doc = ad.preparar(_Q_RELACION, documento="doc-nac")
        self.assertEqual(res_doc["estado"], "ok")
        self.assertEqual(consultas_bm25[-1], _Q_RELACION)
        self.assertEqual(_docs_resultado(res_doc), {"doc-nac"})
        self.assertNotIn("vista_busqueda", res_doc)
        # c) territorio resuelto: solo vista geográfica, cola contextual intacta
        res_ter = ad.preparar(_Q_RELACION_TERRITORIO)
        self.assertEqual(res_ter["estado"], "ok")
        self.assertEqual(res_ter["resolucion_ambito"]["estado"], "resuelto")
        self.assertEqual(consultas_bm25[-1],
                         "¿Qué elementos conecta el colector de retorno "
                         "de un circuito hidráulico")
        self.assertNotIn("vista_busqueda", res_ter)
        self.assertEqual(captura[-1]["perm"], {"doc-nac", "doc-caa-alamo"})

    def test_13_estatal_explicito_corpus_solo_autonomico(self):
        """Caso 13 (CONTRATO): corpus SOLO autonómico/municipal (ninguna
        fuente nacional). «¿Qué norma del Estado …?» (escala explícita +
        lexema normativo): op.documentos_permitidos capturado == set()
        (nunca None), cero resultados del buscador mock y API
        sin_resultados: sin fuentes y sin fallback a las autonómicas
        disponibles. Subcasos de territorial sin lugar: «estado de mi
        licencia» = TRÁMITE aclara AMBOS sin BM25; «norma del Estado» NO."""
        _, ad, captura = self._montar([
            _doc_sintetico("doc-caa-alamo", jurisdiccion=_JUR_ALFA),
            _doc_sintetico("doc-caa-beta", jurisdiccion=_JUR_BETA),
            _doc_sintetico("doc-muni-villa", jurisdiccion=_JUR_ALFA,
                           municipio=_MUN_VILLA),
        ])
        # «estado de mi licencia»: trámite, no escala -> aclara ambos
        res_lic = ad.preparar(_Q_ESTADO_LICENCIA, None, None, 20000, 2)
        self.assertEqual(res_lic["estado"], "aclaracion_necesaria")
        self.assertEqual(set(res_lic["aclaracion"]["campos_requeridos"]),
                         {"comunidad_autonoma", "municipio"})
        self.assertEqual(captura, [])
        # «norma del Estado»: escala explícita -> no aclara, sin fallback
        res_est = ad.preparar(_Q_NORMA_ESTADO, None, None, 20000, 2)
        self.assertEqual(res_est["estado"], "sin_resultados")
        self.assertEqual(len(captura), 1)
        self.assertEqual(captura[0]["perm"], set())
        self.assertEqual(captura[0]["doc_id"], None)
        self.assertIn("doc-caa-alamo", captura[0]["docs"])
        self.assertEqual(res_est["recuperacion"]["resultados"], [])
        self.assertEqual(res_est["paginas"], [])
        self.assertNotIn("resolucion_ambito", res_est)

    def test_14_estatal_conceptual_seleccion_frase(self):
        """Caso 14 (CONTRATO, rojo hasta la corrección): petición estatal EXCLUSIVA
        conceptual sin documento ni ubicación (entidad sintética nueva, sin
        fixtures20); BM25 mock vacío para no medir BM25: la única evidencia de
        enrutado es la captura de op.documentos_permitidos y de la consulta que
        llegan al buscador. El selector REAL del adaptador lee textos: debe
        entrar sólo nacionalA (frase literal «categorías técnicas del producto»
        en texto/página), con consulta enfocada al concepto, consulta original
        conservada y vista trazada; el autonómico con la misma frase queda fuera
        por la escala y el nacional con palabras dispersas, sin frase, no entra.
        Con 0 coincidencias de la frase, los nacionales quedan enteros (sin
        aclaración ni localización inventada)."""
        frase = "categorías técnicas del producto"
        q_estatal = ("¿Cuáles son las categorías técnicas del producto que "
                     "define la legislación estatal?")
        q_ausente = ("¿Cuáles son las plazas mínimas de estacionamiento que "
                     "define la legislación estatal?")
        c_frase = "El marco estatal sintético define %s de la entidad nueva." % frase
        c_disperso = ("Toda categoría de obra exige técnicas propias y el producto "
                      "final se describe por separado.")
        d_a, d_b = _doc_sintetico("nac-prod-a"), _doc_sintetico("nac-prod-b")
        d_c = _doc_sintetico("caa-prod-c", jurisdiccion=_JUR_ALFA)
        for d, texto in ((d_a, c_frase), (d_b, c_disperso), (d_c, c_frase)):
            d["paginas_texto"] = {1: texto}
            d["apartados"][0]["texto"] = texto
        _, ad, _ = self._montar([d_a, d_b, d_c])
        llamadas = []

        def bm25_vacio(_c, _f, _d, consulta, terminos, op, _e):
            perm = getattr(op, "documentos_permitidos", None)
            llamadas.append({"doc_id": getattr(op, "documento", None),
                             "perm": None if perm is None else set(perm),
                             "consulta": consulta})
            return {"resultados": [], "omitidos": [], "advertencias": [],
                    "terminos": list(terminos), "ambito_capa": "oficial+asociada"}

        envol = mock.patch.object(_ACC, "buscar_bm25", bm25_vacio)
        envol.start()
        self.addCleanup(envol.stop)
        # a) frase presente: sólo nacionalA entra por la frase literal del concepto
        res = ad.preparar(q_estatal, None, None, 20000, 2)
        self.assertEqual(res["estado"], "sin_resultados")
        self.assertTrue(llamadas, "el buscador no fue invocado")
        for l in llamadas:
            self.assertEqual(l["doc_id"], None, l)
            self.assertEqual(l["perm"], {"nac-prod-a"}, l)
            self.assertEqual(l["consulta"], frase, l)
        self.assertEqual(res["consulta"], q_estatal)
        self.assertEqual(res.get("vista_busqueda"), frase)
        self.assertTrue(any(frase in a for a in res["recuperacion"]["advertencias"]))
        self.assertNotIn("resolucion_ambito", res)
        self.assertFalse(res.get("aclaracion"))
        # b) 0 coincidencias de la frase: los nacionales quedan enteros; sin
        #    aclaración ni localización inventada; el autonómico sigue fuera
        base = len(llamadas)
        res_b = ad.preparar(q_ausente, None, None, 20000, 2)
        ventana = llamadas[base:]
        self.assertEqual(res_b["estado"], "sin_resultados")
        self.assertTrue(ventana, "el buscador no fue invocado")
        for l in ventana:
            self.assertEqual(l["doc_id"], None, l)
            self.assertEqual(l["perm"], {"nac-prod-a", "nac-prod-b"}, l)
        self.assertNotIn("resolucion_ambito", res_b)
        self.assertFalse(res_b.get("aclaracion"))
        self.assertEqual(res_b["consulta"], q_ausente)


if __name__ == "__main__":
    unittest.main()
