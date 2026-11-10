#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime HTTP local read-only para el corpus público de Normativa Abierta.

Requiere --tools apuntando a la carpeta que contiene acceso.py (dependencia
reutilizada, no se copia aquí). No importa validación, fixtures ni resultados.
"""
import argparse
import json
import mimetypes
import os
import re
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlparse

P = Path(__file__).resolve().parents[2]
CONT = P / "contenido"
SITE = P / "site"
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import acceso as A
except Exception as e:
    raise SystemExit("Falta acceso.py local junto a http_consulta.py: %s" % e)
TIPOS = {".json": "application/json; charset=utf-8",
         ".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
         ".txt": "text/plain; charset=utf-8", ".pdf": "application/pdf",
         ".png": "image/png", ".csv": "text/csv; charset=utf-8"}
ESTADO = {}
MAX_CONSULTA = 2000  # longitud máxima de `q` en /buscar (caracteres)


def docs_publicos(cont):
    filas = ESTADO["A"].cargar_indice(cont)
    docs = ESTADO["A"].cargar_docs(cont, filas)
    # Sólo corpus distribuible: doc.json con distribute is True (mismo criterio
    # que adaptador_contexto), aplicado antes del IDF global. El filtrado de
    # candidatos por defecto (oficial+asociada) permanece intacto.
    permitidos = {d for d, (dj, _base) in docs.items()
                  if (dj or {}).get("distribute") is True}
    filas = [f for f in filas if f["documento"] in permitidos]
    docs = {d: v for d, v in docs.items() if d in permitidos}
    return filas, docs


def opciones():
    return SimpleNamespace(max=3, presupuesto=6000, expandir=1, documento=None,
                           capa=None, materia=None)


def ficha(r):
    return {"documento": r.get("documento"), "codigo": r.get("codigo"),
            "titulo": r.get("titulo"), "version": r.get("version"),
            "sha256": r.get("sha256"), "capa": r.get("capa"),
            "paginas": r.get("paginas") or [], "apartado_id": r.get("apartado_id"),
            "hallada": r.get("hallada")}


def plan_lecturas(busq):
    A, cont = ESTADO["A"], ESTADO["cont"]
    filas, docs, encs = ESTADO["filas"], ESTADO["docs"], ESTADO["encs"]
    lecs, vistos = [], set()
    for r in busq.get("resultados", [])[:3]:
        opt = SimpleNamespace(documento=r["documento"], apartado=None,
                              pagina=int(r["pagina"]), expandir=0) \
            if r.get("pagina") else SimpleNamespace(
                documento=r["documento"], apartado=r["apartado_id"],
                pagina=None, expandir=1)
        lec = A.construir_lectura(cont, filas, docs, opt, encs)
        paginas = set(int(p) for p in (r.get("paginas") or []))
        for p in (lec.get("contexto") or {}).get("paginas_fuente") or []:
            paginas.add(int(p["pagina"]))
        for p in (lec.get("contexto") or {}).get("paginas_continuadas") or []:
            paginas.add(int(p["pagina"]))
        for a in (r.get("contexto") or {}).get("auxiliares") or []:
            paginas.add(int(a["pagina"]))
        if (lec.get("pagina") or {}).get("pagina"):
            paginas.add(int(lec["pagina"]["pagina"]))
        for p in sorted(paginas):
            clave = (r["documento"], r.get("version"), r.get("sha256"), p)
            if clave in vistos:
                continue
            vistos.add(clave)
            lecs.append({"documento": r["documento"], "version": r.get("version"),
                         "sha256": r.get("sha256"), "pagina": p,
                         "motivo": "primario" if p in (r.get("paginas") or []) else "apoyo",
                         "href": "/leer?doc=%s&page=%d" % (r["documento"], p)})
    return lecs


class Handler(BaseHTTPRequestHandler):
    server_version = "NormativaAbiertaHttpLocal/1.0"
    # Validación de Host activa por defecto (sólo loopback con el puerto real
    # del socket). Una subclase puede desactivarla explícitamente con
    # validar_host = False, sin depender del Host del cliente ni del puerto:
    # p. ej. el Handler público detrás de un proxy TLS, que presenta el Host
    # externo.
    validar_host = True

    @staticmethod
    def _host_y_puerto(crudo):
        """Separa host y puerto de la cabecera Host (soporta [::1]:8080)."""
        v = (crudo or "").strip().lower()
        if v.startswith("["):
            h, _, resto = v.partition("]")
            return h.lstrip("["), (resto[1:] if resto.startswith(":") else "")
        h, sep, p = v.rpartition(":")
        return (h, p) if sep else (v, "")

    def _host_valido(self):
        """Host debe ser 127.0.0.1/localhost con el puerto real del socket.

        Sin puerto sólo se acepta si el servidor escucha en el 80.
        """
        crudo = self.headers.get("Host")
        if not crudo:
            return False
        host, puerto = self._host_y_puerto(crudo)
        if host not in ("127.0.0.1", "localhost"):
            return False
        try:
            real = int(self.server.server_port)
        except Exception:
            return False
        if puerto == "":
            return real == 80
        try:
            return int(puerto) == real
        except ValueError:
            return False

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _html(self, txt):
        b = txt.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        self.send_error(405, "sólo GET")

    def do_GET(self):
        if self.validar_host and not self._host_valido():
            self.send_error(403, "host no permitido")
            return
        u = urlparse(self.path)
        qs = parse_qs(u.query, keep_blank_values=True)
        if u.path == "/":
            self._html("<!doctype html><h1>Normativa Abierta — HTTP local</h1>"
                       "<p>GET <code>/buscar?q=consulta</code>; siga los enlaces "
                       "<code>/leer?doc=...&amp;page=N</code>. Sin escritura.</p>")
            return
        if u.path == "/buscar":
            q = (qs.get("q") or [""])[0].strip()
            if not q:
                self._json({"error": "falta q",
                            "ayuda": "/buscar?q=consulta o "
                                     "/buscar?q=consulta&doc=ID&version=YYYY-MM-DD "
                                     "(o version_antes_de=YYYY-MM-DD; doc obligatorio)"},
                           400)
                return
            if len(q) > MAX_CONSULTA:
                self._json({"error": "consulta_demasiado_larga"}, 400)
                return
            terminos = [t for t in re.split(r"[\s,;]+", q) if len(t) > 1]
            docs_ver = [v for v in (qs.get("doc") or [])]
            vers = [v for v in (qs.get("version") or [])]
            antes = [v for v in (qs.get("version_antes_de") or [])]
            filtrar = bool(docs_ver or vers or antes)
            doc_id = docs_ver[0] if len(docs_ver) == 1 else None
            ver_exacta = vers[0] if len(vers) == 1 else None
            ver_antes = antes[0] if len(antes) == 1 else None
            if filtrar:
                if (len(docs_ver) != 1 or len(vers) > 1 or len(antes) > 1 or
                        not doc_id or (ver_exacta and ver_antes) or
                        (not ver_exacta and not ver_antes)):
                    self._json({"error": "parametros_version_invalidos"}, 400)
                    return
                for v in (ver_exacta, ver_antes):
                    if v is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                        self._json({"error": "fecha_iso_invalida"}, 400)
                        return
                    if v is not None:
                        try:
                            date.fromisoformat(v)
                        except ValueError:
                            self._json({"error": "fecha_iso_invalida"}, 400)
                            return
                if doc_id not in ESTADO["docs"]:
                    self._json({"error": "documento_no_existe", "documento": doc_id}, 404)
                    return
                ver_doc = (ESTADO["docs"][doc_id][0] or {}).get("version")
                disponibles = []
                if ver_doc and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(ver_doc)):
                    try:
                        date.fromisoformat(str(ver_doc))
                        disponibles = [str(ver_doc)]
                    except ValueError:
                        disponibles = []
                if ver_exacta is not None:
                    objetivo = ver_exacta if ver_exacta in disponibles else None
                else:
                    candidatas = [v for v in disponibles if v < ver_antes]
                    objetivo = candidatas[0] if candidatas else None
                if objetivo is None:
                    self._json({"error": "version_no_disponible", "documento": doc_id,
                                "version_solicitada": ver_exacta,
                                "version_antes_de": ver_antes,
                                "versiones_disponibles": disponibles,
                                "documentos": [], "lecturas": []}, 404)
                    return
                op = opciones()
                op.documento = doc_id
            else:
                op = opciones()
            try:
                busq = ESTADO["A"].construir_busqueda(
                    ESTADO["cont"], ESTADO["filas"], ESTADO["docs"], q, terminos,
                    op, ESTADO["encs"])
                if filtrar:
                    resultados = busq.get("resultados", [])[:3]
                    lecs = plan_lecturas(busq)
                    if any(r.get("documento") != doc_id or
                           r.get("version") != objetivo for r in resultados) or \
                            any(l.get("documento") != doc_id or
                                l.get("version") != objetivo for l in lecs):
                        self._json({"error": "version_no_respetada",
                                    "documento": doc_id, "version": objetivo,
                                    "documentos": [], "lecturas": []}, 500)
                        return
                    self._json({"consulta": q,
                                "filtro": {"documento": doc_id, "version": objetivo},
                                "documentos": [ficha(r) for r in resultados],
                                "lecturas": lecs,
                                "advertencias": busq.get("advertencias") or []})
                else:
                    self._json({"consulta": q,
                                "documentos": [ficha(r) for r in
                                               busq.get("resultados", [])[:3]],
                                "lecturas": plan_lecturas(busq),
                                "advertencias": busq.get("advertencias") or []})
            except Exception as e:
                sys.stderr.write("fallo_busqueda: %r\n" % (e,))
                self._json({"error": "fallo_busqueda"}, 500)
            return
        if u.path == "/leer":
            doc = (qs.get("doc") or [""])[0]
            try:
                page = int((qs.get("page") or ["0"])[0])
            except ValueError:
                self._json({"error": "page inválida"}, 400)
                return
            if doc not in ESTADO["docs"]:
                self._json({"error": "documento no público"}, 404)
                return
            try:
                lec = ESTADO["A"].construir_lectura(
                    ESTADO["cont"], ESTADO["filas"], ESTADO["docs"],
                    SimpleNamespace(documento=doc, apartado=None, pagina=page,
                                    expandir=0), ESTADO["encs"])
            except SystemExit:
                self._json({"error": "documento o página no disponible"}, 404)
                return
            except Exception as e:
                sys.stderr.write("fallo_lectura: %r\n" % (e,))
                self._json({"error": "fallo_lectura"}, 500)
                return
            pg = lec.get("pagina") or {}
            docf = lec.get("documento") or {}
            self._json({"documento": doc, "version": docf.get("version"),
                        "sha256": docf.get("sha256"), "titulo": docf.get("titulo"),
                        "codigo": docf.get("codigo"), "pagina": page,
                        "texto": pg.get("texto") or "",
                        "ambito": (lec.get("ambito") or {}).get("texto") or "",
                        "fuente": pg.get("archivo"), "pdf": docf.get("url")})
            return
        if u.path == "/estatico":
            rel = unquote((qs.get("path") or [""])[0])
            partes = Path(rel).parts
            if (not rel or rel.startswith("/") or ".." in partes or
                    "\\" in rel or re.match(r"^[A-Za-z]:", rel) or
                    any(x.startswith(".") for x in partes)):
                self.send_error(403)
                return
            if Path(rel).suffix.lower() not in TIPOS:
                self.send_error(403)
                return
            cand = ESTADO["P"] / rel
            if not str(cand).startswith(str(ESTADO["P"]) + os.sep):
                self.send_error(403)
                return
            cur = cand
            while cur != ESTADO["P"]:
                if cur.is_symlink():
                    self.send_error(403)
                    return
                cur = cur.parent
            p = cand.resolve()
            permitido = any(p == base or base in p.parents for base in (CONT, SITE))
            if not permitido or not p.is_file():
                self.send_error(404)
                return
            if CONT in p.parents:
                partes = p.relative_to(CONT).parts
                if "docs" in partes:
                    i = partes.index("docs")
                    if i + 1 < len(partes) and partes[i + 1] not in ESTADO["docs"]:
                        self.send_error(403)
                        return
            b = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TIPOS.get(p.suffix.lower(),
                                                        "application/octet-stream"))
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self.send_error(404)

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=31117)
    args = ap.parse_args()
    if args.host not in ("127.0.0.1", "localhost"):
        raise SystemExit("sólo loopback")
    local_a = Path(__file__).resolve().with_name("acceso.py")
    if not local_a.exists():
        raise SystemExit("copie acceso.py íntegro junto a http_consulta.py")
    cont = CONT
    A.cont_global = cont
    ESTADO.update(P=P, A=A, cont=cont)
    filas, docs = docs_publicos(cont)
    encs, _ = A.crear_contadores()
    ESTADO.update(filas=filas, docs=docs, encs=encs)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("http://%s:%d/ · contenido=%s" % (args.host, args.port, cont), flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
