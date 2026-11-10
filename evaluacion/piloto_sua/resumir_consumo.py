#!/usr/bin/env python3
"""Resumen de consumo de una corrida del piloto SUA.

CLI: python resumir_consumo.py --run <carpeta>
Lee manifest.json (slots: id, brazo, caso_id, repeticion) y consumo.jsonl
(run_id, usage{input, output, total_input_mas_output, cache, reasoning},
coste_usd, elapsed_s, gastado_total). Valida IDs únicos en consumo y
correspondencia exacta con los ids de slots; comprueba
total_input_mas_output == input + output en cada fila.

Agrupa por brazo y por caso+brazo sumando cada contador, coste_usd y
elapsed_s, y contando filas (n). El acumulado es el último gastado_total del
archivo, NO coste_usd_run (etiqueta histórica errónea).

Imprime JSON por stdout. No escribe otros archivos, no llama a la API,
sin dependencias externas. Los errores van a stderr con salida 1.
"""
import argparse
import json
import sys
from pathlib import Path

CONTADORES = ("input", "output", "total_input_mas_output", "cache", "reasoning")


def fail(mensaje):
    print(f"ERROR: {mensaje}", file=sys.stderr)
    raise SystemExit(1)


def cargar_slots(ruta):
    try:
        manifest = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"manifest.json ilegible ({ruta}): {exc}")
    slots = manifest.get("slots") if isinstance(manifest, dict) else None
    if not isinstance(slots, list) or not slots:
        fail("manifest.json sin slots")
    for slot in slots:
        if not isinstance(slot, dict) or not slot.get("id"):
            fail("manifest.json: slot sin id")
    return slots


def cargar_consumo(ruta):
    filas = []
    try:
        fh = ruta.open(encoding="utf-8")
    except OSError as exc:
        fail(f"consumo.jsonl ilegible ({ruta}): {exc}")
    with fh:
        for numero, linea in enumerate(fh, 1):
            if not linea.strip():
                continue
            try:
                fila = json.loads(linea)
            except json.JSONDecodeError as exc:
                fail(f"consumo.jsonl línea {numero}: JSON inválido ({exc})")
            filas.append((numero, fila))
    return filas


def validar(slots, filas):
    ids_slot = [s["id"] for s in slots]
    if len(set(ids_slot)) != len(ids_slot):
        fail("manifest.json: ids de slots duplicados")
    ids_consumo = []
    for numero, fila in filas:
        run_id = fila.get("run_id")
        if not run_id:
            fail(f"consumo.jsonl línea {numero}: sin run_id")
        ids_consumo.append(run_id)
        usage = fila.get("usage")
        if not isinstance(usage, dict):
            fail(f"consumo.jsonl línea {numero} ({run_id}): sin usage")
        for campo in CONTADORES:
            if campo not in usage:
                fail(f"consumo.jsonl línea {numero} ({run_id}): usage sin {campo}")
        for campo in ("coste_usd", "elapsed_s", "gastado_total"):
            if campo not in fila:
                fail(f"consumo.jsonl línea {numero} ({run_id}): sin {campo}")
        if usage["total_input_mas_output"] != usage["input"] + usage["output"]:
            fail(
                f"consumo.jsonl línea {numero} ({run_id}): "
                f"total_input_mas_output={usage['total_input_mas_output']} != "
                f"input={usage['input']} + output={usage['output']}"
            )
    if len(set(ids_consumo)) != len(ids_consumo):
        fail("consumo.jsonl: run_id duplicado")
    set_slot, set_consumo = set(ids_slot), set(ids_consumo)
    faltan = [i for i in ids_slot if i not in set_consumo]
    sobran = [i for i in ids_consumo if i not in set_slot]
    if faltan or sobran:
        fail(
            "ids sin correspondencia slots/consumo; "
            f"slots sin consumo: {faltan}; consumo sin slot: {sobran}"
        )


def caso_de_slot(slot):
    if slot.get("caso_id"):
        return slot["caso_id"]
    # Corridas antiguas (desarrollo): el caso es el prefijo del id de slot.
    return str(slot["id"]).split("-", 1)[0]


def nuevo_balde():
    balde = {campo: 0 for campo in CONTADORES}
    balde["coste_usd"] = 0.0
    balde["elapsed_s"] = 0.0
    balde["n"] = 0
    return balde


def acumular(balde, fila):
    usage = fila["usage"]
    for campo in CONTADORES:
        balde[campo] += usage[campo]
    balde["coste_usd"] += fila["coste_usd"]
    balde["elapsed_s"] += fila["elapsed_s"]
    balde["n"] += 1


def main():
    parser = argparse.ArgumentParser(
        description="Resume consumo.jsonl de una corrida del piloto SUA."
    )
    parser.add_argument(
        "--run",
        required=True,
        help="carpeta de la corrida con manifest.json y consumo.jsonl",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    carpeta = Path(args.run)
    slots = cargar_slots(carpeta / "manifest.json")
    filas = cargar_consumo(carpeta / "consumo.jsonl")
    if not filas:
        fail("consumo.jsonl vacío")
    validar(slots, filas)

    brazo_de = {s["id"]: s["brazo"] for s in slots}
    caso_de = {s["id"]: caso_de_slot(s) for s in slots}

    por_brazo = {}
    por_caso = {}
    for _, fila in filas:
        run_id = fila["run_id"]
        brazo = brazo_de[run_id]
        balde = por_brazo.setdefault(brazo, nuevo_balde())
        acumular(balde, fila)
        caso = caso_de[run_id]
        acumular(por_caso.setdefault(caso, {}).setdefault(brazo, nuevo_balde()), fila)

    resultado = {
        "por_brazo": por_brazo,
        "por_caso": por_caso,
        "coste_acumulado_ultimo_contador": filas[-1][1]["gastado_total"],
        "nota": (
            "coste estimado; cache subconjunto entrada, reasoning subconjunto salida; "
            "indexado interno desconocido"
        ),
    }
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
