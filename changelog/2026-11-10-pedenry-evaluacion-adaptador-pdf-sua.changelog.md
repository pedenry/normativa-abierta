# 2026-11-10 · pedenry · Evaluación adaptador PDF (DB-SUA): V1 BM25 vs V0 file_search

## Resultado
- El adaptador V1 BM25 consumió 40.3% menos tokens totales que V0 file_search (40.2552% bruto) y completó la rúbrica íntegra (todas las condiciones + citas aplicables) en 23/24 respuestas frente a 3/24 del brazo PDF.
- Alcance limitado: 8 casos sintéticos × 3 réplicas, un modelo, una base documental, sin validación técnica humana y sin vigencia cotejada; límites detallados al final. Entrada de informe factual; no cambia código, configuración ni resultados.

## Contexto y roles
- Autor solicitante: pedenry. Especialistas OpenCode `evaluacion-normativa` y `recuperacion-normativa` (nan/glm5.3-flash): código y casos. Codex: shell, API y revisión IA; sin validación humana. Estado al terminar el ensayo (antes de la preparación pública): trabajo local, sin commit ni publicación.

## Diseño
- 8 casos sintéticos de 2 páginas × 3 repeticiones por brazo = 48 responses finales. Snapshot gpt-5.4-mini-2026-03-17, razonamiento low, output 3500. Mismo PDF de proyecto y visión/prompt/schema en ambos brazos. Gold separado.
- Fuente DB-SUA 2022-06-14, SHA-256 3cfb5bbb135e8f02faebd8b844e03e8947994c18d4c9e675a7d2aa37d1cd5958, comprobada contra el [enlace oficial](https://www.codigotecnico.org/pdf/Documentos/SUA/DBSUA.pdf). No se afirma vigencia legal.
- V1 adaptador BM25: páginas literales, versión exacta, max 3, presupuesto 20k proxy sin truncar. V0 file_search PDF textual: max 20, chunk 800, overlap 400, max 3 tool calls, misma edición.
- E08 pide edición 2010, ausente en ambos brazos (abstención esperada).

## Consumo por brazo (24 respuestas cada uno)

| Brazo | Input | Output | Total | Cache | Reasoning | Coste USD | Tiempo API s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Adaptador V1 | 236586 | 16190 | 252776 | 155392 | 3826 | 0.145408 | 103.108 |
| PDF V0 | 399988 | 23105 | 423093 | 37632 | 10419 | 0.456062 | 240.797 |

- Cache y reasoning son subconjuntos: no se suman otra vez. Ahorro bruto: 40.2552% de tokens total.

## Calidad por criterio (V1 adaptador vs V0 PDF)
- Estado correcto: 24/24 vs 23/24. Condiciones correctas: 24/24 vs 21/24.
- Cita normativa: 20/21 vs 2/21 (3 NA por E08 en cada brazo).
- Todas las condiciones + citas aplicables: 23/24 vs 3/24.
- 48 completed, IDs únicos, usage concordante; 31 file_search_calls completed en el brazo final.
- Sin falsos cumple ni cotas fabricadas detectados; los errores de página se clasifican como localización, no invención de norma. Detalle por caso y criterio en revision_codex.json; manifest solo identifica y configura las ejecuciones.

## Fallos registrados
- V1 E02 r1: cita página 41 en vez de 36.
- PDF E01–E06: todas citan 35 en vez de 36 (18 respuestas).
- PDF E07 r1: abstención por recuperación insuficiente + malas citas (11/35); r2/r3 dictamen no-cumple correcto pero aplican 6% en vez de 8% a L3m, enunciando bien los intervalos.
- E06: dos frases comparan adicionalmente (r2 del adaptador y r1 del PDF); en esa comparación aparece la redundancia aritmética 0.76<0.80 junto a la condición decisiva 0.76<0.78, correcta; la revisión independiente de OpenCode acepta la redundancia y la anota como claridad, no como fallo.

## Lectura del ahorro
- Pares con todos los criterios pasados en ambos brazos: solo 3/24 (12.5%), todos E08 (abstención por versión ausente); ahí 5500 vs 11912 tokens, 53.8281% menos.
- Eso NO demuestra ahorro con calidad equivalente en comprobaciones positivas/reales; no se logra el criterio estricto de todos los pares fiables. Resultado prometedor para seguir con el adaptador; no validación general ni del efecto de pegar un enlace GitHub en ChatGPT.

## Desarrollo, calibración y costes acumulados
- Pre-evaluación: 12 responses (8 originales + 4 calibración PDF 20), 165262 tokens, 0.197401 USD. Cambio PDF 5→20 decidido en D03 antes de evaluar; originales conservados.
- Final: 675869 tokens, 0.601467 USD (último acumulado de sesión); suma de filas redondeadas 0.601470. Total 60 responses, 841131 tokens, coste estimado acumulado 0.798868 USD (<4).
- Microdiferencias por redondeo. Costes estimados con tarifas de config, no factura; setup/indexación y tokens internos desconocidos. Dev D03 PDF 5 emitió 4 tool calls (3 completados + 1 searching); estimación conservadora cobra los emitidos.
- Generación OpenCode excluida del consumo de consulta. Preparación local 7.89 s una vez por 8 contextos, separada.

## Recursos e higiene
- 4 vector stores y 4 files borrados confirmados; copia local de clave temporal vaciada; clave de panel caduca 11 nov 2026 y no se revocó desde este ensayo.
- 10 tests unitarios previos pasados; fixtures: 12 PDF deterministas, 24 páginas revisadas visualmente; E05 ausencia ilegible sin filtrar el dato.
- Nota de publicación: los 10 tests originales siguen pasando y no se han tocado (fixtures y pruebas intactos); la revisión de publicación añade otras pruebas ([docs/revision-publicacion.md](../docs/revision-publicacion.md)).
- Corrección posterior del ejecutor solo de etiqueta de coste: cleanup.coste_usd_run histórico incluía previo + sesión; datos crudos intactos y versión actual separa coste_usd_total. Hash del runner difiere por corrección post-run; no hubo nueva llamada API.

## Enlaces relativos
- [Adaptador](../experimentos/http-local/adaptador_contexto.py)
- [Protocolo](../evaluacion/piloto_sua/protocolo.md) · [Referencia](../evaluacion/piloto_sua/referencia.md) · [Casos](../evaluacion/piloto_sua/casos.json)
- [Exportador](../evaluacion/piloto_sua/exportar_publico.py) · [Revisión de publicación](../docs/revision-publicacion.md)
- [Manifest](../evaluacion/piloto_sua/resultados-publicos/evaluacion-20261110/manifest.json) · [Revisión Codex](../evaluacion/piloto_sua/resultados-publicos/evaluacion-20261110/revision_codex.json) · [Resumen de consumo](../evaluacion/piloto_sua/resultados-publicos/evaluacion-20261110/resumen_consumo.json) · [Cierre público](../evaluacion/piloto_sua/resultados-publicos/evaluacion-20261110/cierre_publico.json)
- Evidencia pública: la carpeta resultados-publicos/ tiene la misma estructura que el crudo y es una copia depurada generada por exportar_publico.py. Los originales crudos en resultados/ permanecen ignorados por Git y conservados sin editar; requests, api_llamadas.jsonl, recursos.json y cleanup.json no se enlazan ni publican (IDs opacos, rutas y metadatos).
- La exportación no recalcula métricas: exportar_publico transforma los hashes a listas, elimina IDs y metadatos y reserializa el JSON de salida; las respuestas normativas son semánticamente idénticas, usage y consumo quedan intactos y reproducen las cifras de la tabla; metadatos y estructura saneados. Codex verificó 60 respuestas/filas, 841131 tokens y 22 hashes preservados. cierre_publico.json añade el cierre con conteos, estados de borrado y costes observados, sin IDs.

## Comprobaciones confirmadas (Codex)
- Los siete destinos de los enlaces originales existen (comprobación histórica de Codex; los enlaces añadidos en la edición de publicación se registran a continuación).
- Edición de publicación (OpenCode, 2026-11-10): enlaces de evidencia reorientados de resultados/ a resultados-publicos/ (misma estructura, copia depurada); comprobados en esta sesión el exportador (exportar_publico.py), la carpeta resultados-publicos/evaluacion-20261110, cierre_publico.json y la concordancia del resumen de consumo público con la tabla; docs/revision-publicacion.md existe y Codex comprobó sus enlaces.
- revision_codex.json materializada con 48 filas coincide exactamente con los juicios registrados.
- resumen_consumo.json recalculado coincide con la tabla de consumo.
- Hashes de casos, solicitudes, schema, cliente, adaptador y 8 fixtures iguales al manifest; solo el runner difiere por la corrección post-run de etiqueta de coste.
- Ningún bloqueo pendiente; los permisos de lectura de esta sesión no fueron bloqueo del proyecto y la revisión se resolvió por Codex.

## Próxima vía
- Adaptador como componente de consulta; validar citas contra páginas recuperadas; preregistrar piloto nuevo con planos reales autorizados y técnico humano; mismo modelo y fuente, medir de nuevo sin reutilizar esta eval para afirmar ganancia. No construir web todavía como conclusión necesaria.

## Límites de la muestra
- 8 casos sintéticos simples; 3 réplicas, no 24 proyectos; un modelo y una base documental; sin validación técnica humana; sin vigencia cotejada.
