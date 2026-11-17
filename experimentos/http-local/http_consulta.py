#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime HTTP local read-only para el corpus público de Normativa Abierta.

Reutiliza acceso.py de esta misma carpeta. No importa validación, fixtures
ni resultados de evaluación.

Una única instancia AdaptadorContexto se construye en el arranque
(inicializar_estado) y se reutiliza: GET /buscar sin ningún filtro
doc/version/corte y GET /contexto la usan, sin construir adaptadores por
petición ni fallback global. /buscar con doc+version/corte conserva el camino
previo con A.construir_busqueda.
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
MAX_CONSULTA = 2000  # longitud máxima de `q` en /buscar y /contexto (caracteres)
PRESUPUESTO_CTX = 20000  # presupuesto_tokens del adaptador (/contexto y /buscar sin filtro)
MAX_RESULTADOS_CTX = 2   # max_resultados del adaptador (/contexto y /buscar sin filtro)


def docs_publicos(cont):
    """Interfaz previa conservada para cargar exclusivamente fuentes públicas."""
    filas = ESTADO["A"].cargar_indice(cont)
    docs = ESTADO["A"].cargar_docs(cont, filas)
    permitidos = {d for d, (dj, _base) in docs.items()
                  if (dj or {}).get("distribute") is True}
    filas = [f for f in filas if f["documento"] in permitidos]
    return filas, {d: v for d, v in docs.items() if d in permitidos}


def tarjeta_contexto(r):
    """Tarjeta proyectada desde recuperacion.resultados del adaptador. El
    resumen del adaptador no trae hash/código/capa: se conservan desde los
    metadatos del corpus (ESTADO.docs y, en su defecto, la fila del índice)."""
    doc_id = r.get("documento")
    dj = (ESTADO["docs"].get(doc_id) or (None, None))[0] or {}
    fila = next((f for f in ESTADO["filas"] if f.get("documento") == doc_id),
                None) if doc_id else None
    return {"documento": doc_id, "version": r.get("version"),
            "id_tecnico": r.get("id_tecnico"), "apartado_id": r.get("apartado_id"),
            "titulo": r.get("titulo"), "puntuacion_bm25": r.get("puntuacion_bm25"),
            "paginas": r.get("paginas") or [], "cita": r.get("cita"),
            "paginas_entregadas": r.get("paginas_entregadas") or [],
            "sha256": r.get("sha256") or dj.get("sha256"),
            "codigo": r.get("codigo") or dj.get("code") or (fila or {}).get("codigo"),
            "capa": r.get("capa") or dj.get("capa") or (fila or {}).get("capa")}


def lectura_contexto(pg):
    """Lectura proyectada EXACTAMENTE desde una página entregada por el
    adaptador (sin reabrir páginas ni volver a buscar); href hacia /leer."""
    doc_id = pg.get("doc")
    pag = int(pg.get("pagina") or 0)
    return {"documento": doc_id, "version": pg.get("version"),
            "sha256": pg.get("sha256"), "pagina": pg.get("pagina"),
            "motivo": pg.get("motivo"), "archivo": pg.get("archivo"),
            "url_fuente": pg.get("url_fuente"),
            "texto_sha256": pg.get("texto_sha256"),
            "etiqueta_impresa": pg.get("etiqueta_impresa"),
            "href": "/leer?doc=%s&page=%d" % (doc_id, pag)}


def inicializar_estado(cont=None):
    """Carga el corpus y construye el adaptador UNA sola vez: import perezoso,
    un único AdaptadorContexto y ESTADO completo (P/A/cont/filas/docs/encs/
    adaptador). Sin recarga por petición ni fallback global: las peticiones
    sólo leen ESTADO['adaptador']; si falta, las rutas que lo usan cierran 500."""
    if ESTADO.get("adaptador") is not None:
        return ESTADO
    from adaptador_contexto import AdaptadorContexto  # import perezoso
    cont = Path(cont).resolve() if cont else CONT
    A.cont_global = cont
    ad = AdaptadorContexto(cont, preparar_busqueda=True)
    ESTADO.update(P=P, A=A, cont=cont, filas=ad.filas, docs=ad.docs,
                  encs=ad.encs, adaptador=ad)
    return ESTADO


def opciones():
    preparado = getattr(ESTADO.get("adaptador"), "preparado_bm25", None)
    if not isinstance(preparado, dict):
        preparado = None
    return SimpleNamespace(max=3, presupuesto=6000, expandir=1, documento=None,
                           capa=None, materia=None, preparado_bm25=preparado)


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

    def _buscar_con_adaptador(self, q):
        """GET /buscar sin ningún filtro doc/version/corte: misma instancia
        reutilizada del adaptador (ESTADO['adaptador']), sin construir_busqueda
        ni fallback. Proyección: consulta/documentos/lecturas/advertencias más
        estado y aclaracion/resolucion_ambito si existen. Con aclaración o sin
        resultados: documentos y lecturas vacíos. Sin adaptador: cierre 500."""
        ad = ESTADO.get("adaptador")
        if ad is None:
            self._json({"error": "fallo_busqueda"}, 500)
            return
        try:
            out = ad.preparar(q, None, None, presupuesto_tokens=PRESUPUESTO_CTX,
                              max_resultados=MAX_RESULTADOS_CTX,
                              propagar_errores=True)
            rec = out.get("recuperacion") or {}
            estado = out.get("estado")
            if estado in ("sin_resultados", "aclaracion_necesaria"):
                docs_out, lecs_out = [], []
            else:
                docs_out = [tarjeta_contexto(r) for r in rec.get("resultados") or []]
                lecs_out = [lectura_contexto(p) for p in out.get("paginas") or []]
            resp = {"consulta": q, "estado": estado, "documentos": docs_out,
                    "lecturas": lecs_out,
                    "advertencias": rec.get("advertencias") or []}
            if out.get("aclaracion"):
                resp["aclaracion"] = out["aclaracion"]
            if out.get("resolucion_ambito"):
                resp["resolucion_ambito"] = out["resolucion_ambito"]
        except (SystemExit, Exception) as e:
            # 500 genérico: sin traceback, ruta ni consulta en cuerpo o log
            sys.stderr.write("fallo_busqueda: %s\n" % type(e).__name__)
            self._json({"error": "fallo_busqueda"}, 500)
            return
        self._json(resp)

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
                # Sin ningún filtro doc/version/corte: mismo adaptador
                # reutilizado (una instancia), sin construir_busqueda ni
                # fallback; responde y termina aquí.
                self._buscar_con_adaptador(q)
                return
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
            except Exception as e:
                sys.stderr.write("fallo_busqueda: %r\n" % (e,))
                self._json({"error": "fallo_busqueda"}, 500)
            return
        if u.path == "/contexto":
            ad = ESTADO.get("adaptador")
            if ad is None:
                # cierre en falso: sin adaptador inicializado no hay contexto
                self._json({"error": "fallo_contexto"}, 500)
                return
            for k in qs:
                if k not in ("q", "doc", "version", "version_antes_de",
                             "prueba", "utm_source"):
                    # prueba/utm_source: metadata del Handler público heredado
                    self._json({"error": "parametro_desconocido", "parametro": k}, 400)
                    return
            for k in ("q", "doc", "version", "version_antes_de"):
                if len(qs.get(k) or []) > 1:
                    self._json({"error": "parametro_duplicado", "parametro": k}, 400)
                    return
            q = (qs.get("q") or [""])[0].strip()
            if not q:
                self._json({"error": "falta q",
                            "ayuda": "/contexto?q=consulta [&doc=ID] "
                                     "[&version=AAAA-MM-DD | "
                                     "&version_antes_de=AAAA-MM-DD]"},
                           400)
                return
            if len(q) > MAX_CONSULTA:
                self._json({"error": "consulta_demasiado_larga"}, 400)
                return
            doc_id = (qs.get("doc") or [None])[0]
            ver_exacta = (qs.get("version") or [None])[0]
            ver_antes = (qs.get("version_antes_de") or [None])[0]
            if doc_id is not None and not doc_id.strip():
                self._json({"error": "parametros_version_invalidos"}, 400)
                return
            if (doc_id is None and
                    (ver_exacta is not None or ver_antes is not None)) or \
                    (ver_exacta is not None and ver_antes is not None):
                # version requiere doc; excluyente con version_antes_de
                self._json({"error": "parametros_version_invalidos"}, 400)
                return
            if (ver_exacta is not None and not ver_exacta.strip()) or \
                    (ver_antes is not None and not ver_antes.strip()):
                self._json({"error": "parametros_version_invalidos"}, 400)
                return
            for v in (ver_exacta, ver_antes):
                if v is None:
                    continue
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                    self._json({"error": "fecha_iso_invalida"}, 400)
                    return
                try:
                    date.fromisoformat(v)
                except ValueError:
                    self._json({"error": "fecha_iso_invalida"}, 400)
                    return
            objetivo = None
            if doc_id is not None:
                if doc_id not in ESTADO["docs"]:
                    self._json({"error": "documento_no_existe",
                                "documento": doc_id}, 404)
                    return
                # edición única del doc.json; sin fallback de edición: exacta o
                # estrictamente anterior al corte, jamás otra edición
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
                elif ver_antes is not None:
                    candidatas = [v for v in disponibles if v < ver_antes]
                    objetivo = candidatas[0] if candidatas else None
                if (ver_exacta is not None or ver_antes is not None) and \
                        objetivo is None:
                    self._json({"error": "version_no_disponible",
                                "documento": doc_id,
                                "version_solicitada": ver_exacta,
                                "version_antes_de": ver_antes,
                                "versiones_disponibles": disponibles}, 404)
                    return
            try:
                out = ad.preparar(q, doc_id, objetivo,
                                  presupuesto_tokens=PRESUPUESTO_CTX,
                                  max_resultados=MAX_RESULTADOS_CTX,
                                  propagar_errores=True)
                out = dict(out)
                out.pop("contenido", None)  # no mutar la salida del adaptador
                code = 404 if out.get("estado") in ("documento_no_disponible",
                                                    "version_no_disponible") else 200
            except (SystemExit, Exception) as e:
                # 500 genérico: sin traceback, ruta ni consulta en cuerpo o log
                sys.stderr.write("fallo_contexto: %s\n" % type(e).__name__)
                self._json({"error": "fallo_contexto"}, 500)
                return
            self._json(out, code)
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
    inicializar_estado(cont)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("http://%s:%d/ · contenido=%s" % (args.host, args.port, cont), flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
