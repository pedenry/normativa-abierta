#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_palabras_partidas.py — contrato del ajuste de palabras partidas (motor REAL).

Encargo acotado (solo pruebas; sin tocar acceso.py, corpus ni fixture): el
cambio causal aislado por Codex exige que tokenizar una las letras partidas
por guion + salto LF/CRLF (con espacios horizontales) antes de puntuar, sin
cambiar el texto literal fuente y sin aritmética IDF/pesos nueva; regexp con
letras a ambos lados, no números. Patrón de aislamiento como
test_estabilidad_recuperacion.py: acceso.py REAL con importlib bajo nombre
privado, sin compartir el «acceso» parcheado de otras suites. Sin mock de
ranking y sin corpus real: el marcador de búsqueda usa _bm25 REAL sobre una
página sintética. Sin raíces absolutas fijadas (el stemmer depende del
entorno): se compara contra tokenizar de la palabra íntegra o de su
equivalente con espacios. Estado esperado, registrado sin ocultar fallos:
(1) y su marcador quedan en ROJO hasta que recuperación aplique el cambio;
(2)-(4) son guardas de no-regresión que deben pasar antes y después. Los
recuentos de texto aquí son proxy local, no tokens de API.
"""
import hashlib
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # experimentos/http-local


def _cargar_acceso_privado():
    """Carga acceso.py REAL con importlib sin dejar rastro en sys.modules."""
    spec = importlib.util.spec_from_file_location(
        "_acc_priv_test_palabras", RAIZ / "acceso.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.modules.pop(spec.name, None)
    return modulo


_ACC = _cargar_acceso_privado()


class PruebasPalabrasPartidas(unittest.TestCase):
    """Contrato de unión de palabras partidas sobre tokenizar REAL."""

    def _puntuar_pagina_sintetica(self, texto, termino):
        """BM25 REAL sobre una página sintética (marcador antes/después)."""
        pags = [{"documento": "doc-syn", "pagina": 1, "texto": texto,
                 "titulos": ""}]
        pares = _ACC._bm25(pags, [termino], termino)
        return pares[0][0] if pares else 0.0

    def test_union_letras_partidas_guion_salto(self):
        """(1) guion + LF/CRLF (con espacios horizontales) une letras; se
        compara con la palabra íntegra, sin raíz absoluta fijada; el marcador
        sintético codifica el después (pre-ajuste, BM25 puntúa 0)."""
        self.assertEqual(_ACC.tokenizar("Vivien-\nda"),
                         _ACC.tokenizar("Vivienda"))
        self.assertEqual(_ACC.tokenizar("acce-\r\nsible"),
                         _ACC.tokenizar("accesible"))
        self.assertEqual(_ACC.tokenizar("acce- \r\n sible"),
                         _ACC.tokenizar("accesible"))
        self.assertEqual(_ACC.tokenizar("acce- \n sible"),
                         _ACC.tokenizar("accesible"))
        self.assertGreater(self._puntuar_pagina_sintetica(
            "Zonas comunes Residencial Vivien-\nda con 1,10 m.", "vivienda"),
            0.0)

    def test_no_union_numeros_y_vinietas(self):
        """(2) la unión es solo con letras a ambos lados: '103-\n109' sigue
        dando los tokens 103 y 109 (no 103109) y la viñeta 'anchura\n- libre'
        no se pega en una sola palabra."""
        self.assertEqual(_ACC.tokenizar("103-\n109"),
                         _ACC.tokenizar("103 109"))
        self.assertNotEqual(_ACC.tokenizar("103-\n109"),
                            _ACC.tokenizar("103109"))
        self.assertEqual(_ACC.tokenizar("anchura\n- libre"),
                         _ACC.tokenizar("anchura libre"))
        self.assertNotEqual(_ACC.tokenizar("anchura\n- libre"),
                            _ACC.tokenizar("anchuralibre"))

    def test_guion_misma_linea_dos_palabras(self):
        """(3) guion en la misma línea: 'tecnico-administrativo' mantiene dos
        palabras, sin concatenación en 'tecnicoadministrativo'."""
        self.assertEqual(_ACC.tokenizar("tecnico-administrativo"),
                         _ACC.tokenizar("tecnico administrativo"))
        self.assertNotEqual(_ACC.tokenizar("tecnico-administrativo"),
                            _ACC.tokenizar("tecnicoadministrativo"))

    def test_inmutabilidad_y_sin_partidas_igual(self):
        """(4) literal fuente idéntico (ni argumento ni fichero se
        reescriben) y texto sin partidas con los mismos tokens normales, con
        o sin salto de línea; sin guion no hay unión."""
        texto = "Anchura libre en zonas comunes.\nResidencial Vivienda: 1,10 m."
        copia = str(texto)
        t1 = _ACC.tokenizar(texto)
        self.assertEqual(texto, copia)
        self.assertEqual(t1, _ACC.tokenizar(texto.replace("\n", " ")))
        self.assertNotEqual(_ACC.tokenizar("Residencial\nVivienda"),
                            _ACC.tokenizar("ResidencialVivienda"))
        tmp = Path(tempfile.mkdtemp(prefix="palabras-partidas-")) / "p0001.md"
        self.addCleanup(shutil.rmtree, str(tmp.parent), True)
        partido = "Residencial Vivien-\nda en zonas comunes: 1,10 m."
        tmp.write_text(partido, encoding="utf-8", newline="\n")
        sha0 = hashlib.sha256(tmp.read_bytes()).hexdigest()
        _ACC.tokenizar(tmp.read_text(encoding="utf-8"))
        self.assertEqual(tmp.read_text(encoding="utf-8"), partido)
        self.assertEqual(hashlib.sha256(tmp.read_bytes()).hexdigest(), sha0)


if __name__ == "__main__":
    unittest.main()
