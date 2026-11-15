#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integra fuentes BOE ya extraidas (JSON de entrada) en contenido/.

Contrato del encargo 2026-11-15 (agente fuentes-normativas). La extraccion y el
cotejo de los PDF son previos; este script solo valida e integra. No toca
documentos anteriores; si todo ya esta integrado sale 0 sin reescribir.
Uso (desde cwd EXTERIOR al repo):
    python normativa-abierta/ingesta/integrar_boe.py --origen extraido.json
"""
import argparse, datetime, hashlib, json, os, re, shutil, sys, tempfile
from pathlib import Path

ID_RE = re.compile(r"^BOE-A-\d{4}-\d+$")
FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIC_FICHERO = "ampliacion-boe-2026-11-15.json"
ATRIBUCION = ("Basado en datos de la Agencia Estatal "
              "Boletín Oficial del Estado")


def die(msg):
    sys.exit("ERROR preflight: " + msg)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", required=True)
    ap.add_argument("--contenido", default=str(
        Path(__file__).resolve().parents[1] / "contenido"))
    args = ap.parse_args()
    contenido = Path(args.contenido)

    datos = json.loads(Path(args.origen).read_text(encoding="utf-8"))
    fuentes = datos.get("fuentes", [])
    if not fuentes:
        die("entrada sin fuentes")

    # --- Preflight: unico, IDs, version ISO, SHA real del PDF, conteo paginas
    vistos = set()
    for r in fuentes:
        if r["id"] in vistos:
            die("ID duplicado en entrada: " + r["id"])
        vistos.add(r["id"])
        if not ID_RE.match(r["id"]):
            die("ID no cumple BOE-A-AAAA-N: " + r["id"])
        if not FECHA_RE.match(r.get("version", "")):
            die("version no ISO: %s %s" % (r["id"], r.get("version")))
        datetime.date.fromisoformat(r.get("version", ""))  # fecha valida
        pdf = Path(r["ruta_pdf"])
        if not pdf.is_file():
            die("PDF no encontrado: " + str(r["ruta_pdf"]))
        if pdf.read_bytes()[:5] != b"%PDF-":
            die("firma %PDF- ausente: " + r["id"])
        if sha256_bytes(pdf.read_bytes()) != r["sha256_pdf"]:
            die("sha256_pdf no coincide con el fichero: " + r["id"])
        pags_txt = r.get("paginas_texto", [])
        if not all(isinstance(t, str) for t in pags_txt):
            die("paginas_texto con elementos no string: " + r["id"])
        if len(pags_txt) != r.get("paginas_fisicas"):
            die("paginas_texto != paginas_fisicas: " + r["id"])

    # --- Solo fuentes nuevas; mismo hash = idempotente, distinto = error
    # manifest_publico.json REAL es objeto:
    # {generado_por, manifest_nombre, manifest_sha256, entradas:list, nota}
    manifest_p = contenido / "manifest_publico.json"
    indice_p = contenido / "indice" / "apartados.jsonl"
    manifest = {"generado_por": "ingesta/integrar_boe.py",
                "manifest_nombre": "manifest_publico.json",
                "manifest_sha256": None, "entradas": [], "nota": None}
    if manifest_p.is_file():
        cargado = json.loads(manifest_p.read_text(encoding="utf-8"))
        manifest.update(cargado)  # conserva todas las claves originales
    previos = {e.get("id"): e for e in manifest.get("entradas", [])}
    indice_bytes = indice_p.read_bytes() if indice_p.is_file() else b""
    ya_indice = set()
    if indice_bytes:
        for linea in indice_bytes.splitlines():
            if linea.strip():
                ya_indice.add(json.loads(linea.decode("utf-8")).get("documento"))

    nuevas = []
    for r in fuentes:
        anterior = previos.get(r["id"])
        if anterior:
            if anterior.get("sha256") == r["sha256_pdf"]:
                continue  # ya integrado, idempotente
            die("ID ya indexado con distinto hash: " + r["id"])
        if r["id"] in ya_indice:
            die("ID en indice con distinto hash: " + r["id"])
        nuevas.append(r)

    if not nuevas:
        print("Todo ya integrado; exit 0 sin reescribir.")
        return

    versiones, filas_nuevas = [], []
    for r in nuevas:
        vid = r["id"]
        vdir = contenido / "docs" / vid / ("%s__%s" % (r["version"], r["sha256_pdf"][:12]))
        vdir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(r["ruta_pdf"]), vdir / "fuente.pdf")

        frags, pags, caracteres, rel = [], [], 0, (
            "docs/%s/%s__%s" % (vid, r["version"], r["sha256_pdf"][:12]))
        for n, texto in enumerate(r["paginas_texto"], start=1):
            pn = "p%04d" % n
            h = sha256_bytes(texto.encode("utf-8"))
            (vdir / "pagina").mkdir(exist_ok=True)
            (vdir / "pagina" / (pn + ".md")).write_text(texto, encoding="utf-8", newline="\n")
            (vdir / "apartado").mkdir(exist_ok=True)
            (vdir / "apartado" / (pn + ".md")).write_text(texto, encoding="utf-8", newline="\n")
            frag = {
                "id_tecnico": pn,
                "titulo": "Pagina fisica %d - %s" % (n, r["materia"]),
                "ruta_oficial": None,
                "ruta_semantica": "Pagina fisica %d" % n,
                "seccion_estimada": "Pagina fisica %d" % n,
                "parent_id": None,
                "nivel": 1,
                "paginas": [n],
                "etiquetas_impresas": [None],
                "tipos": [],
                "referencias": [],
                "jerarquia_verificada": False,
                "ruta_oficial_verificada": False,
                "es_encabezado_navegacion": False,
                "archivo": "apartado/%s.md" % pn,
                "archivo_json": "apartado/%s.json" % pn,
                "caracteres": len(texto),
                "primera_linea": texto.splitlines()[0] if texto.strip() else "",
                "sha256_texto": h,
            }
            escribe_atomo(vdir / "apartado" / (pn + ".json"),
                          jbytes(dict(frag, texto=texto)))
            frags.append(frag)
            pags.append({"n": n, "pagina_md": "pagina/%s.md" % pn,
                         "etiqueta_impresa": None, "tablas": 0})
            caracteres += len(texto)
            fila = dict(frag)
            fila.update({"documento": vid, "codigo": vid, "materia": r["materia"],
                         "capa": "asociada", "version": r["version"],
                         "apartado_id": "%s/%s" % (vid, pn),
                         "archivo": rel + "/apartado/%s.md" % pn,
                         "archivo_json": rel + "/apartado/%s.json" % pn,
                         "doc_json": rel + "/doc.json",
                         "estructura": rel + "/estructura.json"})
            filas_nuevas.append(fila)

        tipo = (r.get("tipo") or "")
        adv = ["Consolidado meramente informativo, sin valor oficial."
               if "consolidad" in tipo.lower()
               else "Original que no incorpora correcciones posteriores.",
               "Extraccion automatica: tablas, formulas y notas sin cotejar.",
               "Etiquetas impresas desconocidas; jerarquia no verificada; "
               "figuras no cotejadas.",
               "Ambito y regimen transitorio pendientes de verificacion.",
               "Atribucion: " + ATRIBUCION]
        doc = {
            "id": vid, "code": vid, "title": r["titulo"], "layer": "asociada",
            "scope": r["materia"], "version": r["version"], "version_dir": vdir.name,
            "version_label_literal": r["version_label_literal"], "sha256": r["sha256_pdf"],
            "url": r["url_pdf"], "landing": r["url_fuente"], "distribute": True,
            "normativo": True,
            "license_status": "art13 disposicion legal; reutilizacion BOE",
            "license_evidence": "licencias/" + LIC_FICHERO, "creditos": ATRIBUCION,
            "ambito_literal": None,
            "conteos": {"paginas": len(pags), "apartados": len(frags),
                        "caracteres": caracteres},
            "tablas_por_pagina": {}, "figuras": [], "formulas": {},
            "metodo_segmentacion": "pagina_fisica", "nota_capa": tipo,
            "extraccion": r.get("extraccion"),
            "advertencias": adv,
        }
        escribe_atomo(vdir / "doc.json", jbytes(doc))
        escribe_atomo(vdir / "estructura.json",
                      jbytes({"id": vid, "version": r["version"], "apartados": frags}))
        escribe_atomo(vdir / "paginas.json",
                      jbytes({"id": vid, "version": r["version"], "paginas": pags}))
        # Ficha: actualiza con doc entero (version, sha256, distribute...)
        # y agrega aliases codigo/titulo/capa para el schema de fichas
        ficha_p = contenido / "fichas" / (vid + ".json")
        ficha = json.loads(ficha_p.read_text(encoding="utf-8")) if ficha_p.is_file() else {}
        ficha.update(doc)
        ficha["codigo"] = doc["code"]
        ficha["titulo"] = doc["title"]
        ficha["capa"] = doc["layer"]
        escribe_atomo(ficha_p, jbytes(ficha))

        versiones.append({"id": vid, "version": r["version"],
                          "sha256_pdf": r["sha256_pdf"], "url_pdf": r["url_pdf"],
                          "url_fuente": r["url_fuente"], "capturado_en_utc": r["capturado_en_utc"],
                          "extraccion": r.get("extraccion"),
                          "paginas": len(pags), "apartados": len(frags),
                          "caracteres": caracteres, "paginas_vacias": r.get("paginas_vacias"),
                          "metodo_segmentacion": "pagina_fisica"})
        previos[vid] = {"id": vid, "codigo": vid, "titulo": r["titulo"],
                        "capa": "asociada", "scope": r["materia"],
                        "version": r["version"], "version_dir": vdir.name,
                        "version_label_literal": r["version_label_literal"],
                        "sha256": r["sha256_pdf"], "distribute": True,
                        "url": r["url_pdf"], "estado": "preparado_local"}

    # --- Indice: conserva bytes anteriores, append una vez, temporal replace
    if filas_nuevas:
        prefijo = b"" if not indice_bytes or indice_bytes.endswith(b"\n") else b"\n"
        anexo = prefijo + "".join(json.dumps(f, ensure_ascii=False) + "\n"
                                  for f in filas_nuevas).encode("utf-8")
        escribe_atomo(indice_p, indice_bytes + anexo)

    # --- Manifest publico: objeto con entradas previas + nuevas; se conserva
    # manifest_sha256 historico (hash del conjunto anterior) y se anota en
    # ampliaciones que corresponde al sources.json anterior, no al ampliado.
    manifest["entradas"] = list(previos.values())
    manifest["ampliaciones"] = (manifest.get("ampliaciones") or []) + [{
        "generador": "ingesta/integrar_boe.py", "fecha": "2026-11-15",
        "ids": [v["id"] for v in versiones],
        "nota": "manifest_sha256 es historico: corresponde al conjunto de "
                "fuentes.json anterior, no al conjunto ampliado."}]
    escribe_atomo(manifest_p, jbytes(manifest))

    # --- Validacion interna (contenido) y licencias (raiz del repo)
    val = {"fecha": "2026-11-15", "encargo": "ampliacion-boe-2026-11-15",
           "origen": Path(args.origen).name, "fuentes": versiones,
           "metodo_segmentacion": "pagina_fisica",
           "pendiente": ["cotejo visual tablas/notas/figuras",
                         "etiquetas impresas y jerarquia",
                         "ambito y transitorio",
                         "publicacion oficial y vigencia"]}
    escribe_atomo(contenido / "validacion" / LIC_FICHERO, jbytes(val))

    raiz = contenido.resolve().parent  # raiz de --contenido, no hardcoded
    lic = {"fecha": "2026-11-15",
           "documentos": [{"id": v["id"], "version": v["version"],
                           "sha256": v["sha256_pdf"], "url": v["url_pdf"],
                           "url_fuente": v["url_fuente"],
                           "capturado_en_utc": v["capturado_en_utc"]}
                          for v in versiones],
           "atribucion": ATRIBUCION,
           "licencia_url": "https://www.boe.es/informacion/aviso_legal/index.php",
           "condiciones": "Disposiciones legales BOE (art. 13): reutilizacion "
                          "permitida con atribucion e indicacion de la fecha de "
                          "version; transformacion limitada a segmentacion por "
                          "paginas fisicas, sin alteracion del texto."}
    escribe_atomo(raiz / "licencias" / LIC_FICHERO, jbytes(lic))

    print("Integradas %d fuentes nuevas en %s" % (len(nuevas), contenido))


if __name__ == "__main__":
    main()
