---
fecha: 2026-11-09T00:26:21+01:00
zona: Europe/Madrid
titulo: Experimento HTTP local de consulta
tipo: handoff
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex (copia exacta, comandos, pruebas y publicación autorizada tras revisión)
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: base b12ab29a6e54d78e7bd762d5b1a563cc6dcebb2d; este registro se trazará por el historial
estado: experimento local verificado; runtime no desplegado
---

## Estado observado

- Runtime revisable en `experimentos/http-local/`: `http_consulta.py` y `acceso.py` íntegro reutilizado (SHA256 `b7943…21a39`); sólo loopback, corpus público P, sin fixtures.
- Filtro opt-in de versión verificado el 2026-11-09T00:32:24+01:00: corte histórico con 404 sin tarjetas/lecturas; edición incluida exacta con 3 tarjetas y 10 lecturas; 11 rechazos esperados adicionales (ausencia exacta, parámetros vacíos/duplicados/inválidos, corte estricto y ayuda sin q); 2 q-only con 35 cuerpos idénticos. Runtime final SHA256 `65a8d971623a5b4951e52f5d15f706fa0b94f2584128cfb81a9ce2359b3a2fa3`, distinto del binario medido `1b99…`; no se repitió la batería porque el recorrido ordinario válido quedó intacto. Servidor local detenido.
- Gate corregido 8/8 condiciones y documental; retest 44 con 43 medidos: originales 31/31, variantes 12/12, condiciones 18/18; controles 6/6 reservados. Legacy 27/31 y 33/43 combinado, informado aparte.
- Coste cl100k 756.344/3.201.561 (−76,38 %, mediana 0,241862); o200k 675.356/2.819.516 (−76,05 %, mediana 0,247410). PI-01 crece en ambos; T-01 sólo en o200k.
- 595 HTTP 200 sin fallos; 507 lecturas con paridad textual, ámbito, versión/SHA y PDF local; 324 páginas únicas.
- Primera ejecución inválida y primera batería se conservan como historial, no como resultado válido.

## Pendiente

1. Decidir si se usa por enlace: resolver señal de versión ausente/validación visual e interfaz.
2. Elegir alojamiento Python si se autoriza; no hay contratación ni despliegue.
3. No publicar evaluación, fixtures, respuestas esperadas ni logs privados.
4. T-08: sólo una versión pública; no afirmar ausencia declarada por la API.

## Límites

No se midieron A multimodal, imágenes, wrappers ni uso real ChatGPT/Claude. La paridad de texto no certifica tablas/ejes/fórmulas visuales; el PDF fuente es la referencia. Sin coste visual observado.
