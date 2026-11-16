# 2026-11-16 — pedenry — Evaluación de recuperación territorial

- **Fecha ISO:** 2026-11-16
- **Ejecución:** Codex para extracción y cotejo de PDF, shell y verificación del diff; OpenCode NaN (perfil `evaluacion-normativa`, glm5.3-flash) para fixtures, gold y documentación.
- **Usuario GitHub:** pedenry
- **Commit base:** sin commit nuevo, push ni despliegue. Trabajo local en checkout.

## Método

- 21 consultas nuevas sobre 18 PDF: 17 normas autonómicas (una por CCAA) más 4 trámites de la única municipal integrada (OMLU Málaga).
- 3 lotes en `evaluacion/regresion_recuperacion/territorial/`, cada uno con su fixture y su gold de páginas físicas fijado antes de ejecutar el ranking; referencias elegidas de fuente y sin retocar después; consultas y gold no ajustados por resultados y fallos no marcados como conocidos.
- Filtros por documento y versión, presupuesto 20000 tokens, `max_resultados=2`, sin API. Cada caso lleva nota breve y criterios de evidencia (citas literales de condición, unidad, umbral o excepción de la página fijada).
- Integridad de fuente: SHA-256 del PDF y del texto de página extraído con pypdf verificados con espacios normalizados; sin cotejo visual completo.

## Resultado

| Lote | Casos | Contexto | Primarias | Faltantes (contexto) |
| --- | --- | --- | --- | --- |
| 1 | 6 | 6/6 | 5/6 | — |
| 2 | 6 | 5/6 | 5/6 | T-09 (Comunidad de Madrid, p. 18) |
| 3 | 9 | 7/9 | 7/9 | T-15 (País Vasco, p. 21), T-18 (Málaga, p. 16) |
| Total | 21 | 18/21 | 17/21 | 3 |

- Ámbito: autonómicas 15/17, municipal (Málaga) 3/4.
- Todos los casos terminan con estado ok e integridad ok; no significa acierto.

## Fallos

- T-09, T-15 y T-18: pérdidas nuevas detectadas por estas pruebas nuevas, no regresión causada por modificar el motor (motor y corpus sin cambios de hash).
- La CLI en modo estricto debe seguir fallando en los lotes 2 y 3 (exit 1); el lote 1 retorna 0 con 6/6 en contexto.
- Diagnóstico independiente en [`diagnostico-fallos.json`](../evaluacion/regresion_recuperacion/territorial/diagnostico-fallos.json), redactado por otro agente.

## Comprobaciones

- 89 pruebas unittest en verde (19 + 19 + 33 + 10 + 8).
- Base REBT/SUA 14/14 y fixture SUA extra 6/6, ambas con `--estricto` exit 0.
- Integridad ok por página en los tres lotes (SHA, ruta, edición y literal), verificada por Codex.
- Repetición local de cada lote: `python -B evaluacion/regresion_recuperacion/ejecutar.py --fixture evaluacion/regresion_recuperacion/territorial/casos-territorial-N.json --salida .local/eval-territorial/repeticion-N.json --estricto` con N = 1, 2, 3.

## Límites

- La cobertura por presencia de página no acredita acierto ni calidad global de la respuesta ni fidelidad sustantiva.
- SHA verificados sobre texto normalizado; sin cotejo visual completo de las páginas.
- Sin medición de tokens API ni de ahorro económico; no certifica búsqueda sin selección de documento (filtros doc/versión activos).
- Muestra de 21 casos sin independencia estadística; no es dictamen de vigencia ni de aplicabilidad jurídica.

## Archivos

- Nuevos: [`evaluacion/regresion_recuperacion/territorial/README.md`](../evaluacion/regresion_recuperacion/territorial/README.md) y esta entrada de changelog.
- Existentes sin tocar: fixtures, referencias, `resultados-2026-11-16.json`, `diagnostico-fallos.json`, motor, corpus, README padre y tests.
