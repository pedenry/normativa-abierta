# -*- coding: utf-8 -*-
"""Materializa la revisión manual de Codex del piloto SUA.

8 casos (E01-E08) x r1-r3 x brazos adaptador/pdf_indexado = 48 filas.
Los juicios (criterios, na, errores_criticos, evidencia) están fijados aquí tal
como los registró Codex; este script NO evalúa por texto ni razona normativamente.
Al ejecutar, escribe resultados/evaluacion-20261110/revision_codex.json relativo
a este archivo. Rúbrica: protocolo.md (6 criterios; error crítico: falso cumple,
citas o cotas inventadas, excepción esencial omitida; ninguno en este piloto).
"""
import json
from pathlib import Path

CRITERIOS = ("estado", "condiciones", "datos_proyecto", "cita_norma", "cita_proyecto", "alcance")
CASOS = tuple(f"E0{i}" for i in range(1, 9))
BRAZOS = ("adaptador", "pdf_indexado")
BASE = {
    "E01": ["1.25>=1.20 Admin"],
    "E02": ["1.10<1.20 Admin sin excepción vivienda"],
    "E03": ["común vivienda 1.10 admite excepción"],
    "E04": ["1.25>=1.20", "1.05>=1", "0.40<=0.50", "0.70>=0.65"],
    "E05": ["mismas medidas salvo separación ilegible reconocida"],
    "E06": ["marco 0.82>=0.80", "efectivo 0.76<0.78", "una hoja"],
    "E07": ["L 3m => 8%", "9>8", "1.5<=2"],
    "E08": ["fuente 2010 ausente", "no sustituir 2022", "plano 1.25 legible"],
}
def comun(caso):
    # Cita de proyecto concreta por caso (p2 es la del plano en estos casos).
    return [f"cita_proyecto: {caso}.pdf p2", "alcance: elemento solicitado"]
NA = {"E08": ["cita_norma"]}

# Criterios en false: (brazo, caso, rondas, criterio, evidencia del fallo).
FALLOS = [
    ("pdf_indexado", c, (1, 2, 3), "cita_norma", "cita_norma: cita p.35; página correcta p.36 (E01-E06)") for c in CASOS[:6]
]
FALLOS += [
    ("adaptador", "E02", (1,), "cita_norma", "cita_norma: cita p.41; página correcta p.36 (E01-E06)"),
    ("pdf_indexado", "E07", (1,), "estado", "estado: se abstiene; cita 11/35 por recuperar evidencia insuficiente"),
    ("pdf_indexado", "E07", (1,), "condiciones", "condiciones: se abstiene; cita 11/35 por recuperar evidencia insuficiente"),
    ("pdf_indexado", "E07", (1,), "cita_norma", "cita_norma: se abstiene; cita 11/35 por recuperar evidencia insuficiente"),
    ("pdf_indexado", "E07", (2, 3), "condiciones", "condiciones: citan p.14 pero aplican 6% en vez de 8%"),
]

# Observaciones de claridad / aritmética redundante; sin efecto en el veredicto.
EXTRA = {
    ("pdf_indexado", "E06", 1): [
        "observación: compara adicionalmente 0.76<0.80; aritmética redundante, sin fallo del marco; norma y condición decisiva 0.76<0.78 correctas",
    ],
    ("adaptador", "E06", 2): [
        "observación: compara adicionalmente 0.76<0.80; aritmética redundante, sin fallo del marco; norma y condición decisiva 0.76<0.78 correctas",
        "claridad: no adjudica el marco explícitamente; revisión independiente de OpenCode coincide",
    ],
    ("adaptador", "E08", 3): [
        "claridad: pide confirmación redundante del ancho constante y usa una palabra no española; nota de claridad, dato y abstención correctos",
    ],
}

IDX = {}
for brazo, caso, rondas, criterio, evid in FALLOS:
    for r in rondas:
        IDX.setdefault((brazo, caso, r), {})[criterio] = evid

filas = []
for caso in CASOS:
    for r in (1, 2, 3):
        for brazo in BRAZOS:
            fallos = IDX.get((brazo, caso, r), {})
            na = list(NA.get(caso, []))
            filas.append({
                "run_id": f"{caso}-r{r}-{brazo}",
                "criterios": {c: c not in fallos for c in CRITERIOS if c not in na},
                "na": na,
                "errores_criticos": [],
                "evidencia": [f"Referencia esperada: {b}" for b in BASE[caso]] + comun(caso) + list(fallos.values()) + EXTRA.get((brazo, caso, r), []),
            })
assert len(filas) == 48, f"esperadas 48 filas, generadas {len(filas)}"

revision = {
    "autor": "Codex",
    "tipo": "revision_manual_IA",
    "nota": "No es validación humana; gold y PDFs cotejados por Codex; E06 dudosos contrastados con OpenCode.",
    "notas_agregadas": [
        "páginas correctas E01-E06 = 36; PDF cita p.35 (incluidos algunos usos secundarios: p.38 en lugar de p.39); asignación fila a fila no suministrada por Codex",
    ],
    "filas": filas,
}
salida = Path(__file__).resolve().parent / "resultados" / "evaluacion-20261110" / "revision_codex.json"
salida.parent.mkdir(parents=True, exist_ok=True)
salida.write_text(json.dumps(revision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"OK: {len(filas)} filas -> {salida}")
