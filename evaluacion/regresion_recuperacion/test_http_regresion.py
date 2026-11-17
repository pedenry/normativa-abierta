#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unitarias del runner de regresion HTTP territorial.

Objeto de prueba: evaluacion/regresion_recuperacion/territorial/ejecutar_http.py
(cargado con importlib.util.spec_from_file_location; nunca se ejecuta main()).

Alcance y metodo del encargo:
- SOLO este archivo. No modifica runner, produccion, corpus ni referencia.
- Sin shell, sin red, sin servidor: no se llama a _arrancar_servidor/main().
- Mocks SOLO en _pedir_json y _http_get (en la practica basta sustituir
  _http_get, que es la unica salida de red de todos los caminos probados).
- Casos sinteticos autoconsistentes: cada caso lleva su valor esperado
  embebido (sin fuentes ni gold externos). La "rubrica" de cada modo queda
  fijada por los propios criterios del runner (CRITERIOS), y la unidad
  documental se materializa en las tuplas de lectura
  (documento, version, sha256, pagina) = documento/version/huella/pagina
  fisica, con excepciones cubiertas por casos negativos dedicados.

Rubrica por modo (criterio -> prueba):
- contexto: igualdad del JSON normalizado con texto_contexto_sha256 del
  literal entero (positivo), sello completo detecta un campo profundo mas
  alla de 100 niveles de anidamiento, ausencia de "contenido" en HTTP,
  status 200 obligatorio; URL con q/doc/version y omision de nulos.
- compat: URL /buscar con q/doc/version; status y sha256 del cuerpo exactos
  (positivo y doble diferencia); error de conexion sin cuerpos crudos.
- buscar_auto: estado/consulta/aclaracion, ids de tarjetas en orden, campos
  de tarjetas, conjunto de lecturas (doc/version/sha256/pagina), cero
  tarjetas/lecturas en estados vacios, y deteccion de status != 200 aunque
  estado y aclaracion coincidan.
- _validar_casos: admite contexto con documento/version None pero exige
  consulta y respuesta_sha256 no vacios; compat y buscar_auto segun arriba.

Limites registrados:
- El sello esperado de los casos positivos se recalcula aqui replicando la
  canonizacion del runner (json.dumps ensure_ascii=False, sort_keys=True,
  separadores compactos); si el runner cambia su canonizacion, el positivo
  dejara de pasar (es la senal buscada, no un falso positivo).
- No mide consumo, tiempo ni rendimiento; es una prueba de contrato.
- La comprobacion con shell (python -m unittest) queda a cargo de Codex.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

DIR_AQUI = Path(__file__).resolve().parent
RUTA_RUNNER = DIR_AQUI / "territorial" / "ejecutar_http.py"

# URL base solo nominal: nunca se abre una conexion real (_http_get simulado).
URL_BASE = "http://127.0.0.1:47521"

CLAVES_A_QUITAR = ("contenido", "tiempo_ms", "texto_contexto")


# ----------------------------------------------------------------- carga runner

def _cargar_runner():
    especificacion = importlib.util.spec_from_file_location(
        "ejecutar_http_bajo_prueba", RUTA_RUNNER)
    if especificacion is None or especificacion.loader is None:
        raise RuntimeError("importlib no genero un spec para el runner")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


RUNNER = _cargar_runner()


# -------------------------------------------------------------------- utilidades

class _FalsoHTTP:
    """Sustituto de _http_get: captura URLs y devuelve (status, cuerpo)."""

    def __init__(self, status=200, cuerpo=b"{}", error=None):
        self.status = status
        self.cuerpo = cuerpo
        self.error = error
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.status, self.cuerpo


def _json_bytes(objeto):
    return json.dumps(objeto, ensure_ascii=False).encode("utf-8")


def _sha_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _sha_bytes(datos):
    return hashlib.sha256(datos).hexdigest()


def _sello_de(payload):
    """Replica la canonizacion del runner para el modo contexto.

    normalizado = payload sin contenido/tiempo_ms/texto_contexto, mas
    texto_contexto_sha256 (sha256 del literal entero del texto_contexto,
    o del texto vacio si no es str). sello = sha256 del volcado canonico.
    Devuelve (sello, sha_texto, normalizado).
    """
    texto = payload.get("texto_contexto")
    sha_texto = _sha_texto(texto) if isinstance(texto, str) else _sha_texto("")
    normalizado = {k: v for k, v in payload.items() if k not in CLAVES_A_QUITAR}
    normalizado["texto_contexto_sha256"] = sha_texto
    canonico = json.dumps(normalizado, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    return _sha_bytes(canonico), sha_texto, normalizado


def _query_params(url):
    return {k: v[0] for k, v in
            urllib.parse.parse_qs(url.split("?", 1)[1]).items()}


class BasePrueba(unittest.TestCase):
    """Un fallo al importar el evaluador debe fallar la suite."""


# --------------------------------------------------------------- casos sinteticos

def _caso_contexto_ok():
    """Caso contexto positivo: ref con recuperacion.resultados y paginas."""
    texto = ("Articulo 12.1 Plazos. El plazo de alegaciones sera de diez dias "
             "habiles, salvo disposicion contraria de la norma que ordene "
             "el procedimiento.")
    base = {
        "estado": "ok",
        "consulta": "plazo de alegaciones en procedimiento sancionador",
        "documento": "BOJA_nr35_2024",
        "version": "2024-02-21",
        "recuperacion": {"resultados": [
            {"documento": "BOJA_nr35_2024", "apartado_id": "art-12-1",
             "cita": "art. 12.1", "pagina": 17},
        ]},
        "paginas": [17],
    }
    payload = json.loads(json.dumps(base))
    payload["texto_contexto"] = texto
    sello, sha_texto, normalizado = _sello_de(payload)
    caso = {
        "fixture": "fixture-boja-35-contexto",
        "id": "ctx-ok",
        "consulta": base["consulta"],
        "documento": base["documento"],
        "version": base["version"],
        "respuesta_sha256": sello,
        "respuesta_referencia": json.loads(json.dumps(normalizado)),
    }
    return caso, payload, texto, sha_texto


def _caso_compat_ok():
    """Caso compat positivo: cuerpo legacy con status y sha256 coherentes."""
    cuerpo = _json_bytes({"resultados": [{"documento": "BOE-A-2023-1234",
                                          "total": 1}]})
    caso = {
        "fixture": "fixture-boe-1234",
        "id": "compat-ok",
        "consulta": "visado de colegio profesional",
        "documento": "BOE-A-2023-1234",
        "version": "2023-06-02",
        "http_legacy": {"status": 200, "sha256_cuerpo": _sha_bytes(cuerpo)},
    }
    return caso, cuerpo


def _caso_auto_ok():
    """Caso buscar_auto positivo: ref con recuperacion.resultados y paginas
    (clave 'doc'), HTTP con documentos y lecturas (clave 'documento')."""
    tarjeta = {
        "documento": "BOCM_supl_126_2023",
        "apartado_id": "dispo-adic-2",
        "version": "2023-05-29",
        "id_tecnico": "bocm-126-2023-dispo-adic-2",
        "titulo": "Disposicion adicional segunda",
        "puntuacion_bm25": 8.4,
        "paginas": [3, 4],
        "cita": "dispo. adic. 2a",
        "paginas_entregadas": [3],
    }
    sha_lectura = "a" * 64
    ref = {
        "estado": "ok",
        "consulta": "licencia de actividad clasificada",
        "aclaracion": None,
        "resolucion_ambito": {"ambito": "municipal", "municipio": "Madrid"},
        "recuperacion": {
            "resultados": [json.loads(json.dumps(tarjeta))],
            "advertencias": ["consulta sin documento: busqueda automatica"],
        },
        "paginas": [{"doc": "BOCM_supl_126_2023", "version": "2023-05-29",
                     "sha256": sha_lectura, "pagina": 3}],
    }
    payload = {
        "estado": "ok",
        "consulta": ref["consulta"],
        "aclaracion": None,
        "resolucion_ambito": dict(ref["resolucion_ambito"]),
        "documentos": [json.loads(json.dumps(tarjeta))],
        "advertencias": list(ref["recuperacion"]["advertencias"]),
        "lecturas": [{"documento": "BOCM_supl_126_2023",
                      "version": "2023-05-29", "sha256": sha_lectura,
                      "pagina": 3}],
    }
    caso = {
        "fixture": "fixture-bocm-126-auto",
        "id": "auto-ok",
        "consulta": ref["consulta"],
        "respuesta_referencia": ref,
    }
    return caso, payload, sha_lectura


# ------------------------------------------------------------------- pruebas

class TestCargaRunner(BasePrueba):

    def test_expone_los_puntos_de_entrada_esperados(self):
        for atributo in ("_caso_contexto", "_caso_compat", "_caso_auto",
                         "_validar_casos", "_pedir_json", "_http_get"):
            self.assertTrue(hasattr(RUNNER, atributo), atributo)
        self.assertTrue(RUTA_RUNNER.is_file(), str(RUTA_RUNNER))


class TestValidarCasos(BasePrueba):

    def test_contexto_admite_documento_y_version_none(self):
        caso = {"fixture": "f", "id": "ctx-sin-doc", "consulta": "q de prueba",
                "documento": None, "version": None,
                "respuesta_sha256": "a" * 64, "respuesta_referencia": {}}
        self.assertEqual(RUNNER._validar_casos([caso], "contexto"), [])

    def test_contexto_exige_consulta_y_sello(self):
        base = {"fixture": "f", "id": "ctx-roto", "documento": "D",
                "version": "v", "respuesta_referencia": {}}
        sin_consulta = dict(base)
        sin_consulta["respuesta_sha256"] = "a" * 64
        sello_vacio = dict(base, consulta="q", respuesta_sha256="")
        problemas = RUNNER._validar_casos([sin_consulta, sello_vacio], "contexto")
        self.assertEqual(len(problemas), 2)
        self.assertTrue(any("falta consulta" in p for p in problemas))
        self.assertTrue(any("falta respuesta_sha256" in p for p in problemas))

    def test_contexto_exige_respuesta_referencia_como_objeto(self):
        caso = {"fixture": "f", "id": "ctx-ref", "consulta": "q",
                "documento": None, "version": None,
                "respuesta_sha256": "a" * 64, "respuesta_referencia": ["no"]}
        problemas = RUNNER._validar_casos([caso], "contexto")
        self.assertEqual(len(problemas), 1)
        self.assertIn("respuesta_referencia no es objeto", problemas[0])

    def test_contexto_exige_claves_documento_y_version_incluso_con_none(self):
        # documento/version None se admiten; la CLAVE ausente no.
        caso = {"fixture": "f", "id": "ctx-sin-clave", "consulta": "q",
                "respuesta_sha256": "a" * 64, "respuesta_referencia": {}}
        problemas = RUNNER._validar_casos([caso], "contexto")
        self.assertEqual(len(problemas), 2)
        self.assertTrue(any("falta documento" in p for p in problemas))
        self.assertTrue(any("falta version" in p for p in problemas))

    def test_compat_exige_http_legacy_sha256_y_documento_version(self):
        caso_ok = {"fixture": "f", "id": "compat-ok", "consulta": "q",
                   "documento": "D", "version": "v",
                   "http_legacy": {"status": 200, "sha256_cuerpo": "a" * 64}}
        self.assertEqual(RUNNER._validar_casos([caso_ok], "compat"), [])
        sin_sha = {"fixture": "f", "id": "compat-sin-sha", "consulta": "q",
                   "documento": "D", "version": "v",
                   "http_legacy": {"status": 200}}
        sin_doc = {"fixture": "f", "id": "compat-sin-doc", "consulta": "q",
                   "documento": None, "version": "v",
                   "http_legacy": {"status": 200, "sha256_cuerpo": "a" * 64}}
        legacy_roto = {"fixture": "f", "id": "compat-legacy", "consulta": "q",
                       "http_legacy": "no-soy-dict"}
        problemas = RUNNER._validar_casos([sin_sha, sin_doc, legacy_roto],
                                          "compat")
        self.assertEqual(len(problemas), 3)
        self.assertTrue(any("sha256_cuerpo" in p and "compat-sin-sha" in p
                            for p in problemas))
        self.assertTrue(any("falta documento o version" in p
                            and "compat-sin-doc" in p for p in problemas))
        self.assertTrue(any("http_legacy no es objeto" in p
                            and "compat-legacy" in p for p in problemas))

    def test_buscar_auto_exige_consulta_y_referencia_objeto(self):
        caso_ok = {"fixture": "f", "id": "auto-ok", "consulta": "q",
                   "respuesta_referencia": {}}
        self.assertEqual(RUNNER._validar_casos([caso_ok], "buscar_auto"), [])
        mal = [{"fixture": "f", "id": "auto-1", "consulta": None,
                "respuesta_referencia": {}},
               {"fixture": "f", "id": "auto-2", "consulta": "q",
                "respuesta_referencia": "x"}]
        problemas = RUNNER._validar_casos(mal, "buscar_auto")
        self.assertEqual(len(problemas), 2)
        self.assertTrue(any("falta consulta" in p for p in problemas))
        self.assertTrue(any("respuesta_referencia no es objeto" in p
                            for p in problemas))


class TestCasoContexto(BasePrueba):

    def test_positivo_realista_coincide(self):
        caso, payload, texto, sha_texto = _caso_contexto_ok()
        falso = _FalsoHTTP(200, _json_bytes(payload))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_contexto(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "coincide")
        self.assertEqual(resultado["diferencias"], [])
        self.assertEqual(resultado["diferencias_total"], 0)
        self.assertEqual(resultado["estados"], {"http": 200, "respuesta": "ok"})
        hashes = resultado["hashes"]
        self.assertEqual(hashes["texto_contexto_sha256"], sha_texto)
        self.assertEqual(hashes["texto_contexto_sha256_esperado"], sha_texto)
        self.assertTrue(hashes["texto_contexto_presente"])
        self.assertEqual(hashes["respuesta_normalizada_sha256"],
                         caso["respuesta_sha256"])
        self.assertEqual(resultado["primarios"],
                         payload["recuperacion"]["resultados"])
        self.assertEqual(resultado["paginas"], [17])
        # URL esperada: /contexto con q/doc/version.
        self.assertEqual(len(falso.urls), 1)
        self.assertTrue(falso.urls[0].startswith(URL_BASE + "/contexto?"))
        self.assertEqual(_query_params(falso.urls[0]),
                         {"q": caso["consulta"], "doc": caso["documento"],
                          "version": caso["version"]})

    def test_url_omite_documento_y_version_nulos(self):
        caso, payload, _texto, _sha = _caso_contexto_ok()
        caso_sin = dict(caso)
        caso_sin["documento"] = None
        caso_sin["version"] = None
        falso = _FalsoHTTP(200, _json_bytes(payload))
        with mock.patch.object(RUNNER, "_http_get", falso):
            RUNNER._caso_contexto(caso_sin, URL_BASE)
        self.assertEqual(falso.urls[0], URL_BASE + "/contexto?"
                         + urllib.parse.urlencode({"q": caso_sin["consulta"]}))

    def test_status_distinto_de_200(self):
        caso, payload, _texto, _sha = _caso_contexto_ok()
        falso = _FalsoHTTP(500, _json_bytes(payload))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_contexto(caso, URL_BASE)
        self.assertEqual(resultado["estados"]["http"], 500)
        self.assertEqual(resultado["diferencias"],
                         [{"ruta": "http", "tipo": "status_distinto_de_200"}])
        self.assertEqual(resultado["resultado"], "diferencia")

    def test_contenido_prohibido_en_http(self):
        caso, payload, _texto, _sha = _caso_contexto_ok()
        payload_con_contenido = json.loads(json.dumps(payload))
        payload_con_contenido["contenido"] = "Texto reservado del corpus." * 3
        # El sello excluye la clave prohibida: el resto sigue coincidiendo.
        falso = _FalsoHTTP(200, _json_bytes(payload_con_contenido))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_contexto(caso, URL_BASE)
        self.assertEqual(resultado["diferencias"],
                         [{"ruta": "contenido",
                           "tipo": "clave_prohibida_en_http"}])
        self.assertEqual(resultado["resultado"], "diferencia")
        # El sello de la respuesta normalizada sigue siendo el esperado.
        self.assertEqual(resultado["hashes"]["respuesta_normalizada_sha256"],
                         caso["respuesta_sha256"])

    def test_sello_cubre_una_hoja_a_mas_de_100_niveles(self):
        texto = "Texto del apartado con estructura anidada profunda."
        profundo_ref = {"hoja": "valor_referencia"}
        profundo_obs = {"hoja": "valor_observado"}
        for _ in range(130):
            profundo_ref = {"nivel": profundo_ref}
            profundo_obs = {"nivel": profundo_obs}
        base = {"estado": "ok", "consulta": "caso anidado",
                "documento": "DOC-ANIDADO", "version": "2026-01-01"}
        esperado = dict(base)
        observado = dict(base)
        # Solo cambia la hoja profunda, entre muchos campos iguales.
        for i in range(111):
            esperado[f"f_{i:03d}"] = "igual"
            observado[f"f_{i:03d}"] = "igual"
        esperado["z_anidado"] = profundo_ref
        observado["z_anidado"] = profundo_obs
        payload_esperado = json.loads(json.dumps(esperado))
        payload_esperado["texto_contexto"] = texto
        sello_esperado, _, _ = _sello_de(payload_esperado)
        payload_real = json.loads(json.dumps(observado))
        payload_real["texto_contexto"] = texto
        _, sha_texto, _normalizado = _sello_de(payload_real)
        ref = json.loads(json.dumps(esperado))
        ref["texto_contexto_sha256"] = sha_texto
        caso = {"fixture": "fix-profundo", "id": "ctx-profundo",
                "consulta": base["consulta"], "documento": base["documento"],
                "version": base["version"], "respuesta_sha256": sello_esperado,
                "respuesta_referencia": ref}
        falso = _FalsoHTTP(200, _json_bytes(payload_real))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_contexto(caso, URL_BASE)
        # El sello completo si captura la diferencia profunda.
        self.assertEqual(resultado["resultado"], "diferencia")
        self.assertEqual(resultado["diferencias"][0],
                         {"ruta": "$", "tipo": "respuesta_completa_distinta"})
        self.assertNotEqual(resultado["hashes"]["respuesta_normalizada_sha256"],
                            caso["respuesta_sha256"])
        # Tanto el sello completo como el diagnóstico detectan la hoja.
        self.assertEqual(len(resultado["diferencias"]), 2)
        rutas = [d["ruta"] for d in resultado["diferencias"]]
        self.assertTrue(any("z_anidado" in r and r.endswith(".hoja") for r in rutas))
        self.assertEqual(resultado["diferencias_total"], 2)


class TestCasoCompat(BasePrueba):

    def test_url_con_q_doc_y_version(self):
        caso, cuerpo = _caso_compat_ok()
        falso = _FalsoHTTP(200, cuerpo)
        with mock.patch.object(RUNNER, "_http_get", falso):
            RUNNER._caso_compat(caso, URL_BASE)
        self.assertEqual(falso.urls[0], URL_BASE + "/buscar?"
                         + urllib.parse.urlencode({"q": caso["consulta"],
                                                   "doc": caso["documento"],
                                                   "version": caso["version"]}))

    def test_coincide_status_y_sha_del_cuerpo(self):
        caso, cuerpo = _caso_compat_ok()
        falso = _FalsoHTTP(200, cuerpo)
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_compat(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "coincide")
        self.assertEqual(resultado["diferencias"], [])
        self.assertEqual(resultado["diferencias_total"], 0)
        self.assertEqual(resultado["estados"], {"http": 200, "esperado": 200})
        self.assertEqual(resultado["hashes"]["sha256_cuerpo"],
                         caso["http_legacy"]["sha256_cuerpo"])
        self.assertEqual(resultado["hashes"]["longitud_cuerpo"], len(cuerpo))
        self.assertEqual(resultado["primarios"],
                         {"status": 200,
                          "sha256_cuerpo": caso["http_legacy"]["sha256_cuerpo"]})

    def test_diferencia_por_status_y_por_sha256(self):
        caso, cuerpo = _caso_compat_ok()
        caso = dict(caso)
        caso["http_legacy"] = {"status": 404, "sha256_cuerpo": "0" * 64}
        falso = _FalsoHTTP(200, cuerpo)
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_compat(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "diferencia")
        self.assertEqual(resultado["diferencias_total"], 2)
        rutas = {d["ruta"] for d in resultado["diferencias"]}
        self.assertEqual(rutas, {"status_http", "sha256_cuerpo"})
        self.assertEqual(resultado["estados"], {"http": 200, "esperado": 404})

    def test_error_timeout_cliente_sin_cuerpo_crudo(self):
        caso, _cuerpo = _caso_compat_ok()
        falso = _FalsoHTTP(error=TimeoutError("pasado el plazo del cliente"))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_compat(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "error")
        self.assertEqual(resultado["error"], "timeout_cliente")
        self.assertEqual(resultado["estados"], {"http": None})
        self.assertNotIn("hashes", resultado)


class TestCasoAuto(BasePrueba):

    def test_positivo_realista_coincide(self):
        caso, payload, sha_lectura = _caso_auto_ok()
        falso = _FalsoHTTP(200, _json_bytes(payload))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_auto(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "coincide")
        self.assertEqual(resultado["diferencias"], [])
        self.assertEqual(resultado["diferencias_total"], 0)
        self.assertEqual(resultado["estados"], {"http": 200, "respuesta": "ok"})
        # URL /buscar solo con q (el gold jamas viaja en la peticion).
        self.assertEqual(len(falso.urls), 1)
        self.assertEqual(falso.urls[0], URL_BASE + "/buscar?"
                         + urllib.parse.urlencode({"q": caso["consulta"]}))
        # Lecturas normalizadas (documento, version, sha256, pagina fisica).
        self.assertEqual(resultado["hashes"]["sha256_lecturas"], [sha_lectura])
        self.assertEqual(resultado["paginas"], {"BOCM_supl_126_2023": [3]})
        primarios = resultado["primarios"]
        self.assertEqual(primarios["estado"], "ok")
        self.assertEqual(primarios["clave_lecturas_observada"], "lecturas")
        self.assertEqual(primarios["clave_lecturas_referencia"], "paginas")
        self.assertEqual(primarios["total_lecturas"], 1)
        self.assertEqual(primarios["lecturas"],
                         [{"doc": "BOCM_supl_126_2023",
                           "version": "2023-05-29", "sha256": sha_lectura,
                           "pagina": 3}])

    def test_status_500_con_estado_y_aclaracion_iguales(self):
        caso, payload, _sha = _caso_auto_ok()
        falso = _FalsoHTTP(500, _json_bytes(payload))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_auto(caso, URL_BASE)
        self.assertEqual(resultado["estados"]["http"], 500)
        self.assertEqual(resultado["resultado"], "diferencia")
        # Estado y aclaracion son iguales; la unica diferencia es el status.
        self.assertEqual(len(resultado["diferencias"]), 1)
        self.assertEqual(resultado["diferencias"][0],
                         {"ruta": "http", "tipo": "valor",
                          "referencia": 200, "observado": 500})
        rutas = {d["ruta"] for d in resultado["diferencias"]}
        self.assertNotIn("estado", rutas)
        self.assertNotIn("aclaracion", rutas)

    def test_documentos_ausentes_se_detectan(self):
        caso, payload, _sha = _caso_auto_ok()
        payload_sin_tarjetas = json.loads(json.dumps(payload))
        payload_sin_tarjetas.pop("documentos")
        falso = _FalsoHTTP(200, _json_bytes(payload_sin_tarjetas))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_auto(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "diferencia")
        rutas = {d["ruta"] for d in resultado["diferencias"]}
        self.assertIn("tarjetas_ids", rutas)
        self.assertIn("documentos.titulo", rutas)
        # tarjetas_ids + los 8 campos de tarjeta comparados por el runner.
        self.assertEqual(len(resultado["diferencias"]), 9)
        self.assertEqual(resultado["estados"]["respuesta"], "ok")

    def test_lecturas_erradas_se_detectan(self):
        caso, payload, _sha = _caso_auto_ok()
        payload_malas = json.loads(json.dumps(payload))
        payload_malas["lecturas"][0]["sha256"] = "b" * 64
        falso = _FalsoHTTP(200, _json_bytes(payload_malas))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_auto(caso, URL_BASE)
        self.assertEqual(resultado["resultado"], "diferencia")
        sha_ref = caso["respuesta_referencia"]["paginas"][0]["sha256"]
        # La diferencia describe ambos lados con _lecturas_desc (doc/version/
        # sha256/pagina); nunca el contenido crudo.
        self.assertEqual(resultado["diferencias"], [{
            "ruta": "lecturas", "tipo": "conjunto",
            "referencia": [{"doc": "BOCM_supl_126_2023", "version": "2023-05-29",
                            "sha256": sha_ref, "pagina": 3}],
            "observado": [{"doc": "BOCM_supl_126_2023", "version": "2023-05-29",
                           "sha256": "b" * 64, "pagina": 3}],
        }])
        self.assertEqual(resultado["hashes"]["sha256_lecturas"], ["b" * 64])

    def test_estado_vacio_no_puede_traer_tarjetas_ni_lecturas(self):
        caso, payload, _sha = _caso_auto_ok()
        caso_estado = json.loads(json.dumps(caso))
        payload_estado = json.loads(json.dumps(payload))
        caso_estado["respuesta_referencia"]["estado"] = "aclaracion_necesaria"
        payload_estado["estado"] = "aclaracion_necesaria"
        # Listas NO vacias con estado vacio: el protector debe saltar solo.
        falso = _FalsoHTTP(200, _json_bytes(payload_estado))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado = RUNNER._caso_auto(caso_estado, URL_BASE)
        self.assertEqual(resultado["resultado"], "diferencia")
        self.assertEqual(resultado["diferencias"],
                         [{"ruta": "tarjetas_lecturas",
                           "tipo": "no_vacios_en_estado",
                           "estado": "aclaracion_necesaria",
                           "tarjetas": 1, "lecturas": 1}])


class TestPedirJson(BasePrueba):

    def _caso(self, cid="c1"):
        return {"fixture": "f", "id": cid}

    def test_exito_objeto_json(self):
        falso = _FalsoHTTP(200, _json_bytes({"estado": "ok"}))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado, payload = RUNNER._pedir_json(
                self._caso(), URL_BASE + "/contexto")
        self.assertEqual(payload, {"estado": "ok"})
        self.assertEqual(resultado["resultado"], "coincide")
        self.assertEqual(resultado["estados"], {"http": 200})
        self.assertNotIn("hashes", resultado)

    def test_cuerpo_no_json_y_respuesta_no_objeto(self):
        falso = _FalsoHTTP(200, b"<html>no es json</html>")
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado, payload = RUNNER._pedir_json(self._caso(), URL_BASE)
        self.assertIsNone(payload)
        self.assertEqual(resultado["resultado"], "error")
        self.assertEqual(resultado["error"], "cuerpo_no_json")

        falso = _FalsoHTTP(200, _json_bytes([1, 2, 3]))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado, payload = RUNNER._pedir_json(self._caso(), URL_BASE)
        self.assertIsNone(payload)
        self.assertEqual(resultado["resultado"], "error")
        self.assertEqual(resultado["error"], "respuesta_no_objeto")

    def test_errores_de_conexion_y_timeout(self):
        # URLError con razon TimeoutError se clasifica como timeout_cliente.
        falso = _FalsoHTTP(error=urllib.error.URLError(
            TimeoutError("pasado el plazo")))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado, payload = RUNNER._pedir_json(self._caso(), URL_BASE)
        self.assertIsNone(payload)
        self.assertEqual(resultado["error"], "timeout_cliente")
        self.assertEqual(resultado["estados"], {"http": None})

        # OSError/ConnectionError directos se clasifican como conexion.
        falso = _FalsoHTTP(error=ConnectionError("conexion rechazada"))
        with mock.patch.object(RUNNER, "_http_get", falso):
            resultado, payload = RUNNER._pedir_json(self._caso(), URL_BASE)
        self.assertIsNone(payload)
        self.assertEqual(resultado["error"], "conexion")
        self.assertEqual(resultado["estados"], {"http": None})


if __name__ == "__main__":
    unittest.main()
