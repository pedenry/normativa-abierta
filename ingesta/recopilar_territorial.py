#!/usr/bin/env python3
"""Captura web reproducible de fuentes territoriales (autonomicas y municipales).

Objetivo: desde el catalogo declarativo ``fuentes-territoriales.json``
(17 CCAA + Ceuta + Melilla y 7 municipios), rastrear las paginas oficiales de
cada territorio y registrar candidatos de normativa de edificacion, urbanismo,
vivienda, accesibilidad y habitabilidad. Este script SOLO descubre y captura:
no afirma vigencia, no extrae texto normativo, no publica nada.

Seguridad y limites de red (fail-closed):
- Solo HTTPS y solo hosts de la allowlist de cada fuente, validados tambien en
  TODAS las redirecciones (esquema y host).
- robots.txt por host con cache: HTTP 404/410 permite el resto del sitio segun
  practica estandar; cualquier otro fallo (error de red, 5xx, 403) es
  fail-closed (se bloquea el host y se registra).
- Descarga secuencial con pausa >= 1 s (el argumento --pausa no puede bajar el
  minimo; Crawl-delay de robots lo sube si es mayor).
- Limites por pagina (bytes), por fuente (paginas) y de profundidad BFS.
- Solo HTML/texto; los PDF y otros binarios NUNCA se descargan: los enlaces
  PDF con palabras clave se registran como candidatos ``pdf_no_descargado``.
- Las semillas http se actualizan a HTTPS y se conserva la URL publicada.

Clasificacion honesta: las semillas y las paginas sin senales de materia se
guardan como ``portada_indice`` (contexto), NO como normas. Solo enlaces o
paginas con palabras clave (castellano + equivalentes cooficiales del
catalogo) se registran como candidatos y requieren revision humana.

Metadatos: cada pagina guarda SHA-256, fecha UTC de captura, estado HTTP, URL
final tras redirecciones y bytes. ``disposicion``, ``edicion`` y
``pagina_fisica`` quedan ``null``; ``vigencia``, ``licencia`` (por fuente),
``transitorio`` y ``fidelidad`` quedan PENDIENTES/NO COTEJADA hasta revision.

Uso:
    python ingesta/recopilar_territorial.py --listar
    python ingesta/recopilar_territorial.py [--catalogo RUTA] [--salida DIR]
        [--limite N] [--solo-id ID] [--max-paginas N] [--profundidad N]
        [--pausa S] [--timeout S]

La salida solo puede vivir dentro de ``.local/`` del checkout (gitignored):
cualquier otra ruta se rechaza. Ejecucion de red y pruebas: Codex.

Codigos de salida: 0 = todo ok; 1 = alguna fuente con error; 2 = error de
configuracion (catalogo ausente o invalido, --solo-id desconocido, --salida
fuera de .local/, semilla o hosts invalidos).
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

VERSION = "1.0"

CHECKOUT_RAIZ = Path(__file__).resolve().parent.parent
CATALOGO_DEFECTO = Path(__file__).resolve().parent / "fuentes-territoriales.json"
SALIDA_DEFECTO = CHECKOUT_RAIZ / ".local" / "territoriales"

PAUSA_MIN_S = 1.0
PAUSA_DEFECTO_S = 1.0
TIMEOUT_DEFECTO_S = 30
MAX_BYTES_PAGINA = 5 * 1024 * 1024
MAX_BYTES_ROBOTS = 1024 * 1024
MAX_PAGINAS_DEFECTO = 25
PROFUNDIDAD_DEFECTO = 2
TAMANO_BLOQUE = 64 * 1024
MAX_CANDIDATOS = 500
MAX_ERRORES = 200
MAX_REDIRECCIONES = 5
TOKEN_AGENTE = "normativa-abierta-ingesta-territorial"
USER_AGENT = f"{TOKEN_AGENTE}/{VERSION} (+https://github.com/pedenry/normativa-abierta)"
TIPOS_CONTENIDO = ("text/html", "application/xhtml+xml", "text/plain")
EXT_NO_RASTREABLES = (
    ".pdf", ".zip", ".rar", ".7z", ".gz", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".odt", ".ods", ".odp", ".jpg", ".jpeg", ".png", ".gif",
    ".svg", ".webp", ".mp3", ".mp4", ".avi", ".ics", ".rss", ".xml", ".json",
)
AVISO_PORTADAS = (
    "Las semillas y las paginas de contexto son portadas o indices, no normas. "
    "Solo los candidatos con palabras clave requieren revision humana; nada de "
    "lo capturado se declara norma, ni vigente ni aplicable."
)
PENDIENTES = {
    "disposicion": None,
    "edicion": None,
    "pagina_fisica": None,
    "vigencia": "PENDIENTE: requiere ambito y regimen transitorio por fuente",
    "licencia": "PENDIENTE por fuente: revisar el aviso legal del portal antes de publicar",
    "transitorio": "PENDIENTE",
    "fidelidad": "NO COTEJADA: captura automatica sin revision humana",
}


class FalloConfig(Exception):
    """Error de configuracion: termina con codigo 2."""


class FalloPermanente(Exception):
    """Error de captura que no debe reintentarse."""


class NoSeguirRedireccion(urllib.request.HTTPRedirectHandler):
    """Desactiva el seguimiento automatico: las redirecciones se validan a mano."""


class AnalizadorPagina(HTMLParser):
    """Extrae <title>, <h1> y enlaces (href + texto) con html.parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulo = None
        self.h1 = None
        self.enlaces = []
        self._en_title = False
        self._buf_title = []
        self._nivel_h1 = 0
        self._buf_h1 = []
        self._en_a = False
        self._buf_a = []
        self._href = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self._en_title = True
            self._buf_title = []
        elif tag == "h1":
            self._nivel_h1 += 1
            if self._nivel_h1 == 1:
                self._buf_h1 = []
        elif tag == "a":
            self._en_a = True
            self._buf_a = []
            self._href = None
            for nombre, valor in attrs:
                if nombre.lower() == "href" and valor is not None:
                    self._href = valor.strip()
                    break

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title" and self._en_title:
            self._en_title = False
            if self.titulo is None:
                self.titulo = " ".join("".join(self._buf_title).split())
        elif tag == "h1" and self._nivel_h1:
            self._nivel_h1 -= 1
            if self._nivel_h1 == 0 and self.h1 is None:
                self.h1 = " ".join("".join(self._buf_h1).split())
        elif tag == "a" and self._en_a:
            self._en_a = False
            texto = " ".join("".join(self._buf_a).split())
            if self._href is not None:
                self.enlaces.append((self._href, texto))
            self._href = None

    def handle_data(self, dato):
        if self._en_title:
            self._buf_title.append(dato)
        if self._nivel_h1:
            self._buf_h1.append(dato)
        if self._en_a:
            self._buf_a.append(dato)


def normalizar_texto(texto):
    """Minúsculas y sin acentos, para comparar palabras clave."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return sin_acentos.lower()


def normalizar_url(url):
    """Canonical para deduplicar: sin fragmento, y path/query Unicode a
    percent-encoding UTF-8 sin re-codificar los % ya presentes ni tocar
    separadores (?=&/ y otros reservados)."""
    partes = urllib.parse.urlsplit(url)
    ruta = urllib.parse.quote(partes.path, safe="/%:@!$&'()*+,;=~-._")
    consulta = urllib.parse.quote(partes.query, safe="=&%/?@:!$&'()*+,;=~-._")
    return urllib.parse.urlunsplit(
        (partes.scheme.lower(), partes.netloc.lower(), ruta,
         consulta, ""))


def actualizar_https(url):
    """Convierte semillas http a HTTPS; devuelve (url, avisado)."""
    limpio = url.strip()
    partes = urllib.parse.urlsplit(limpio)
    if partes.scheme == "http":
        return (urllib.parse.urlunsplit(
            ("https", partes.netloc, partes.path, partes.query, partes.fragment)),
            True)
    if partes.scheme != "https":
        raise FalloConfig(f"semilla con esquema no HTTPS: {url}")
    return limpio, False


def validar_url(url, hosts):
    """Exige HTTPS y host en allowlist; lanza FalloPermanente si falla."""
    partes = urllib.parse.urlsplit(url)
    if partes.scheme != "https":
        raise FalloPermanente(f"URL no HTTPS: {url}")
    host = (partes.hostname or "").lower()
    if host not in hosts:
        raise FalloPermanente(f"host fuera de allowlist: {url}")
    return host


def analizar_robots(texto):
    """Parser minimo de robots.txt (User-agent/Disallow/Allow/Crawl-delay).
    Soporta comodin * y ancla $ via coincide_patron_robots."""
    grupos = []
    actual = None
    for linea in texto.splitlines():
        if "#" in linea:
            linea = linea.split("#", 1)[0]
        linea = linea.strip()
        if not linea or ":" not in linea:
            continue
        clave, valor = linea.split(":", 1)
        clave = clave.strip().lower()
        valor = valor.strip()
        if clave == "user-agent":
            if actual is None or actual["reglas"] or actual["demora"] is not None:
                actual = {"agentes": [], "reglas": [], "demora": None}
                grupos.append(actual)
            actual["agentes"].append(valor.lower())
        elif actual is None:
            continue
        elif clave == "disallow":
            actual["reglas"].append((False, valor))
        elif clave == "allow":
            actual["reglas"].append((True, valor))
        elif clave == "crawl-delay":
            try:
                actual["demora"] = max(0.0, float(valor.replace(",", ".")))
            except ValueError:
                pass
    return grupos


def seleccionar_grupo_robots(grupos):
    """Reglas del grupo con token propio; si no existe, del grupo ``*``."""
    exactos = [g for g in grupos if TOKEN_AGENTE in g["agentes"]]
    generales = [g for g in grupos if "*" in g["agentes"]]
    elegidos = exactos if exactos else generales
    reglas = []
    demora = None
    for grupo in elegidos:
        reglas.extend(grupo["reglas"])
        if grupo["demora"] is not None:
            demora = (grupo["demora"] if demora is None
                      else max(demora, grupo["demora"]))
    return reglas, demora


def coincide_patron_robots(patron, ruta):
    """Patron robots: prefijo plano, comodin * y ancla $."""
    if patron == "$" or patron == "":
        return patron == ruta
    ancla = patron.endswith("$")
    cuerpo = patron[:-1] if ancla else patron
    if "*" in cuerpo:
        regex = ".*".join(re.escape(p) for p in cuerpo.split("*"))
        if ancla:
            regex += "$"
        return re.fullmatch(regex, ruta) is not None or (
            not ancla and re.match(regex, ruta) is not None)
    return ruta.endswith(cuerpo) if ancla else ruta.startswith(cuerpo)


def ruta_permitida_robots(reglas, ruta):
    """El patron mas especifico (mas caracteres literales) gana; empate: Allow."""
    mejor = None
    for permitir, patron in reglas:
        if not patron:
            continue
        if coincide_patron_robots(patron, ruta):
            especificidad = len(patron.replace("*", ""))
            if mejor is None or especificidad > mejor[0]:
                mejor = (especificidad, permitir)
            elif mejor is not None and especificidad == mejor[0] and permitir:
                mejor = (especificidad, True)
    return True if mejor is None else mejor[1]


class Rastreador:
    """Descarga secuencial con pausa, timeout, robots cache y limites."""

    def __init__(self, pausa_s, timeout_s, cache_raiz=None, reanudar=False):
        self.pausa_s = pausa_s
        self.timeout_s = timeout_s
        self.ultima_solicitud = 0.0
        self.robots_cache = {}
        self.demoras = {}
        self.cache_raiz = Path(cache_raiz) if cache_raiz else None
        self.reanudar = bool(reanudar)

    def esperar(self, host):
        pausa_efectiva = max(self.pausa_s, self.demoras.get(host, 0.0))
        espera = pausa_efectiva - (time.monotonic() - self.ultima_solicitud)
        if espera > 0:
            time.sleep(espera)

    def descargar(self, url, hosts, max_bytes=MAX_BYTES_PAGINA,
                  exigir_tipo=True, verificar_robots=True):
        """Descarga con redirecciones manuales: cada salto valida HTTPS,
        allowlist, robots (path+query) y pausa ANTES de pedir el destino."""
        if self.reanudar:
            en_cache = self.leer_cache(url)
            if en_cache is not None:
                return en_cache
        try:
            actual = normalizar_url(url)
        except (ValueError, UnicodeError) as exc:
            raise FalloPermanente(f"URL no normalizable ({exc}): {url}")
        for _salto in range(MAX_REDIRECCIONES + 1):
            try:
                actual = normalizar_url(actual)
            except (ValueError, UnicodeError) as exc:
                raise FalloPermanente(
                    f"URL no normalizable tras redireccion ({exc}): {actual}")
            partes = urllib.parse.urlsplit(actual)
            host = (partes.hostname or "").lower()
            if partes.scheme != "https" or host not in hosts:
                raise FalloPermanente(
                    f"URL fuera de politica HTTPS/allowlist: {actual}")
            ruta_completa = (partes.path or "/") + \
                (("?" + partes.query) if partes.query else "")
            if verificar_robots:
                robots = self.robots_para(host, hosts)
                if not robots["permitido"] or not ruta_permitida_robots(
                        robots.get("reglas") or [], ruta_completa):
                    raise FalloPermanente(f"robots prohibe: {actual}")
            self.esperar(host)
            self.ultima_solicitud = time.monotonic()
            opener = urllib.request.build_opener(
                NoSeguirRedireccion(), urllib.request.HTTPSHandler())
            solicitud = urllib.request.Request(
                actual, headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
                    "Accept-Language": "es, ca;q=0.8, gl;q=0.6, eu;q=0.6",
                })
            try:
                with opener.open(solicitud, timeout=self.timeout_s) as respuesta:
                    estado = respuesta.getcode()
                    tipo = (respuesta.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    if exigir_tipo and tipo and not tipo.startswith(TIPOS_CONTENIDO):
                        raise FalloPermanente(
                            f"tipo de contenido no admitido ({tipo}): {actual}")
                    bloques = []
                    total = 0
                    while True:
                        bloque = respuesta.read(TAMANO_BLOQUE)
                        if not bloque:
                            break
                        total += len(bloque)
                        if total > max_bytes:
                            raise FalloPermanente(
                                f"excede el maximo de {max_bytes} bytes: {actual}")
                        bloques.append(bloque)
                    datos = b"".join(bloques)
                    url_final = actual
            except urllib.error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308):
                    destino = (exc.headers or {}).get("Location")
                    if not destino:
                        raise FalloPermanente(
                            f"redireccion {exc.code} sin Location: {actual}")
                    actual = urllib.parse.urljoin(actual, destino)
                    continue
                raise
            if self.reanudar:
                self.guardar_cache(url, datos, estado, url_final, tipo)
            return datos, estado, url_final, tipo, total
        raise FalloPermanente(f"demasiadas redirecciones (>{MAX_REDIRECCIONES}): {url}")

    def _clave_cache(self, url):
        canon = normalizar_url(url)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]

    def leer_cache(self, url):
        """Entrada cacheada verificada por SHA-256; ninguna si no hay valida."""
        if not self.cache_raiz:
            return None
        base = self.cache_raiz / self._clave_cache(url)
        if not base.is_dir():
            return None
        for meta_ruta in sorted(base.glob("*.json"),
                                key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                meta = json.loads(meta_ruta.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            cuerpo = meta_ruta.with_suffix(".body")
            if not cuerpo.is_file():
                continue
            datos = cuerpo.read_bytes()
            if hashlib.sha256(datos).hexdigest() != meta.get("sha256"):
                continue  # cuerpo corrupto: se ignora y se vuelve a la red
            return (datos, int(meta.get("estado_http") or 200),
                    meta.get("url_final") or url,
                    meta.get("tipo_contenido") or "", len(datos))
        return None

    def guardar_cache(self, url, datos, estado, url_final, tipo):
        """Cache persistente sin sobrescribir: nombre por SHA del cuerpo."""
        if not self.cache_raiz:
            return
        base = self.cache_raiz / self._clave_cache(url)
        base.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256(datos).hexdigest()
        if (base / f"{sha}.json").exists():
            return
        (base / f"{sha}.body").write_bytes(datos)
        (base / f"{sha}.json").write_text(json.dumps({
            "url": url,
            "estado_http": estado,
            "url_final": url_final,
            "tipo_contenido": tipo,
            "sha256": sha,
            "bytes": len(datos),
            "guardado_en_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def robots_para(self, host, hosts):
        """Devuelve el resultado cacheado de robots.txt para el host."""
        if host in self.robots_cache:
            return self.robots_cache[host]
        url_robots = f"https://{host}/robots.txt"
        resultado = {"permitido": True, "estado": "ok", "demora_s": None,
                     "detalle": "", "reglas": []}
        try:
            datos, _estado, _final, tipo_robots, _total = self.descargar(
                url_robots, hosts, max_bytes=MAX_BYTES_ROBOTS,
                exigir_tipo=False, verificar_robots=False)
            cuerpo = datos.decode("utf-8", "replace")
            cabecera = cuerpo[:2048].lower()
            es_html = (tipo_robots or "").startswith("text/html") or \
                "<html" in cabecera or "<!doctype html" in cabecera
            if es_html:
                resultado["estado"] = "fail_closed"
                resultado["permitido"] = False
                resultado["detalle"] = (
                    f"robots.txt devolvio HTML/captcha (tipo {tipo_robots or 'desconocido'}): "
                    "respuesta no fiable, bloqueo conservador del host")
            else:
                grupos = analizar_robots(cuerpo)
                reglas, demora = seleccionar_grupo_robots(grupos)
                resultado["reglas"] = reglas
                resultado["demora_s"] = demora
                if demora:
                    self.demoras[host] = demora
                resultado["detalle"] = (
                    f"robots.txt ok ({len(reglas)} reglas); el bloqueo se evalua "
                    "por ruta y consulta en cada solicitud")
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                resultado["estado"] = "sin_archivo"
                resultado["reglas"] = []
                resultado["detalle"] = (
                    f"robots.txt HTTP {exc.code}: sin archivo (reglas vacias), "
                    "se permite el resto del sitio segun practica estandar")
            else:
                resultado["estado"] = "fail_closed"
                resultado["permitido"] = False
                resultado["detalle"] = (
                    f"robots.txt HTTP {exc.code}: sin respuesta fiable, "
                    "bloqueo conservador del host")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            resultado["estado"] = "fail_closed"
            resultado["permitido"] = False
            resultado["detalle"] = (
                f"robots.txt inaccesible ({exc}): bloqueo conservador del host")
        self.robots_cache[host] = resultado
        return resultado


def leer_catalogo(ruta):
    if not ruta.is_file():
        raise FalloConfig(f"catalogo no encontrado: {ruta}")
    try:
        with ruta.open("r", encoding="utf-8") as flujo:
            catalogo = json.load(flujo)
    except (json.JSONDecodeError, OSError) as exc:
        raise FalloConfig(f"catalogo ilegible ({ruta}): {exc}")
    fuentes = catalogo.get("fuentes")
    if not isinstance(fuentes, list) or not fuentes:
        raise FalloConfig("catalogo sin 'fuentes' o lista vacia")
    filtro = catalogo.get("filtro_materias")
    palabras = []
    if isinstance(filtro, dict):
        for lista in filtro.values():
            if isinstance(lista, list):
                palabras.extend(str(p) for p in lista if str(p).strip())
    if not palabras:
        raise FalloConfig(
            "catalogo sin 'filtro_materias' utilizable: no se rastrea sin filtro "
            "declarativo de materias (fail-closed)")
    return catalogo, fuentes, [normalizar_texto(p) for p in palabras]


def seleccionar_fuentes(fuentes, limite, solo_id):
    if solo_id is not None:
        elegidas = [f for f in fuentes if f.get("id") == solo_id]
        if not elegidas:
            raise FalloConfig(f"--solo-id desconocido en el catalogo: {solo_id}")
        return elegidas
    if limite is not None:
        return fuentes[:limite]
    return fuentes


def validar_fuente(fuente, indice):
    ident = fuente.get("id")
    if not ident or not isinstance(ident, str) or \
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", ident):
        raise FalloConfig(f"fuente #{indice} con 'id' invalido: {ident!r}")
    if not fuente.get("urls_semilla"):
        raise FalloConfig(f"{ident}: sin 'urls_semilla'")
    hosts = {h.strip().lower() for h in (fuente.get("hosts_permitidos") or [])
             if h.strip()}
    if not hosts:
        raise FalloConfig(f"{ident}: sin 'hosts_permitidos'")
    if fuente.get("nivel") not in ("autonomia", "ciudad_autonoma", "municipio"):
        raise FalloConfig(f"{ident}: 'nivel' invalido ({fuente.get('nivel')})")
    return hosts


def validar_salida(ruta):
    if ruta is None:
        return SALIDA_DEFECTO
    dada = Path(ruta)
    absoluta = dada if dada.is_absolute() else Path.cwd() / dada
    resuelta = absoluta.resolve()
    base = (CHECKOUT_RAIZ / ".local").resolve()
    if resuelta != base and base not in resuelta.parents:
        raise FalloConfig(
            f"--salida solo acepta rutas dentro de .local/ del checkout "
            f"(gitignored); recibido: {ruta}")
    return resuelta


def carpeta_snapshot(salida, ident, ts):
    base = salida / ident
    carpeta = base / ts
    sufijo = 2
    while carpeta.exists():
        carpeta = base / f"{ts}-{sufijo}"
        sufijo += 1
    resuelta = carpeta.resolve()
    if salida.resolve() not in resuelta.parents:
        raise FalloConfig(f"snapshot fuera de la salida: {carpeta}")
    carpeta.mkdir(parents=True)
    return carpeta


def recopilar_fuente(fuente, hosts, salida, rastreo, max_paginas, profundidad,
                     palabras, ts):
    ident = fuente["id"]
    resultado = {
        "id": ident,
        "territorio": fuente.get("territorio"),
        "nivel": fuente.get("nivel"),
        "municipio": fuente.get("municipio"),
        "estado": "ok",
        "paginas": [],
        "candidatos": [],
        "errores": [],
        "robots": {},
        "semillas": [],
        "bytes_total": 0,
        "capturado_en_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
    }
    visitadas = set()
    candidatos_vistos = set()
    cola = deque()
    carpeta = None
    indice_pagina = 0
    truncado_candidatos = False
    truncado_errores = False

    for semilla in fuente["urls_semilla"]:
        try:
            url, avisado = actualizar_https(semilla)
        except FalloConfig as exc:
            resultado["errores"].append({"url": semilla,
                                         "error": str(exc)})
            continue
        entrada = {"url_original": semilla, "url_https": url,
                   "actualizada_https": avisado,
                   "publicada_en_catalogo": bool(fuente.get("urls_semilla_publicadas"))}
        resultado["semillas"].append(entrada)
        cola.append((url, 0))

    max_intentos = max_paginas * 3
    max_cola = max_paginas * 20
    intentos = 0
    truncado_intentos = False
    truncado_cola = False
    while cola and len(resultado["paginas"]) < max_paginas:
        if intentos >= max_intentos:
            truncado_intentos = True
            break
        intentos += 1
        url, prof = cola.popleft()
        canon = normalizar_url(url)
        if canon in visitadas:
            continue
        visitadas.add(canon)
        try:
            host = validar_url(url, hosts)
        except FalloPermanente as exc:
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append({"url": url, "error": str(exc)})
            else:
                truncado_errores = True
            continue
        robots = None
        try:
            robots = rastreo.robots_para(host, hosts)
        except FalloPermanente as exc:
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append(
                    {"url": url, "error": f"robots: {exc}"})
            else:
                truncado_errores = True
            continue
        if host not in resultado["robots"]:
            copia = dict(robots)
            copia.pop("permitido", None)
            copia.pop("reglas", None)
            resultado["robots"][host] = copia
        ruta = (urllib.parse.urlsplit(url).path or "/")
        consulta = urllib.parse.urlsplit(url).query
        if consulta:
            ruta += "?" + consulta
        if not robots["permitido"] or not ruta_permitida_robots(
                robots.get("reglas") or [], ruta):
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append({
                    "url": url,
                    "error": ("robots_" + robots["estado"]
                              if not robots["permitido"] else "robots_bloqueado"),
                    "detalle": robots.get("detalle", ""),
                })
            else:
                truncado_errores = True
            continue
        try:
            datos, estado_http, url_final, tipo, total = rastreo.descargar(url, hosts)
        except FalloPermanente as exc:
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append({"url": url, "error": str(exc)})
            else:
                truncado_errores = True
            continue
        except urllib.error.HTTPError as exc:
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append(
                    {"url": url, "error": f"HTTP {exc.code}"})
            else:
                truncado_errores = True
            continue
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append(
                    {"url": url, "error": f"error de red: {exc}"})
            else:
                truncado_errores = True
            continue
        resultado["bytes_total"] += total
        analisis = AnalizadorPagina()
        try:
            analisis.feed(datos.decode("utf-8", "replace"))
            analisis.close()
        except Exception as exc:  # html.parser no suele lanzar, pero fail-closed
            if len(resultado["errores"]) < MAX_ERRORES:
                resultado["errores"].append(
                    {"url": url, "error": f"analisis HTML: {exc}"})
            continue
        titulo = analisis.titulo or analisis.h1 or ""
        claves = coincidencias(normalizar_texto(titulo) + " " +
                               normalizar_texto(url), palabras)
        clasificacion = "posible_norma" if claves else "portada_indice"
        indice_pagina += 1
        sha = hashlib.sha256(datos).hexdigest()
        if carpeta is None:
            carpeta = carpeta_snapshot(salida, ident, ts)
        nombre = f"pagina-{indice_pagina:03d}-{sha[:12]}.html"
        (carpeta / nombre).write_bytes(datos)
        resultado["paginas"].append({
            "archivo": nombre,
            "url": url,
            "url_final": url_final,
            "estado_http": estado_http,
            "tipo_contenido": tipo or None,
            "bytes": total,
            "sha256": sha,
            "capturado_en_utc": resultado["capturado_en_utc"],
            "profundidad": prof,
            "titulo": titulo or None,
            "clasificacion": clasificacion,
            "palabras_clave": claves,
            "es_semilla": prof == 0,
        })
        # Enlaces: candidatos por palabras clave; PDF y binarios NO se descargan
        for href, texto_enlace in analisis.enlaces:
            if not href:
                continue
            bajo = href.strip().lower()
            if bajo.startswith(("mailto:", "javascript:", "tel:", "data:")):
                continue
            absoluto = urllib.parse.urljoin(url_final or url, href)
            partes = urllib.parse.urlsplit(absoluto)
            if partes.scheme not in ("http", "https"):
                continue
            host_enlace = (partes.hostname or "").lower()
            if host_enlace not in hosts:
                continue
            ruta_enlace = partes.path.lower()
            objetivo = normalizar_texto(texto_enlace) + " " + \
                normalizar_texto(partes.path)
            canon_enlace = normalizar_url(absoluto)
            claves_enlace = coincidencias(objetivo, palabras)
            tipo_enlace = None
            if ruta_enlace.endswith(".pdf"):
                tipo_enlace = "pdf_no_descargado"
            elif not ruta_enlace.endswith(EXT_NO_RASTREABLES):
                tipo_enlace = "candidato_enlace"
            if tipo_enlace and claves_enlace:
                if canon_enlace in candidatos_vistos:
                    pass
                elif len(resultado["candidatos"]) < MAX_CANDIDATOS:
                    candidatos_vistos.add(canon_enlace)
                    resultado["candidatos"].append({
                        "url": canon_enlace,
                        "texto_enlace": texto_enlace or None,
                        "palabras_clave": claves_enlace,
                        "tipo": tipo_enlace,
                        "profundidad": prof,
                        "origen": url,
                    })
                else:
                    truncado_candidatos = True
            if tipo_enlace == "pdf_no_descargado":
                continue
            if tipo_enlace is None or prof + 1 > profundidad or \
                    canon_enlace in visitadas:
                continue
            if len(cola) >= max_cola:
                truncado_cola = True
                continue
            if claves_enlace:
                # prioridad entre iguales: delante de su nivel, nunca de niveles previos
                _pos = len(cola)
                while _pos > 0 and cola[_pos - 1][1] >= prof + 1:
                    _pos -= 1
                cola.insert(_pos, (absoluto, prof + 1))
            else:
                cola.append((absoluto, prof + 1))

    resultado["truncado_candidatos"] = bool(truncado_candidatos)
    resultado["truncado_errores"] = bool(
        truncado_errores or len(resultado["errores"]) >= MAX_ERRORES)
    if truncado_intentos:
        resultado["truncado_intentos"] = True
    if truncado_cola:
        resultado["truncado_cola"] = True
    resultado["cola_pendiente"] = len(cola)
    resultado["limites"] = {"max_paginas": max_paginas,
                            "max_intentos": max_intentos,
                            "max_cola": max_cola,
                            "intentos": intentos,
                            "profundidad": profundidad}
    if not resultado["paginas"]:
        resultado["estado"] = "fallida"
    elif resultado["errores"]:
        resultado["estado"] = "con_errores"
    carpeta_final = carpeta if carpeta is not None else carpeta_snapshot(
        salida, ident, ts + "__sin-paginas")
    metadatos = {
        "version": VERSION,
        "fuente": {
            "id": ident,
            "territorio": fuente.get("territorio"),
            "nivel": fuente.get("nivel"),
            "municipio": fuente.get("municipio"),
            "idiomas": fuente.get("idiomas"),
            "hosts_permitidos": sorted(hosts),
            "evidencia_semilla": fuente.get("evidencia"),
            "verificado": bool(fuente.get("verificado")),
        },
        "estado": resultado["estado"],
        "semillas": resultado["semillas"],
        "robots": resultado["robots"],
        "paginas": resultado["paginas"],
        "candidatos": resultado["candidatos"],
        "errores": resultado["errores"],
        "bytes_total": resultado["bytes_total"],
        "limites": resultado.get("limites"),
        "cola_pendiente": resultado.get("cola_pendiente", 0),
        "truncado_intentos": bool(resultado.get("truncado_intentos")),
        "truncado_cola": bool(resultado.get("truncado_cola")),
        "truncado_candidatos": bool(resultado.get("truncado_candidatos")),
        "truncado_errores": bool(resultado.get("truncado_errores")),
        "capturado_en_utc": resultado["capturado_en_utc"],
        "aviso": AVISO_PORTADAS,
        "pendientes": PENDIENTES,
    }
    (carpeta_final / "metadata.json").write_text(
        json.dumps(metadatos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return resultado


def coincidencias(texto_norm, palabras_norm):
    encontradas = [p for p in palabras_norm if p in texto_norm]
    return sorted(set(encontradas))


def escribir_resumen(salida, argumentos, resultados):
    totales = {
        "paginas": sum(len(r["paginas"]) for r in resultados),
        "bytes": sum(r["bytes_total"] for r in resultados),
        "candidatos": sum(len(r["candidatos"]) for r in resultados),
        "errores": sum(len(r["errores"]) for r in resultados),
        "fuentes_ok": sum(1 for r in resultados if r["estado"] == "ok"),
        "fuentes_con_errores": sum(1 for r in resultados if r["estado"] == "con_errores"),
        "fuentes_fallidas": sum(1 for r in resultados if r["estado"] == "fallida"),
    }
    resumen = {
        "version": VERSION,
        "ejecutado_en_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "argumentos": argumentos,
        "totales": totales,
        "aviso": AVISO_PORTADAS,
        "pendientes_globales": PENDIENTES,
        "fuentes": [
            {
                "id": r["id"],
                "territorio": r["territorio"],
                "nivel": r["nivel"],
                "municipio": r["municipio"],
                "estado": r["estado"],
                "paginas": len(r["paginas"]),
                "bytes": r["bytes_total"],
                "candidatos": len(r["candidatos"]),
                "robots": {h: c["estado"] for h, c in r["robots"].items()},
                "errores": len(r["errores"]),
                "detalle_errores": r["errores"][:10],
            }
            for r in resultados
        ],
    }
    ruta_json = salida / "resumen.json"
    ruta_json.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    lineas = [
        f"# Resumen captura territorial ({resumen['ejecutado_en_utc']})",
        "",
        f"Fuentes: {totales['fuentes_ok']} ok, "
        f"{totales['fuentes_con_errores']} con errores, "
        f"{totales['fuentes_fallidas']} fallidas · "
        f"Paginas: {totales['paginas']} · "
        f"Bytes: {totales['bytes']} · "
        f"Candidatos: {totales['candidatos']} · "
        f"Errores: {totales['errores']}",
        "",
        AVISO_PORTADAS,
        "",
        "| ID | Territorio | Nivel | Municipio | Estado | Paginas | Bytes | Candidatos | Robots | Errores |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in resultados:
        robots = ", ".join(f"{h}:{e}" for h, e in
                           ((h, c["estado"]) for h, c in r["robots"].items())) or "-"
        lineas.append(
            f"| {r['id']} | {r['territorio'] or '-'} | {r['nivel']} | "
            f"{r['municipio'] or '-'} | {r['estado']} | {len(r['paginas'])} | "
            f"{r['bytes_total']} | {len(r['candidatos'])} | {robots} | "
            f"{len(r['errores'])} |")
    lineas += [
        "",
        "Errores por fuente (primeros 10):",
        "",
    ]
    con_errores = [r for r in resultados if r["errores"]]
    if not con_errores:
        lineas.append("- ninguno")
    for r in con_errores:
        lineas.append(f"- {r['id']}:")
        for error in r["errores"][:10]:
            lineas.append(f"  - {error.get('error')}: {error.get('url')}")
        if len(r["errores"]) > 10:
            lineas.append(f"  - ... ({len(r['errores']) - 10} mas en metadata.json)")
    (salida / "resumen.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return resumen


def listar_fuentes(catalogo, fuentes):
    print(f"Catalogo: {catalogo.get('version')} · "
          f"{len(fuentes)} fuentes · filtro materias: "
          f"{sum(len(v) for v in (catalogo.get('filtro_materias') or {}).values())} palabras")
    for fuente in fuentes:
        municipio = fuente.get("municipio") or "-"
        semillas = len(fuente.get("urls_semilla") or [])
        hosts = len(fuente.get("hosts_permitidos") or [])
        marca = "verificada" if fuente.get("verificado") else "PENDIENTE"
        print(f"{fuente.get('id')}\t{fuente.get('territorio')}\t"
              f"{fuente.get('nivel')}\t{municipio}\tsemillas={semillas}\t"
              f"hosts={hosts}\t{marca}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Captura web reproducible de fuentes territoriales "
                    "(solo .local/, fail-closed, sin afirmar vigencia).")
    parser.add_argument("--catalogo", default=str(CATALOGO_DEFECTO),
                        help="ruta del JSON de semillas (defecto: fuentes-territoriales.json)")
    parser.add_argument("--salida", default=None,
                        help="directorio de salida; SOLO rutas dentro de .local/ del checkout")
    parser.add_argument("--limite", type=int, default=None,
                        help="procesar solo las N primeras fuentes")
    parser.add_argument("--solo-id", default=None,
                        help="procesar solo esta fuente (prevalece sobre --limite)")
    parser.add_argument("--max-paginas", type=int, default=MAX_PAGINAS_DEFECTO,
                        help=f"maximo de paginas por fuente (defecto {MAX_PAGINAS_DEFECTO})")
    parser.add_argument("--profundidad", type=int, default=PROFUNDIDAD_DEFECTO,
                        help=f"profundidad BFS desde la semilla (defecto {PROFUNDIDAD_DEFECTO})")
    parser.add_argument("--pausa", type=float, default=PAUSA_DEFECTO_S,
                        help="pausa entre solicitudes en segundos (minimo 1.0)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_DEFECTO_S,
                        help=f"timeout de red en segundos (defecto {TIMEOUT_DEFECTO_S})")
    parser.add_argument("--listar", action="store_true",
                        help="listar fuentes del catalogo y salir, sin red ni escritura")
    parser.add_argument("--reanudar", action="store_true",
                        help="reusar la cache persistente de .local/ si el hash del "
                             "cuerpo coincide; sin este flag toda pagina se descarga")
    args = parser.parse_args(argv)

    try:
        catalogo, fuentes, palabras = leer_catalogo(Path(args.catalogo))
        if args.listar:
            listar_fuentes(catalogo, fuentes)
            return 0
        salida = validar_salida(args.salida)
        elegidas = seleccionar_fuentes(fuentes, args.limite, args.solo_id)
        pausa = max(PAUSA_MIN_S, float(args.pausa))
        if args.pausa < PAUSA_MIN_S:
            print(f"aviso: --pausa {args.pausa} por debajo del minimo; se usa "
                  f"{PAUSA_MIN_S} s", file=sys.stderr)
        timeout = max(1, int(args.timeout))
        max_paginas = max(1, int(args.max_paginas))
        profundidad = max(0, int(args.profundidad))
    except FalloConfig as exc:
        print(f"error de configuracion: {exc}", file=sys.stderr)
        return 2

    rastreo = Rastreador(pausa, timeout,
                         cache_raiz=salida / "cache-territorial",
                         reanudar=bool(args.reanudar))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    salida.mkdir(parents=True, exist_ok=True)
    argumentos = {
        "catalogo": str(Path(args.catalogo)),
        "salida": str(salida),
        "limite": args.limite,
        "solo_id": args.solo_id,
        "max_paginas": max_paginas,
        "profundidad": profundidad,
        "pausa_s": pausa,
        "timeout_s": timeout,
        "reanudar": bool(args.reanudar),
    }
    resultados = []
    for fuente in elegidas:
        try:
            hosts = validar_fuente(fuente, fuente.get("id"))
        except FalloConfig as exc:
            print(f"error de configuracion: {exc}", file=sys.stderr)
            return 2
        try:
            resultado = recopilar_fuente(fuente, hosts, salida, rastreo,
                                         max_paginas, profundidad, palabras, ts)
        except Exception as exc:  # conservar el resto de fuentes y el resumen
            resultado = {
                "id": fuente.get("id"),
                "territorio": fuente.get("territorio"),
                "nivel": fuente.get("nivel"),
                "municipio": fuente.get("municipio"),
                "estado": "fallida",
                "paginas": [],
                "candidatos": [],
                "errores": [{"url": None, "error": f"excepcion no esperada: {exc}"}],
                "robots": {},
                "bytes_total": 0,
            }
            print(f"[   fallida] {resultado['id']}: {exc}", file=sys.stderr)
        resultados.append(resultado)
        print(f"[{resultado['estado']:>11}] {resultado['id']} "
              f"{resultado['territorio']}: {len(resultado['paginas'])} paginas, "
              f"{len(resultado['candidatos'])} candidatos, "
              f"{len(resultado['errores'])} errores")
    escribir_resumen(salida, argumentos, resultados)
    print(f"Resumen: {salida / 'resumen.json'} y {salida / 'resumen.md'}")
    fallida = any(r["estado"] in ("con_errores", "fallida") for r in resultados)
    return 1 if fallida else 0


if __name__ == "__main__":
    sys.exit(main())
