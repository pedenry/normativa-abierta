# 2026-11-16 — pedenry — evaluación: SUA-02 resuelto (palabras partidas en tokenizar)

## Ámbito

Cierre del fallo conocido SUA-02 de la regresión de recuperación REBT/SUA. Codex aisló la causa y comprobó las baterías con generación del informe; OpenCode NaN (perfil recuperacion-normativa) aplicó el cambio en `acceso.py`, y OpenCode NaN (perfil evaluación) autoró la fixture adicional, las pruebas de contrato y la actualización de la fixture base, README y esta entrada. Sin commit ni despliegue; sin tocar el texto literal del corpus ni el gold.

## Problema y causa

- SUA-02 (anchura libre en zonas comunes de Residencial Vivienda, p. 36 del DB-SUA-oficial 2022-06-14) fallaba en todos los brazos previos.
- Causa aislada por Codex: el PDF oficial parte palabras a fin de línea («Vivien-\nda») y `tokenizar` (acceso.py) las tokenizaba como fragmentos, de modo que la consulta no casaba con el texto de la página en la vista BM25.

## Cambio

- Corrección general de tokenización, solo en `tokenizar` (~15 líneas): une las letras a ambos lados del guion + salto (LF/CRLF, con espacios horizontales) antes de puntuar; expresión regular con letras a ambos lados (no números), sin aritmética IDF ni pesos nuevos y sin cambiar la fuente literal (ni el argumento ni los ficheros).
- Efecto declarado: los guiones compuestos reales a fin de línea también se unen en la vista de búsqueda; no altera el texto entregado al contexto.
- Guardas: no se une `103-\n109` (tokens 103 y 109, no 103109), ni viñetas «anchura\n- libre»; el guion de la misma línea («tecnico-administrativo») sigue dando dos palabras; la función no reescribe ficheros (SHA-256 del archivo de prueba invariante).

## Comprobaciones (reales, Codex)

- 89 pruebas unittest en verde: 19 tests + 19 piloto SUA + 33 HTTP + 10 herramientas + 8 del evaluador; 4 nuevas de palabras partidas (`test_palabras_partidas.py`).
- Batería original (casos.json): contexto 13/14 → 14/14; primarias 12/14 sin cambiar (SUA-02 entrega la p. 36 como auxiliar en contexto, no primaria); cero pérdidas de referencias previas; integridad OK.
- Fixture adicional independiente del ranking (casos-sua-residencial.json, presupuesto 20000 y max_resultados 2): 5/6 → 6/6 en contexto y primarias. Conjunta: 21 casos, 19 consultas distintas (2 controles repetidos SR-05/SR-06).
- Ambas CLI con `--estricto` retornan 0; hashes de fuente y datos previos conservados.
- Informe nuevo: `evaluacion/regresion_recuperacion/resultados-sua-2026-11-16.json`; `resultados-2026-11-16.json` se conserva como histórico sin sobrescribir.

## Ajuste de esperados (fixture casos.json)

- Fecha: 2026-11-16 — Cambio: SUA-02 pasa a `fallo_conocido=false`; el esperado deja de declarar `fallo_conocido`, con `referencias_evaluables=14` y `cobertura_contexto "14/14"`; nota de referencia actualizada. — Razón: corrección del motor verificada con gold intacto (ni consultas ni páginas cambiadas por resultados). — Efecto: consultas y gold pasan a ser guardas obligatorias de regresión; REBT-09 sigue sin gold y sin puntuar; queries, páginas y config sin cambios.

## Roles

- Codex: aislamiento de la causa, comprobación de las baterías y generación del informe nuevo.
- OpenCode NaN (recuperacion-normativa): aplicó el cambio en `acceso.py` (solo `tokenizar`, ~15 líneas).
- OpenCode NaN (evaluación): autor de `casos-sua-residencial.json`, `test_palabras_partidas.py` (4 métodos) y de la actualización de `casos.json`, README y esta entrada.

## Límites y muestra

- Muestra pequeña (dos documentos; 21 casos): sin independencia estadística ni dictamen de calidad global o de fidelidad sustantiva; la cobertura por presencia de página en contexto no certifica respuesta completa.
- Sin consumo API medido ni ahorro económico; los recuentos de texto son proxy local.
- La unión de partidas afecta a la vista de búsqueda, no al texto literal entregado; la fidelidad de página sigue verificada por SHA-256 y literal.

## Inventario final

- `experimentos/http-local/acceso.py` (solo `tokenizar`, ~15 líneas) — aplicado por OpenCode NaN (recuperacion-normativa).
- `experimentos/http-local/tests/test_palabras_partidas.py` (nuevo).
- `evaluacion/regresion_recuperacion/casos-sua-residencial.json` (nuevo) y `evaluacion/regresion_recuperacion/casos.json` (esperados y nota).
- `evaluacion/regresion_recuperacion/resultados-sua-2026-11-16.json` (nuevo, generado por Codex).
- `evaluacion/regresion_recuperacion/README.md` y `changelog/2026-11-16-pedenry-evaluacion-sua-palabras-partidas.changelog.md`.
- Sin commit, despliegue ni corpus modificado; fuente literal intacta.
