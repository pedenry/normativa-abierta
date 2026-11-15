"""Extrae texto de los PDFs BOE listados en un JSON normalizado (pypdf, modo layout)."""
import argparse
import hashlib
import io
import json
import os
import sys

import pypdf
from pypdf import PdfReader

ap = argparse.ArgumentParser(description="Valida SHA256/cabecera/paginas/ID_BOE de cada PDF y extrae texto layout.")
ap.add_argument("--origen", required=True, help="JSON normalizado con fuentes[]")
ap.add_argument("--salida", required=True, help="JSON de salida con paginas_texto")
args = ap.parse_args()

try:
    with open(args.origen, encoding="utf-8") as fh:
        fuentes = json.load(fh)["fuentes"]
    print(f"{len(fuentes)} documentos", flush=True)

    # Pase 1: verificar TODOS los PDFs antes de extraer nada.
    for i, r in enumerate(fuentes, 1):
        with open(r["ruta_pdf"], "rb") as fh:
            datos = fh.read()
        if not datos.startswith(b"%PDF-"):
            raise ValueError(f"{r['id']}: sin firma %PDF- en {r['ruta_pdf']}")
        if hashlib.sha256(datos).hexdigest() != r["sha256_pdf"].lower().strip():
            raise ValueError(f"{r['id']}: SHA256 no coincide con el fichero")
        lector = PdfReader(io.BytesIO(datos))
        if len(lector.pages) != r["paginas_fisicas"]:
            raise ValueError(f"{r['id']}: {len(lector.pages)} paginas != {r['paginas_fisicas']} declaradas")
        primera = lector.pages[0].extract_text() or ""
        if r["id"] not in primera:
            raise ValueError(f"{r['id']}: el ID no aparece en la primera pagina")
        print(f"[{i}/{len(fuentes)}] verificado {r['id']}", flush=True)

    # Pase 2: extraer todas las paginas en modo layout (sin omitir texto girado).
    res = []
    cuenta = 0
    for i, r in enumerate(fuentes, 1):
        lector = PdfReader(r["ruta_pdf"])
        paginas_texto = []
        vacias = []
        for num, pag in enumerate(lector.pages, 1):
            texto = pag.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False) or ""
            paginas_texto.append(texto)
            if not texto.strip():
                vacias.append(num)
            cuenta += 1
            if cuenta % 100 == 0:
                print(f"progreso: {cuenta} paginas extraidas", flush=True)
        res.append({**r, "paginas_texto": paginas_texto,
                    "extraccion": f"pypdf {pypdf.__version__} layout; strip_rotated=False",
                    "paginas_vacias": vacias})
        print(f"[{i}/{len(fuentes)}] {r['id']}: {len(paginas_texto)} paginas ({len(vacias)} vacias)", flush=True)

    # La salida se escribe solo al final: fichero hermano temporal + replace.
    padre = os.path.dirname(os.path.abspath(args.salida))
    os.makedirs(padre, exist_ok=True)
    temporal = args.salida + f".tmp{os.getpid()}"
    with open(temporal, "w", encoding="utf-8") as fh:
        json.dump({"fuentes": res}, fh, ensure_ascii=False, indent=2)
    os.replace(temporal, args.salida)
    print(f"escrito {args.salida}", flush=True)
except Exception as exc:
    print(f"ERROR: {exc}", file=sys.stderr, flush=True)
    sys.exit(1)
