# Piloto SUA · Referencia y gold

## Fuente verificada (visual por Codex, 2026-11-10)
- URL oficial: https://www.codigotecnico.org/pdf/Documentos/SUA/DBSUA.pdf
- SHA-256: 3cfb5bbb135e8f02faebd8b844e03e8947994c18d4c9e675a7d2aa37d1cd5958 (comprobado idéntico)
- Edición: 2022-06-14. Verificación visual de las páginas citadas; NO es revisión humana ni asegura vigencia (sin comprobación de ámbito ni régimen transitorio).
- Gold separado: estados esperados y criterios de esta tabla no se entregan al modelo ni a la recuperación (V0/V1); uso exclusivo de la rúbrica.

## Reglas citadas (edición 2022-06-14)
- P36 · Anejo A (itinerario accesible): pasillos ancho libre >= 1.20 m; excepción zonas comunes de Residencial Vivienda >= 1.10 m. Estrechamiento: w >= 1.00 m, L <= 0.50 m, separación a puerta o cambio de dirección >= 0.65 m. Puerta de una hoja: hueco de marco >= 0.80 m y ancho efectivo con puerta abierta a máxima apertura >= 0.78 m.
- P14 · SUA 1, punto 4.3.1 (rampas): pendiente máxima longitudinal según longitud: < 3 m → 10 %; < 6 m → 8 %; resto → 6 %; L exactamente 3.00 m → 8 %. Pendiente transversal <= 2 %.

## Tabla gold · 12 casos (proyecto: PDFID.pdf p2 · elemento; alcance acotado al elemento consultado, nunca el edificio entero)

| id | Proyecto (PDFID.pdf p2 · elemento) | Cita norma | Condiciones a comprobar | Estado esperado |
|---|---|---|---|---|
| D01 | pasillo administración, ancho 1.30 m | P36 · Anejo A | pasillo >= 1.20 | cumple |
| D02 | puerta una hoja, marco 0.85 / efectivo 0.80 | P36 · Anejo A | marco >= 0.80 y efectivo >= 0.78 | cumple |
| D03 | rampa L 2.50 m, 9 %, transversal 1 % | P14 · SUA 1 4.3.1 | L < 3 → máx 10 %; transversal <= 2 % | cumple |
| D04 | rampa L 4.00 m, 7 %, transversal ausente | P14 · SUA 1 4.3.1 | longitudinal cumple (< 6 → máx 8 %); transversal no consta | no_comprobable |
| E01 | pasillo administración, ancho 1.25 m | P36 · Anejo A | pasillo >= 1.20 | cumple |
| E02 | pasillo administración, ancho 1.10 m | P36 · Anejo A | 1.10 < 1.20; excepción no aplicable (no es zona común de Residencial Vivienda) | no_cumple |
| E03 | zona común de Residencial Vivienda, ancho 1.10 m | P36 · Anejo A | excepción zona común de Residencial Vivienda >= 1.10 | cumple |
| E04 | pasillo admin 1.25 + estrechamiento 1.05 × 0.40, separación 0.70 | P36 · Anejo A | pasillo >= 1.20; w >= 1.00; L <= 0.50; separación >= 0.65 (3 condiciones del estrechamiento) | cumple |
| E05 | igual a E04, separación ilegible (null) | P36 · Anejo A | pasillo, w y L verificables; separación >= 0.65 sin dato | no_comprobable |
| E06 | puerta una hoja, marco 0.82 / efectivo 0.76 | P36 · Anejo A | marco >= 0.80 (ok); efectivo 0.76 < 0.78 mínimo | no_cumple |
| E07 | rampa L 3.00 m, 9 %, transversal 1.5 % | P14 · SUA 1 4.3.1 | L = 3.00 → máx 8 %: 9 % excede; transversal 1.5 <= 2 correcta | no_cumple |
| E08 | pasillo 1.25 m; edición solicitada 2010-03-11 | NA (edición 2010-03-11 ausente; no citar 2022 como norma de la edición 2010) | edición inexistente: sin negarla, sin sustituirla ni evaluar la geometría 1.25 con otra edición | no_comprobable |

Las ausencias (D04, E05, E08) se declaran como tales; no se inventan datos ni se sustituye la edición solicitada.
