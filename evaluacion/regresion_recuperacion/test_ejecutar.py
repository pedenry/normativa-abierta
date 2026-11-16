#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ejecutar.py — pruebas unitarias de _registro_caso y _resumen.

Alcance (encargo de validación; este archivo NO modifica ejecutar.py):
- Solo funciones puras del evaluador de regresión: `_registro_caso(caso, res,
  contenido)` y `_resumen(registros, datos, estricto)` de `ejecutar.py`,
  importado POR RUTA con importlib.
- Sin adaptador, sin motor, sin ranking y sin red: `res` es un resultado
  sintético y el corpus es un árbol temporal mínimo con una única página
  válida docs/doc-base/2026-01-01__abc/pagina/p0001.md.
- No se afirman valores de BM25 ni se simula el motor; se valida cómo el
  evaluador registra integridad, cobertura y código de salida.

Contrato anclado (según el docstring y esquema de ejecutar.py):
- Caso válido (VAL-01, doc-base 2026-01-01, gold [1]): página con doc/versión
  correctos, motivo "primaria", texto_sha256 = SHA-256 del texto completo del
  cuerpo, texto literal presente en texto_contexto y estado "ok" → cobertura
  del gold, integridad_ok y resumen con exit 0 (esperado declarado
  referencias_evaluables=1).
- Controles negativos (cada uno debe dar integridad False, sin cobertura y
  exit 1): cuerpo inexistente, texto recortado en contexto, SHA devuelto
  incorrecto, metadatos doc/edición incorrectos, ruta con '..' que sale de
  docs/doc-base/<version>__ aunque el fichero exista (no debe leerse como
  válida), y texto vacío (no cuenta como gold; detecta cobertura falsa).
- _resumen: la referencia faltante del caso con fallo_conocido (SUA-02) se ve
  en el resumen y NO en pérdidas nuevas; exit 0 por defecto y 1 con
  --estricto; cualquier pérdida no conocida da exit 1 siempre; el esperado
  referencias_evaluables=1 se comprueba sin ocultar el fallo conocido.
- Los registros no persisten textos completos (solo sha256, longitudes y
  metadatos) y las pruebas no hacen llamadas externas.

Límites: no se ejecuta el runner completo ni el adaptador real. Los nombres
de tipo de incidencia NO se anclan (solo la triada integridad/cobertura/exit
y la semántica por fila), para resistir el refactor concurrente de la
implementación de validación con nombres de helper estables. El subtest
"texto_vacio_con_sha_del_texto_vacio" ancla el contrato deseado: un cuerpo
vacío con sha del vacío es autocoherente pero no acredita la página ('' in
ctx es True y el sha del vacío es un hex no vacío); si la implementación
actual lo contabilizara como cobertura, el subtest lo detecta como falsa
cobertura y el arreglo se decide con el responsable.

Ejecución (desde la raíz del checkout interior):
    python -m unittest evaluacion/regresion_recuperacion/test_ejecutar.py -v
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_RUTA_RUNNER = Path(__file__).resolve().parent / "ejecutar.py"

# --- fixture sintética compartida ----------------------------------------
DOC = "doc-base"
VERSION = "2026-01-01"
RAIZ_VALIDA_REL = "docs/doc-base/2026-01-01__abc/pagina/p0001.md"
TEXTO_PAGINA = "Artículo 1. Página física p0001 del corpus sintético.\n"
SHA_PAGINA = hashlib.sha256(TEXTO_PAGINA.encode("utf-8")).hexdigest()
SHA_OTRO_TEXTO = hashlib.sha256(b"texto distinto que no es la pagina\n").hexdigest()
SHA_TEXTO_VACIO = hashlib.sha256(b"").hexdigest()
CTX_VALIDO = "ENCABEZADO DEL CONTEXTO\n" + TEXTO_PAGINA + "PIE DEL CONTEXTO\n"
CONSULTA = "consulta sintética de prueba"


def _importar_runner():
    """Importa ejecutar.py por ruta; sin instanciar el adaptador ni red.

    El import del módulo solo ejecuta definiciones (main está bajo guard
    __main__), así que no toca corpus ni adaptador_contexto.
    """
    nombre = "ejecutar_regresion_bajo_prueba"
    if nombre in sys.modules:
        return sys.modules[nombre]
    spec = importlib.util.spec_from_file_location(nombre, _RUTA_RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(
            "no se pudo crear spec de importlib para %s" % _RUTA_RUNNER)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    try:
        spec.loader.exec_module(modulo)
    except Exception:
        sys.modules.pop(nombre, None)
        raise
    return modulo


EJECUTAR = _importar_runner()


def _caso_base():
    """Caso del encargo: VAL-01, doc-base 2026-01-01, gold página 1."""
    return {"id": "VAL-01", "consulta": CONSULTA, "documento": DOC,
            "version": VERSION, "referencias_paginas": [1]}


def _res_valido(ctx=CTX_VALIDO, **pagina):
    """Resultado sintético estado='ok' con UNA página primaria válida."""
    fila = {"doc": DOC, "version": VERSION, "pagina": 1,
            "motivo": "primaria", "archivo": RAIZ_VALIDA_REL,
            "texto_sha256": SHA_PAGINA, "etiqueta_impresa": "p. 1",
            "url_fuente": "https://www.boe.es/ejemplo"}
    fila.update(pagina)
    return {"estado": "ok", "excedido": False, "tokens_contexto": 11,
            "limite_tokens": 20000, "texto_contexto": ctx,
            "recuperacion": {"resultados": []}, "paginas": [fila]}


def _registro_resumen(cid, contexto=(), primaria=(), faltantes=(),
                      fallo_conocido=False, estado="ok", integridad_ok=True):
    """Registro con la forma exacta que _resumen lee (esquema del runner)."""
    refs = sorted(set(contexto) | set(faltantes))
    return {
        "id": cid, "estado": estado,
        "gold": {"referencias_paginas": refs,
                 "fallo_conocido": bool(fallo_conocido), "puntua": bool(refs)},
        "cobertura": {"referencias": refs, "contexto": list(contexto),
                      "primaria": list(primaria), "faltantes": list(faltantes),
                      "puntua": bool(refs)},
        "integridad_ok": bool(integridad_ok),
        "integridad_incidencias": ([] if integridad_ok
                                   else [{"tipo": "simulado", "detalle": cid}]),
    }


class TestRegistroCaso(unittest.TestCase):
    """_registro_caso sobre fixture temporal sintética (sin motor ni red)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="regresion-recuperacion-")
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name)
        self.contenido = (self.raiz / "contenido").resolve()
        self.ruta_cuerpo = self.contenido / RAIZ_VALIDA_REL
        self._escribir_cuerpo()

    def _escribir_cuerpo(self, bytes_texto=None):
        self.ruta_cuerpo.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_cuerpo.write_bytes(
            TEXTO_PAGINA.encode("utf-8") if bytes_texto is None
            else bytes_texto)

    def _registro(self, **pagina):
        return EJECUTAR._registro_caso(_caso_base(), _res_valido(**pagina),
                                       self.contenido)

    def test_caso_valido_cubre_gold_sha_y_literal_con_resumen_0(self):
        registro = self._registro()
        self.assertEqual(registro["id"], "VAL-01")
        self.assertEqual(registro["documento"], DOC)
        self.assertEqual(registro["version"], VERSION)
        self.assertEqual(registro["consulta"], CONSULTA)
        self.assertEqual(registro["estado"], "ok")
        self.assertIsNone(registro["error_preparar"])
        self.assertEqual(registro["gold"], {"referencias_paginas": [1],
                                            "fallo_conocido": False,
                                            "puntua": True})
        # El contexto se resume solo con sha y longitud: nada del texto.
        self.assertEqual(registro["texto_contexto_sha256"],
                         hashlib.sha256(CTX_VALIDO.encode("utf-8")).hexdigest())
        self.assertEqual(registro["texto_contexto_longitud"], len(CTX_VALIDO))
        self.assertEqual(registro["primarias"], [])
        self.assertEqual(len(registro["paginas"]), 1)
        fila = registro["paginas"][0]
        self.assertEqual(fila["archivo"], RAIZ_VALIDA_REL)
        self.assertEqual(fila["pagina"], 1)
        self.assertEqual(fila["motivo"], "primaria")
        self.assertEqual(fila["texto_sha256"], SHA_PAGINA)
        self.assertEqual(fila["sha256_local"], SHA_PAGINA)
        self.assertEqual(fila["longitud_texto"], len(TEXTO_PAGINA))
        self.assertIs(fila["ruta_ok"], True)
        self.assertIs(fila["edicion_ok"], True)
        self.assertIs(fila["sha_coincide"], True)
        self.assertIs(fila["texto_en_contexto"], True)
        self.assertEqual(registro["cobertura"], {"referencias": [1],
                                                 "contexto": [1],
                                                 "primaria": [1],
                                                 "faltantes": [],
                                                 "puntua": True})
        self.assertIs(registro["integridad_ok"], True)
        self.assertEqual(registro["integridad_incidencias"], [])
        # Sin textos privados persistidos: solo sha, longitudes y metadatos.
        volcado = json.dumps(registro, ensure_ascii=False)
        self.assertNotIn(TEXTO_PAGINA, volcado)
        self.assertNotIn(CTX_VALIDO, volcado)
        self.assertNotIn("texto_contexto", registro)
        # Resumen: exit 0 con esperado declarado referencias_evaluables=1.
        datos = {"casos": [_caso_base()],
                 "esperado": {"referencias_evaluables": 1}}
        resumen, codigo = EJECUTAR._resumen([registro], datos, False)
        self.assertEqual(codigo, 0)
        self.assertEqual(resumen["casos_ok"], ["VAL-01"])
        self.assertEqual(resumen["casos_no_ok"], [])
        self.assertEqual(resumen["referencias_evaluables"], 1)
        self.assertEqual(resumen["cobertura_contexto_evaluable"], 1)
        self.assertIs(resumen["cumple_esperado_contexto"], True)
        self.assertEqual(resumen["perdidas_nuevas"], [])
        self.assertEqual(resumen["integridad_fallos"], [])

    def _afirmar_control_negativo(self, registro):
        """Triada del encargo: integridad False, sin cobertura y exit 1."""
        self.assertEqual(registro["cobertura"]["contexto"], [])
        self.assertEqual(registro["cobertura"]["primaria"], [])
        self.assertEqual(registro["cobertura"]["faltantes"], [1])
        self.assertIs(registro["integridad_ok"], False)
        self.assertTrue(registro["integridad_incidencias"])
        datos = {"casos": [_caso_base()],
                 "esperado": {"referencias_evaluables": 1}}
        resumen, codigo = EJECUTAR._resumen([registro], datos, False)
        self.assertEqual(codigo, 1,
                         "un control negativo no puede producir exit 0")
        self.assertEqual(resumen["perdidas_nuevas"],
                         [{"id": "VAL-01", "pagina": 1}])
        self.assertEqual([c["id"] for c in resumen["integridad_fallos"]],
                         ["VAL-01"])

    def test_controles_negativos_no_dan_cobertura_ni_integridad(self):
        with self.subTest(control="cuerpo_inexistente"):
            self._escribir_cuerpo()
            self.ruta_cuerpo.unlink()
            registro = self._registro()
            fila = registro["paginas"][0]
            self.assertIs(fila["ruta_ok"], True)      # ruta resuelta válida...
            self.assertIsNone(fila["sha256_local"])   # ...pero ilegible: sin texto inventado
            self.assertIsNone(fila["texto_en_contexto"])
            self._afirmar_control_negativo(registro)

        with self.subTest(control="texto_recortado_en_contexto"):
            self._escribir_cuerpo()
            ctx_recortado = ("ENCABEZADO\n"
                             + TEXTO_PAGINA[:len(TEXTO_PAGINA) // 2])
            registro = self._registro(ctx=ctx_recortado)
            fila = registro["paginas"][0]
            self.assertIs(fila["sha_coincide"], True)        # cuerpo íntegro en disco
            self.assertIs(fila["texto_en_contexto"], False)  # ctx no lo contiene literal
            self._afirmar_control_negativo(registro)

        with self.subTest(control="sha_devuelto_incorrecto"):
            self._escribir_cuerpo()
            registro = self._registro(texto_sha256=SHA_OTRO_TEXTO)
            fila = registro["paginas"][0]
            self.assertIs(fila["texto_en_contexto"], True)  # literal presente...
            self.assertIs(fila["sha_coincide"], False)      # ...pero el sha no lo acredita
            self._afirmar_control_negativo(registro)

        with self.subTest(control="doc_incorrecto"):
            self._escribir_cuerpo()
            registro = self._registro(doc="doc-otro")
            self.assertIs(registro["paginas"][0]["edicion_ok"], False)
            self._afirmar_control_negativo(registro)

        with self.subTest(control="edicion_incorrecta"):
            self._escribir_cuerpo()
            registro = self._registro(version="2025-06-30")
            self.assertIs(registro["paginas"][0]["edicion_ok"], False)
            self._afirmar_control_negativo(registro)

        with self.subTest(control="ruta_puntos_fuera_con_fichero_existente"):
            self._escribir_cuerpo()
            escapado = self.raiz / "fuera-corpus" / "p0001.md"
            escapado.parent.mkdir(parents=True, exist_ok=True)
            escapado.write_bytes(TEXTO_PAGINA.encode("utf-8"))  # el fichero SÍ existe
            registro = self._registro(archivo="../fuera-corpus/p0001.md",
                                      texto_sha256=SHA_PAGINA)
            fila = registro["paginas"][0]
            self.assertIs(fila["ruta_ok"], False)    # sale de docs/doc-base/<version>__
            self.assertIsNone(fila["sha256_local"])  # y NO se lee aunque exista
            self.assertIsNone(fila["longitud_texto"])
            self._afirmar_control_negativo(registro)

        with self.subTest(control="texto_vacio_con_sha_del_texto_esperado"):
            self._escribir_cuerpo(b"")
            registro = self._registro()  # sha declarado = SHA_PAGINA (texto completo)
            self.assertEqual(registro["paginas"][0]["longitud_texto"], 0)
            self._afirmar_control_negativo(registro)

        with self.subTest(control="texto_vacio_con_sha_del_texto_vacio"):
            # Contrato deseado: un cuerpo vacío autocoherente (sha del vacío)
            # NO acredita la página; contarlo sería cobertura falsa.
            self._escribir_cuerpo(b"")
            registro = self._registro(texto_sha256=SHA_TEXTO_VACIO)
            self.assertEqual(registro["paginas"][0]["longitud_texto"], 0)
            self._afirmar_control_negativo(registro)

    def test_pagina_archivo_inconsistente_detecta_etiquetado(self):
        """Página etiquetada 1 servida desde p0002.md con contenido válido.

        Texto, SHA y literal en contexto son correctos; solo la relación
        pagina<->archivo (p0002.md para la página 1) miente. El evaluador debe
        detectar el etiquetado incorrecto, no solo la ausencia del fichero.
        """
        texto_2 = "Artículo 1. Página física p0002 del corpus sintético.\n"
        ruta_2 = self.contenido / ("docs/doc-base/2026-01-01__abc"
                                   "/pagina/p0002.md")
        ruta_2.parent.mkdir(parents=True, exist_ok=True)
        ruta_2.write_bytes(texto_2.encode("utf-8"))
        registro = self._registro(
            ctx="CABECERA\n" + texto_2 + "PIE\n",
            archivo="docs/doc-base/2026-01-01__abc/pagina/p0002.md",
            texto_sha256=hashlib.sha256(texto_2.encode("utf-8")).hexdigest())
        fila = registro["paginas"][0]
        # El CONTENIDO es válido: la contradicción es solo la etiqueta.
        self.assertIs(fila["sha_coincide"], True)
        for clave in ("texto_en_contexto", "literal_en_contexto"):
            if clave in fila:
                self.assertIs(fila[clave], True)
        self._afirmar_control_negativo(registro)

    def test_presentacion_final_ajuste_espacios_solo_al_final(self):
        """Fuente con espacios finales; el ajuste del adaptador no es global.

        El fichero termina en ' \\n\\n' (SHA del texto completo) y el contexto
        trae texto.rstrip() + '\\n': sin literal exacto pero con el cierre
        esperado. La excepción es solo de espacios finales: un cambio interno
        del contenido no se perdona.
        """
        fuente = TEXTO_PAGINA + " \n\n"
        sha_fuente = hashlib.sha256(fuente.encode("utf-8")).hexdigest()
        with self.subTest(control="ajuste_espacios_finales_valido"):
            self._escribir_cuerpo(fuente.encode("utf-8"))
            registro = self._registro(
                ctx="Cabecera\n" + fuente.rstrip() + "\n",
                texto_sha256=sha_fuente)
            fila = registro["paginas"][0]
            self.assertIs(fila["sha_coincide"], True)
            self.assertEqual(registro["cobertura"], {"referencias": [1],
                                                     "contexto": [1],
                                                     "primaria": [1],
                                                     "faltantes": [],
                                                     "puntua": True})
            self.assertIs(registro["integridad_ok"], True)
            self.assertEqual(registro["integridad_incidencias"], [])
            self.assertIs(fila["literal_en_contexto"], False)
            self.assertIs(fila["texto_en_contexto"], True)
            self.assertIs(fila["ajuste_espacios_finales"], True)
            datos = {"casos": [_caso_base()],
                     "esperado": {"referencias_evaluables": 1}}
            _, codigo = EJECUTAR._resumen([registro], datos, False)
            self.assertEqual(codigo, 0)
        with self.subTest(control="cambio_interno_no_perdonado"):
            self._escribir_cuerpo(fuente.encode("utf-8"))
            ctx_alterado = ("Cabecera\n"
                            + fuente.rstrip().replace("p0001", "p000X")
                            + "\n")
            registro = self._registro(ctx=ctx_alterado,
                                      texto_sha256=sha_fuente)
            self._afirmar_control_negativo(registro)


class TestResumen(unittest.TestCase):
    """_resumen puro sobre registros sintéticos (sin corpus ni motor)."""

    DATOS_ESPERADO_1 = {"esperado": {"referencias_evaluables": 1}}

    def test_fallo_conocido_faltante_visible_default_0_estricto_1(self):
        reg_ok = _registro_resumen("REBT-01", contexto=[1], primaria=[1])
        reg_sua = _registro_resumen("SUA-02", fallo_conocido=True,
                                    faltantes=[2])
        resumen, codigo = EJECUTAR._resumen(
            [reg_ok, reg_sua], dict(self.DATOS_ESPERADO_1), False)
        self.assertEqual(codigo, 0)
        self.assertEqual(resumen["casos_total"], 2)
        self.assertEqual(resumen["casos_ok"], ["REBT-01", "SUA-02"])
        # El conocido no se oculta ni se maquilla: cuenta en total, no en evaluables.
        self.assertEqual(resumen["referencias_totales"], 2)
        self.assertEqual(resumen["referencias_evaluables"], 1)
        self.assertIs(resumen["cumple_esperado_contexto"], True)
        self.assertEqual(len(resumen["fallo_conocido"]), 1)
        fc = resumen["fallo_conocido"][0]
        self.assertEqual(fc["id"], "SUA-02")
        self.assertEqual(fc["referencias_paginas"], [2])
        self.assertEqual(fc["cubiertas"], [])
        self.assertEqual(fc["faltantes"], [2])
        self.assertEqual(fc["resultado"], "falta")
        self.assertEqual(resumen["perdidas_nuevas"], [])
        self.assertEqual(resumen["mejoras"], [])
        resumen_estricto, codigo_estricto = EJECUTAR._resumen(
            [reg_ok, reg_sua], dict(self.DATOS_ESPERADO_1), True)
        self.assertEqual(codigo_estricto, 1)
        self.assertIs(resumen_estricto["estricto"], True)
        self.assertEqual(resumen_estricto["perdidas_nuevas"], [])
        self.assertEqual(resumen_estricto["fallo_conocido"][0]["resultado"],
                         "falta")

    def test_perdida_no_conocida_y_estado_no_ok_siempre_exit_1(self):
        reg_falta = _registro_resumen("REBT-09", faltantes=[9])
        resumen, codigo = EJECUTAR._resumen(
            [reg_falta], dict(self.DATOS_ESPERADO_1), False)
        self.assertEqual(codigo, 1)
        self.assertEqual(resumen["perdidas_nuevas"],
                         [{"id": "REBT-09", "pagina": 9}])
        self.assertIs(resumen["cumple_esperado_contexto"], False)
        _, codigo_estricto = EJECUTAR._resumen(
            [reg_falta], dict(self.DATOS_ESPERADO_1), True)
        self.assertEqual(codigo_estricto, 1)
        reg_error = _registro_resumen("VAL-ERR", estado="error_preparar",
                                      integridad_ok=False)
        _, codigo_error = EJECUTAR._resumen(
            [reg_error], dict(self.DATOS_ESPERADO_1), False)
        self.assertEqual(codigo_error, 1)

    def test_mejora_del_fallo_conocido_se_registra_sin_tocar_gold(self):
        reg_sua = _registro_resumen("SUA-02", fallo_conocido=True,
                                    contexto=[2], primaria=[2])
        resumen, codigo = EJECUTAR._resumen([reg_sua], {}, False)
        self.assertEqual(codigo, 0)
        self.assertEqual(resumen["mejoras"],
                         [{"id": "SUA-02", "paginas": [2]}])
        self.assertEqual(resumen["fallo_conocido"][0]["resultado"], "cubre")
        self.assertEqual(resumen["referencias_evaluables"], 0)
        self.assertEqual(resumen["perdidas_nuevas"], [])

    def test_cardinalidad_y_casos_ausentes_en_resumen(self):
        """Inconsistencias de cardinalidad no pueden salir con exit 0.

        Esperado declarado frente a lo computado: sin registros el resumen
        debe fallar aunque no haya pérdidas; un caso de la fixture sin
        registro propio también. El esperado no se toca para borrar el fallo.
        """
        with self.subTest(control="sin_registros_con_esperado_declarado"):
            resumen, codigo = EJECUTAR._resumen(
                [], {"esperado": {"referencias_totales": 14,
                                  "referencias_evaluables": 13}}, False)
            self.assertEqual(codigo, 1)
            # Contradicción visible en el propio resumen: 0 computado frente
            # a 14/13 declarado en 'esperado'.
            self.assertEqual(resumen["casos_total"], 0)
            self.assertEqual(resumen["referencias_totales"], 0)
            self.assertEqual(resumen["referencias_evaluables"], 0)
            self.assertEqual(resumen["esperado"]["referencias_totales"], 14)
            self.assertEqual(resumen["esperado"]["referencias_evaluables"], 13)
            self.assertEqual(resumen["perdidas_nuevas"], [])
            self.assertEqual(resumen["integridad_fallos"], [])
        with self.subTest(control="caso_de_fixture_sin_registro"):
            datos = {"casos": [{"id": "VAL-01"}, {"id": "OTRO-01"}],
                     "esperado": {"referencias_evaluables": 1}}
            unico = _registro_resumen("VAL-01", contexto=[1], primaria=[1])
            resumen, codigo = EJECUTAR._resumen([unico], datos, False)
            self.assertEqual(codigo, 1)
            self.assertEqual(resumen["casos_total"], 1)
            self.assertEqual(resumen["casos_ok"], ["VAL-01"])
            self.assertEqual(resumen["perdidas_nuevas"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
