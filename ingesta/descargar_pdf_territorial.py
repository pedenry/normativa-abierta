#!/usr/bin/env python3
"""Descarga de PDF candidatos territoriales (solo .local/pdf-territorial).

Lee un JSON con ``candidatos[]`` (id, fuente_id, url, origen, texto_enlace,
hosts_permitidos) y descarga en secuencia con ``Rastreador.descargar`` de
recopilar_territorial (HTTPS, allowlist, robots, redirecciones y pausa >= 1 s;
el crawler no se reescribe ni se tocan otros scripts). Valida la firma
``%PDF-`` antes de guardar, calcula SHA-256 y verifica con pypdf apertura,
paginas y cifrado. Originales inmutables en ``archivos/{sha}.pdf``; metadata
por candidato (URL pedida/final, captura de red, sha, bytes, paginas, fuente,
origen, titulo del enlace) y ``resumen.json`` atomico tras cada descarga con
estados (ok/error/pendiente_limite/pendiente), totales y preview (2 primeras
paginas + ultima, max 2500 caracteres por candidato). Reanuda sin red si
id+URL canonica coinciden y el archivo existente pasa el hash (conserva
``capture_original``, registra ``reuso``); dedupe: SHA ya en ``archivos/`` o
URL canonica ya vista en esta ejecucion no duplica fichero (``dedupe``). El
presupuesto ``--max-total-mb`` limita la lectura al restante ANTES de cada
descarga. Ctrl+C escribe progreso y devuelve 130. PDF crudos sin cotejar:
sin publicacion ni corpus; licencia y revision humana aparte.

Uso (red y shell: Codex):
    python ingesta/descargar_pdf_territorial.py --origen candidatos.json
Salidas: 0 ok · 1 con errores · 2 configuracion invalida · 130 Ctrl+C.
"""

from __future__ import annotations

import argparse, hashlib, http.client, io, json, os, re, shutil, sys, tempfile, urllib.error  # noqa: E401
from datetime import datetime, timezone
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # se informa como error de configuracion (salida 2)
    PdfReader = None

from recopilar_territorial import (FalloConfig, FalloPermanente, Rastreador,
                                   normalizar_url, validar_salida)

VERSION = "1.0"
CHECKOUT_RAIZ = Path(__file__).resolve().parent.parent
SALIDA_BASE = CHECKOUT_RAIZ / ".local" / "pdf-territorial"
MB = 1024 * 1024
MAX_MB_DEFECTO, MAX_TOTAL_MB_DEFECTO, TIMEOUT_DEFECTO_S = 80, 2048, 20
MAX_PREVIEW = 2500
RESERVA_DISCO = 128 * MB
ID_VALIDO = r"[A-Za-z0-9][A-Za-z0-9_-]*"
ESTADOS = ("ok", "error", "pendiente_limite", "pendiente")
AVISO = ("Captura cruda de PDF candidatos: no son normas ni afirman vigencia; "
         "fidelidad, licencia por portal y revision humana PENDIENTES. Sin "
         "publicacion ni integracion al corpus.")


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def escribir_atomico(ruta, texto):
    """Escritura atomica: temporal en el mismo directorio + os.replace."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(dir=str(ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as flujo:
            flujo.write(texto)
        os.replace(temporal, ruta)
    except BaseException:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise


def escribir_atomico_bytes(ruta, datos):
    """Escritura atomica binaria: temporal en el mismo directorio + os.replace."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(dir=str(ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as flujo:
            flujo.write(datos)
        os.replace(temporal, ruta)
    except BaseException:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise


def guardar_metadata(ruta_meta, meta):
    escribir_atomico(ruta_meta, json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def validar_salida_pdf(ruta):
    """Restringe la salida a .local/pdf-territorial (validar_salida exige .local/)."""
    if ruta is None:
        return SALIDA_BASE
    salida = validar_salida(ruta)
    base = SALIDA_BASE.resolve()
    if salida != base and base not in salida.parents:
        raise FalloConfig(f"--salida solo acepta rutas dentro de {base}; recibido: {ruta}")
    return salida


def leer_candidatos(ruta):
    """Valida el JSON de candidatos; sin campos requeridos no hay descarga."""
    if not ruta.is_file():
        raise FalloConfig(f"origen no encontrado: {ruta}")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise FalloConfig(f"origen ilegible ({ruta}): {exc}")
    candidatos = datos.get("candidatos") if isinstance(datos, dict) else None
    if not isinstance(candidatos, list) or not candidatos:
        raise FalloConfig("origen sin 'candidatos' o lista vacia")
    vistos = set()
    for indice, cand in enumerate(candidatos):
        ident = cand.get("id") if isinstance(cand, dict) else None
        if not isinstance(ident, str) or not re.fullmatch(ID_VALIDO, ident):
            raise FalloConfig(f"candidato #{indice} con 'id' invalido: {ident!r}")
        if ident in vistos:
            raise FalloConfig(f"id duplicado en candidatos: {ident}")
        vistos.add(ident)
        if not isinstance(cand.get("fuente_id"), str) or not cand["fuente_id"].strip():
            raise FalloConfig(f"{ident}: sin 'fuente_id'")
        if not isinstance(cand.get("url"), str) or not cand["url"].strip():
            raise FalloConfig(f"{ident}: sin 'url'")
        if not [h for h in (cand.get("hosts_permitidos") or [])
                if isinstance(h, str) and h.strip()]:
            raise FalloConfig(f"{ident}: sin 'hosts_permitidos' utilizable")
    return candidatos


def validar_pdf(datos):
    """Firma %PDF-, SHA-256 y pypdf (paginas, cifrado, preview).

    Devuelve (sha, paginas, cifrado, preview, truncado); FalloPermanente si
    la firma o la lectura pypdf fallan (nada se guarda en ese caso)."""
    if b"%PDF-" not in datos[:1024]:
        raise FalloPermanente("sin firma %PDF- en los primeros 1024 bytes")
    sha = hashlib.sha256(datos).hexdigest()
    try:
        lector = PdfReader(io.BytesIO(datos))
        paginas = len(lector.pages)
        cifrado = bool(lector.is_encrypted)
        indices = [0, 1] if paginas >= 2 else ([0] if paginas == 1 else [])
        if paginas >= 3:
            indices.append(paginas - 1)
        textos = []
        for i in indices:
            try:
                textos.append(lector.pages[i].extract_text() or "")
            except Exception:
                textos.append("")
        preview = "\n<<<pagina>>>\n".join(t.strip() for t in textos)
    except Exception as exc:
        raise FalloPermanente(f"pypdf no pudo verificar el PDF: {exc}")
    return sha, paginas, cifrado, preview[:MAX_PREVIEW], len(preview) > MAX_PREVIEW


def procesar_candidato(cand, salida, rastreo, max_bytes_desc, por_presupuesto,
                       dedupe_url):
    """Descarga y valida un candidato; devuelve (detalle, bytes_descargados).

    Reanuda sin red si id+URL canonica coinciden y el archivo existente pasa
    el hash; dedupe por URL canonica en la misma ejecucion. ``por_presupuesto``
    distingue el limite de presupuesto (pendiente_limite) del maximo por
    fichero (error) cuando descargar aborta por tamano."""
    ident = cand["id"]
    canon = normalizar_url(cand["url"].strip())
    hosts = [h.strip().lower() for h in cand["hosts_permitidos"] if h.strip()]
    ruta_meta = salida / "metadata" / f"{ident}.json"
    previo = None
    if ruta_meta.is_file():
        try:
            previo = json.loads(ruta_meta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previo = None
    if isinstance(previo, dict) and previo.get("url_canonica") == canon \
            and previo.get("sha256"):
        archivo = salida / "archivos" / f"{previo['sha256']}.pdf"
        if archivo.is_file() and hashlib.sha256(
                archivo.read_bytes()).hexdigest() == previo["sha256"]:
            meta = dict(previo)
            meta["capture_original"] = previo.get("capture_original") \
                or previo.get("capturado_en_utc")
            meta.update({"reuso": True, "reanudado_en_utc": ahora()})
            guardar_metadata(ruta_meta, meta)
            return {"estado": "ok", "reuso": True, "dedupe": bool(previo.get("dedupe")),
                    "sha256": meta["sha256"], "bytes": meta["bytes"],
                    "paginas": meta.get("paginas"), "cifrado": meta.get("cifrado"),
                    "url_final": meta.get("url_final"),
                    "capture_original": meta["capture_original"],
                    "nota": "reusado sin red: hash del archivo verificado"}, 0
    if canon in dedupe_url:
        prev = dedupe_url[canon]
        captura = ahora()
        guardar_metadata(ruta_meta, {
            "id": ident, "fuente_id": cand["fuente_id"], "url_pedida": cand["url"],
            "url_canonica": canon, "url_final": prev.get("url_final"),
            "sha256": prev["sha256"], "bytes": prev["bytes"],
            "paginas": prev.get("paginas"), "cifrado": prev.get("cifrado"),
            "capture_original": prev.get("captura"), "capturado_en_utc": captura,
            "reuso": False, "dedupe": True, "origen": cand.get("origen"),
            "titulo_enlace": cand.get("texto_enlace"), "preview": None,
            "nota": "mismo SHA ya guardado; archivo no duplicado",
            "error": None, "aviso": AVISO})
        return {"estado": "ok", "reuso": False, "dedupe": True,
                "sha256": prev["sha256"], "bytes": prev["bytes"],
                "paginas": prev.get("paginas"), "cifrado": prev.get("cifrado"),
                "url_final": prev.get("url_final"),
                "capture_original": prev.get("captura"),
                "nota": "URL canonica ya descargada en esta ejecucion"}, 0
    libre = shutil.disk_usage(salida).free - RESERVA_DISCO
    if libre <= 0:
        return {"estado": "pendiente_limite",
                "nota": "espacio en disco insuficiente (reserva 128 MiB)",
                "motivo": "espacio_disco"}, 0
    if libre < max_bytes_desc:
        max_bytes_desc = int(libre)
        por_presupuesto = True  # el exceso por disco es pendiente_limite, no fallo PDF
    try:
        datos, estado_http, url_final, tipo, total = rastreo.descargar(
            cand["url"].strip(), hosts, max_bytes=max_bytes_desc, exigir_tipo=False)
    except FalloPermanente as exc:
        estado = ("pendiente_limite" if por_presupuesto
                  and "excede el maximo" in str(exc) else "error")
        return {"estado": estado, "error": str(exc), "url_final": None}, 0
    except urllib.error.HTTPError as exc:
        return {"estado": "error", "error": f"HTTP {exc.code}", "url_final": None}, 0
    except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        return {"estado": "error", "error": f"error de red: {exc}", "url_final": None}, 0
    try:
        sha, paginas, cifrado, preview, truncado = validar_pdf(datos)
    except FalloPermanente as exc:
        return {"estado": "error", "error": str(exc), "url_final": url_final,
                "estado_http": estado_http, "tipo_contenido": tipo or None,
                "bytes_descargados": total}, total
    archivo = salida / "archivos" / f"{sha}.pdf"
    existente = archivo.read_bytes() if archivo.is_file() else None
    dedupe = existente is not None and \
        hashlib.sha256(existente).hexdigest() == sha
    if not dedupe:
        if existente is not None:
            # fichero corrupto (hash distinto): preservarlo en corruptos/ con
            # nombre por su hash real y reponer los bytes correctos; nunca se
            # toca un original correcto ni se marca ok sin verificar el SHA
            destino = salida / "corruptos" / \
                f"{hashlib.sha256(existente).hexdigest()}.pdf"
            if not destino.exists():
                escribir_atomico_bytes(destino, existente)
        escribir_atomico_bytes(archivo, datos)
        if hashlib.sha256(archivo.read_bytes()).hexdigest() != sha:
            return {"estado": "error",
                    "error": "el archivo final no verifica el SHA; no se marca ok"}, \
                total
    captura = ahora()
    guardar_metadata(ruta_meta, {
        "id": ident, "fuente_id": cand["fuente_id"], "url_pedida": cand["url"],
        "url_canonica": canon, "url_final": url_final, "estado_http": estado_http,
        "tipo_contenido": tipo or None, "sha256": sha, "bytes": len(datos),
        "paginas": paginas, "cifrado": cifrado, "capture_original": captura,
        "capturado_en_utc": captura, "reuso": False, "dedupe": dedupe,
        "origen": cand.get("origen"), "titulo_enlace": cand.get("texto_enlace"),
        "preview": preview, "preview_truncado": truncado,
        "error": None, "aviso": AVISO})
    dedupe_url[canon] = {"sha256": sha, "bytes": len(datos), "paginas": paginas,
                         "cifrado": cifrado, "url_final": url_final, "captura": captura}
    return {"estado": "ok", "reuso": False, "dedupe": dedupe, "sha256": sha,
            "bytes": len(datos), "paginas": paginas, "cifrado": cifrado,
            "url_final": url_final, "estado_http": estado_http,
            "capture_original": captura}, total


def construir_resumen(argumentos, resultados, bytes_usados, interrumpido):
    totales = {e: 0 for e in ESTADOS}
    totales.update({"reuso": 0, "dedupe": 0, "bytes": bytes_usados})
    shas = set()
    for r in resultados:
        totales[r["estado"]] = totales.get(r["estado"], 0) + 1
        totales["reuso"] += 1 if r.get("reuso") else 0
        totales["dedupe"] += 1 if r.get("dedupe") else 0
        if r.get("sha256"):
            shas.add(r["sha256"])
    totales["archivos_unicos"] = len(shas)
    return {"version": VERSION, "ejecutado_en_utc": ahora(),
            "interrumpido": bool(interrumpido), "argumentos": argumentos,
            "totales": totales, "aviso": AVISO,
            "pendientes": {"fidelidad": "NO COTEJADA: PDF crudo sin revision humana",
                           "licencia": "PENDIENTE por portal: revisar antes de publicar",
                           "vigencia": "PENDIENTE: sin ambito ni transitorio verificados"},
            "candidatos": resultados}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Descarga PDF candidatos territoriales (solo "
                    ".local/pdf-territorial, resumen atomico, sin publicar).")
    parser.add_argument("--origen", required=True,
                        help="JSON con candidatos[] (id, fuente_id, url, origen, "
                             "texto_enlace, hosts_permitidos)")
    parser.add_argument("--salida", default=None,
                        help="directorio de salida; SOLO dentro de .local/pdf-territorial")
    parser.add_argument("--limite", type=int, default=None,
                        help="procesar solo los N primeros candidatos")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_DEFECTO_S,
                        help=f"timeout de red en segundos (defecto {TIMEOUT_DEFECTO_S})")
    parser.add_argument("--max-mb", type=int, default=MAX_MB_DEFECTO,
                        help=f"maximo MB por PDF (defecto {MAX_MB_DEFECTO})")
    parser.add_argument("--max-total-mb", type=int, default=MAX_TOTAL_MB_DEFECTO,
                        help=f"presupuesto total en MB (defecto {MAX_TOTAL_MB_DEFECTO})")
    args = parser.parse_args(argv)
    if PdfReader is None:
        print("error de configuracion: pypdf no instalado (python -m pip install "
              "-r ingesta/requirements.txt)", file=sys.stderr)
        return 2
    try:
        candidatos = leer_candidatos(Path(args.origen))
        if args.limite is not None:
            if args.limite < 1:
                raise FalloConfig("--limite debe ser >= 1")
            candidatos = candidatos[:args.limite]
        salida = validar_salida_pdf(args.salida)
        max_bytes = max(1, int(args.max_mb)) * MB
        max_total = max(1, int(args.max_total_mb)) * MB
        timeout = max(1, int(args.timeout))
    except FalloConfig as exc:
        print(f"error de configuracion: {exc}", file=sys.stderr)
        return 2
    rastreo = Rastreador(1, timeout)
    salida.mkdir(parents=True, exist_ok=True)
    argumentos = {"origen": str(Path(args.origen)), "salida": str(salida),
                  "limite": args.limite, "timeout_s": timeout,
                  "max_mb": args.max_mb, "max_total_mb": args.max_total_mb}
    ruta_resumen = salida / "resumen.json"
    resultados, bytes_usados, dedupe_url = [], 0, {}
    codigo, interrumpido, cand_en_curso = 0, False, None

    def persistir():
        escribir_atomico(ruta_resumen, json.dumps(
            construir_resumen(argumentos, resultados, bytes_usados, interrumpido),
            ensure_ascii=False, indent=2) + "\n")
    try:
        for cand in candidatos:
            cand_en_curso = cand
            base = {"id": cand["id"], "fuente_id": cand["fuente_id"],
                    "url": cand["url"], "origen": cand.get("origen"),
                    "titulo_enlace": cand.get("texto_enlace")}
            restante = max_total - bytes_usados
            if restante <= 0:
                base.update({"estado": "pendiente_limite",
                             "nota": "presupuesto --max-total-mb agotado"})
                resultados.append(base)
                persistir()
                continue
            try:
                detalle, bytes_desc = procesar_candidato(
                    cand, salida, rastreo, min(max_bytes, restante),
                    restante < max_bytes, dedupe_url)
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # conservar el progreso y seguir
                detalle = {"estado": "error", "error": f"excepcion no esperada: {exc}"}
                bytes_desc = 0
            bytes_usados += bytes_desc
            base.update(detalle)
            resultados.append(base)
            persistir()
            print(f"[{base['estado']:>16}] {base['id']}: "
                  f"{str(base.get('sha256') or '-')[:12]} "
                  f"pag={base.get('paginas')} bytes={base.get('bytes')}")
    except KeyboardInterrupt:
        interrumpido, codigo = True, 130
        pendientes = candidatos[len(resultados):]
        if pendientes and pendientes[0] is cand_en_curso:
            resultados.append({"id": pendientes[0]["id"],
                               "fuente_id": pendientes[0]["fuente_id"],
                               "url": pendientes[0]["url"], "estado": "pendiente",
                               "nota": "interrumpido por Ctrl+C a mitad de proceso"})
            pendientes = pendientes[1:]
        for cand in pendientes:
            resultados.append({"id": cand["id"], "fuente_id": cand["fuente_id"],
                               "url": cand["url"], "estado": "pendiente",
                               "nota": "interrumpido por Ctrl+C antes de procesar"})
    finally:
        persistir()
    if interrumpido:
        print(f"Interrumpido (Ctrl+C): progreso en {ruta_resumen}", file=sys.stderr)
    elif any(r["estado"] == "error" for r in resultados):
        codigo = 1
    print(f"Resumen: {ruta_resumen} · {AVISO}")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
