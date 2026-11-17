#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cache_paginas_http.py — equivalencia del precalc BM25 de páginas/notas
(preparar_bm25 «paginas_notas») frente a la rama por petición de _bm25.

Encargo acotado: SOLO este archivo de prueba. Sin producción, sin tocar
acceso.py ni otros archivos, sin shell, sin API, sin red y sin corpus real:
corpus sintético mínimo en temporal aislado vía test_estabilidad_recuperacion
(ayudante real, sin parches); A = F._ACC es el motor REAL.

Dos brazos con el MISMO objetivo y condiciones verificadas idénticas (mismo
corpus, filas, consulta, terminos y filtros), solo cambia el arranque BM25:
 - legacy: opciones SIN el atributo preparado_bm25 (getattr -> None): _bm25
   tokeniza, cuenta TF, norm() y tokeniza títulos por petición, sobre los
   objetos de cargar_paginas/cargar_notas (cachés del propio motor).
 - preparado: opciones con preparado_bm25=prep, siendo prep =
   A.preparar_bm25(raiz, filas), que precalcula también páginas/notas
   («paginas_notas») que _bm25 consume por identidad de objeto («obj» is p)
   sin alterar filtros, scores ni orden.

Rúbrica por caso (subTest consulta x filtro x salida):
 1) EQUIVALENCIA paginas (proyección): [(puntuación, documento, página
    física, texto íntegro)] idénticos en orden, floats incluidos, entre
    brazos. Igualdad exacta (mismo motor, mismos objetos y fórmula); no hay
    valores absolutos esperados ni tolerancias.
 2) EQUIVALENCIA notas (proyección): ídem añadiendo el número de nota
    (numero); el texto de nota es el literal reconstruido por el motor.
 3) EQUIVALENCIA salida completa: además de la proyección, la lista de pares
    (score, objeto) devuelta por A.buscar_paginas / A.buscar_notas es igual
    en ambos brazos (IDs y textos comparados también de forma integral).
 4) EXCEPCIÓN de no-tautología: en el caso sin filtro con 'ventilacion 103',
    las páginas y las notas del brazo legacy deben ser NO VACÍAS (referencia
    independiente del precalc); la igualdad así compara contenido real y no
    dos vacíos.
 5) EDICIÓN/DISPOSICIÓN/PÁGINA FÍSICA: no se reescribe ni recorta texto: la
    proyección incluye el texto íntegro de la página física (pagina) y el
    texto de la nota tal como el motor lo reconstruye; el objeto devuelto es
    el del índice auxiliar con sus metadatos intactos (incluido el sha256 que
    cargar_paginas toma de doc.json): sin reedición, sin sustitución de
    edición y sin páginas sintéticas ajenas.

Límites de la muestra: 2 documentos sintéticos (1 página y 2 notas por doc),
4 combinaciones de filtro (sinfiltro, doc-a, capa todas, materia-a) y 2
consultas ('ventilacion 103', 'marcador'); el doc B usa otros términos, otra
capa (asociada) y otra materia para variar DF: el df/N/avg de _bm25 se
calculan sobre la lista recibida tras filtros, por igual en ambos brazos, de
modo que cada subTest compara la MISMA colección (la invariancia entre
colecciones distintas NO se exige, es diseño declarado del IDF global). Sin
corpus real y sin medición de consumo: no hay recuento de tokens (si se
contara, sería proxy local de texto, no tokens de API ni gasto). No se
presumen campos internos de prep ni valores absolutos: solo igualdad entre
brazos y la no-vacuidad marcada. Estado: el precalc de páginas/notas se
completaba en paralelo; si el brazo preparado falla con ValueError
(«preparado BM25 de paginas/notas ausente o invalido»), eso es evidencia de
precalc ausente o invalido, no de equivalencia rota; el resto se ejecuta
igual y el fallo queda registrado por subTest.

Ejecución: python test_cache_paginas_http.py -v   (desde tests/)
            python -m unittest discover -s tests -p "test_cache_paginas_http.py" -v
"""
import re
import unittest
from types import SimpleNamespace

import test_estabilidad_recuperacion as F

A = F._ACC  # motor real (la misma instancia privada que usa la suite entera)


def _terminos(consulta):
    """Términos crudos como los pasa la suite de estabilidad (len>1)."""
    return [t for t in re.split(r"[\s,;]+", consulta) if len(t) > 1]


def _vista_paginas(pares):
    """Proyección comparable: (puntuación, documento, página física, texto)."""
    return [(s, p["documento"], p["pagina"], p["texto"]) for s, p in pares]


def _vista_notas(pares):
    """Proyección comparable: (puntuación, documento, página, número, texto)."""
    return [(s, n["documento"], n["pagina"], n["numero"], n["texto"])
            for s, n in pares]


class PruebasCachePaginasHttp(unittest.TestCase):
    """Equivalencia del precalc de paginas/notas frente a la rama legacy."""

    def test_equivalencia_paginas_notas_con_preparado_bm25(self):
        """Mismos filtros y consulta: la salida completa de buscar_paginas y
        buscar_notas (floats, orden, IDs y textos) es igual con y sin el
        precalc de preparar_bm25; el caso sin filtro con 'ventilacion 103'
        devuelve páginas y notas no vacías en el brazo legacy."""
        docs = [
            {
                "id": "doc-a", "codigo": "SIN-CA", "capa": "oficial",
                "materia": "materia-a", "title": "Doc cache paginas A",
                "paginas": {1: "\n".join([
                    "Ventilacion 103",
                    "Marcador de pagina del documento A.",
                    "(1) Ventilacion nota 103 explicativa",
                    "(2) Marcador de nota del documento A.",
                ]) + "\n"},
                "apartados": [{
                    "id_tecnico": "1.1", "titulo": "Apartado A",
                    "texto": "Texto de apartado sintetico con Ventilacion 103 "
                             "y marcador del documento A.",
                    "paginas": [1],
                }],
            },
            {
                "id": "doc-b", "codigo": "SIN-CB", "capa": "asociada",
                "materia": "materia-b", "title": "Doc cache paginas B",
                "paginas": {1: "\n".join([
                    "Climatizacion 205",
                    "Marcador de pagina del documento B.",
                    "(1) Climatizacion nota 205 diversa",
                    "(2) Marcador de nota del documento B.",
                ]) + "\n"},
                "apartados": [{
                    "id_tecnico": "1.1", "titulo": "Apartado B",
                    "texto": "Texto de apartado sintetico con Climatizacion 205 "
                             "y marcador del documento B.",
                    "paginas": [1],
                }],
            },
        ]
        ayudante = F.PruebasEstabilidadRecuperacion()
        self.addCleanup(ayudante.doCleanups)
        corpus = ayudante._corpus(docs)
        raiz, filas = corpus["raiz"], corpus["filas"]
        # Premisas del corpus (identidad declarada, no valores esperados):
        self.assertEqual({f["documento"] for f in filas}, {"doc-a", "doc-b"})
        self.assertEqual({f["capa"] for f in filas}, {"oficial", "asociada"})
        self.assertEqual({f["materia"] for f in filas},
                         {"materia-a", "materia-b"})
        prep = A.preparar_bm25(raiz, filas)
        filtros = [
            ("sinfiltro", {"documento": None, "capa": None, "materia": None}),
            ("doca", {"documento": "doc-a", "capa": None, "materia": None}),
            ("capatodas", {"documento": None, "capa": "todas", "materia": None}),
            ("materiaa", {"documento": None, "capa": None, "materia": "materia-a"}),
        ]
        for consulta in ("ventilacion 103", "marcador"):
            terminos = _terminos(consulta)
            for nombre, filt in filtros:
                # Brazo legacy: SIN el atributo preparado_bm25 (getattr->None).
                sin = SimpleNamespace(documento=filt["documento"],
                                      capa=filt["capa"], materia=filt["materia"])
                # Brazo preparado: mismas condiciones + prep de arranque.
                con = SimpleNamespace(preparado_bm25=prep,
                                      documento=filt["documento"],
                                      capa=filt["capa"], materia=filt["materia"])
                pag_legado = A.buscar_paginas(raiz, filas, consulta, terminos, sin)
                notas_legado = A.buscar_notas(raiz, filas, consulta, terminos, sin)
                no_tautologia = (consulta == "ventilacion 103"
                                 and nombre == "sinfiltro")
                with self.subTest(consulta=consulta, filtro=nombre,
                                  salida="paginas"):
                    if no_tautologia:
                        self.assertTrue(
                            pag_legado,
                            "paginas legacy vacias: el caso sin filtro con "
                            "'ventilacion 103' debe devolver paginas no vacias")
                    pag_prep = A.buscar_paginas(raiz, filas, consulta,
                                                terminos, con)
                    self.assertEqual(
                        _vista_paginas(pag_prep), _vista_paginas(pag_legado),
                        "proyeccion de paginas distinta entre brazos "
                        "(floats/orden/IDs/textos)")
                    self.assertEqual(
                        pag_prep, pag_legado,
                        "salida completa de buscar_paginas distinta entre brazos")
                with self.subTest(consulta=consulta, filtro=nombre,
                                  salida="notas"):
                    if no_tautologia:
                        self.assertTrue(
                            notas_legado,
                            "notas legacy vacias: el caso sin filtro con "
                            "'ventilacion 103' debe devolver notas no vacias")
                    notas_prep = A.buscar_notas(raiz, filas, consulta,
                                                terminos, con)
                    self.assertEqual(
                        _vista_notas(notas_prep), _vista_notas(notas_legado),
                        "proyeccion de notas distinta entre brazos "
                        "(floats/orden/IDs/textos)")
                    self.assertEqual(
                        notas_prep, notas_legado,
                        "salida completa de buscar_notas distinta entre brazos")


if __name__ == "__main__":
    unittest.main()
