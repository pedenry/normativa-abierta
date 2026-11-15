#!/usr/bin/env python3
"""Recopilacion reproducible de normativa espanola de edificacion (BOE).

Primera tanda: 15 documentos legales adicionales al CTE/RITE/RSCIEI definidos
en ``fuentes-ampliacion.json``. Por cada fuente:

1. Descarga la pagina oficial ``https://www.boe.es/buscar/act.php?id={ID}`` (siempre).
2. Extrae metadatos con ``html.parser.HTMLParser``: ELI, titulo real,
   fecha de publicacion, fecha del documento y fecha de version/actualizacion.
3. Localiza el PDF consolidado (href con el ID y ``consolidado.pdf``) o, si no
   existe, el PDF original (href con ``ID.pdf``). Nunca inventa consolidado.
4. Valida la firma ``%PDF-`` y guarda HTML original, PDF sin modificar y
   metadatos JSON (SHA-256 de los bytes, enlaces fuente, disposicion literal,
   fecha de captura UTC, tipo original/consolidado, atribucion BOE, licencia,
   aplicabilidad y transitorio PENDIENTES, fidelidad NO cotejada).

Por que scraping y no la API de datos abiertos: la API documentada en
https://www.boe.es/datosabiertos/api/api.php
(``/legislacion-consolidada/id/{ID}/metadatos`` y ``/texto``) respondio
HTTP 400/404 en la verificacion de Codex del 2026-11-15 (evidencia del
encargo). Retest pendiente en una tanda futura.

Limites de red: solo HTTPS en www.boe.es o boe.es (validado tambien tras cada
redireccion), tamano maximo 60 MB, pausa >= 1 s entre solicitudes, timeout de
30 s, hasta 2 reintentos para errores transitorios con espera creciente
(2 s, 4 s). Descarga secuencial.

Este script NO afirma vigencia ni aplicabilidad. La fidelidad del texto
extraido queda NO cotejada y requiere revision tecnica humana; por eso se
conservan los bytes originales del HTML y del PDF.

Uso:
    python ingesta/recopilar_boe.py [--salida DIR] [--limite N] [--solo-id ID]

Salida por defecto: ``.local/ampliacion-boe`` en la raiz del checkout
(resuelta desde la ubicacion del script, no desde el CWD). Los crudos solo
viven en ``.local/`` (gitignored): no apuntar ``--salida`` nunca a rutas
publicas como ``contenido/`` o ``site/``.

Codigos de salida: 0 = todo ok; 1 = alguna fuente con error; 2 = error de
configuracion (JSON ausente, ID desconocido, ID con formato invalido).
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

VERSION = "0.1"

CHECKOUT_RAIZ = Path(__file__).resolve().parent.parent
RUTA_FUENTES = Path(__file__).resolve().parent / "fuentes-ampliacion.json"
SALIDA_DEFECTO = CHECKOUT_RAIZ / ".local" / "ampliacion-boe"

URL_PLANTILLA_ACT = "https://www.boe.es/buscar/act.php?id={id}"
URL_API_DOC = "https://www.boe.es/datosabiertos/api/api.php"
URL_LICENCIA_BOE = "https://www.boe.es/informacion/aviso_legal/index.php"
ATRIBUCION = "Basado en datos de la Agencia Estatal Boletín Oficial del Estado"
MOTIVO_API_NO_USADA = (
    "/legislacion-consolidada/id/{ID}/metadatos y /texto respondieron HTTP 400/404 "
    "en la verificacion de Codex (2026-11-15); se usa la pagina oficial "
    "buscar/act.php. Retest de la API pendiente."
)

HOSTS_PERMITIDOS = {"www.boe.es", "boe.es"}
MAX_BYTES = 60 * 1024 * 1024
TIMEOUT_S = 30
PAUSA_S = 1.0
MAX_REINTENTOS = 2
MAX_REDIRECCIONES = 5
TAMANO_BLOQUE = 64 * 1024
USER_AGENT = "normativa-abierta-ingesta/0.1 (+https://github.com/pedenry/normativa-abierta)"
CODIGOS_TRANSITORIOS = {408, 429, 500, 502, 503, 504}
RE_ID_BOE = re.compile(r"^BOE-[A-Z]-\d{4}-\d+$")

ERRORES_TRANSITORIOS = (urllib.error.URLError, OSError, http.client.HTTPException)

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

RE_FECHA_BARRA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
RE_FECHA_TEXTO = re.compile(r"\b(\d{1,2})\s+de\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ]+)(?:\s+de\s+(\d{4}))?\b")

PATRON_IDENTIFICADOR = r"Identificador"
PATRON_DIARIO = r"Diario(?:\s+Oficial)?"
PATRON_PUBLICACION = r"Publicaci[oó]n"
PATRON_FECHA_DOCUMENTO = r"Fecha\s+del\s+documento"
PATRON_VERSION = (
    r"(?:Última|Ultima)\s+(?:actualizaci[oó]n|modificaci[oó]n|versi[oó]n)"
    r"|Versi[oó]n\s+(?:en\s+vigor|consolidada)"
    r"|Version\s+(?:en\s+vigor|consolidada)"
)


class FalloPermanente(Exception):
    """Error que no debe reintentarse (politica, tamano o destino no permitido)."""


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    """Desactiva el seguimiento automatico para validar cada salto."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(SinRedireccion())


def cerrar_error_http(error_http) -> None:
    """Cierra el cuerpo de un HTTPError sin fallar si no hay cuerpo."""
    try:
        error_http.close()
    except Exception:
        pass


def validar_url(url: str) -> None:
    partes = urllib.parse.urlsplit(url)
    if partes.scheme.lower() != "https":
        raise FalloPermanente(f"esquema no permitido: {partes.scheme!r} en {url}")
    host = (partes.hostname or "").lower()
    if host not in HOSTS_PERMITIDOS:
        raise FalloPermanente(f"host no permitido: {host!r} en {url}")


def solicitud_unica(url: str) -> tuple[bytes, str, str | None, int | None]:
    """Una descarga HTTPS con redirecciones validadas manualmente.

    Devuelve (bytes, url_final, content_type, status). Aplica el limite de
    60 MB tanto al Content-Length anunciado como a los bytes leidos.
    """
    actual = url
    for _ in range(MAX_REDIRECCIONES + 1):
        validar_url(actual)
        peticion = urllib.request.Request(actual, headers={"User-Agent": USER_AGENT})
        try:
            respuesta = OPENER.open(peticion, timeout=TIMEOUT_S)
        except urllib.error.HTTPError as error_http:
            codigo = error_http.code
            if codigo in (301, 302, 303, 307, 308):
                destino = error_http.headers.get("Location") if error_http.headers else None
                cerrar_error_http(error_http)
                if not destino:
                    raise FalloPermanente(
                        f"redireccion {codigo} sin Location en {actual}"
                    ) from None
                actual = urllib.parse.urljoin(actual, destino)
                time.sleep(PAUSA_S)
                continue
            cerrar_error_http(error_http)
            raise
        with respuesta:
            url_final = respuesta.geturl()
            validar_url(url_final)
            content_type = respuesta.headers.get("Content-Type")
            longitud = respuesta.headers.get("Content-Length")
            if longitud is not None:
                try:
                    if int(longitud) > MAX_BYTES:
                        raise FalloPermanente(
                            f"tamano anunciado {longitud} supera el limite de "
                            f"{MAX_BYTES} bytes: {url_final}"
                        )
                except ValueError:
                    pass  # Content-Length no numerico: el limite aplica a los bytes leidos
            datos = bytearray()
            while True:
                bloque = respuesta.read(TAMANO_BLOQUE)
                if not bloque:
                    break
                datos.extend(bloque)
                if len(datos) > MAX_BYTES:
                    raise FalloPermanente(
                        f"descarga supera {MAX_BYTES} bytes: {url_final}"
                    )
            status = getattr(respuesta, "status", None) or getattr(respuesta, "code", None)
            return bytes(datos), url_final, content_type, status
    raise FalloPermanente(f"demasiadas redirecciones (> {MAX_REDIRECCIONES}) desde {url}")


def solicitud_con_reintentos(url: str, anotar) -> tuple[bytes, str, str | None, int | None]:
    """Descarga con hasta MAX_REINTENTOS reintentos para errores transitorios."""
    ultimo: Exception | None = None
    for intento in range(MAX_REINTENTOS + 1):
        if intento > 0:
            espera = PAUSA_S * (2 ** intento)
            anotar(f"reintento {intento}/{MAX_REINTENTOS} de {url} tras espera de {espera:.0f} s")
            time.sleep(espera)
        try:
            resultado = solicitud_unica(url)
        except urllib.error.HTTPError as error_http:
            if error_http.code in CODIGOS_TRANSITORIOS:
                ultimo = error_http
                cerrar_error_http(error_http)
                time.sleep(PAUSA_S)
                continue
            cerrar_error_http(error_http)
            raise
        except FalloPermanente:
            raise
        except ERRORES_TRANSITORIOS as error_red:
            ultimo = error_red
            time.sleep(PAUSA_S)
            continue
        time.sleep(PAUSA_S)  # pausa >= 1 s entre solicitudes
        return resultado
    if ultimo is not None:
        raise ultimo
    raise FalloPermanente(f"sin respuesta de {url} tras los reintentos")


class AnalisisAct(HTMLParser):
    """Extrae enlaces, h1, <title>, <meta name> y lineas de texto de la pagina."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.enlaces: list[tuple[str | None, str]] = []
        self.h1: list[str] = []
        self.titulo_html: str | None = None
        self.metas: dict[str, str] = {}
        self.lineas: list[str] = []
        self._nivel_h1 = 0
        self._texto_h1: list[str] = []
        self._en_titulo = False
        self._texto_titulo: list[str] = []
        self._ignorar = 0
        self._href: str | None = None
        self._texto_enlace: list[str] = []
        self._en_enlace = False

    def handle_starttag(self, etiqueta, atributos):
        dic = dict(atributos)
        if etiqueta in ("script", "style"):
            self._ignorar += 1
        elif etiqueta == "h1":
            self._nivel_h1 += 1
            self._texto_h1 = []
        elif etiqueta == "title":
            self._en_titulo = True
            self._texto_titulo = []
        elif etiqueta == "a":
            self._href = dic.get("href")
            self._texto_enlace = []
            self._en_enlace = True
        elif etiqueta == "meta":
            nombre = (dic.get("name") or "").lower()
            if nombre:
                self.metas[nombre] = dic.get("content") or ""

    def handle_endtag(self, etiqueta):
        if etiqueta in ("script", "style"):
            if self._ignorar:
                self._ignorar -= 1
        elif etiqueta == "h1" and self._nivel_h1:
            self._nivel_h1 -= 1
            texto = " ".join("".join(self._texto_h1).split())
            if texto:
                self.h1.append(texto)
            self._texto_h1 = []
        elif etiqueta == "title":
            self._en_titulo = False
            texto = " ".join("".join(self._texto_titulo).split())
            if texto:
                self.titulo_html = texto
        elif etiqueta == "a" and self._en_enlace:
            texto = " ".join("".join(self._texto_enlace).split())
            self.enlaces.append((self._href, texto))
            self._en_enlace = False

    def handle_data(self, datos):
        if self._ignorar:
            return
        if self._nivel_h1:
            self._texto_h1.append(datos)
        if self._en_titulo:
            self._texto_titulo.append(datos)
        if self._en_enlace:
            self._texto_enlace.append(datos)
        limpio = " ".join(datos.split())
        if limpio:
            self.lineas.append(limpio)


def quitar_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()


def fecha_iso(anio: int, mes: int, dia: int) -> str | None:
    try:
        return datetime(anio, mes, dia).date().isoformat()
    except ValueError:
        return None


def parsear_fecha(texto: str | None) -> str | None:
    """Convierte '30 de junio de 2021' o '30/06/2021' a ISO 8601 (o None)."""
    if not texto:
        return None
    m = RE_FECHA_BARRA.search(texto)
    if m:
        return fecha_iso(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = RE_FECHA_TEXTO.search(texto)
    if m and m.group(3):
        mes = quitar_acentos(m.group(2))
        if mes in MESES:
            return fecha_iso(int(m.group(3)), MESES[mes], int(m.group(1)))
    return None


def valor_label(lineas: list[str], patron_label: str) -> tuple[str | None, str | None]:
    """Valor de un campo etiquetado: en la misma linea o en la siguiente.

    Devuelve (valor, linea_cruda). La linea cruda se conserva literal para
    poder cotejar contra el HTML guardado.
    """
    for i, linea in enumerate(lineas):
        m = re.match(rf"^\s*(?:{patron_label})\s*[:\-]?\s*(.*)$", linea, re.IGNORECASE)
        if m:
            valor = (m.group(1) or "").strip()
            if valor:
                return valor, linea
            if i + 1 < len(lineas):
                siguiente = lineas[i + 1].strip()
                if siguiente:
                    return siguiente, linea
    return None, None


def elegir_pdf(
    enlaces: list[tuple[str | None, str]], id_norma: str, url_base: str
) -> tuple[str | None, str | None, str | None]:
    """Devuelve (url_absoluta, tipo, href_crudo) del PDF de la pagina.

    Consolidado primero: href con el ID y ``consolidado.pdf``. Si no existe,
    PDF original: href con ``ID.pdf``. Si no hay ninguno, (None, None, None):
    nunca se inventa un consolidado.
    """
    consolidado = original = None
    crudo_consolidado = crudo_original = None
    for href, _texto in enlaces:
        if not href:
            continue
        absoluto = urllib.parse.urljoin(url_base, href)
        if consolidado is None and id_norma in absoluto and "consolidado.pdf" in absoluto.lower():
            consolidado, crudo_consolidado = absoluto, href
        elif original is None and (id_norma + ".pdf") in absoluto:
            original, crudo_original = absoluto, href
    if consolidado:
        return consolidado, "consolidado", crudo_consolidado
    if original:
        return original, "original", crudo_original
    return None, None, None


def buscar_eli(
    enlaces: list[tuple[str | None, str]], url_base: str, texto_plano: str
) -> tuple[str | None, str | None]:
    for href, _texto in enlaces:
        if href and "/eli/" in href:
            return urllib.parse.urljoin(url_base, href), "enlace"
    m = re.search(r"https?://www\.boe\.es/eli/[^\s\"'<>]+", texto_plano)
    if m:
        return m.group(0), "texto"
    return None, None


def buscar_date_document(
    lineas: list[str], titulo: str | None
) -> tuple[str | None, str | None, str | None]:
    """Fecha del documento: campo etiquetado en la pagina o, si no, del titulo."""
    valor, crudo = valor_label(lineas, PATRON_FECHA_DOCUMENTO)
    if valor:
        iso = parsear_fecha(valor)
        if iso:
            return iso, "pagina", crudo
    if titulo:
        m = re.search(
            r"\bde\s+(\d{1,2})\s+de\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ]+)(?:\s+de\s+(\d{4}))?",
            titulo,
            re.IGNORECASE,
        )
        if m:
            mes = quitar_acentos(m.group(2))
            anio = int(m.group(3)) if m.group(3) else None
            if anio is None:
                my = re.search(r"/(\d{4})\b", titulo)
                if my:
                    anio = int(my.group(1))
            if anio and mes in MESES:
                iso = fecha_iso(anio, MESES[mes], int(m.group(1)))
                if iso:
                    return iso, "titulo", None
    return None, None, None


def _unir_literal(partes: list[str | None]) -> str | None:
    literales = [p.strip() for p in partes if p and p.strip()]
    return " | ".join(literales) if literales else None


def sha256_hex(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def carpeta_libre(base: Path) -> Path:
    """Carpeta nueva bajo el patron base; nunca sobrescribe un snapshot previo."""
    candidato = base
    n = 2
    while candidato.exists():
        candidato = base.with_name(base.name + f"-{n}")
        n += 1
    return candidato


def escribir_json(ruta: Path, datos: dict) -> None:
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


def log(mensaje: str) -> None:
    try:
        print(mensaje)
    except UnicodeEncodeError:
        print(mensaje.encode("ascii", "replace").decode("ascii"))


def procesar_fuente(fuente: dict, salida_raiz: Path) -> dict:
    id_norma = fuente["id"]
    url_act = URL_PLANTILLA_ACT.format(id=urllib.parse.quote(id_norma))
    ahora = datetime.now(timezone.utc)
    captura_utc = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")
    resultado: dict = {
        "id": id_norma,
        "version_script": VERSION,
        "tema": fuente.get("tema"),
        "url_act": url_act,
        "captura_utc": captura_utc,
        "estado": "ok",
        "errores": [],
        "carpeta": None,
        "html": None,
        "pdf": None,
        "metadatos_pagina": {},
        "api_oficial": {
            "documentacion": URL_API_DOC,
            "usada": False,
            "motivo": MOTIVO_API_NO_USADA,
        },
        "atribucion": ATRIBUCION,
        "licencia": {
            "nombre": "Aviso legal del BOE",
            "url": URL_LICENCIA_BOE,
            "condiciones": (
                "Permite la extraccion y reordenacion con atribucion, indicando "
                "fechas y transformaciones. El consolidado es informativo y no "
                "tiene valor oficial."
            ),
        },
        "aplicabilidad": (
            "PENDIENTE: ambito y regimen transitorio sin verificar; no se afirma vigencia"
        ),
        "transitorio": "PENDIENTE",
        "fidelidad": (
            "NO COTEJADA: extraccion automatica; el HTML y el PDF se conservan sin "
            "modificar y requieren revision tecnica humana"
        ),
    }
    eventos: list[str] = []

    def anotar(mensaje: str) -> None:
        eventos.append(f"{datetime.now(timezone.utc).strftime('%H:%M:%SZ')} {mensaje}")

    def fallar(paso: str, mensaje: str) -> None:
        resultado["estado"] = "error"
        resultado["errores"].append({"paso": paso, "mensaje": mensaje})

    # 1. Pagina oficial act.php
    html_bytes: bytes | None = None
    url_final_html: str | None = None
    content_type_html: str | None = None
    try:
        html_bytes, url_final_html, content_type_html, _status = solicitud_con_reintentos(
            url_act, anotar
        )
    except urllib.error.HTTPError as error_http:
        fallar("descarga_html", f"HTTP {error_http.code} en {url_act}")
    except FalloPermanente as error_permanente:
        fallar("descarga_html", str(error_permanente))
    except Exception as error_generico:
        fallar("descarga_html", f"{type(error_generico).__name__}: {error_generico}")

    # 2. Analisis HTML y extraccion de metadatos
    analisis: AnalisisAct | None = None
    if html_bytes is not None:
        try:
            analisis = AnalisisAct()
            analisis.feed(html_bytes.decode("utf-8", errors="replace"))
            analisis.close()
        except Exception as error_parseo:
            fallar("analisis_html", f"{type(error_parseo).__name__}: {error_parseo}")
            analisis = None

    if analisis is not None:
        texto_plano = "\n".join(analisis.lineas)
        titulo = analisis.h1[0] if analisis.h1 else None
        titulo_fuente = "h1" if titulo else None
        if not titulo and analisis.titulo_html:
            titulo = analisis.titulo_html
            titulo_fuente = "html_title"
        eli, eli_fuente = buscar_eli(analisis.enlaces, url_final_html or url_act, texto_plano)
        publicacion, cruda_publicacion = valor_label(analisis.lineas, PATRON_PUBLICACION)
        version, cruda_version = valor_label(analisis.lineas, PATRON_VERSION)
        identificador, crudo_identificador = valor_label(analisis.lineas, PATRON_IDENTIFICADOR)
        diario, crudo_diario = valor_label(analisis.lineas, PATRON_DIARIO)
        date_document, fuente_dd, crudo_dd = buscar_date_document(analisis.lineas, titulo)
        resultado["metadatos_pagina"] = {
            "titulo": titulo,
            "titulo_fuente": titulo_fuente,
            "titulo_html_title": analisis.titulo_html,
            "eli": eli,
            "eli_fuente": eli_fuente,
            "fecha_publicacion": parsear_fecha(publicacion),
            "fecha_publicacion_cruda": publicacion,
            "date_document": date_document,
            "date_document_fuente": fuente_dd,
            "date_document_cruda": crudo_dd,
            "fecha_version": parsear_fecha(version),
            "fecha_version_cruda": version,
            "disposicion_literal": _unir_literal(
                [crudo_identificador, crudo_diario, cruda_publicacion, titulo]
            ),
            "identificador_pagina": identificador,
            "diario_crudo": diario,
            "aviso": (
                "Campos extraidos automaticamente con HTMLParser. Un campo null puede "
                "existir en la pagina y no haberse localizado: cotejar contra el "
                "act.html conservado. Revision humana pendiente."
            ),
        }

    # 3. Localizar y descargar el PDF (consolidado si existe; si no, original)
    tipo_pdf: str | None = None
    url_pdf: str | None = None
    href_pdf_crudo: str | None = None
    if analisis is not None:
        url_pdf, tipo_pdf, href_pdf_crudo = elegir_pdf(
            analisis.enlaces, id_norma, url_final_html or url_act
        )
        if url_pdf is None:
            fallar(
                "busqueda_pdf",
                "la pagina no ofrece ningun enlace PDF con el ID (ni consolidado ni "
                "original); no se inventa ninguno",
            )

    datos_pdf: bytes | None = None
    url_final_pdf: str | None = None
    content_type_pdf: str | None = None
    if url_pdf:
        try:
            validar_url(url_pdf)
        except FalloPermanente as error_enlace:
            fallar("busqueda_pdf", f"enlace PDF fuera de la politica de host/esquema: {error_enlace}")
            url_pdf = None
    if url_pdf:
        try:
            datos_pdf, url_final_pdf, content_type_pdf, _status = solicitud_con_reintentos(
                url_pdf, anotar
            )
        except urllib.error.HTTPError as error_http:
            fallar("descarga_pdf", f"HTTP {error_http.code} en {url_pdf}")
        except FalloPermanente as error_permanente:
            fallar("descarga_pdf", str(error_permanente))
        except Exception as error_generico:
            fallar("descarga_pdf", f"{type(error_generico).__name__}: {error_generico}")

    hash_pdf: str | None = None
    if datos_pdf is not None:
        if datos_pdf[:5] != b"%PDF-":
            fallar(
                "validacion_pdf",
                "firma %PDF- ausente; primeros bytes: " + datos_pdf[:8].hex(),
            )
            datos_pdf = None
        else:
            hash_pdf = sha256_hex(datos_pdf)

    # 4. Carpeta de snapshot: {ID}/{fecha UTC de captura}__{hash PDF | sin-pdf}
    sufijo = hash_pdf[:8] if hash_pdf else "sin-pdf"
    carpeta = carpeta_libre(salida_raiz / id_norma / f"{ahora.strftime('%Y%m%dT%H%M%SZ')}__{sufijo}")
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        resultado["carpeta"] = carpeta.relative_to(salida_raiz).as_posix()
    except ValueError:
        resultado["carpeta"] = str(carpeta)

    # 5. Guardar bytes originales sin modificar
    if html_bytes is not None:
        ruta_html = carpeta / "act.html"
        ruta_html.write_bytes(html_bytes)
        resultado["html"] = {
            "archivo": ruta_html.name,
            "sha256": sha256_hex(html_bytes),
            "bytes": len(html_bytes),
            "url_final": url_final_html,
            "content_type": content_type_html,
        }
    if datos_pdf is not None and tipo_pdf:
        nombre_pdf = f"{id_norma}-{tipo_pdf}.pdf"
        (carpeta / nombre_pdf).write_bytes(datos_pdf)
        entrada_pdf = {
            "archivo": nombre_pdf,
            "tipo": tipo_pdf,
            "enlace_en_pagina": href_pdf_crudo,
            "url": url_pdf,
            "url_final": url_final_pdf,
            "content_type": content_type_pdf,
            "sha256": hash_pdf,
            "bytes": len(datos_pdf),
        }
        if tipo_pdf == "original":
            entrada_pdf["nota"] = (
                "la pagina no ofrecia un PDF consolidado localizable con el ID; "
                "no se inventa consolidado"
            )
        resultado["pdf"] = entrada_pdf

    # 6. Metadatos JSON por fuente
    metadatos = dict(resultado)
    metadatos["eventos"] = eventos
    escribir_json(carpeta / "metadatos.json", metadatos)
    return resultado


def _resumen_fuente(r: dict) -> dict:
    mp = r.get("metadatos_pagina") or {}
    pdf = r.get("pdf") or {}
    errores = r.get("errores") or []
    texto_errores = "; ".join(
        f"[{e.get('paso')}] {e.get('mensaje')}" for e in errores if isinstance(e, dict)
    )
    return {
        "id": r["id"],
        "tema": r.get("tema"),
        "estado": r["estado"],
        "carpeta": r.get("carpeta"),
        "tipo_pdf": pdf.get("tipo"),
        "titulo": mp.get("titulo"),
        "fecha_publicacion": mp.get("fecha_publicacion"),
        "date_document": mp.get("date_document"),
        "fecha_version": mp.get("fecha_version"),
        "pdf_sha256": pdf.get("sha256"),
        "pdf_bytes": pdf.get("bytes"),
        "errores": texto_errores or None,
    }


def _celda(texto) -> str:
    if texto is None:
        return ""
    return str(texto).replace("|", "\\|").replace("\n", " ")


ALCANCE = [
    "Primera recopilacion reproducible de normativa espanola de edificacion "
    "adicional al CTE/RITE/RSCIEI (15 documentos legales, fuentes-ampliacion.json).",
    "Captura desde la pagina oficial https://www.boe.es/buscar/act.php?id={ID}. "
    "La API de datos abiertos (/legislacion-consolidada) respondio HTTP 400/404 en "
    "la verificacion de Codex (2026-11-15); retest pendiente.",
    "Los crudos (HTML, PDF y metadatos) permanecen solo en .local/ (gitignored): "
    "no se publican ni se integran en contenido/, el manifiesto o el visor.",
    "No se afirma vigencia ni aplicabilidad: ambito y regimen transitorio quedan "
    "pendientes por fuente.",
    "Fidelidad NO cotejada: extraccion automatica pendiente de revision tecnica "
    "humana; el HTML y el PDF originales se conservan sin modificar para el cotejo.",
    "Exclusiones: sin textos UNE y sin obras recopilatorias de Biblioteca Juridica "
    "(condiciones de licencia distintas).",
    "Atribucion: " + ATRIBUCION + " Licencia: " + URL_LICENCIA_BOE,
]


def escribir_resumen(salida_raiz: Path, parametros: dict, resultados: list[dict]) -> None:
    ok = sum(1 for r in resultados if r["estado"] == "ok")
    con_error = len(resultados) - ok
    resumen = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script_version": VERSION,
        "alcance": ALCANCE,
        "parametros": parametros,
        "totales": {"fuentes": len(resultados), "ok": ok, "error": con_error},
        "fuentes": [_resumen_fuente(r) for r in resultados],
    }
    escribir_json(salida_raiz / "resumen.json", resumen)

    lineas: list[str] = []
    ap = lineas.append
    ap("# Ingesta BOE — ampliación de normativa de edificación (primera tanda)")
    ap("")
    ap(
        f"Generado: {resumen['generado_utc']} · Script: `recopilar_boe.py` v{VERSION} · "
        "Semillas: `fuentes-ampliacion.json`"
    )
    ap("")
    ap("## Alcance")
    ap("")
    for item in ALCANCE:
        ap(f"- {item}")
    ap("")
    ap("## Resultado")
    ap("")
    ap("| ID | Tema | Estado | PDF | Título (extraído) | Publicación | Versión | SHA-256 (8) | Error |")
    ap("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for f in resumen["fuentes"]:
        sha8 = (f.get("pdf_sha256") or "")[:8]
        ap(
            "| "
            + " | ".join(
                [
                    _celda(f.get("id")),
                    _celda(f.get("tema")),
                    _celda(f.get("estado")),
                    _celda(f.get("tipo_pdf")),
                    _celda(f.get("titulo")),
                    _celda(f.get("fecha_publicacion")),
                    _celda(f.get("fecha_version")),
                    _celda(sha8),
                    _celda(f.get("errores")),
                ]
            )
            + " |"
        )
    ap("")
    tot = resumen["totales"]
    ap(f"Totales: {tot['ok']} ok / {tot['error']} con error sobre {tot['fuentes']} fuentes.")
    con_fallos = [f for f in resumen["fuentes"] if f.get("errores")]
    if con_fallos:
        ap("")
        ap("## Errores por fuente")
        ap("")
        for f in con_fallos:
            ap(f"- **{f.get('id')}** ({_celda(f.get('tema'))}): {f.get('errores')}")
    ap("")
    (salida_raiz / "resumen.md").write_text(
        "\n".join(lineas), encoding="utf-8", newline="\n"
    )


def cargar_fuentes() -> list[dict]:
    datos = json.loads(RUTA_FUENTES.read_text(encoding="utf-8"))
    fuentes = datos.get("fuentes")
    if not isinstance(fuentes, list) or not fuentes:
        raise ValueError("fuentes-ampliacion.json no contiene la lista 'fuentes'")
    return fuentes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Recopilacion reproducible de normativa espanola de edificacion (BOE): "
            "descarga paginas act.php, PDF y metadatos de las fuentes de "
            "fuentes-ampliacion.json."
        ),
    )
    parser.add_argument(
        "--salida",
        default=str(SALIDA_DEFECTO),
        help="directorio de salida (por defecto .local/ampliacion-boe en la raiz del checkout; mantenerlo fuera de rutas publicas)",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="procesar solo las N primeras fuentes del JSON",
    )
    parser.add_argument(
        "--solo-id",
        default=None,
        help="procesar unicamente el ID indicado (debe figurar en fuentes-ampliacion.json)",
    )
    args = parser.parse_args(argv)

    try:
        fuentes = cargar_fuentes()
    except (OSError, ValueError, KeyError) as error_config:
        log(f"FALLO: no se pudo cargar {RUTA_FUENTES}: {error_config}")
        return 2

    if args.solo_id:
        seleccion = [f for f in fuentes if f.get("id") == args.solo_id]
        if not seleccion:
            log(f"FALLO: --solo-id {args.solo_id} no figura en fuentes-ampliacion.json")
            return 2
    elif args.limite is not None:
        if args.limite <= 0:
            log("FALLO: --limite debe ser un entero positivo")
            return 2
        seleccion = fuentes[: args.limite]
    else:
        seleccion = fuentes

    invalidos = [f.get("id") for f in seleccion if not RE_ID_BOE.match(str(f.get("id") or ""))]
    if invalidos:
        log("FALLO: IDs con formato inesperado: " + ", ".join(map(str, invalidos)))
        return 2

    salida_raiz = Path(args.salida).expanduser()
    if salida_raiz.exists() and not salida_raiz.is_dir():
        log(f"FALLO: --salida existe y no es un directorio: {salida_raiz}")
        return 2
    salida_raiz.mkdir(parents=True, exist_ok=True)

    parametros = {
        "salida": str(salida_raiz),
        "limite": args.limite,
        "solo_id": args.solo_id,
        "pausa_s": PAUSA_S,
        "timeout_s": TIMEOUT_S,
        "max_reintentos": MAX_REINTENTOS,
        "max_bytes": MAX_BYTES,
        "hosts_permitidos": sorted(HOSTS_PERMITIDOS),
    }

    log(f"Ingesta BOE v{VERSION}: {len(seleccion)} fuente(s) -> {salida_raiz}")
    resultados: list[dict] = []
    for i, fuente in enumerate(seleccion, 1):
        id_norma = fuente.get("id")
        log(f"[{i}/{len(seleccion)}] {id_norma} ...")
        try:
            resultado = procesar_fuente(fuente, salida_raiz)
        except Exception as error_inesperado:
            resultado = {
                "id": id_norma,
                "tema": fuente.get("tema"),
                "url_act": URL_PLANTILLA_ACT.format(id=id_norma),
                "captura_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "estado": "error",
                "errores": [
                    {
                        "paso": "procesar_fuente",
                        "mensaje": f"{type(error_inesperado).__name__}: {error_inesperado}",
                    }
                ],
            }
        resultados.append(resultado)
        pdf = resultado.get("pdf") or {}
        mp = resultado.get("metadatos_pagina") or {}
        log(
            f"  -> {resultado['estado']}"
            f" pdf={pdf.get('tipo') or '-'}"
            f" titulo={(mp.get('titulo') or '-')[:80]}"
            + (f" errores={len(resultado['errores'])}" if resultado["errores"] else "")
        )

    escribir_resumen(salida_raiz, parametros, resultados)
    ok = sum(1 for r in resultados if r["estado"] == "ok")
    log(f"Resumen: {ok}/{len(resultados)} ok; reportes en {salida_raiz / 'resumen.json'} y resumen.md")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
