#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unitarias del criterio c2 y fallos asociados en ejecutar_sin_ubicacion.py.

Revisión del contrato de evaluación (2026-11-16): la rúbrica pasa a v2 y c2 exige
IGUALDAD de conjuntos entre aclaracion.campos_requeridos y los campos requeridos del
caso (key 'campos_requeridos_permitidos' conservada por compatibilidad): v1 admitía
subconjunto no vacío y dejaba pasar preguntar SOLO municipio cuando hacen falta
CA+municipio (falsoacierto lógico). La evaluación v1 y la captura API de baseline las
conserva Codex; estos tests prueban la semántica v2 del helper _registro REUTILIZADO
del runner, SIN I/O de corpus ni modelos: se pasan respuestas sintéticas (páginas
vacías, o con doc=None que jamás tocan disco) y un contenido ficticio.

Método 1 (c2 igualdad): con CA+municipio requeridos, la aclaración que pide AMBOS
campos pasa; pedir SOLO comunidad_autonoma o SOLO municipio falla (omisión de campo
requerido); con SOLO CA requerida, pedir además municipio falla (extra fuera del
conjunto); duplicados fallan aunque el conjunto coincida.
Método 2 (otros fallos): pregunta ausente falla (c3, omisión: una aclaración sin
pregunta no es acierto); páginas entregadas fallan (c4, error: una aclaración con
páginas no es acierto); estado ok en un caso territorial falla (c1, error: responder
cuando tocaba aclarar no se convierte en acierto).

Sin red, sin procesos externos, sin corpus real; unittest.
"""
import sys
import unittest
from pathlib import Path

TERRITORIAL = Path(__file__).resolve().parent / "territorial"
if str(TERRITORIAL) not in sys.path:
    sys.path.insert(0, str(TERRITORIAL))
import ejecutar_sin_ubicacion as EU  # noqa: E402  (import puro del módulo, sin I/O)


def _caso(permitidos):
    return {"id": "T-TEST", "grupo": "territorial",
            "consulta": "¿Qué documentación debo presentar para solicitar una licencia de obras?",
            "esperado_estado": "aclaracion_necesaria",
            "campos_requeridos_permitidos": list(permitidos)}


def _res(campos=None, pregunta="¿En qué municipio o comunidad autónoma se ubica el terreno?",
         estado="aclaracion_necesaria", paginas=None):
    res = {"estado": estado, "texto_contexto": "", "excedido": False,
           "tokens_contexto": None,
           "recuperacion": {"resultados": []},
           "paginas": [] if paginas is None else paginas}
    if campos is not None:
        res["aclaracion"] = {"pregunta": pregunta, "campos_requeridos": campos}
    return res


def _criterio(reg, cid):
    return next(c for c in reg["criterios"] if c["criterio"] == cid)


AMBOS = ["comunidad_autonoma", "municipio"]


class PruebasCriterioC2SinUbicacion(unittest.TestCase):
    """Semántica v2 de _registro sobre respuestas sintéticas (sin corpus, sin motor)."""

    def test_01_c2_igualdad_todos_los_campos_requeridos(self):
        """v2: con CA+municipio requeridos pasa SOLO el conjunto EXACTO; pedir solo CA
        o solo municipio falla (omisión); extras fallan si solo CA requerida (error);
        duplicados fallan aunque el conjunto coincida (error)."""
        contenido = Path(".")  # ficticio: nunca se lee (páginas vacías, sin I/O)
        # conjunto EXACTO de los campos requeridos: pasa
        reg = EU._registro(_caso(AMBOS), _res(AMBOS), contenido, [])
        self.assertTrue(reg["acierto"])
        self.assertEqual(_criterio(reg, "c2")["resultado"], "ok")
        # SOLO comunidad_autonoma cuando hacen falta CA+municipio: omisión
        reg = EU._registro(_caso(AMBOS), _res(["comunidad_autonoma"]), contenido, [])
        self.assertFalse(reg["acierto"])
        c2 = _criterio(reg, "c2")
        self.assertEqual((c2["resultado"], c2["clase"]), ("fallo", "omision"))
        self.assertIn("faltan", c2["evidencia"])
        # SOLO municipio cuando hacen falta CA+municipio: omisión
        reg = EU._registro(_caso(AMBOS), _res(["municipio"]), contenido, [])
        self.assertFalse(reg["acierto"])
        self.assertEqual(_criterio(reg, "c2")["clase"], "omision")
        # extras fallan si SOLO CA requerida (aunque incluya la CA pedida): error
        reg = EU._registro(_caso(["comunidad_autonoma"]),
                           _res(["comunidad_autonoma", "municipio"]), contenido, [])
        self.assertFalse(reg["acierto"])
        c2 = _criterio(reg, "c2")
        self.assertEqual((c2["resultado"], c2["clase"]), ("fallo", "error"))
        self.assertIn("sobran", c2["evidencia"])
        # duplicados: conjunto coincidente pero lista con duplicados falla
        reg = EU._registro(_caso(["comunidad_autonoma"]),
                           _res(["comunidad_autonoma", "comunidad_autonoma"]),
                           contenido, [])
        self.assertFalse(reg["acierto"])
        self.assertEqual(_criterio(reg, "c2")["clase"], "error")

    def test_02_pregunta_ausente_paginas_y_estado_ok_fallan(self):
        """Una aclaración sin pregunta no es acierto (c3, omisión); una aclaración que
        entrega páginas no es acierto (c4, error); un estado ok en un caso territorial
        no es acierto (c1, error): responder cuando tocaba aclarar no puntúa."""
        contenido = Path(".")  # ficticio: sin I/O
        # pregunta ausente (c2 sigue ok: solo falla lo tocado)
        reg = EU._registro(_caso(AMBOS), _res(AMBOS, pregunta=None), contenido, [])
        self.assertFalse(reg["acierto"])
        c3 = _criterio(reg, "c3")
        self.assertEqual((c3["resultado"], c3["clase"]), ("fallo", "omision"))
        self.assertEqual(_criterio(reg, "c2")["resultado"], "ok")
        # páginas entregadas (página sintética con doc=None: sin lectura de disco)
        reg = EU._registro(_caso(AMBOS),
                           _res(AMBOS, paginas=[{"pagina": 1, "doc": None,
                                                 "version": None, "motivo": "primaria",
                                                 "archivo": None, "texto_sha256": None,
                                                 "etiqueta_impresa": None,
                                                 "url_fuente": None}]),
                           contenido, [])
        self.assertFalse(reg["acierto"])
        c4 = _criterio(reg, "c4")
        self.assertEqual((c4["resultado"], c4["clase"]), ("fallo", "error"))
        # estado ok cuando tocaba aclarar
        reg = EU._registro(_caso(AMBOS), _res(estado="ok"), contenido, [])
        self.assertFalse(reg["acierto"])
        c1 = _criterio(reg, "c1")
        self.assertEqual((c1["resultado"], c1["clase"]), ("fallo", "error"))


if __name__ == "__main__":
    unittest.main()
