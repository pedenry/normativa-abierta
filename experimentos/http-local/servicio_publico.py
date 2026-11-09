#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entrada pública aislada para el corpus público de Normativa Abierta.

Read-only. Reutiliza http_consulta.Handler y acceso.py sin duplicar la
recuperación. Loopback por defecto; `--host 0.0.0.0` queda sólo para una
plataforma con proxy TLS. El HTTPS se aporta con un túnel/proxy externo.
"""
import argparse
import hashlib
import json
import os
import re
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit, urlparse

import http_consulta as H

BASE = "https://pedenry.github.io/normativa-abierta"
MAX_TARGET = 2048
MAX_LINE = 4096
MAX_Q = 400
MAX_DOC = 80
MAX_CONCURRENT = 8
TIMEOUT = 15
PERMITIDOS = {
    "/": set(),
    "/robots.txt": set(),
    "/buscar": {"q", "doc", "version", "version_antes_de", "prueba", "utm_source"},
    "/leer": {"doc", "page", "prueba", "utm_source"},
}
ERR = {400: "solicitud_invalida", 404: "no_encontrado", 405: "metodo_no_permitido",
       414: "uri_demasiado_larga", 503: "servicio_ocupado"}
_LOCK = threading.Lock()
_N = 0


def _base_externa():
    raw = os.environ.get("RENDER_EXTERNAL_URL")
    if not raw:
        return None
    try:
        u = urlsplit(raw.strip())
        puerto = u.port
        host = (u.hostname or "").lower()
    except ValueError:
        return None
    if u.scheme.lower() != "https" or u.username or u.password or u.query or u.fragment:
        return None
    if u.path not in ("", "/") or puerto not in (None, 443):
        return None
    if host != "onrender.com" and not host.endswith(".onrender.com"):
        return None
    return "https://" + host


def _siguiente():
    global _N
    with _LOCK:
        _N += 1
        return _N


class Handler(H.Handler):
    server_version = "NormativaAbiertaPublico/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(TIMEOUT)

    def send_error(self, code, message=None, explain=None):
        self._json({"error": ERR.get(code, "error")}, code)

    def _text(self, txt):
        b = txt.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _validar(self):
        u = urlparse(self.path)
        if u.path not in PERMITIDOS:
            self.send_error(404)
            return False
        qs = parse_qs(u.query, keep_blank_values=True)
        if len(qs) > len(PERMITIDOS[u.path]):
            self.send_error(400)
            return False
        for k, vs in qs.items():
            if k not in PERMITIDOS[u.path] or len(vs) != 1:
                self.send_error(400)
                return False
            if len(vs[0]) > MAX_Q:
                self.send_error(400)
                return False
        if "utm_source" in qs and qs["utm_source"][0] != "chatgpt.com":
            self.send_error(400)
            return False
        if "prueba" in qs:
            p = qs["prueba"][0]
            if not re.fullmatch(r"[A-Za-z0-9]{1,32}", p):
                self.send_error(400)
                return False
            self._prueba = p
        if u.path == "/buscar":
            q = (qs.get("q") or [""])[0]
            if len(q) > MAX_Q:
                self.send_error(400)
                return False
            d = (qs.get("doc") or [""])[0]
            if d and (len(d) > MAX_DOC or d in H.ESTADO["docs"]):
                if len(d) > MAX_DOC:
                    self.send_error(400)
                    return False
                self._doc_ev = d
        if u.path == "/leer":
            d = (qs.get("doc") or [""])[0]
            p = (qs.get("page") or [""])[0]
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", d):
                self.send_error(400)
                return False
            if not re.fullmatch(r"\d{1,4}", p) or not 1 <= int(p) <= 9999:
                self.send_error(400)
                return False
            if d in H.ESTADO["docs"]:
                self._doc_ev = d
                doc = H.ESTADO["docs"][d][0] or {}
                total = doc.get("paginas_pdf") or (doc.get("conteos") or {}).get("paginas")
                if isinstance(total, int) and 1 <= int(p) <= total:
                    self._page_ev = int(p)
        return True

    def do_GET(self):
        self._n = _siguiente()
        self._ruta = urlparse(self.path).path
        self._prueba = None
        self._doc_ev = None
        self._page_ev = None
        if len(self.path.encode("utf-8")) > MAX_TARGET or len(self.raw_requestline) > MAX_LINE:
            self.send_error(414)
            return
        if not self._validar():
            return
        if self._ruta == "/":
            self._html(LANDING)
            return
        if self._ruta == "/robots.txt":
            self._text(ROBOTS)
            return
        if self._ruta in ("/buscar", "/leer"):
            H.Handler.do_GET(self)
            return
        self.send_error(404)

    def _propagar(self, obj):
        base = _base_externa()
        for l in obj.get("lecturas") or []:
            h = l.get("href")
            if not isinstance(h, str) or not h.startswith("/leer"):
                continue
            if base:
                h = base + h
            if self._prueba and "prueba=" not in h:
                h += ("&" if "?" in h else "?") + "prueba=" + quote(self._prueba)
            l["href"] = h

    def _enlazar(self, obj):
        doc_id = obj.get("documento")
        page = obj.get("pagina")
        doc, base = H.ESTADO["docs"].get(doc_id, (None, None))
        if doc is None or not isinstance(page, int):
            return
        vd = doc.get("version_dir")
        sha = doc.get("sha256") or ""
        slug = "%s-%s-%s" % (str(doc.get("id") or doc_id).lower(),
                             str(vd or "").split("__", 1)[0].lower(), sha[:12])
        rec = {}
        pdf = base / "fuente.pdf"
        if pdf.is_file():
            rec["pdf"] = "%s/contenido/docs/%s/%s/fuente.pdf#page=%d" % (
                BASE, quote(doc_id), quote(vd), page)
        pagina = "%s__p%04d.html" % (slug, page)
        html = H.SITE / "pagina" / pagina
        if html.is_file():
            rec["pagina"] = "%s/site/pagina/%s" % (BASE, quote(pagina))
        tablas = []
        tdir = base / "tabla"
        if tdir.is_dir():
            for t in sorted(tdir.glob("p%04d_t*.json" % page)):
                tablas.append("%s/contenido/docs/%s/%s/tabla/%s" % (
                    BASE, quote(doc_id), quote(vd), quote(t.name)))
        if tablas:
            rec["tablas"] = tablas
        fig = base / "figura" / ("p%04d.png" % page)
        if fig.is_file():
            rec["figura"] = "%s/contenido/docs/%s/%s/figura/%s" % (
                BASE, quote(doc_id), quote(vd), quote(fig.name))
        if rec:
            obj["recursos"] = rec
        fuente = obj.get("fuente")
        if isinstance(fuente, str) and fuente:
            if (H.CONT / fuente).is_file():
                obj["fuente"] = BASE + "/contenido/" + quote(fuente)
            else:
                obj.pop("fuente", None)

    def _json(self, obj, code=200):
        if code >= 500:
            obj = {"error": "error_interno"}
        elif code == 200 and isinstance(obj, dict) and getattr(self, "_ruta", "") == "/buscar":
            self._propagar(obj)
        elif code == 200 and isinstance(obj, dict) and getattr(self, "_ruta", "") == "/leer":
            self._enlazar(obj)
        if not getattr(self, "_prueba", None):
            super()._json(obj, code)
            return
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
        self._evidencia(b, code)

    def _evidencia(self, cuerpo, code):
        texto = cuerpo.decode("utf-8", "replace")
        encs = H.ESTADO.get("encs") or {}
        ev = {
            "ruta": self._ruta,
            "metodo": self.command,
            "id": self._prueba,
            "status": code,
            "bytes": len(cuerpo),
            "sha256": hashlib.sha256(cuerpo).hexdigest(),
            "tokens_cuerpo": H.A.contar(texto, encs, "cl100k_base"),
            "target": self._ruta,
            "tokens_target": H.A.contar(self.path, encs, "cl100k_base"),
            "n": self._n,
        }
        if self._doc_ev:
            ev["documento"] = self._doc_ev
        if self._page_ev:
            ev["pagina"] = self._page_ev
        qs = parse_qs(urlparse(self.path).query)
        if "prueba" in qs:
            ev["extra_bytes"] = len("prueba=" + qs["prueba"][0])
        print(json.dumps(ev, ensure_ascii=False, sort_keys=True), flush=True)


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 8

    def __init__(self, addr, handler, sem):
        self.sem = sem
        super().__init__(addr, handler)

    def _cerrar(self, request):
        try:
            self.shutdown_request(request)
        except Exception:
            pass

    def _rechazar(self, request):
        try:
            request.settimeout(TIMEOUT)
            request.sendall(b"HTTP/1.1 503 Service Unavailable\r\n"
                            b"Content-Type: text/plain; charset=utf-8\r\n"
                            b"Content-Length: 0\r\nConnection: close\r\n\r\n")
        except Exception:
            pass
        self._cerrar(request)

    def process_request(self, request, client_address):
        if not self.sem.acquire(False):
            self._rechazar(request)
            return
        try:
            t = threading.Thread(target=self.process_request_thread,
                                 args=(request, client_address))
            t.daemon = self.daemon_threads
            t.start()
        except Exception:
            self.sem.release()
            self._cerrar(request)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.sem.release()

    def handle_error(self, request, client_address):
        pass


def validar(filas, docs):
    if len(docs) != 31:
        raise SystemExit("corpus público inesperado: se esperaban 31 documentos")
    base = H.CONT.resolve()
    for did, (doc, _) in docs.items():
        if doc.get("id") != did or doc.get("distribute") is not True:
            raise SystemExit("documento no público en el índice")
        if not doc.get("version_dir") or not re.fullmatch(r"[0-9a-f]{64}", str(doc.get("sha256") or "")):
            raise SystemExit("metadatos de documento incompletos")
    vistos = set()
    for f in filas:
        if f.get("documento") not in docs:
            raise SystemExit("fila fuera del corpus público")
        for k in ("doc_json", "archivo", "estructura"):
            rel = f.get(k)
            if not isinstance(rel, str) or not rel:
                raise SystemExit("referencia incompleta en el índice")
            if rel in vistos:
                continue
            vistos.add(rel)
            p = (H.CONT / rel).resolve()
            if p != base and base not in p.parents:
                raise SystemExit("referencia fuera del corpus")
            if not p.is_file():
                raise SystemExit("referencia inexistente en el corpus")


LANDING = """<!doctype html><html lang="es"><meta charset="utf-8">
<title>Normativa Abierta — consulta pública</title>
<body><h1>Normativa Abierta — consulta pública</h1>
<p>Servicio read-only de prueba. No es el visor oficial. El PDF y el SHA son la referencia.</p>
<p>Uso: <code>/buscar?q=consulta</code>; siga los <code>href</code> de <code>/leer?doc=...&amp;page=N</code>.</p>
<p>Evidencia opcional: añada <code>prueba=abc123</code> (alfanumérico corto, no secreto).</p>
<p><a href="%s/">GitHub Pages</a> · <a href="%s/site/index.html">índice</a> · <a href="%s/changelog/">cambios</a></p>
</body></html>""" % (BASE, BASE, BASE)
ROBOTS = "User-agent: *\nAllow: /\nDisallow: /estatico\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    ap.add_argument("--port", type=int, default=31118)
    args = ap.parse_args()
    cont = H.CONT
    H.A.cont_global = cont
    H.ESTADO.update(P=H.P, A=H.A, cont=cont)
    filas, docs = H.docs_publicos(cont)
    encs, _ = H.A.crear_contadores()
    H.ESTADO.update(filas=filas, docs=docs, encs=encs)
    validar(filas, docs)
    sem = threading.BoundedSemaphore(MAX_CONCURRENT)
    srv = Servidor((args.host, args.port), Handler, sem)
    print("http://%s:%d/ filas=%d docs=%d" % (args.host, args.port, len(filas), len(docs)), flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
