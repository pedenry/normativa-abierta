#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regresión HTTP de recuperación territorial contra servidor real en loopback.

Ejecuta los casos de la referencia congelada contra un servidor HTTP real en
127.0.0.1 (sin modelos, sin red externa, sin reintentos, sin mocks) y compara
las respuestas normalizadas con la captura anterior guardada en la referencia. Esta
(respuesta_referencia / http_legacy) nunca se envía al motor: las peticiones
llevan únicamente q/doc/version según el modo.

Modos:
  (defecto)      GET /contexto con q/doc/version por caso; compara el JSON
                 normalizado (sin contenido/tiempo_ms/texto_contexto, con
                 texto_contexto_sha256 del literal entero) contra
                 respuesta_referencia y exige ausencia de "contenido" en HTTP.
  --compat       GET /buscar con doc/version para los casos con http_legacy;
                 compara status y SHA-256 exacto del cuerpo.
  --buscar-auto  GET /buscar sin doc (solo q) para los casos sin http_legacy;
                 compara estado/consulta/aclaracion, ids de tarjetas en orden
                 y el conjunto de lecturas (documento, version, sha256,
                 pagina) contra paginas de la referencia (clave "doc"); exige
                 cero tarjetas/lecturas en aclaracion/sin_resultados.

El informe (JSON dentro de .local/) guarda estados, hashes, paginas,
primarios y diferencias por caso; nunca el contexto completo, rutas absolutas
ni errores crudos. Valida los SHA-256 de los fixtures contra la tabla y no
modifica nunca la referencia, los casos ni el corpus.

Exit: 0 todas las comparaciones coinciden; 1 algún error o diferencia;
      2 problema de configuración o bloqueo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DIR_AQUI = Path(__file__).resolve().parent
DIR_RUNTIME = RAIZ / "experimentos" / "http-local"
RUTA_REFERENCIA_DEFECTO = DIR_AQUI / "referencia-http-2026-11-16.json"
DIR_LOCAL = RAIZ / ".local" / "http-integracion"

# Los 3 módulos de runtime y acceso.py: mismos archivos que codigo_origen_sha256
# de la referencia.
ARCHIVOS_RUNTIME = ("acceso.py", "adaptador_contexto.py", "http_consulta.py", "servicio_publico.py")
CLAVES_A_QUITAR = ("contenido", "tiempo_ms", "texto_contexto")
CLAVE_SHA_CONTEXTO = "texto_contexto_sha256"
ESTADOS_VACIOS = ("aclaracion_necesaria", "sin_resultados")
ESPERADO_CASOS = {"contexto": 91, "compat": 48, "buscar_auto": 43}
TIMEOUT_CLIENTE_S = 45.0
LIMITE_DIFERENCIAS_INFORME = 20
LIMITE_RECORRIDO = 100
LIMITE_ITEMS_LISTA = 30
ANCHO_TEXTO_LIBRE = 80

CRITERIOS = {
    "contexto": [
        "igualdad del JSON normalizado: sin contenido/tiempo_ms/texto_contexto, "
        "con texto_contexto_sha256 del literal entero",
        "ausencia de la clave 'contenido' en la respuesta HTTP",
    ],
    "compat": [
        "status HTTP igual a http_legacy.status",
        "sha256 del cuerpo igual a http_legacy.sha256_cuerpo (exacto)",
    ],
    "buscar_auto": [
        "estado igual",
        "consulta igual",
        "aclaracion igual",
        "ids de tarjetas iguales en orden",
        "conjunto de lecturas (documento, version, sha256, pagina) igual a "
        "paginas de la referencia (clave 'doc')",
        "cero tarjetas y lecturas cuando el estado es aclaracion o sin_resultados",
    ],
}

# Cliente sin proxies: todo el tráfico queda confinado a 127.0.0.1 (loopback real).
_ABRIDOR = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# ------------------------------------------------------------------ utilidades

def _sha_bytes(datos):
    return hashlib.sha256(datos).hexdigest()


def _sha_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _ruta_rel(ruta):
    """Ruta relativa a RAIZ; fuera de RAIZ, solo el nombre (sin rutas absolutas)."""
    try:
        return ruta.resolve().relative_to(RAIZ).as_posix()
    except (ValueError, OSError):
        return ruta.name


def _acotar_mensaje(exc, ancho=300):
    return " ".join(str(exc).split())[:ancho]


def _config_exit(*lineas):
    for linea in lineas:
        print(f"CONFIG/BLOQUEO: {linea}")
    raise SystemExit(2)


def _describir(valor):
    """Descripción compacta y segura: textos largos solo como SHA-256."""
    if isinstance(valor, str):
        if len(valor) > ANCHO_TEXTO_LIBRE:
            return {"texto_sha256": _sha_texto(valor), "longitud": len(valor)}
        return valor
    if isinstance(valor, (dict, list)):
        try:
            canonico = json.dumps(valor, ensure_ascii=False, sort_keys=True, default=str)
        except (TypeError, ValueError):
            canonico = repr(valor)
        return {
            "estructura": "objeto" if isinstance(valor, dict) else "lista",
            "tamano": len(valor),
            "sha256": _sha_texto(canonico),
        }
    if valor is None or isinstance(valor, (bool, int, float)):
        return valor
    return repr(valor)


def _acotar_lista(lista, maximo=LIMITE_ITEMS_LISTA):
    if not isinstance(lista, list):
        return _describir(lista)
    corta = len(lista) <= maximo and all(
        v is None
        or isinstance(v, (bool, int, float))
        or (isinstance(v, str) and len(v) <= ANCHO_TEXTO_LIBRE)
        for v in lista
    )
    if corta:
        return lista
    try:
        canonico = json.dumps(lista, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        canonico = repr(lista)
    return {"total": len(lista), "sha256": _sha_texto(canonico)}


def _diferencias(ref, obs, ruta="$", salida=None, estado=None):
    """Recorrido estructural ref vs obs; describe valores sin volcar textos largos."""
    if salida is None:
        salida = []
    if estado is None:
        estado = {"total": 0}
    if estado["total"] >= LIMITE_RECORRIDO:
        return salida
    if isinstance(ref, dict) and isinstance(obs, dict):
        for clave in sorted(set(ref) | set(obs)):
            if estado["total"] >= LIMITE_RECORRIDO:
                break
            sub = f"{ruta}.{clave}"
            if clave not in ref:
                estado["total"] += 1
                if len(salida) < LIMITE_DIFERENCIAS_INFORME:
                    salida.append({"ruta": sub, "tipo": "solo_en_observado",
                                   "observado": _describir(obs[clave])})
            elif clave not in obs:
                estado["total"] += 1
                if len(salida) < LIMITE_DIFERENCIAS_INFORME:
                    salida.append({"ruta": sub, "tipo": "ausente_en_observado",
                                   "referencia": _describir(ref[clave])})
            else:
                _diferencias(ref[clave], obs[clave], sub, salida, estado)
    elif isinstance(ref, list) and isinstance(obs, list):
        if len(ref) != len(obs):
            estado["total"] += 1
            if len(salida) < LIMITE_DIFERENCIAS_INFORME:
                salida.append({"ruta": ruta, "tipo": "longitud_lista",
                               "referencia": len(ref), "observado": len(obs)})
        else:
            for i, (r, o) in enumerate(zip(ref, obs)):
                if estado["total"] >= LIMITE_RECORRIDO:
                    break
                _diferencias(r, o, f"{ruta}[{i}]", salida, estado)
    elif ref != obs:
        estado["total"] += 1
        if len(salida) < LIMITE_DIFERENCIAS_INFORME:
            salida.append({"ruta": ruta, "tipo": "valor",
                           "referencia": _describir(ref), "observado": _describir(obs)})
    return salida


# ------------------------------------------------------------- extracción JSON

def _campo_filas(fila, nombre):
    if isinstance(fila, dict):
        return fila.get(nombre)
    return getattr(fila, nombre, None)


def _documentos_de_filas(filas):
    documentos = set()
    if isinstance(filas, (list, tuple)):
        for fila in filas:
            valor = _campo_filas(fila, "documento")
            if isinstance(valor, str) and valor:
                documentos.add(valor)
    return sorted(documentos)


def _extraer_ids_tarjetas(valor):
    ids = []
    if isinstance(valor, list):
        for item in valor:
            ids.append((item.get("documento"), item.get("apartado_id"))
                       if isinstance(item, dict) else item)
    return ids


def _extraer_lecturas(valor):
    """Tuplas (documento, version, sha256, pagina); admite 'doc' o 'documento'."""
    tuplas = []
    if isinstance(valor, list):
        for item in valor:
            if isinstance(item, dict):
                doc = item.get("documento")
                if doc is None:
                    doc = item.get("doc")
                tuplas.append((doc, item.get("version"), item.get("sha256"), item.get("pagina")))
    return tuplas


def _conjunto_igual(a, b):
    try:
        return set(a) == set(b)
    except TypeError:
        canon = lambda seq: Counter(
            json.dumps(x, ensure_ascii=False, sort_keys=True, default=str) for x in seq
        )
        return canon(a) == canon(b)


def _lecturas_desc(tuplas, maximo=LIMITE_ITEMS_LISTA):
    items = [{"doc": d, "version": v, "sha256": s, "pagina": p}
             for (d, v, s, p) in sorted(tuplas, key=repr)]
    if len(items) <= maximo:
        return items
    canonico = json.dumps(items, ensure_ascii=False, sort_keys=True, default=str)
    return {"total": len(items), "sha256": _sha_texto(canonico)}


# ------------------------------------------------------------------- HTTP real

def _http_get(url):
    """GET real sobre loopback; sin reintentos. Devuelve (status, cuerpo bytes)."""
    peticion = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with _ABRIDOR.open(peticion, timeout=TIMEOUT_CLIENTE_S) as respuesta:
            return int(respuesta.status or 0), respuesta.read()
    except urllib.error.HTTPError as error:
        try:
            cuerpo = error.read()
        except Exception:
            cuerpo = b""
        return int(error.code or 0), cuerpo


def _arrancar_servidor(tipo, H, SP):
    direccion = ("127.0.0.1", 0)
    if tipo == "publico":
        semaforo = threading.BoundedSemaphore(SP.MAX_CONCURRENT)
        servidor = SP.Servidor(direccion, SP.Handler, semaforo)
    else:
        servidor = ThreadingHTTPServer(direccion, H.Handler)
    hilo = threading.Thread(target=servidor.serve_forever, name="servicio-http", daemon=True)
    hilo.start()
    return servidor, hilo, int(servidor.server_address[1])


def _cerrar_servidor(servidor, hilo):
    for paso in (servidor.shutdown, servidor.server_close):
        try:
            paso()
        except Exception:
            pass
    hilo.join(timeout=5.0)


# -------------------------------------------------------------------- casos

def _caso_base(caso):
    return {"fixture": caso.get("fixture"), "id": caso.get("id"),
            "resultado": "coincide", "diferencias": [], "diferencias_total": 0}


def _caso_error(caso, tipo):
    resultado = _caso_base(caso)
    resultado["resultado"] = "error"
    resultado["error"] = tipo  # taxonomía corta, nunca el error crudo
    resultado["estados"] = {"http": None}
    return resultado


def _pedir_json(caso, url):
    """GET + parse JSON; devuelve (resultado, payload) o (resultado_error, None)."""
    try:
        status, cuerpo = _http_get(url)
    except (TimeoutError, socket.timeout):
        return _caso_error(caso, "timeout_cliente"), None
    except urllib.error.URLError as exc:
        razon = getattr(exc, "reason", None)
        tipo = "timeout_cliente" if isinstance(razon, (TimeoutError, socket.timeout)) else "conexion"
        return _caso_error(caso, tipo), None
    except (ConnectionError, OSError):
        return _caso_error(caso, "conexion"), None
    base = _caso_base(caso)
    base["estados"] = {"http": status}
    base["hashes"] = {"cuerpo_sha256": _sha_bytes(cuerpo)}
    try:
        payload = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        base["resultado"] = "error"
        base["error"] = "cuerpo_no_json"
        return base, None
    if not isinstance(payload, dict):
        base["resultado"] = "error"
        base["error"] = "respuesta_no_objeto"
        return base, None
    base.pop("hashes")
    return base, payload


def _caso_contexto(caso, url_base):
    # Solo q/doc/version: el gold jamás viaja en la petición.
    params = {"q": caso.get("consulta"), "doc": caso.get("documento"), "version": caso.get("version")}
    params = {k: v for k, v in params.items() if v is not None}
    url = f"{url_base}/contexto?{urllib.parse.urlencode(params)}"
    resultado, payload = _pedir_json(caso, url)
    if payload is None:
        return resultado
    ref = caso["respuesta_referencia"]

    # Criterio: ausencia de "contenido" en la respuesta HTTP.
    if "contenido" in payload:
        resultado["diferencias"].append({"ruta": "contenido", "tipo": "clave_prohibida_en_http"})
        resultado["diferencias_total"] += 1

    texto = payload.get("texto_contexto")
    presente = "texto_contexto" in payload
    sha_texto = _sha_texto(texto) if isinstance(texto, str) else _sha_texto("")

    # Normalización: quitar contenido/tiempo_ms/texto_contexto y añadir el SHA
    # del literal entero; comparar contra respuesta_referencia.
    normalizado = {clave: valor for clave, valor in payload.items() if clave not in CLAVES_A_QUITAR}
    normalizado[CLAVE_SHA_CONTEXTO] = sha_texto
    sello = _sha_bytes(json.dumps(normalizado, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8"))
    if sello != caso["respuesta_sha256"]:
        resultado["diferencias"].append({"ruta": "$", "tipo": "respuesta_completa_distinta"})
        resultado["diferencias_total"] += 1
    # El modo del contador permanece cubierto por el sello de la respuesta
    # completa; no se duplica su etiqueta descriptiva en el informe legible.
    normalizado.pop("modo_tokens", None)
    if resultado["estados"]["http"] != 200:
        resultado["diferencias"].append({"ruta": "http", "tipo": "status_distinto_de_200"})
        resultado["diferencias_total"] += 1

    resultado["estados"]["respuesta"] = payload.get("estado")
    resultado["hashes"] = {"texto_contexto_sha256": sha_texto,
                           "respuesta_normalizada_sha256": sello,
                           "texto_contexto_sha256_esperado": ref.get(CLAVE_SHA_CONTEXTO),
                           "texto_contexto_presente": presente}
    resultado["primarios"] = (payload.get("recuperacion") or {}).get("resultados") or []
    resultado["paginas"] = payload.get("paginas") or []
    contador = {"total": 0}
    _diferencias(ref, normalizado, "$", resultado["diferencias"], contador)
    resultado["diferencias_total"] += contador["total"]
    if resultado["diferencias"]:
        resultado["resultado"] = "diferencia"
    return resultado


def _caso_compat(caso, url_base):
    params = {"q": caso.get("consulta"), "doc": caso.get("documento"), "version": caso.get("version")}
    params = {k: v for k, v in params.items() if v is not None}
    url = f"{url_base}/buscar?{urllib.parse.urlencode(params)}"
    legacy = caso["http_legacy"]
    try:
        status, cuerpo = _http_get(url)
    except (TimeoutError, socket.timeout):
        return _caso_error(caso, "timeout_cliente")
    except urllib.error.URLError as exc:
        razon = getattr(exc, "reason", None)
        tipo = "timeout_cliente" if isinstance(razon, (TimeoutError, socket.timeout)) else "conexion"
        return _caso_error(caso, tipo)
    except (ConnectionError, OSError):
        return _caso_error(caso, "conexion")
    resultado = _caso_base(caso)
    sha_cuerpo = _sha_bytes(cuerpo)
    resultado["estados"] = {"http": status, "esperado": legacy.get("status")}
    resultado["hashes"] = {"sha256_cuerpo": sha_cuerpo,
                           "sha256_cuerpo_esperado": legacy.get("sha256_cuerpo"),
                           "longitud_cuerpo": len(cuerpo)}
    resultado["primarios"] = {"status": status, "sha256_cuerpo": sha_cuerpo}
    contador = 0
    if "status" in legacy and status != legacy.get("status"):
        contador += 1
        resultado["diferencias"].append({"ruta": "status_http", "tipo": "valor",
                                         "referencia": legacy.get("status"), "observado": status})
    if sha_cuerpo != legacy.get("sha256_cuerpo"):
        contador += 1
        resultado["diferencias"].append({"ruta": "sha256_cuerpo", "tipo": "valor",
                                         "referencia": legacy.get("sha256_cuerpo"),
                                         "observado": sha_cuerpo})
    resultado["diferencias_total"] = contador
    if resultado["diferencias"]:
        resultado["resultado"] = "diferencia"
    return resultado


def _caso_auto(caso, url_base):
    params = {"q": caso.get("consulta")}
    url = f"{url_base}/buscar?{urllib.parse.urlencode(params)}"
    resultado, payload = _pedir_json(caso, url)
    if payload is None:
        return resultado
    ref = caso["respuesta_referencia"]

    estado_obs = payload.get("estado")
    ids_obs = _extraer_ids_tarjetas(payload.get("documentos"))
    clave_obs = "lecturas" if "lecturas" in payload else ("paginas" if "paginas" in payload else None)
    lecturas_obs = _extraer_lecturas(payload.get(clave_obs)) if clave_obs else []
    clave_ref = "paginas" if "paginas" in ref else ("lecturas" if "lecturas" in ref else None)
    lecturas_ref = _extraer_lecturas(ref.get(clave_ref)) if clave_ref else []

    paginas = {}
    for doc, _version, _sha, pagina in lecturas_obs:
        clave = doc if isinstance(doc, str) and doc else "(sin doc)"
        if pagina not in paginas.setdefault(clave, []):
            paginas[clave].append(pagina)
    for lista in paginas.values():
        lista.sort()

    resultado["estados"]["respuesta"] = estado_obs
    resultado["hashes"] = {"sha256_lecturas": sorted(
        {sha for (_d, _v, sha, _p) in lecturas_obs if isinstance(sha, str)})}
    resultado["paginas"] = paginas
    resultado["primarios"] = {"estado": estado_obs,
                              "aclaracion": _describir(payload.get("aclaracion")),
                              "ids_tarjetas": _acotar_lista(ids_obs),
                              "clave_lecturas_observada": clave_obs,
                              "clave_lecturas_referencia": clave_ref,
                              "total_lecturas": len(lecturas_obs),
                              "lecturas": _lecturas_desc(lecturas_obs)}

    contador = {"total": 0}
    diferencias = resultado["diferencias"]

    def _dif(ruta, esperado, observado, acotar=None):
        if esperado != observado:
            contador["total"] += 1
            if len(diferencias) < LIMITE_DIFERENCIAS_INFORME:
                diferencias.append({"ruta": ruta, "tipo": "valor",
                                    "referencia": acotar(esperado) if acotar else _describir(esperado),
                                    "observado": acotar(observado) if acotar else _describir(observado)})

    _dif("http", 200, resultado["estados"]["http"])
    _dif("estado", ref.get("estado"), estado_obs)
    _dif("consulta", ref.get("consulta"), payload.get("consulta"))
    _dif("aclaracion", ref.get("aclaracion"), payload.get("aclaracion"))
    _dif("tarjetas_ids", _extraer_ids_tarjetas((ref.get("recuperacion") or {}).get("resultados")), ids_obs, acotar=_acotar_lista)
    for campo in ("version", "id_tecnico", "apartado_id", "titulo", "puntuacion_bm25", "paginas", "cita", "paginas_entregadas"):
        _dif("documentos." + campo,
             [r.get(campo) for r in (ref.get("recuperacion") or {}).get("resultados", [])],
             [r.get(campo) for r in payload.get("documentos", [])])
    _dif("resolucion_ambito", ref.get("resolucion_ambito"), payload.get("resolucion_ambito"))
    _dif("advertencias", (ref.get("recuperacion") or {}).get("advertencias") or [], payload.get("advertencias"))
    if not _conjunto_igual(lecturas_ref, lecturas_obs):
        contador["total"] += 1
        if len(diferencias) < LIMITE_DIFERENCIAS_INFORME:
            diferencias.append({"ruta": "lecturas", "tipo": "conjunto",
                                "referencia": _lecturas_desc(lecturas_ref),
                                "observado": _lecturas_desc(lecturas_obs)})
    if estado_obs in ESTADOS_VACIOS and (ids_obs or lecturas_obs):
        contador["total"] += 1
        if len(diferencias) < LIMITE_DIFERENCIAS_INFORME:
            diferencias.append({"ruta": "tarjetas_lecturas", "tipo": "no_vacios_en_estado",
                                "estado": estado_obs,
                                "tarjetas": len(ids_obs), "lecturas": len(lecturas_obs)})
    resultado["diferencias_total"] = contador["total"]
    if diferencias:
        resultado["resultado"] = "diferencia"
    return resultado


# ------------------------------------------------------------------- ejecución

def _ejecutar(seleccion, modo, url_base):
    corredor = {"contexto": _caso_contexto, "compat": _caso_compat, "buscar_auto": _caso_auto}[modo]
    total = len(seleccion)
    conteo_fixtures = Counter(c.get("fixture") for c in seleccion)
    vistos = set()
    resultados = []
    for indice, caso in enumerate(seleccion, 1):
        fixture = caso.get("fixture")
        if fixture not in vistos:
            vistos.add(fixture)
            print(f"-- fixture {len(vistos)}/{len(conteo_fixtures)}: {fixture} ({conteo_fixtures[fixture]} casos)")
        try:
            resultado = corredor(caso, url_base)
        except Exception as exc:  # blindaje: el fallo de un caso no aborta la ronda
            resultado = _caso_error(caso, f"excepcion_interna:{type(exc).__name__}")
        resultados.append(resultado)
        detalle = f" ({resultado['diferencias_total']} diferencias)" if resultado["resultado"] == "diferencia" else ""
        print(f"   [{indice}/{total}] {caso.get('id')}: {resultado['resultado']}{detalle}")
    return resultados


def _validar_estructura(referencia):
    problemas = []
    if not isinstance(referencia, dict):
        return ["la referencia no es un objeto JSON"]
    if not isinstance(referencia.get("fixtures_sha256"), dict) or not referencia["fixtures_sha256"]:
        problemas.append("fixtures_sha256 ausente o no es objeto")
    if not isinstance(referencia.get("casos"), list) or not referencia["casos"]:
        problemas.append("casos ausente o vacio")
    if not isinstance(referencia.get("parametros"), dict):
        problemas.append("parametros ausente o no es objeto")
    return problemas


def _validar_fixtures(tabla, casos):
    """SHA-256 de cada fixture contra la tabla; elige la base por sondeo de existencia."""
    problemas = []
    base = None
    for candidato in (DIR_AQUI.parent, DIR_AQUI, RAIZ):
        if all((candidato / clave).is_file() for clave in tabla):
            base = candidato
            break
    if base is None:
        base = DIR_AQUI.parent
    coinciden = 0
    for clave in sorted(tabla):
        ruta = base / clave
        if not ruta.is_file():
            problemas.append(f"{clave}: archivo no encontrado")
            continue
        if _sha_bytes(ruta.read_bytes()) == tabla[clave]:
            coinciden += 1
        else:
            problemas.append(f"{clave}: sha256 distinto")
    vistos = set()
    for caso in casos:
        fixture = caso.get("fixture")
        if fixture not in tabla and fixture not in vistos:
            vistos.add(fixture)
            problemas.append(f"caso {caso.get('id')}: fixture sin entrada en fixtures_sha256")
    return base, coinciden, problemas


def _validar_casos(seleccion, modo):
    problemas = []
    for caso in seleccion:
        cid = caso.get("id")
        if modo == "compat":
            legacy = caso.get("http_legacy")
            if not isinstance(legacy, dict):
                problemas.append(f"caso {cid}: http_legacy no es objeto")
                continue
            if not legacy.get("sha256_cuerpo"):
                problemas.append(f"caso {cid}: http_legacy sin sha256_cuerpo")
            if caso.get("documento") is None or caso.get("version") is None:
                problemas.append(f"caso {cid}: falta documento o version")
        elif modo == "buscar_auto":
            if caso.get("consulta") is None:
                problemas.append(f"caso {cid}: falta consulta")
            if not isinstance(caso.get("respuesta_referencia"), dict):
                problemas.append(f"caso {cid}: respuesta_referencia no es objeto")
        else:
            for campo in ("consulta", "documento", "version", "respuesta_sha256"):
                if campo not in caso or (campo in ("consulta", "respuesta_sha256") and not caso[campo]):
                    problemas.append(f"caso {cid}: falta {campo}")
            if not isinstance(caso.get("respuesta_referencia"), dict):
                problemas.append(f"caso {cid}: respuesta_referencia no es objeto")
    return problemas


def _hashes_runtime(codigo_origen):
    hashes = {}
    for nombre in ARCHIVOS_RUNTIME:
        ruta = DIR_RUNTIME / nombre
        sha = _sha_bytes(ruta.read_bytes()) if ruta.is_file() else None
        coincide = None
        if nombre in codigo_origen:
            coincide = (sha == codigo_origen[nombre])
        hashes[nombre] = {"sha256": sha, "coincide_codigo_origen": coincide}
    return hashes


def _informe(modo, tipo_servidor, puerto, referencia, ruta_ref, bytes_ref,
             base_fixtures, coinciden_fixtures, resultados):
    codigo_origen = referencia.get("codigo_origen_sha256")
    codigo_origen = codigo_origen if isinstance(codigo_origen, dict) else {}
    conteo = Counter(r["resultado"] for r in resultados)
    return {
        "metadata": {
            "script": "evaluacion/regresion_recuperacion/territorial/ejecutar_http.py",
            "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ejecucion": {
                "servidor": tipo_servidor,
                "modo": modo,
                "url_base": f"http://127.0.0.1:{puerto}",
                "puerto": puerto,
                "orden": "orden de la referencia, sin reordenar",
                "reintentos": 0,
                "mocks": False,
                "timeout_cliente_s": TIMEOUT_CLIENTE_S,
                "alcance_red": "solo loopback 127.0.0.1, sin proxies",
                "motor_modelos": "ninguno (solo HTTP real)",
            },
            "criterios": CRITERIOS,
            "referencia": {
                "archivo": _ruta_rel(ruta_ref),
                "sha256": _sha_bytes(bytes_ref),
                "esquema": referencia.get("esquema"),
                "fecha": referencia.get("fecha"),
                "commit_origen": referencia.get("commit_origen"),
                "parametros": referencia.get("parametros"),
            },
            "hashes_runtime": _hashes_runtime(codigo_origen),
        },
        "validacion_fixtures": {
            "base": _ruta_rel(base_fixtures),
            "total": len(referencia["fixtures_sha256"]),
            "coinciden": coinciden_fixtures,
            "problemas": [],
        },
        "casos": resultados,
        "resumen": {
            "casos": len(resultados),
            "coinciden": conteo.get("coincide", 0),
            "diferencias": conteo.get("diferencia", 0),
            "errores": conteo.get("error", 0),
            "esperado_casos": ESPERADO_CASOS[modo],
            "exit": 0 if (conteo.get("diferencia", 0) + conteo.get("error", 0)) == 0 else 1,
        },
    }


def _argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Regresion HTTP de recuperacion territorial contra servidor real en "
                    "127.0.0.1 (sin modelos, sin red externa, sin reintentos).",
        allow_abbrev=False,
    )
    parser.add_argument("--servidor", choices=("local", "publico"), default="publico",
                        help="publico usa SP.validar + SP.Servidor; local usa ThreadingHTTPServer con H.Handler")
    parser.add_argument("--referencia", default=None,
                        help="ruta del JSON de referencia (por defecto la congelada junto a este script)")
    parser.add_argument("--salida", default=None,
                        help="ruta del informe JSON (por defecto dentro de .local/ junto a este script)")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--compat", action="store_true",
                       help="GET /buscar con doc/version contra http_legacy (sha exacto del cuerpo)")
    grupo.add_argument("--buscar-auto", action="store_true",
                       help="GET /buscar sin doc; comparacion dirigida contra respuesta_referencia")
    return parser.parse_args(argv)


def main(argv=None):
    args = _argumentos(argv)
    modo = "compat" if args.compat else ("buscar_auto" if args.buscar_auto else "contexto")

    ruta_ref = Path(args.referencia) if args.referencia else RUTA_REFERENCIA_DEFECTO
    if not ruta_ref.is_file():
        _config_exit(f"referencia no encontrada: {_ruta_rel(ruta_ref)}")
    bytes_ref = ruta_ref.read_bytes()
    try:
        referencia = json.loads(bytes_ref.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        _config_exit(f"la referencia no es JSON valido ({type(exc).__name__})")

    problemas = _validar_estructura(referencia)
    if problemas:
        _config_exit(*problemas)

    base_fixtures, coinciden_fixtures, problemas = _validar_fixtures(
        referencia["fixtures_sha256"], referencia["casos"])
    if problemas:
        _config_exit("validacion de fixtures:", *problemas)

    casos = referencia["casos"]
    if modo == "compat":
        seleccion = [c for c in casos if isinstance(c.get("http_legacy"), dict)]
    elif modo == "buscar_auto":
        seleccion = [c for c in casos if not isinstance(c.get("http_legacy"), dict)]
    else:
        seleccion = list(casos)
    problemas = _validar_casos(seleccion, modo)
    if len(seleccion) != ESPERADO_CASOS[modo]:
        problemas.append("numero de casos inesperado")
    if problemas:
        _config_exit(*problemas)

    # Runtime: RAIZ + experimentos/http-local; singleton ESTADO via inicializar_estado.
    if not DIR_RUNTIME.is_dir():
        _config_exit("no existe experimentos/http-local en la raiz del checkout interior")
    hashes_antes = _hashes_runtime({})
    runner_antes = _sha_bytes(Path(__file__).read_bytes())
    sys.path.insert(0, str(DIR_RUNTIME))
    try:
        import http_consulta as H
    except Exception as exc:
        _config_exit(f"bloqueo: no se pudo importar http_consulta "
                     f"({type(exc).__name__}: {_acotar_mensaje(exc)})")
    try:
        import servicio_publico as SP
    except Exception as exc:
        _config_exit(f"bloqueo: no se pudo importar servicio_publico "
                     f"({type(exc).__name__}: {_acotar_mensaje(exc)})")

    if not hasattr(H, "inicializar_estado"):
        _config_exit("bloqueo: http_consulta sin inicializar_estado (lo agrega otro encargo)")
    try:
        H.inicializar_estado(RAIZ / "contenido")
    except Exception as exc:
        _config_exit(f"bloqueo: inicializar_estado fallo ({type(exc).__name__}: {_acotar_mensaje(exc)})")
    if not hasattr(H, "ESTADO"):
        _config_exit("bloqueo: http_consulta sin ESTADO tras inicializar_estado")
    filas = H.ESTADO.get("filas")
    docs = H.ESTADO.get("docs")
    if not docs:
        _config_exit("no se pudieron derivar documentos desde ESTADO.filas (estructura inesperada)")

    if args.servidor == "publico":
        for atributo in ("validar", "Servidor", "Handler", "MAX_CONCURRENT"):
            if not hasattr(SP, atributo):
                _config_exit(f"bloqueo: servicio_publico sin {atributo}")
        try:
            SP.validar(filas, docs)
        except Exception as exc:
            _config_exit(f"bloqueo: SP.validar rechazo el corpus publico "
                         f"({type(exc).__name__}: {_acotar_mensaje(exc)})")
    elif not hasattr(H, "Handler"):
        _config_exit("bloqueo: http_consulta sin Handler")

    try:
        servidor, hilo, puerto = _arrancar_servidor(args.servidor, H, SP)
    except Exception as exc:
        _config_exit(f"bloqueo: no se pudo arrancar el servidor {args.servidor} "
                     f"({type(exc).__name__}: {_acotar_mensaje(exc)})")

    url_base = f"http://127.0.0.1:{puerto}"
    print(f"Servidor {args.servidor} en {url_base} | modo {modo} | {len(seleccion)} casos "
          f"| sin reintentos, sin mocks, solo loopback")
    try:
        resultados = _ejecutar(seleccion, modo, url_base)
    finally:
        _cerrar_servidor(servidor, hilo)

    ruta_salida = (Path(args.salida) if args.salida
                   else DIR_LOCAL / f"informe-http-{modo}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    informe = _informe(modo, args.servidor, puerto, referencia, ruta_ref, bytes_ref,
                       base_fixtures, coinciden_fixtures, resultados)
    estable = (hashes_antes == _hashes_runtime({}) and
               runner_antes == _sha_bytes(Path(__file__).read_bytes()) and
               _sha_bytes(bytes_ref) == _sha_bytes(ruta_ref.read_bytes()))
    informe["metadata"]["codigo_estable_durante_ejecucion"] = estable
    informe["metadata"]["runner_sha256"] = runner_antes
    if not estable:
        informe["resumen"]["exit"] = 2
    informe["metadata"]["salida"] = _ruta_rel(ruta_salida)
    try:
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_text(
            json.dumps(informe, ensure_ascii=False, indent=2, sort_keys=True, default=str),
            encoding="utf-8")
    except OSError as exc:
        _config_exit(f"no se pudo escribir el informe en {_ruta_rel(ruta_salida)} ({type(exc).__name__})")

    resumen = informe["resumen"]
    print(f"Resumen: casos={resumen['casos']} coincide={resumen['coinciden']} "
          f"diferencia={resumen['diferencias']} error={resumen['errores']} "
          f"(esperado {resumen['esperado_casos']}) -> exit {resumen['exit']}")
    print(f"Informe: {_ruta_rel(ruta_salida)}")
    return resumen["exit"]


if __name__ == "__main__":
    sys.exit(main())
