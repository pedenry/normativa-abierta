#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cache_http.py — caché opcional BM25 (preparado_bm25) sobre el buscador REAL.

Encargo acotado: SOLO este archivo de pruebas (sin shell, sin red, sin API, sin
corpus real). Contrato nuevo: A.preparar_bm25(cont, filas) devuelve un preparado
OPACO (una vez por corpus, antes de atender peticiones) y buscar_bm25 REAL (la
misma instancia A = F._ACC que cargó el corpus) acepta en opciones un
SimpleNamespace con max=5, presupuesto=100000, expandir=0,
documento=capa=materia=None y, OPCIONALES, preparado_bm25=<preparado> y
documentos_permitidos=<set>; encs={} siempre.

Rúbrica por caso (criterio -> aserción clave; unidad de medición: la salida
COMPLETA de buscar_bm25, dict íntegro con resultados, omitidos, advertencias,
presupuesto, terminos, ambito_capa y navegacion):
 1) IGUALDAD COMPLETA preparada==sin preparar: para varias consultas y filtros
    (documento por id y por código, capa explícita y «guias», materia en ambas
    direcciones, documentos_permitidos con subconjunto y con set() vacío), el
    dict devuelto con op.preparado_bm25 es igual al del brazo sin ese atributo
    (getattr por defecto). La preservación del IDF GLOBAL se evidencia además
    con gates: la salida con documentos_permitidos que incluye al único doc que
    casa coincide con la del brazo sin gate (el filtrado va DESPUÉS de las
    estadísticas: diseño declarado) y el gate que lo excluye da estructura
    normal (resultados=[], aviso «Sin coincidencias para los términos dados.»),
    no excepción. Nota honesta: con set() vacío la igualdad entre brazos no
    distingue IDF local de global (ambos quedan vacíos); la evidencia fuerte
    del IDF global son los subconjuntos con puntuación.
 2) REUTILIZACIÓN de la MISMA prep en llamadas sucesivas y CONCURRENTES
    (ThreadPoolExecutor, 2 trabajadores): cada resultado es igual al brazo sin
    cache de SU MISMA consulta y filtros; sin mezclar territorios (una sola
    raíz por prep), sin mezclar filtros entre casos y sin estado compartido
    por consulta; tras la fase concurrente, un brazo sin cache vuelve a
    coincidir (sin mutación persistente del corpus o del preparado).
 3) RECHAZO: usar la prep con OTRA lista filas (mismo contenido, objetos nuevos
    vía cargar_indice) u OTRA raíz (segundo corpus de contenido idéntico)
    levanta ValueError o RuntimeError, SIN fallback global; control positivo
    antes y después: la prep válida sigue en uso y sigue igualando al brazo sin
    cache (los rechazos no corrompen la prep ni el corpus original).

Corpus sintético (ayudante REAL F.PruebasEstabilidadRecuperacion()._corpus;
cada prueba instancia el suyo y conecta self.addCleanup(ayudante.doCleanups)):
2 documentos con término común «ventilacion» y términos propios («higiene» en
doc-syn-a, «estanqueidad» en doc-syn-b) + 24 documentos excluidos por los
filtros (12 capa «guias» + 12 oficiales de materia ajena) que portan el término
común para el IDF global: 27 filas indexadas. Sin mocks de ranking, sin gold,
sin páginas reales y sin IDs de documentos reales: marcadores sintéticos sin
relación con normativa.

Límites de la muestra: corpus mínimo (27 filas, una página por documento), sin
notas de tabla, multi-página, tiktoken real ni presupuesto ajustado; la igualdad
se verifica sobre las MISMAS filas (la identidad de filas es requisito del
contrato) dentro del mismo proceso. No se mide ahorro, tiempos ni umbrales de
hardware; los recuentos de texto que devuelve el motor (tokens_texto,
usado_cl100k_base) son proxy local chars/4, no tokens de API ni consumo de
proveedores, y aquí solo participan de la igualdad entre brazos. La edición, la
disposición y la página física del corpus sintético (paginas.json,
pagina/pXXXX.md, estructura.json) no son alteradas por la caché: quedan
cubiertas por la igualdad completa entre brazos; fuera de este corpus sintético
no se toca ninguna edición ni disposición real.

La preparación ajena se rechaza expresamente. Las comprobaciones comparan
ambos caminos del motor y no usan referencias normativas como respuestas fijas.

Ejecución: python test_cache_http.py -v   (desde tests/)
            python -m unittest discover -s tests -p "test_cache_http.py" -v
"""
import re
import unittest
from concurrent import futures
from types import SimpleNamespace

# Módulo completo (NO la clase TestCase) de la suite de estabilidad: aporta el
# ayudante de corpus REAL y la instancia privada REAL de acceso.py (F._ACC).
import test_estabilidad_recuperacion as F

# Instancia REAL del motor, la misma que construyó el corpus (comparte
# tokenizar/_norm/_clave_cache y sus cachés): sin mocks ni recargas paralelas.
A = F._ACC


def _filas_publicas(filas):
    """Proyección de las filas sin claves internas (_dl/_tt/_tok/_tokens_set)."""
    return [{k: v for k, v in f.items() if not k.startswith("_")} for f in filas]


class PruebasCachePreparadoBM25(unittest.TestCase):
    """Caché opcional de BM25: igualdad de salida, reutilización y rechazo."""

    # ------------------------------------------------------------ ayudantes

    def _nuevo_corpus(self):
        """Corpus sintético REAL nuevo (temporal aislado por llamada).

        2 docs con término común y términos propios + 24 docs excluidos por los
        filtros pero indexados (IDF global). Devuelve {raiz, filas, docs}.
        """
        ayudante = F.PruebasEstabilidadRecuperacion()
        self.addCleanup(ayudante.doCleanups)
        docs = [
            {"id": "doc-syn-a", "codigo": "SYN-A", "capa": "oficial",
             "materia": "ventilaciones", "title": "Doc sintetico A",
             "apartados": [
                 {"id_tecnico": "1.1", "titulo": "Apartado base higiene",
                  "texto": "Regla sintetica de ventilacion e higiene en pasillos comunes."},
                 {"id_tecnico": "1.2", "titulo": "Apartado extra higiene",
                  "texto": "Ventilacion ventilacion ventilacion con higiene declarada."}]},
            {"id": "doc-syn-b", "codigo": "SYN-B", "capa": "asociada",
             "materia": "sellados", "title": "Doc sintetico B",
             "apartados": [
                 {"id_tecnico": "1.1", "titulo": "Apartado estanqueidad",
                  "texto": "Criterio sintetico de ventilacion y estanqueidad en fachadas."}]},
        ]
        docs += [F.PruebasEstabilidadRecuperacion._extras(
            i, "guias", "gui", "Guia rellena %02d") for i in range(12)]
        docs += [F.PruebasEstabilidadRecuperacion._extras(
            i, "oficial", "aj", "Apartado ajeno %02d") for i in range(12)]
        corpus = ayudante._corpus(docs)
        self.assertEqual(len(corpus["filas"]), 27)  # los excluidos SÍ están indexados
        return corpus

    def _op(self, prep=None, **filtros):
        """Opciones según contrato: preparado_bm25/documentos_permitidos SOLO si se pasan."""
        valores = dict(max=5, presupuesto=100000, expandir=0,
                       documento=None, capa=None, materia=None)
        valores.update(filtros)
        if prep is not None:
            valores["preparado_bm25"] = prep
        return SimpleNamespace(**valores)

    def _buscar(self, corpus, consulta, op, filas=None):
        """Llamada REAL a A.buscar_bm25 con encs={} y el corte de términos de F."""
        terminos = [t for t in re.split(r"[\s,;]+", consulta) if len(t) > 1]
        return A.buscar_bm25(corpus["raiz"], corpus["filas"] if filas is None else filas,
                             corpus["docs"], consulta, terminos, op, {})

    # ------------------------------------------------------------ caso 1

    def test_salida_completa_igual_con_y_sin_preparado(self):
        """Caso 1: para cada consulta y filtro declarados, la salida COMPLETA con
        op.preparado_bm25 es igual a la del brazo sin el atributo; los gates con
        subconjunto evidencian IDF global (puntuaciones intactas) y el set()
        vacío da estructura normal, no excepción."""
        corpus = self._nuevo_corpus()
        prep = A.preparar_bm25(corpus["raiz"], corpus["filas"])
        casos = [
            ("ventilacion higiene", {}),
            ("higiene", {"documento": "doc-syn-a"}),
            ("higiene", {"documento": "SYN-A"}),      # código exacto (alias)
            ("estanqueidad", {"capa": "asociada"}),
            ("ventilacion", {"capa": "guias"}),
            ("ventilacion", {"materia": "ventilaciones"}),
            ("ventilacion", {"materia": "sellados"}),
            ("ventilacion", {"documentos_permitidos": {"doc-syn-a", "doc-syn-b"}}),
            ("ventilacion", {"documentos_permitidos": {"doc-syn-a"}}),
            ("estanqueidad", {"documentos_permitidos": {"doc-syn-b"}}),
            ("ventilacion", {"documentos_permitidos": set()}),
        ]
        for consulta, filtros in casos:
            with self.subTest(consulta=consulta, filtros=sorted(filtros)):
                con = self._buscar(corpus, consulta, self._op(prep, **filtros))
                sin = self._buscar(corpus, consulta, self._op(**filtros))
                self.assertEqual(con, sin)
        # Evidencia acotada sobre brazos reales (sin oráculos ni gold):
        # el gate que incluye al único doc que casa NO altera la salida
        # completa (filtrado después de las estadísticas: IDF global preservado).
        base = self._buscar(corpus, "estanqueidad", self._op())
        con_gate = self._buscar(corpus, "estanqueidad",
                                self._op(documentos_permitidos={"doc-syn-b"}))
        self.assertEqual(con_gate, base)
        self.assertEqual(con_gate["resultados"][0]["documento"], "doc-syn-b")
        # el gate que lo excluye: estructura normal, sin excepción ni fuga
        excluido = self._buscar(corpus, "estanqueidad",
                                self._op(documentos_permitidos={"doc-syn-a"}))
        self.assertEqual(excluido["resultados"], [])
        self.assertIn("Sin coincidencias para los términos dados.",
                      excluido["advertencias"])
        # set() vacío: nada elegible con estructura normal en ambos brazos
        vacio_con = self._buscar(corpus, "ventilacion",
                                 self._op(prep, documentos_permitidos=set()))
        self.assertEqual(vacio_con["resultados"], [])
        self.assertIn("Sin coincidencias para los términos dados.",
                      vacio_con["advertencias"])
        # el filtro por defecto sigue excluyendo las guías (la omisión es el filtro)
        defecto = self._buscar(corpus, "ventilacion", self._op())
        self.assertNotIn("doc-gui-00",
                         {r["documento"] for r in defecto["resultados"]})

    # ------------------------------------------------------------ caso 2

    def test_preparado_reutilizado_sucesivo_y_concurrente(self):
        """Caso 2: la MISMA prep en sucesivas y concurrentes (2 trabajadores);
        cada resultado es igual al brazo sin cache de su misma consulta; una
        sola raíz por prep, filtros propios por caso y sin estado residual."""
        corpus = self._nuevo_corpus()
        prep = A.preparar_bm25(corpus["raiz"], corpus["filas"])
        casos = [
            ("ventilacion higiene", {}),
            ("higiene", {"documento": "doc-syn-a"}),
            ("ventilacion", {"materia": "sellados"}),
            ("estanqueidad", {"documentos_permitidos": {"doc-syn-b"}}),
        ]
        esperados = [self._buscar(corpus, c, self._op(**f)) for c, f in casos]
        # sucesivas: cada consulta SOLO con sus filtros, misma prep compartida
        for i, (consulta, filtros) in enumerate(casos):
            self.assertEqual(
                self._buscar(corpus, consulta, self._op(prep, **filtros)),
                esperados[i], msg="sucesiva %d" % i)
        # concurrentes: 2 trabajadores sobre la MISMA prep (solo lectura)
        with futures.ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [pool.submit(self._buscar, corpus, c, self._op(prep, **f))
                       for c, f in casos]
        for i, futuro in enumerate(futuros):
            self.assertEqual(futuro.result(), esperados[i],
                             msg="concurrente %d" % i)
        # sin estado residual: un brazo sin cache tras la fase concurrente iguala
        self.assertEqual(self._buscar(corpus, casos[0][0], self._op(**casos[0][1])),
                         esperados[0])

    # ------------------------------------------------------------ caso 3

    def test_rechazo_preparado_de_otras_filas_o_raiz(self):
        """Caso 3 (contrato nuevo): prep ajena a las filas (contenido idéntico,
        objetos nuevos) o a la raíz (segundo corpus idéntico) levanta
        ValueError/RuntimeError sin fallback global; la prep válida sigue en uso
        antes y después de los rechazos."""
        corpus = self._nuevo_corpus()
        prep = A.preparar_bm25(corpus["raiz"], corpus["filas"])
        # control positivo: prep válida == brazo sin cache
        self.assertEqual(self._buscar(corpus, "higiene", self._op(prep)),
                         self._buscar(corpus, "higiene", self._op()))
        # otra lista filas: mismo contenido, objetos nuevos -> rechazo
        filas_otras = A.cargar_indice(corpus["raiz"])
        self.assertEqual(_filas_publicas(filas_otras),
                         _filas_publicas(corpus["filas"]))
        self.assertIsNot(filas_otras[0], corpus["filas"][0])
        with self.assertRaises((ValueError, RuntimeError)):
            self._buscar(corpus, "higiene", self._op(prep), filas=filas_otras)
        # otra raíz: segundo corpus de contenido idéntico -> rechazo
        corpus_b = self._nuevo_corpus()
        self.assertEqual(_filas_publicas(corpus_b["filas"]),
                         _filas_publicas(corpus["filas"]))
        with self.assertRaises((ValueError, RuntimeError)):
            self._buscar(corpus_b, "higiene", self._op(prep))
        # la prep válida no quedó corrompida: sigue igualando al brazo sin cache
        self.assertEqual(self._buscar(corpus, "higiene", self._op(prep)),
                         self._buscar(corpus, "higiene", self._op()))


if __name__ == "__main__":
    unittest.main()
