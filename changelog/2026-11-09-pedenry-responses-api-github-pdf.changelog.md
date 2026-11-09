---
fecha: 2026-11-09T22:29:50+01:00
zona: Europe/Madrid
titulo: "Comparación en Responses API de GitHub, PDF indexado y PDF completo"
tipo: changelog
solicitante: pedenry
ejecutor: Codex
asistencia: "OpenCode documentos con nan/glm5.3-flash para ejecutor y registro"
usuario_github_verificado: pedenry (id 35270581)
corpus_commit: f05b84fb6a7ed2da59bb03031d73c51c4159c507
estado: completado
---

# Comparación en Responses API de GitHub, PDF indexado y PDF completo

## Contexto y configuración

Responses API completó nueve solicitudes aisladas entre las 22:26:53 y las 22:29:50 del 9 de noviembre de 2026. El orden fue ABC para DB-SI, BCA para RITE y CAB para RSCIEI, con un envío por combinación. Las nueve solicitudes usaron el snapshot `gpt-5.4-mini-2026-03-17`, razonamiento `low`, `max_output_tokens=3500`, `truncation=disabled`, `store=false` y servicio `default`. Cada caso mantuvo la misma pregunta y el mismo formato de respuesta en sus tres variantes. En el DB-SI se retiraron los identificadores de tabla y apartado de la pregunta previa. La prueba mide Responses API. [Protocolo de referencia de la prueba web](https://github.com/pedenry/normativa-abierta/blob/f05b84fb6a7ed2da59bb03031d73c51c4159c507/changelog/2026-11-09-pedenry-github-pdf-chatgpt.changelog.md).

Se cotejaron los tres PDF públicos completos con el corpus fijado. [Commit del corpus](https://github.com/pedenry/normativa-abierta/tree/f05b84fb6a7ed2da59bb03031d73c51c4159c507).

| Documento | Edición | Páginas | SHA-256 del PDF |
| --- | --- | ---: | --- |
| DB-SI | 2025-03-04 | 92 | `0a2e78cd62471d9cc5cfe2efbc6aa39fdbad73c124aea7b039f9de96c141e105` |
| RITE | Consolidado 2022-08-02 | 97 | `ad1680c83bf4c7f5c656af1794c32ad0669ad9f36ac293737ff3f95177ff7b26` |
| RSCIEI | RD 164/2025, publicado 2025-04-10 | 108 | `85aa0af25d51e5b58d8975a4eefbf76d3f57a8933445cfe814ae9c4818a2e3e7` |

El SHA-256 del protocolo previo fue `5cd88507f4c0a444e4b47e9da3e5ead877e27f3f82b37f7ca158978a4c8ef443` y el del manifiesto de diseño fue `427382cc98b45c0bb339da2123b448b9bee385b4c97017aeede04b54657e7c44`.

- **A. GitHub.** Solo recibió la URL raíz. Se exigió `web_search` con contexto `medium`, hasta ocho llamadas, filtro de dominio para `github.com` y `pedenry.github.io` e inclusión de `web_search_call.action.sources`. [Repositorio](https://github.com/pedenry/normativa-abierta) · [Web Search](https://developers.openai.com/api/docs/guides/tools-web-search).
- **B. PDF indexado.** Se exigió `file_search` en un índice aislado por caso, con hasta ocho llamadas, 12 fragmentos por llamada e inclusión de `file_search_call.results`. La solicitud no llevaba herramienta web. [File Search](https://developers.openai.com/api/docs/guides/tools-file-search).
- **C. PDF completo.** Se envió el mismo PDF en base64 como `input_file`, con detalle visual `low` y sin herramientas. Los tres envíos completaron con el truncamiento desactivado y sin errores de límite. [Entradas de archivo](https://developers.openai.com/api/docs/guides/file-inputs).

[Modelo y capacidades](https://developers.openai.com/api/docs/models/gpt-5.4-mini) · [Contrato de Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create).

## Consumo registrado

| Caso/Variante | Entrada | Salida | Total | Caché | Razonamiento | Criterios |
|---|---|---|---|---|---|---|
| CTE A | 21837 | 1460 | 23297 | 0 | 939 | 0/5 |
| CTE B | 10801 | 1201 | 12002 | 0 | 392 | 3/5 |
| CTE C | 83184 | 998 | 84182 | 0 | 76 | 4/5 |
| RITE A | 26551 | 1710 | 28261 | 2304 | 1026 | 4/5 |
| RITE B | 10747 | 1263 | 12010 | 0 | 406 | 4/5 |
| RITE C | 106553 | 1313 | 107866 | 0 | 237 | 3/5 |
| RSCIEI A | 20867 | 1555 | 22422 | 2304 | 980 | 0/5 |
| RSCIEI B | 19452 | 1293 | 20745 | 0 | 583 | 5/5 |
| RSCIEI C | 144947 | 1246 | 146193 | 0 | 205 | 3/5 |

Las cifras proceden de `response.usage`. La caché forma parte de los tokens de entrada y el razonamiento forma parte de los de salida.

| Variante | Entrada | Salida | Total | Caché |
| --- | ---: | ---: | ---: | ---: |
| A. GitHub | 69.255 | 4.725 | 73.980 | 4.608 |
| B. PDF indexado | 41.000 | 3.757 | 44.757 | 0 |
| C. PDF completo | 334.684 | 3.557 | 338.241 | 0 |

En los tres casos, GitHub consumió más tokens de entrada y totales que el PDF indexado y menos que el PDF completo.

El ahorro con cobertura conservada quedó sin estimar. Hubo **0 de 3 pares elegibles** tanto para A/B como para A/C. B/C tampoco reunió cobertura y trazabilidad completas en ambos brazos. El cálculo previsto era `100 × (PDF − GitHub) / PDF`, por separado para entrada y total. El agregado usaría la suma del mismo conjunto de casos elegibles para cada comparación.

## Cobertura por criterios

Cada posición de la matriz corresponde a un criterio en el orden indicado. Se asignó `1` si la respuesta conservó sus condiciones y `0` si lo omitió, lo dejó incompleto o lo contradijo. Documento, edición, disposición, página física y fuente se verificaron por separado.

- **DB-SI.** Umbral general y aplicación al caso, excepciones de ocupación y prohibición hospitalaria, recorridos y excepciones, ampliación por extinción automática y comprobaciones pendientes de uso, recorrido y altura.
- **RITE.** Calificación como reforma, alcance de la reforma, continuidad de mantenimiento, uso e inspección con sus límites, requisitos de incorporación de equipos con independencia de la calificación y datos técnicos pendientes para la documentación.
- **RSCIEI.** Régimen de usos subsidiarios, umbral individual de oficina, umbral individual de aparcamiento, condición espacial y efectos del cómputo conjunto y sectorización independiente con permanencia en el establecimiento.

| Caso | A | B | C |
|---|---|---|---|
| DB-SI | 00000 | 10110 | 11110 |
| RITE | 11101 | 11011 | 11001 |
| RSCIEI | 00000 | 11111 | 11100 |
| Total | 4/15 | 12/15 | 10/15 |

En DB-SI, A abrió portada y visor sin llegar a la tabla ni a la nota y sin edición o páginas. B acertó umbral, recorridos y nota, omitió el supuesto residencial de 500, presentó los límites de 50 como prohibiciones y omitió comprobar la altura, y citó las páginas físicas 24-25 del PDF sin edición. C cubrió cuatro de cinco criterios. Faltó señalar la altura como comprobación pendiente. Identificó la edición y las páginas físicas 24 y 25, aunque etiquetó el apartado 3 como 3.1.

En RITE, A abrió ficha y apartado 18, acertó alcance, obligaciones y datos faltantes, omitió que los requisitos del art. 18 se aplican con independencia de la calificación de la intervención y no citó edición ni página. B omitió explicitar las limitaciones reglamentarias del art. 2.2 y la edición, acertó los otros cuatro criterios y citó mal la excepción secundaria como art. 22.11 cuando corresponde al art. 24.11 en la página 17. C omitió tanto las limitaciones como la independencia de la condición de reforma, omitió la edición y sobregeneralizó la exigencia documental del art. 15.4, que remite al 2.3 cuando el caso se encuadra en el 2.4.

En RSCIEI, A identificó la fecha y no llegó al art. 4.2 ni a la página 37, sin resolver los criterios. B logró 5/5 con el art. 4.2 y la página 37, sin fecha de edición y con cita agrupada. C acertó régimen y umbrales individuales, mezcló el criterio de almacén del DB-SI con el art. 4.2.h, omitió que los espacios sectorizados siguen siendo parte del establecimiento, citó la página 37 en las letras a y g y una referencia h desplazada a la página 23, con la fecha sin precisar.

Páginas del corpus cotejadas. [DB-SI, página 24](https://pedenry.github.io/normativa-abierta/site/pagina/db-si-oficial-2025-03-04-0a2e78cd6247__p0024.html) · [DB-SI, página 25](https://pedenry.github.io/normativa-abierta/site/pagina/db-si-oficial-2025-03-04-0a2e78cd6247__p0025.html) · [RITE, página 8](https://pedenry.github.io/normativa-abierta/site/pagina/rite-asociada-sin-fecha-ad1680c83bf4__p0008.html) · [RSCIEI, página 37](https://pedenry.github.io/normativa-abierta/site/pagina/rsciei-asociada-sin-fecha-85aa0af25d51__p0037.html).

## Trazas y operaciones

- **A.** En DB-SI, RITE y RSCIEI hubo ocho acciones web completadas por caso. DB-SI y RSCIEI devolvieron además una apertura con estado `searching`. Las búsquedas devolvieron 27, 26 y 23 URL distintas fuera de las rutas del repositorio o visor, respectivamente. Las 3, 8 y 1 citas de las respuestas apuntaron al repositorio o al visor. La traza mostró acceso a ficha y al apartado del artículo 18 del RITE. El artículo 15 apareció citado, sin una apertura registrada. En los otros dos casos la traza no llegó a una disposición del documento.
- **B.** Se completaron 1, 1 y 2 llamadas de File Search, con 12, 12 y 24 fragmentos del PDF correspondiente, respectivamente. Sumaron 36.404, 35.798 y 70.411 caracteres, con solapamientos. Las 6, 10 y 8 citas se asociaron al archivo correcto. El fragmento 5 del DB-SI contenía la excepción residencial y los fragmentos 5 y 10 incluían condiciones de altura. Los fragmentos 1 y 5 del RITE incluían las limitaciones del artículo 2.2. La respuesta perdió esos datos pese a estar en el material recuperado.
- **C.** Las referencias se comprobaron en el texto de la respuesta. En este brazo no hubo llamadas de herramienta ni anotaciones automáticas.

Se crearon tres archivos y tres índices temporales para B. Las seis peticiones de borrado devolvieron HTTP 200.

A tarifa estándar, el coste de los tokens registrados se estima en **0,38477 USD** para el lote. El cálculo aplica 0,75 USD por millón de tokens de entrada, 0,075 USD por millón de tokens de entrada en caché y 4,50 USD por millón de tokens de salida. Las tarifas de herramientas se contabilizan por separado. Se observaron 24 acciones web completadas, dos con estado `searching` y cuatro llamadas de File Search completadas. Si cada acción completada correspondiera a una llamada facturable, aplicar 0,01 USD por llamada web y 0,0025 USD por llamada de File Search añadiría 0,25 USD. La factura, el tratamiento de las dos acciones sin cierre y el importe de almacenamiento quedaron sin comprobar. [Precios del modelo](https://developers.openai.com/api/docs/models/gpt-5.4-mini) · [Precios de herramientas](https://developers.openai.com/api/docs/pricing).

Platform confirmó la revocación de las dos credenciales temporales. La primera figuró sin uso. La segunda fue la credencial restringida con la que se ejecutó el lote.
