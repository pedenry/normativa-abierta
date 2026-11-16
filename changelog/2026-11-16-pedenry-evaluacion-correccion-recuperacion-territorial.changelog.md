---
fecha: 2026-11-16
zona: Europe/Madrid
titulo: "Corrección de recuperación territorial: señal de pasaje y predicado definitorio"
tipo: changelog
usuario: pedenry
solicitante: pedenry
ejecutor: Codex
herramienta_modelo: OpenCode especialistas nan/glm5.3-flash (evaluación y recuperación)
estado: completado
---

# Corrección de recuperación territorial: señal de pasaje y predicado definitorio

## Diseño

Tras el diagnóstico independiente de los 3 fallos del run territorial estricto (T-09 Madrid p. 18, T-15 País Vasco p. 21, T-18 Málaga p. 16), el agente de evaluación preparó antes de ver resultados el fixture de contraste de 6 casos ([casos-contraste.json](../evaluacion/regresion_recuperacion/territorial/casos-contraste.json)) y el fichero de pruebas de pasajes; el agente de recuperación aplicó el cambio en `experimentos/http-local/acceso.py`; Codex aisló la causa, ejecutó, comparó y reportó. Ningún agente de OpenCode ejecutó el motor: la ejecución real fue de Codex.

## Mecanismo

Fuente intacta, auxiliar previa conservada y el segundo hueco ya permitido para lecturas auxiliares (hasta 2 por documento) ocupado con el mejor pasaje por operación (máximo/mínimo, inicio/dicotomía) y predicado definitorio ligado al término consultado; purga editorial solo en la vista de puntuación. `max_resultados=2` sigue limitando los resultados principales: son límites independientes. Sin IDs, páginas ni regiones fijadas en código y sin IDF local primario. El ranking primario BM25 mantiene IDs, páginas y puntuaciones idénticas en los 48 casos; las correcciones no reciclan primarios como auxiliares nuevos ni arrastran continuadas según `expandir`.

## Resultados

| Conjunto | Antes | Después |
| --- | --- | --- |
| Territorial (21 referencias, 3 lotes) | 18/21 en contexto, 17/21 primarias | 21/21 en contexto (17/17 CCAA, 4/4 Málaga) |
| Suite completa (48 casos, 47 referencias; REBT-09 amplia sin referencia exclusiva) | 44/47 | 47/47 |
| V1 experimental (solo T-09 sin resolver) | — | 46/47 |
| Contraste territorial (6 casos) | 6/6 | 6/6 |

- Las 3 correcciones entran como auxiliares en contexto: 38/47 referencias primarias finales, cero referencias previas perdidas y cero pérdidas de primarias anteriores.
- Consultas y gold congelados: 46 consultas distintas (2 repetidas), ninguna alterada tras ver resultados.

## Comprobación

- 96 pruebas unittest en verde (19 tests + 19 piloto SUA + 40 HTTP + 10 herramientas + 8 evaluador), entre ellas 7 nuevas de pasajes ([test_pasajes.py](../experimentos/http-local/tests/test_pasajes.py)).
- Los tres lotes territoriales y el fixture de contraste retornan exit 0 en `--estricto`; base REBT/SUA 14/14 y fixture SUA extra 6/6 preservadas.
- Estados ok e integridad ok en todos los casos: gold literal, documento, versión y SHA por página; presupuesto 20000 tokens, `max_resultados=2` y auxiliares ≤2 por documento sin ampliaciones; corpus, índice, manifiestos, consultas y gold originales sin cambios de hash, con el ajuste previo de palabras partidas preservado.
- Informe nuevo de Codex: [resultados-correccion-2026-11-16.json](../evaluacion/regresion_recuperacion/territorial/resultados-correccion-2026-11-16.json); resultados históricos sin sobrescribir.

## Límites

- Solo se corrige recuperación en la muestra curada de 20 PDF; la presencia de página en contexto no acredita respuesta completa ni fidelidad sustantiva; sin certificado de calidad global.
- Sin respuesta jurídica ni dictamen de validez o vigencia global; filtros doc/versión activos.
- Sin latencia ni ahorro demostrados (corridas en paralelo); las páginas auxiliares completas añadidas bajo igual presupuesto pueden aumentar la longitud del contexto; recuentos proxy local, no facturación de API.
- Sin commit, publicación ni despliegue en este cambio.
