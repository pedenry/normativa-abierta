#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integra fuentes territoriales revisadas (JSON de entrada) en contenido/.

Encargo 2026-11-16: solo crea este archivo. Valida fail-closed TODO antes de
escribir; extrae texto con pypdf por pagina fisica, sin inventar jerarquia,
articulos ni etiquetas impresas; conserva los bytes del PDF.
Uso (desde cwd EXTERIOR): python normativa-abierta/ingesta/integrar_territorial.py --origen fuentes.json [--simular]
"""
import argparse, datetime, hashlib, json, os, re, shutil, sys, tempfile
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("ERROR: pypdf no instalado (ver ingesta/requirements.txt)")

ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}|sin-fecha)$")
FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTTPS_RE = re.compile(r"^https://\S+$")
LIC_FICHERO = "territorial-2026-11-16.json"
PROHIBIDAS = ("guia", "guía", "obra privada", "todos los derechos",
              "copyright", "sin derecho")

def die(msg):
    sys.exit("ERROR preflight: " + msg)

def chk(cond, msg):
    if not cond:
        die(msg)

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def escribe_atomo(ruta, datos):
    """Escritura atomica: temporal en el mismo dir + os.replace."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(datos if isinstance(datos, bytes) else datos.encode("utf-8"))
        os.replace(tmp, str(ruta))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

def jbytes(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")

def req_str(obj, k, vid):
    v = obj.get(k)
    chk(isinstance(v, str) and v.strip(), "%s: campo '%s' ausente o vacio" % (vid, k))
    return v

def valida_reutilizacion(r, vid):
    reu = r.get("reutilizacion")
    chk(isinstance(reu, dict) and reu.get("estado") == "APROBADA",
        "reutilizacion ausente o != APROBADA (sin excepciones): " + vid)
    for k in ("base_juridica", "alcance", "revision_por"):
        req_str(reu, k, vid)
    chk(bool(HTTPS_RE.match(req_str(reu, "evidencia_url", vid))),
        "evidencia_url no HTTPS: " + vid)
    ev = Path(req_str(reu, "evidencia_ruta_local", vid))
    chk(ev.is_file() and sha256_bytes(ev.read_bytes()) == reu.get("evidencia_sha256"),
        "evidencia ausente o evidencia_sha256 no coincide: " + vid)
    texto = " ".join([reu["base_juridica"], reu["alcance"], r["creditos"]]).lower()
    for t in PROHIBIDAS:
        chk(t not in texto,
            "termino prohibido '%s' (guia/obra privada/sin derechos): %s" % (t, vid))
    return reu

def preflight(r, vistos):
    """Validacion fail-closed de campos y derechos por fuente."""
    vid = r.get("id", "?")
    chk(isinstance(r, dict) and ID_RE.match(str(vid)), "ID inseguro ([A-Za-z0-9_-]+): %s" % (vid,))
    chk(vid not in vistos, "ID duplicado en entrada: " + vid)
    vistos.add(vid)
    for k in ("titulo", "disposicion", "jurisdiccion", "materia",
              "version_label_literal", "creditos", "capturado_en_utc"):
        req_str(r, k, vid)
    mun = r.get("municipio")
    chk(mun is None or (isinstance(mun, str) and mun.strip()), "municipio debe ser texto no vacio o null: " + vid)
    v = req_str(r, "version", vid)
    chk(bool(VER_RE.match(v)),
        "version no ISO ni 'sin-fecha' (nunca inventada desde captura): %s %s" % (vid, v))
    if v != "sin-fecha":
        datetime.date.fromisoformat(v)
    fp = r.get("fecha_publicacion")
    chk(fp is None or (isinstance(fp, str) and FECHA_RE.match(fp)),
        "fecha_publicacion debe ser null o ISO: " + vid)
    n = r.get("paginas_fisicas")
    chk(isinstance(n, int) and not isinstance(n, bool) and n >= 1,
        "paginas_fisicas invalida: " + vid)
    for k in ("url_pdf", "url_fuente"):
        chk(bool(HTTPS_RE.match(req_str(r, k, vid))), "%s no HTTPS: %s" % (k, vid))
    valida_reutilizacion(r, vid)

def extrae_pdf(r):
    """Firma %PDF-, hash, concordancia de paginas y texto extraible no vacio."""
    vid = r["id"]
    pdf = Path(r["ruta_pdf"])
    chk(pdf.is_file(), "PDF no encontrado %s: %s" % (vid, pdf))
    b = pdf.read_bytes()
    chk(b[:5] == b"%PDF-", "firma %PDF- ausente: " + vid)
    chk(sha256_bytes(b) == r["sha256_pdf"], "sha256_pdf no coincide: " + vid)
    try:
        lector = PdfReader(str(pdf))
        paginas = [(p.extract_text() or "") for p in lector.pages]
    except Exception as e:
        die("pypdf no puede leer %s: %s" % (vid, e))
    chk(len(paginas) == r["paginas_fisicas"], "paginas pypdf %d != paginas_fisicas %s: %s" % (len(paginas), r["paginas_fisicas"], vid))
    chk(any(t.strip() for t in paginas), "texto extraible vacio: " + vid)
    return paginas

def integra(r, paginas, contenido, previos, versiones, filas_nuevas):
    vid = r["id"]
    vdir = contenido / "docs" / vid / ("%s__%s" % (r["version"], r["sha256_pdf"][:12]))
    vdir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(r["ruta_pdf"]), vdir / "fuente.pdf")
    rel = "docs/%s/%s__%s" % (vid, r["version"], r["sha256_pdf"][:12])
    frags, pags, caracteres = [], [], 0
    for n, texto in enumerate(paginas, start=1):
        pn = "p%04d" % n
        for sub in ("pagina", "apartado"):
            (vdir / sub).mkdir(exist_ok=True)
            (vdir / sub / (pn + ".md")).write_text(texto, encoding="utf-8", newline="\n")
        frag = {"id_tecnico": pn, "titulo": "Pagina fisica %d - %s" % (n, r["materia"]),
                "ruta_oficial": None, "ruta_semantica": "Pagina fisica %d" % n,
                "seccion_estimada": "Pagina fisica %d" % n, "parent_id": None, "nivel": 1,
                "paginas": [n], "etiquetas_impresas": [None], "tipos": [], "referencias": [],
                "jerarquia_verificada": False, "ruta_oficial_verificada": False,
                "es_encabezado_navegacion": False, "archivo": "apartado/%s.md" % pn,
                "archivo_json": "apartado/%s.json" % pn, "caracteres": len(texto),
                "primera_linea": texto.splitlines()[0] if texto.strip() else "",
                "sha256_texto": sha256_bytes(texto.encode("utf-8"))}
        escribe_atomo(vdir / "apartado" / (pn + ".json"), jbytes(dict(frag, texto=texto)))
        frags.append(frag)
        pags.append({"n": n, "pagina_md": "pagina/%s.md" % pn, "etiqueta_impresa": None, "tablas": 0})
        caracteres += len(texto)
        fila = dict(frag)
        fila.update({"documento": vid, "codigo": vid, "materia": r["materia"], "capa": "asociada",
                     "version": r["version"], "apartado_id": "%s/%s" % (vid, pn),
                     "archivo": rel + "/apartado/%s.md" % pn,
                     "archivo_json": rel + "/apartado/%s.json" % pn,
                     "doc_json": rel + "/doc.json", "estructura": rel + "/estructura.json",
                     "jurisdiccion": r["jurisdiccion"], "municipio": r.get("municipio")})
        filas_nuevas.append(fila)
    reu = r["reutilizacion"]
    adv = ["Extraccion automatica (pypdf): tablas, formulas y notas sin cotejar.",
           "Etiquetas impresas desconocidas; jerarquia y articulos no inventados; figuras no cotejadas.",
           "Fidelidad del texto no cotejada visualmente con el PDF.",
           "Vigencia, regimen transitorio y aplicabilidad pendientes de verificacion.",
           "Atribucion: " + r["creditos"]] + list(r.get("advertencias", []))
    ev_meta = {k: r[k] for k in ("emisor_literal", "version_origen",
               "fecha_publicacion_literal", "fecha_publicacion_boe", "tipo",
               "procedencia_catalogo", "cotejos_automaticos")
               if r.get(k) not in (None, "", [], {})}
    doc = {"id": vid, "code": vid, "title": r["titulo"], "layer": "asociada", "scope": r["materia"],
           "version": r["version"], "version_dir": vdir.name,
           "version_label_literal": r["version_label_literal"], "sha256": r["sha256_pdf"],
           "url": r["url_pdf"], "landing": r["url_fuente"], "distribute": True, "normativo": True,
           "jurisdiccion": r["jurisdiccion"], "municipio": r.get("municipio"),
           "disposicion": r["disposicion"], "fecha_publicacion": r.get("fecha_publicacion"),
           "license_status": reu["base_juridica"], "license_evidence": "licencias/" + LIC_FICHERO,
           "creditos": r["creditos"], "ambito_literal": None,
           "conteos": {"paginas": len(pags), "apartados": len(frags), "caracteres": caracteres},
           "tablas_por_pagina": {}, "figuras": [], "formulas": {},
           "metodo_segmentacion": "pagina_fisica", "nota_capa": None,
           "extraccion": r.get("extraccion"), "advertencias": adv,
           "evidencia_metadatos": ev_meta}
    escribe_atomo(vdir / "doc.json", jbytes(doc))
    escribe_atomo(vdir / "estructura.json",
                  jbytes({"id": vid, "version": r["version"], "apartados": frags}))
    escribe_atomo(vdir / "paginas.json",
                  jbytes({"id": vid, "version": r["version"], "paginas": pags}))
    ficha_p = contenido / "fichas" / (vid + ".json")
    ficha = json.loads(ficha_p.read_text(encoding="utf-8")) if ficha_p.is_file() else {}
    ficha.update(doc)
    ficha.update({"codigo": doc["code"], "titulo": doc["title"], "capa": doc["layer"]})
    escribe_atomo(ficha_p, jbytes(ficha))
    versiones.append({"id": vid, "version": r["version"], "sha256_pdf": r["sha256_pdf"],
                      "url_pdf": r["url_pdf"], "url_fuente": r["url_fuente"],
                      "capturado_en_utc": r["capturado_en_utc"],
                      "jurisdiccion": r["jurisdiccion"], "municipio": r.get("municipio"),
                      "disposicion": r["disposicion"],
                      "fecha_publicacion": r.get("fecha_publicacion"),
                      "paginas": len(pags), "apartados": len(frags), "caracteres": caracteres,
                      "metodo_segmentacion": "pagina_fisica",
                      "paginas_vacias": sum(1 for t in paginas if not t.strip()),
                      "creditos": r["creditos"],
                      "reutilizacion": {"estado": reu["estado"], "base_juridica": reu["base_juridica"],
                          "evidencia_url": reu["evidencia_url"], "evidencia_sha256": reu["evidencia_sha256"],
                          "alcance": reu["alcance"], "revision_por": reu["revision_por"]}})
    previos[vid] = {"id": vid, "codigo": vid, "titulo": r["titulo"], "capa": "asociada",
                    "scope": r["materia"], "version": r["version"], "version_dir": vdir.name,
                    "version_label_literal": r["version_label_literal"],
                    "sha256": r["sha256_pdf"], "distribute": True, "url": r["url_pdf"],
                    "estado": "preparado_local", "jurisdiccion": r["jurisdiccion"],
                    "municipio": r.get("municipio")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", required=True)
    ap.add_argument("--contenido", default=str(Path(__file__).resolve().parents[1] / "contenido"))
    ap.add_argument("--simular", action="store_true", help="preflight completo sin escribir")
    args = ap.parse_args()
    contenido = Path(args.contenido)
    fuentes = json.loads(Path(args.origen).read_text(encoding="utf-8")).get("fuentes", [])
    chk(isinstance(fuentes, list) and fuentes, "entrada sin fuentes")
    # --- Preflight fail-closed de TODAS antes de tocar el corpus
    vistos, extraidos = set(), {}
    for r in fuentes:
        preflight(r, vistos)
        extraidos[r["id"]] = extrae_pdf(r)
    # --- Idempotencia contra manifest e indice reales (mismo hash: nada)
    manifest_p = contenido / "manifest_publico.json"
    indice_p = contenido / "indice" / "apartados.jsonl"
    manifest = {"generado_por": "ingesta/integrar_territorial.py",
                "manifest_nombre": "manifest_publico.json", "manifest_sha256": None,
                "entradas": [], "nota": None}
    if manifest_p.is_file():
        manifest.update(json.loads(manifest_p.read_text(encoding="utf-8")))
    previos = {e.get("id"): e for e in manifest.get("entradas", [])}
    indice_bytes = indice_p.read_bytes() if indice_p.is_file() else b""
    ya_indice = set()
    for linea in indice_bytes.splitlines():
        if linea.strip():
            ya_indice.add(json.loads(linea.decode("utf-8")).get("documento"))
    nuevas = []
    for r in fuentes:
        vid = r["id"]
        anterior = previos.get(vid)
        if anterior:
            if anterior.get("sha256") == r["sha256_pdf"]:
                continue  # ya integrado, idempotente
            die("ID ya indexado con distinto hash: " + vid)
        chk(vid not in ya_indice, "ID en indice con distinto hash: " + vid)
        nuevas.append(r)
    if not nuevas:
        print("Todo ya integrado; exit 0 sin reescribir.")
        return
    # --- Contradiccion con registros previos antes de tocar el corpus
    raiz = contenido.resolve().parent
    lic_p = raiz / "licencias" / LIC_FICHERO
    val_p = contenido / "validacion" / LIC_FICHERO
    docs_prev = (json.loads(lic_p.read_text(encoding="utf-8")).get("documentos", [])
                 if lic_p.is_file() else [])
    val_prev = (json.loads(val_p.read_text(encoding="utf-8")).get("fuentes", [])
                if val_p.is_file() else [])
    prev_sha = {d.get("id"): d.get("sha256") for d in docs_prev}
    prev_sha.update({d.get("id"): d.get("sha256_pdf") for d in val_prev})
    for r in nuevas:
        if r["id"] in prev_sha and prev_sha[r["id"]] != r["sha256_pdf"]:
            die("contradiccion registros previos id=%s sha_previo=%s sha_nuevo=%s"
                % (r["id"], prev_sha[r["id"]], r["sha256_pdf"]))
    if args.simular:
        print("Preflight OK: %d fuentes validadas; %d nuevas a integrar (--simular, nada escrito)."
              % (len(fuentes), len(nuevas)))
        for r in nuevas:
            print(" - %s [%s%s] %s" % (r["id"], r["jurisdiccion"],
                  ", " + r["municipio"] if r.get("municipio") else "", r["titulo"]))
        return
    versiones, filas_nuevas = [], []
    for r in nuevas:
        integra(r, extraidos[r["id"]], contenido, previos, versiones, filas_nuevas)
    # --- Indice: conserva bytes anteriores, append una vez, sin duplicados
    if filas_nuevas:
        prefijo = b"" if not indice_bytes or indice_bytes.endswith(b"\n") else b"\n"
        anexo = prefijo + "".join(json.dumps(f, ensure_ascii=False) + "\n"
                                  for f in filas_nuevas).encode("utf-8")
        escribe_atomo(indice_p, indice_bytes + anexo)
    manifest["entradas"] = list(previos.values())
    manifest["ampliaciones"] = (manifest.get("ampliaciones") or []) + [{
        "generador": "ingesta/integrar_territorial.py", "fecha": "2026-11-16",
        "ids": [v["id"] for v in versiones],
        "nota": "manifest_sha256 es historico del conjunto anterior."}]
    escribe_atomo(manifest_p, jbytes(manifest))
    # --- Validacion interna (contenido) y licencias (raiz de --contenido)
    # Acumulan tandas: merge por id/sha, preservando evidencia anterior.
    por_idv = {d.get("id"): d for d in val_prev}
    for v in versiones:
        p = por_idv.get(v["id"])
        if p and p.get("sha256_pdf") == v["sha256_pdf"]:
            m = dict(v)
            m.update({k: p[k] for k in p if p.get(k) not in (None, "", [], {})})
            por_idv[v["id"]] = m
        elif not p:
            por_idv[v["id"]] = v
    val = {"fecha": "2026-11-16", "encargo": "territorial-2026-11-16",
           "origen": Path(args.origen).name, "fuentes": list(por_idv.values()),
           "metodo_segmentacion": "pagina_fisica",
           "pendiente": ["cotejo visual tablas/notas/figuras", "etiquetas impresas, jerarquia y articulos",
                         "vigencia, regimen transitorio y aplicabilidad", "publicacion oficial y vigencia"]}
    escribe_atomo(contenido / "validacion" / LIC_FICHERO, jbytes(val))
    nuevos_docs = [{"id": v["id"], "version": v["version"], "sha256": v["sha256_pdf"],
                    "url": v["url_pdf"], "url_fuente": v["url_fuente"],
                    "capturado_en_utc": v["capturado_en_utc"], "jurisdiccion": v["jurisdiccion"],
                    "municipio": v["municipio"], "creditos": v["creditos"],
                    "reutilizacion": v["reutilizacion"]} for v in versiones]
    por_id = {d.get("id"): d for d in docs_prev}
    for d in nuevos_docs:
        p = por_id.get(d["id"])
        if p and p.get("sha256") == d["sha256"]:
            m = dict(d)
            m.update({k: p[k] for k in p if p.get(k) not in (None, "", [], {})})
            por_id[d["id"]] = m
        elif not p:
            por_id[d["id"]] = d
    lic = {"fecha": "2026-11-16", "encargo": "territorial-2026-11-16",
           "documentos": list(por_id.values()),
           "nota": "Registro por SHA; evidencia por URL y SHA-256; se omiten "
                   "rutas locales privadas por privacidad."}
    escribe_atomo(raiz / "licencias" / LIC_FICHERO, jbytes(lic))
    print("Integradas %d fuentes nuevas en %s" % (len(nuevas), contenido))

if __name__ == "__main__":
    main()
