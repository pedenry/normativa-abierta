#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unittest del parámetro propagar_errores de AdaptadorContexto.

Encargo acotado: SOLO el parámetro nuevo `propagar_errores` (keyword-only en
preparar()) del adaptador REAL; NO el mock HTTP, acceso.py ni el servidor.
Corpus SINTÉTICO temporal (sin normativa real, sin red, sin API, sin modelos);
los fallos se inyectan con el marcador privado de baja entropía "PRUEBA"
(mensajes deterministas, sin contenido real ni rutas ni secretos). El
adaptador se obtiene con el ayudante existente (`_montar`), que parchea
buscar_bm25 y construir_lectura sobre la instancia privada de acceso.py.

Rúbrica por caso (criterio -> aserción clave):
 1) fallo inyectado en buscar_bm25:
    - sin bandera (fallback previo conservado): sin excepción; estado
      "sin_resultados"; la única advertencia es el aviso íntegro
      "fallo del buscador (<Tipo): PRUEBA..." y no hay resultados ni páginas.
    - con propagar_errores=True: se reeleva el tipo inyectado y el mensaje
      conserva el marcador "PRUEBA".
 2) fallo inyectado en la PRIMERA construir_lectura (opt.pagina es None; la
    apertura de páginas del plan sigue permitida para otros llamados):
    - sin bandera: estado "ok"; lista exacta de avisos = [
      "lectura_no_disponible doc-demo/1: PRUEBA..."]; el ensamblaje avisa
      ("-- Advertencias de ensamblaje --") y la página del plan se entrega
      igualmente (contexto de fallback, sin recortes).
    - con bandera: reeleva el tipo inyectado.
 3) fallo inyectado SOLO en la lectura de página (opt.pagina con valor; la
    llamada previa de contexto pasa):
    - sin bandera: estado "ok"; sin páginas entregadas; avisos exactos [
      "página_no_abierta doc-demo p.1: PRUEBA...", "resultado demo-1 sin
      páginas abiertas ni reutilizadas: ..."]; omitido pagina_no_abierta y
      fallback con el texto íntegro del apartado ("Literal").
    - con bandera: reeleva el tipo inyectado.

Cada caso repite el par de brazos (sin bandera / con bandera) bajo subTest
para RuntimeError y SystemExit, los dos tipos que el adaptador captura.

Límites de la muestra: preparar() NO está mockeado; cargar_indice,
cargar_docs y el filtrado distribute son REALES sobre los fixtures del
temporal; buscar_bm25 y construir_lectura están parcheados (el segundo se
envuelve después para inyectar el fallo en el punto exacto y dejar pasar los
demás llamados). Las cadenas de aviso exactas ligadas aquí ("fallo del
buscador (...)", "lectura_no_disponible", "página_no_abierta", texto_integro)
son del contrato vigente del adaptador: si cambia la redacción, estas
aserciones deberán ajustarse (comprobación pendiente en cada corrida). No
cubre el HTTP (http_consulta/acceso), BM25 real ni tiktoken; no hay recuento
de consumo (ejecución local, sin llamadas a modelos).
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

_CARPETA = Path(__file__).resolve().parent
if str(_CARPETA) not in sys.path:  # hallar el módulo hermano por script o discover
    sys.path.insert(0, str(_CARPETA))

# Import del módulo COMPLETO; NO de su clase TestCase (duplicaría sus pruebas).
import test_advertencias_fuentes as F

_MARCA = "PRUEBA"  # marcador privado de baja entropía, sin contenido real
_TIPOS = (RuntimeError, SystemExit)
_CONSULTA = "consulta sintetica de errores"  # sin ámbito ni materia territorial
_SELECCION = ("doc-demo", "1")


def _doc_demo():
    """Documento sintético mínimo coherente con _corpus_sintetico."""
    return {"id": "doc-demo", "distribute": True, "version": "2020-10-01",
            "sha256": "SHA", "url": "https://ejemplo.test", "title": "Documento",
            "paginas_texto": {1: "Literal de prueba"},
            "apartados": [{"apartado_id": "1", "id_tecnico": "demo-1",
                           "titulo": "Apartado demo", "archivo": "p0001.md",
                           "paginas": [1], "texto": "Literal"}]}


def _montar_adaptador(caso):
    """Ayudante existente + adaptador REAL sobre corpus sintético temporal."""
    ayudante = F.PruebasAdvertenciasFuentes()
    caso.addCleanup(ayudante.doCleanups)
    _corpus, ad, _captura = ayudante._montar([_doc_demo()], [_SELECCION])
    return ad


def _inyectar_fallo_buscar(registrar, tipo):
    """Reemplaza buscar_bm25 por uno que lanza SIEMPRE `tipo` con la marca."""
    def fallar(*_args, **_kwargs):
        raise tipo("%s: fallo inyectado en buscar_bm25" % _MARCA)
    parche = mock.patch.object(F._ACC, "buscar_bm25", fallar)
    parche.start()
    registrar(parche.stop)


def _inyectar_fallo_lectura(registrar, tipo, con_pagina):
    """Envuelve el construir_lectura montado y lanza `tipo` SOLO cuando la
    condición opt.pagina (None / con valor) coincide con `con_pagina`; los
    demás llamados pasan al fake previo sin alterar el flujo del adaptador."""
    previa = F._ACC.construir_lectura  # fake_lectura instalado por _montar

    def falla_si_pagina(*args, **kwargs):
        opt = kwargs["opt"] if "opt" in kwargs else (args[3] if len(args) > 3
                                                     else None)
        si = getattr(opt, "pagina", None) is not None
        if si == con_pagina:
            raise tipo("%s: fallo inyectado en construir_lectura" % _MARCA)
        return previa(*args, **kwargs)

    parche = mock.patch.object(F._ACC, "construir_lectura", falla_si_pagina)
    parche.start()
    registrar(parche.stop)


class PruebasPropagarErroresAdaptador(unittest.TestCase):
    """Fallo inyectado en el buscador o en la lectura, con el adaptador real."""

    def test_fallo_buscar_bm25_propaga_o_fallback(self):
        """Caso 1: fallo del buscador -> fallback sin_resultados, o reeleva."""
        for tipo in _TIPOS:
            with self.subTest(tipo=tipo.__name__):
                ad = _montar_adaptador(self)
                _inyectar_fallo_buscar(self.addCleanup, tipo)
                # Sin bandera: fallback previo, sin excepción.
                res = ad.preparar(_CONSULTA)
                self.assertEqual(res["estado"], "sin_resultados")
                self.assertEqual(res["recuperacion"]["resultados"], [])
                self.assertEqual(res["paginas"], [])
                self.assertEqual(
                    res["recuperacion"]["advertencias"],
                    ["fallo del buscador (%s): %s: fallo inyectado en buscar_bm25"
                     % (tipo.__name__, _MARCA)])
                # Con bandera: el fallo inyectado se reeleva sin alteración.
                with self.assertRaises(tipo) as ctx:
                    ad.preparar(_CONSULTA, propagar_errores=True)
                self.assertIn(_MARCA, str(ctx.exception))

    def test_fallo_primera_construir_lectura_propaga_o_fallback(self):
        """Caso 2: fallo en la llamada de contexto (pagina None); la página
        del plan sigue abriéndose; sin bandera hay aviso y contexto fallback."""
        for tipo in _TIPOS:
            with self.subTest(tipo=tipo.__name__):
                ad = _montar_adaptador(self)
                _inyectar_fallo_lectura(self.addCleanup, tipo, con_pagina=False)
                # Sin bandera: el ensamblaje continúa con aviso, sin excepción.
                res = ad.preparar(_CONSULTA)
                self.assertEqual(res["estado"], "ok")
                self.assertEqual(
                    res["recuperacion"]["advertencias"],
                    ["lectura_no_disponible doc-demo/1: %s: fallo inyectado "
                     "en construir_lectura" % _MARCA])
                self.assertIn("-- Advertencias de ensamblaje --",
                              res["texto_contexto"])
                # Resto del flujo intacto: página entregada por el plan del motor.
                self.assertEqual([p["pagina"] for p in res["paginas"]], [1])
                self.assertIn("Literal de prueba", res["texto_contexto"])
                # Con bandera: se reeleva en la primera llamada.
                with self.assertRaises(tipo) as ctx:
                    ad.preparar(_CONSULTA, propagar_errores=True)
                self.assertIn(_MARCA, str(ctx.exception))

    def test_fallo_lectura_pagina_propaga_o_fallback(self):
        """Caso 3: fallo SOLO en la apertura de página (pagina con valor); sin
        bandera se omite la página y se conserva el texto íntegro del apartado."""
        for tipo in _TIPOS:
            with self.subTest(tipo=tipo.__name__):
                ad = _montar_adaptador(self)
                _inyectar_fallo_lectura(self.addCleanup, tipo, con_pagina=True)
                # Sin bandera: la página no se entrega; fallback sin recortes.
                res = ad.preparar(_CONSULTA)
                self.assertEqual(res["estado"], "ok")
                self.assertEqual(res["paginas"], [])
                self.assertEqual(
                    res["recuperacion"]["advertencias"],
                    ["página_no_abierta doc-demo p.1: %s: fallo inyectado "
                     "en construir_lectura" % _MARCA,
                     "resultado demo-1 sin páginas abiertas ni reutilizadas: "
                     "se incluyó texto_integro del apartado"])
                self.assertTrue(
                    any(o.get("motivo") == "pagina_no_abierta" and
                        o.get("documento") == "doc-demo" and o.get("pagina") == 1
                        for o in res["recuperacion"]["omitidos"]),
                    res["recuperacion"]["omitidos"])
                self.assertIn("sin recortar", res["texto_contexto"])
                self.assertIn("Literal", res["texto_contexto"])
                # Con bandera: se reeleva en la apertura de la página.
                with self.assertRaises(tipo) as ctx:
                    ad.preparar(_CONSULTA, propagar_errores=True)
                self.assertIn(_MARCA, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
