# Regresión de recuperación territorial (lotes 1–3)

La integración HTTP posterior está verificada en [el informe del 17 de noviembre](resultados-http-2026-11-17.json): 91 consultas por `/contexto` en cada servidor, 48 respuestas anteriores de `/buscar` con documento y edición y 43 consultas automáticas de `/buscar`, sin diferencias. La [referencia congelada](referencia-http-2026-11-16.json) contiene una captura de la API anterior; sirve para detectar regresiones, no como gold independiente de corrección normativa. Contrato y aclaración: [HTTP local](../../../experimentos/http-local/README.md#contexto-y-aclaración-por-http).

Para repetir la comprobación, desde la raíz del checkout:

```sh
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_http.py --servidor publico
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_http.py --servidor local
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_http.py --compat --servidor local
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_http.py --buscar-auto --servidor publico
```

Se inicia un servidor real en loopback y se cierra al terminar, sin modelos ni red externa. Los informes se guardan en `.local/http-integracion/`. La comparación de `/contexto` cubre el JSON normalizado completo y el SHA del contexto literal; la de compatibilidad comprueba los bytes del cuerpo. Los modos son excluyentes. Los casos, la referencia y el corpus no se modifican al ejecutar.

Suite de regresión territorial para el motor de recuperación: 21 consultas nuevas sobre 18 PDF (17 normas autonómicas, una por CCAA, más 4 trámites de la única municipal integrada, OMLU Málaga), con gold de páginas físicas fijado antes de ejecutar el ranking y referencias sin retocar después. Filtros por documento y versión, presupuesto 20000 tokens y máximo de dos resultados, sin API. Runner y contrato: [../ejecutar.py](../ejecutar.py) y [../README.md](../README.md).

> **Estado actual (2026-11-16, tras la corrección de recuperación):** 21/21 referencias en contexto (17/17 autonómicas, 4/4 Málaga); los tres lotes en `--estricto` con exit 0. Las 3 correcciones (T-09, T-15, T-18) entran como auxiliares en contexto, sin perder ninguna referencia previa. Informe de la corrección por Codex: [resultados-correccion-2026-11-16.json](resultados-correccion-2026-11-16.json) · Fixture de contraste: [casos-contraste.json](casos-contraste.json) · Changelog: [../../../changelog/2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md](../../../changelog/2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md).

## Resultados antes y después de la corrección

| Conjunto | Contexto antes | Contexto después | Primarias después |
| --- | --- | --- | --- |
| Territorial, 21 referencias (3 lotes) | 18/21 | 21/21 | 17/21 (sin pérdidas; T-09, T-15 y T-18 como auxiliares) |
| Suite completa, 48 casos y 47 referencias | 44/47 | 47/47 | 38/47 |
| V1 experimental (solo T-09 sin resolver) | — | 46/47 | — |

La suite completa reúne 48 casos (42 previos + 6 de contraste) con 46 consultas distintas (2 repetidas) sobre 47 referencias (la consulta amplia REBT-09 no lleva referencia exclusiva de página). El ranking primario BM25 mantiene IDs, páginas y puntuaciones idénticas en los 48 casos.

Historia por lote antes de la corrección (18/21 en contexto y 17/21 primarias):

| Lote | Fixture | Casos | Contexto (antes) | Primarias (antes) | Faltantes (antes) |
| --- | --- | --- | --- | --- | --- |
| 1 | [casos-territorial-1.json](casos-territorial-1.json) | 6 | 6/6 | 5/6 | — |
| 2 | [casos-territorial-2.json](casos-territorial-2.json) | 6 | 5/6 | 5/6 | T-09 (Comunidad de Madrid, p. 18) |
| 3 | [casos-territorial-3.json](casos-territorial-3.json) | 9 | 7/9 | 7/9 | T-15 (País Vasco, p. 21), T-18 (Málaga, p. 16) |
| Total | — | 21 | 18/21 | 17/21 | 3 |

Referencias de origen, elegidas de fuente antes del ranking: [referencias-1.json](referencias-1.json), [referencias-2.json](referencias-2.json) y [referencias-3.json](referencias-3.json).

## Historia de fallos (resueltos el 2026-11-16)

- T-09 (Comunidad de Madrid, p. 18), T-15 (País Vasco, p. 21) y T-18 (Málaga, p. 16) fallaban: el gold no entraba en contexto. Eran pérdidas nuevas que estas pruebas detectaron, no regresión causada por modificar el motor; no se ocultaron, no se marcaron como conocidas y no se ajustó el gold. Tras la corrección están en contexto como auxiliares; diagnóstico previo: [diagnostico-fallos.json](diagnostico-fallos.json).
- La CLI en modo estricto fallaba en los lotes 2 y 3 (exit 1) y el lote 1 retornaba 0; tras la corrección los tres lotes retornan 0.

## Mecanismo de la corrección (2026-11-16)

- Fuente intacta, auxiliar previa conservada y el segundo hueco ya permitido para lecturas auxiliares (hasta 2 por documento) ocupado con el mejor pasaje por operación (máximo/mínimo, inicio/dicotomía) y predicado definitorio ligado al término consultado; purga editorial solo en la vista de puntuación. `max_resultados=2` sigue limitando los resultados principales: son límites independientes.
- Sin IDs, páginas ni regiones fijadas en código y sin IDF local primario; los primarios no se reciclan como auxiliares nuevos y las continuadas se evitan según `expandir`.
- Fixture de contraste preparado antes del ajuste ([casos-contraste.json](casos-contraste.json), 6 casos): 6/6 antes y después; consultas y gold congelados, ninguna alteración tras ver resultados.

## Ejecución

Desde la raíz del checkout, en modo estricto:

```powershell
python -B evaluacion/regresion_recuperacion/ejecutar.py --fixture evaluacion/regresion_recuperacion/territorial/casos-territorial-1.json --salida .local/eval-territorial/repeticion-1.json --estricto
python -B evaluacion/regresion_recuperacion/ejecutar.py --fixture evaluacion/regresion_recuperacion/territorial/casos-territorial-2.json --salida .local/eval-territorial/repeticion-2.json --estricto
python -B evaluacion/regresion_recuperacion/ejecutar.py --fixture evaluacion/regresion_recuperacion/territorial/casos-territorial-3.json --salida .local/eval-territorial/repeticion-3.json --estricto
python -B evaluacion/regresion_recuperacion/ejecutar.py --fixture evaluacion/regresion_recuperacion/territorial/casos-contraste.json --salida .local/eval-territorial/repeticion-contrastes.json --estricto
```

Los tres lotes y el fixture de contraste retornan exit 0 (estados comprobados por Codex).

## Comprobaciones

- 96 pruebas unittest en verde (19 tests + 19 piloto SUA + 40 HTTP + 10 herramientas + 8 evaluador), entre ellas 7 nuevas de pasajes en [test_pasajes.py](../../../experimentos/http-local/tests/test_pasajes.py).
- Base REBT/SUA 14/14 y fixture SUA extra 6/6 preservadas, ambas con `--estricto` exit 0; contraste territorial 6/6 antes y después.
- Integridad ok en todos los casos: gold literal, documento, versión y SHA por página; control de presupuesto sin ampliaciones (20000 tokens y máximo de dos resultados, auxiliares ≤2 por documento); corpus, índice, manifiestos, consultas y gold originales sin cambios de hash, con el ajuste previo de palabras partidas preservado.

## Límites

- Solo se corrige recuperación en la muestra curada de 20 PDF; la cobertura por presencia de página no acredita acierto ni fidelidad sustantiva; sin certificado de calidad global ni respuesta jurídica.
- Las páginas auxiliares completas añadidas bajo igual presupuesto pueden aumentar la longitud del contexto entregado; recuentos proxy local, no facturación de API; sin latencia ni ahorro demostrados (corridas en paralelo).
- SHA de PDF y texto extraído con pypdf verificados con espacios normalizados; sin cotejo visual completo.
- Filtros doc/versión activos: no certifica búsqueda sin selección de documento.
- Muestra curada sin independencia estadística; no es dictamen de vigencia ni de aplicabilidad jurídica.
- [diagnostico-fallos.json](diagnostico-fallos.json) lo redactó otro agente de forma independiente y no se ajustó al preparar este README ni la corrección.

## Enlaces

- Informe de la corrección (Codex): [resultados-correccion-2026-11-16.json](resultados-correccion-2026-11-16.json); histórico de los tres lotes sin sobrescribir: [resultados-2026-11-16.json](resultados-2026-11-16.json)
- Diagnóstico previo (agente independiente, historial): [diagnostico-fallos.json](diagnostico-fallos.json)
- Fixtures: [casos-territorial-1.json](casos-territorial-1.json), [casos-territorial-2.json](casos-territorial-2.json), [casos-territorial-3.json](casos-territorial-3.json), [casos-contraste.json](casos-contraste.json)
- Referencias previas al ranking: [referencias-1.json](referencias-1.json), [referencias-2.json](referencias-2.json), [referencias-3.json](referencias-3.json)
- Tests de pasajes: [../../../experimentos/http-local/tests/test_pasajes.py](../../../experimentos/http-local/tests/test_pasajes.py)
- Changelog de la corrección: [../../../changelog/2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md](../../../changelog/2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md)
- Runner y suite base: [../ejecutar.py](../ejecutar.py), [../README.md](../README.md)

## Búsqueda libre (2026-11-16, cierre verificado)

Cierre ya verificado por Codex, documentado aquí sin ejecutar shell; hechos medidos transcritos del encargo. Changelog: [../../../changelog/2026-11-16-pedenry-evaluacion-busqueda-libre-territorial.changelog.md](../../../changelog/2026-11-16-pedenry-evaluacion-busqueda-libre-territorial.changelog.md)

- **Alcance:** 21 consultas libres (17 CCAA + 4 municipales Málaga); la API recibe `(consulta, None, None, 20000, 2)`. Golds y queries congelados intactos.
- **Resultados** (criterio de evidencia revisado tras los resultados por cotejo independiente p33/p16, con adjudicación versionada explícita y aplicado por igual antes y después; gold/queries y resumen original intactos): fuente + edición + evidencia suficiente + integridad + ámbito 10/21 → 21/21; gold exclusivo original 9/21 → 20/21; páginas exactas 17/21 → 20/21; mezcla CCAA 10 casos → 0.
- **Málaga L18:** no era recuperación incorrecta. p33 art. 31.1 contiene la misma regla de entrada (documentación completa REGMálaga) que p16 art. 9.3; cotejo posterior independiente y hashes medidos. La evaluación original (20/21) queda visible y sin modificar.
- **Alternativas:** solo con flag opt-in `--alternativas` y [alternativas-libres-2026-11-16.json](alternativas-libres-2026-11-16.json), documentadas en [adjudicacion-libres-2026-11-16.json](adjudicacion-libres-2026-11-16.json); no se fuerza el motor a p16.
- **Motor:** enrutado desde metadata pública, sin IDs ni golds en producción; nacionales complementarias; solo la comunidad/municipio pedidos y el padre desde la propia fuente; municipal explícita ausente → abstiene (Madrid, Sevilla); unión Aragón/Navarra verificada. Scoring auxiliar original restaurado: solo `acceso._pasa_filtro` y `buscar_bm25` existentes cambiados (puerta de candidatos después del IDF global); tokenizar y selector previo intactos. Evaluator corregido para carpeta legacy HS sin fecha usando metadata propia (version/version_dir), sin alterar corpus.
- **Regresión y controles:** controles CTE sin documento 2/2 antes y después; exclusión nacional V1 rechazada; 48 consultas anteriores con 47 referencias intactas (primarias/puntuaciones) y páginas/SHA y los 48 contextos completos con SHA idénticos; 116 unittest verdes (19 generales + 19 piloto SUA + 10 herramientas + 15 evaluador + 53 HTTP); rehash de 20 PDF fuente y de 8 archivos protegidos (corpus/fixtures) iguales.
- **Consumo (proxy):** presupuesto 20k, max principal 2, aux 2, sin ampliar; máximo de contexto observado (proxy caracteres/4): 11547 en el lote territorial de 21, 11877 en controles CTE 2; no son tokens de resultados primarios ni pronóstico. El informe conserva recuentos locales antes/después, que no miden latencia, coste API ni ahorro OpenCode. Informe: [resultados-libres-2026-11-16.json](resultados-libres-2026-11-16.json), con metadata de fuentes por caso.

Repetición desde la raíz del checkout:

```powershell
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_libres.py --alternativas evaluacion/regresion_recuperacion/territorial/alternativas-libres-2026-11-16.json --salida .local/busqueda-libre/repeticion.json
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_libres.py --fixture evaluacion/regresion_recuperacion/territorial/casos-libres-controles.json --salida .local/busqueda-libre/repeticion-controles.json
```

Salida declarada: sin flag, la discrepancia original L18 devuelve exit 1; con flag, 21/21 y exit 0; control 2/2 y exit 0.

**Límites:** no se afirma vigencia, aplicabilidad ni calidad global; municipal solo Málaga incorporado; recuentos de texto proxy, no facturación.

**Consultas sin ubicación (2026-11-16, cierre verificado):** [SIN-UBICACION.md](SIN-UBICACION.md) · Changelog: [../../../changelog/2026-11-16-pedenry-evaluacion-sin-ubicacion.changelog.md](../../../changelog/2026-11-16-pedenry-evaluacion-sin-ubicacion.changelog.md)
