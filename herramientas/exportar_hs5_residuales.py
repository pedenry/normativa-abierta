"""Exporta tablas cuantitativas cotejadas de DB HS 5 para consumidores BIM."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "contenido/docs/DB-HS-oficial/sin-fecha__68df3caacc95"
OUTPUT = ROOT / "contenido/reglas/db-hs-5-residuales-2022-06-14.json"
EXPECTED_SHA = "68df3caacc95f71aee2ec1ba7b2c65ae66155c21e3a8785521b8fdd4fd640d3b"
NUMBER = re.compile(r"-|[0-9]+(?:\.[0-9]+)*")
# Orden literal de la tabla. Los cuatro últimos son grupos completos y
# el consumidor no debe sumarlos a los aparatos individuales del mismo cuarto.
FIXTURES = (
    "lavabo", "bide", "ducha", "banera", "inodoro_cisterna", "inodoro_fluxometro",
    "urinario_pedestal", "urinario_suspendido", "urinario_bateria", "fregadero",
    "fregadero_profesional", "lavadero", "vertedero", "fuente", "sumidero_sifonico",
    "lavavajillas", "lavadora", "bano_cisterna", "bano_fluxometro", "aseo_cisterna",
    "aseo_fluxometro",
)
LABELS = ("Lavabo", "Bidé", "Ducha", "Bañera (con o sin ducha)", "Con cisterna", "Con fluxómetro",
          "Pedestal", "Suspendido", "En batería", "De cocina", "etc.", "Lavadero",
          "Vertedero", "Fuente para beber", "Sumidero sifónico", "Lavavajillas",
          "Lavadora", "Inodoro con cisterna", "Inodoro con fluxómetro",
          "Inodoro con cisterna", "Inodoro con fluxómetro")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def numeric_cells(target):
    for line in target.splitlines():
        token = line.strip()
        if NUMBER.fullmatch(token):
            yield token


def cells(tokens, width, count):
    values = list(tokens)
    if len(values) != width * count:
        raise ValueError(f"Se esperaban {width * count} celdas, hay {len(values)}")
    return [values[i:i+width] for i in range(0, len(values), width)]


def between(page, start, stop=None):
    _, sep, text = page.partition(start)
    if not sep:
        raise ValueError(f"No se encontró {start}")
    if stop:
        text, sep, _ = text.partition(stop)
        if not sep:
            raise ValueError(f"No se encontró fin de tabla {stop}")
    return text


def tabular(fields, width, count, page, start, row_start, stop=None):
    plain = between(between(page, start, stop), row_start)
    rows = cells(numeric_cells(plain), width, count)
    with fields.open(encoding="utf-8", newline="") as handle:
        csv_rows = []
        for row in csv.reader(handle):
            values = [cell.strip() for cell in row if cell.strip()]
            if len(values) == width and all(NUMBER.fullmatch(x) for x in values):
                csv_rows.append(values)
    if rows != csv_rows:
        raise ValueError(f"El texto de página y el CSV discrepan en {fields.name}")
    return [[int(r[-1]), *(int(c.replace(".", "")) if c != "-" else None for c in r[:-1])] for r in rows]


def fixtures(page, table_path):
    body = between(page, "Tabla 4.1 ", "Los diámetros indicados en la tabla 4.1")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    rows = []
    pos = 0
    for appliance, label in zip(FIXTURES, LABELS, strict=True):
        pos = lines.index(label, pos) + 1
        entries = lines[pos:pos+4]
        if len(entries) != 4 or not all(NUMBER.fullmatch(x) for x in entries):
            raise ValueError(f"Las cuatro celdas de {label} no tienen el formato esperado")
        pos += 4
        ud_private, ud_public, mm_private, mm_public = entries
        rows.append([appliance, ud_private, mm_private, ud_public, mm_public])
    # El CSV contiene las dos series numéricas en celdas multilínea.
    with table_path.open(encoding="utf-8", newline="") as handle:
        csv_table = list(csv.reader(handle))
    candidates = [row for row in csv_table if len(row) == 3 and
                  len(row[1].splitlines()) == len(FIXTURES) and len(row[2].splitlines()) == len(FIXTURES)]
    ud = [[r[1], r[3]] for r in rows]
    diameters = [[r[2], r[4]] for r in rows]
    if len(candidates) != 1 or any(
        [line.split() for line in candidates[0][i].splitlines()] != values
        for i, values in ((1, ud), (2, diameters))
    ):
        raise ValueError("La tabla 4.1 no coincide con las columnas numéricas del CSV")

    return {r[0]: [None if v=="-" else float(v) if "." in v else int(v) for v in r[1:]] for r in rows}


def build():
    metadata = json.loads((DOC / "doc.json").read_text(encoding="utf-8"))
    if metadata["sha256"] != EXPECTED_SHA or sha((DOC / "fuente.pdf").read_bytes()) != EXPECTED_SHA:
        raise ValueError("El PDF no coincide con la edición que se cotejó")
    physical = {n: DOC / f"pagina/p{n:04}.md" for n in (117, 118)}
    pages = {n: p.read_text(encoding="utf-8") for n, p in physical.items()}
    tables = DOC / "tabla"
    return {
        "schema": 1, "norma": "CTE DB HS 5", "seccion": "4.1",
        "fuente": {"documento": metadata["id"], "edicion": metadata["version"],
                   "sha256": EXPECTED_SHA, "url": metadata["url"],
                   "tablas": {key: {"pagina_fisica": page, "texto_sha256": sha(pages[page].encode("utf-8")),
                                    "csv": f"p{page:04}_t{index:02}.csv"}
                              for key, page, index in (("4.1",117,1),("4.3",117,3),("4.4",118,1),("4.5",118,2))}},
        "columnas": {"aparatos": ["ud_privado", "diametro_privado_mm", "ud_publico", "diametro_publico_mm"],
                     "ramales": ["diametro_mm", "ud_1_pct", "ud_2_pct", "ud_4_pct"],
                     "colectores": ["diametro_mm", "ud_1_pct", "ud_2_pct", "ud_4_pct"],
                     "bajantes": ["diametro_mm", "ud_total_hasta_3", "ud_total_mas_de_3",
                                  "ud_ramal_hasta_3", "ud_ramal_mas_de_3"]},
        "aparatos": fixtures(pages[117], tables / "p0117_t01.csv"),
        "ramales": tabular(tables / "p0117_t03.csv",4,10,pages[117],"Tabla 4.3","4 %"),
        "bajantes": tabular(tables / "p0118_t01.csv",5,10,pages[118],"Tabla 4.4","Diámetro (mm)", "\n3 "),
        "colectores": tabular(tables / "p0118_t02.csv",4,11,pages[118],"Tabla 4.5","4 %"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comprobar", action="store_true")
    args = ap.parse_args()
    result = build()
    if args.comprobar:
        if json.loads(OUTPUT.read_text(encoding="utf-8")) != result:
            raise SystemExit("La exportación no coincide con la fuente")
    else:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
