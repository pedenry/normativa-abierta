# 2026-11-17 · pedenry · evaluación HTTP territorial

## Problema

La API HTTP de recuperación territorial no exponía un endpoint de contexto ni una capa de contexto
reutilizable para `/buscar` sin documento, con el corpus ampliado a 149 documentos y el plazo de
15 s como restricción.

## Cambio

- `/contexto` nuevo en `http_consulta.py` y `servicio_publico.py`: singleton `AdaptadorContexto`,
  presupuesto 20000 y máximo 2.
- `/buscar` sin documento usa ese adaptador: aclara la ubicación cuando hace falta y no recurre a
  fuentes municipales sustitutas.
- Se corrigen dos huecos previos del adaptador: «en Madrid … ordenanza municipal» no puede
  responder con la fuente autonómica, y «ordenanza municipal de Sevilla» reconoce el lugar
  solicitado para declarar que falta esa fuente. La regla es genérica, sin catálogo de ciudades:
  no convierte «competencia urbanística municipal» ni el ayuntamiento receptor de una cesión
  en una petición de ordenanza local.
- `/buscar` con documento + versión/corte y `/leer` preservan el contrato. En `/contexto`,
  parámetros no válidos → 400 y documento/edición ausente → 404; errores nuevos → 500 genérico.
  Se excluye el campo `contenido`, que contiene la ruta absoluta del corpus.
- El servicio público admite 149 documentos y mantiene plazo de 15 s, 8 concurrentes y validaciones.
- Caché BM25 opcional de arranque: conserva el IDF global primario y las puntuaciones; incluye
  páginas y notas para cumplir el plazo; rechaza preparación ajena; se reinicia si cambia el corpus.
- Job HTTP añadido a GitHub Actions, sin ejecutar CI remota.

## Evidencia

- [resultados-http-2026-11-17.json](../evaluacion/regresion_recuperacion/territorial/resultados-http-2026-11-17.json):
  273 comparaciones HTTP reales en loopback, sin modelos ni reintentos (91 + 91 + 48 + 43): 91
  `/contexto` público y 91 local exactas frente a la captura previa de la API del commit
  `b2b2d423af55a47c52ff5876b463f8e49ea72c8e`; 48 `/buscar` explícitos locales con cuerpos SHA
  idénticos; 43 `/buscar` auto públicos con estados, ámbito, tarjetas y lecturas iguales.
- [referencia-http-2026-11-16.json](../evaluacion/regresion_recuperacion/territorial/referencia-http-2026-11-16.json):
  congelada antes de generar los resultados nuevos; esquema 2, sella por SHA la respuesta
  normalizada completa; la etiqueta de contador se omite solo en la copia legible por un falso
  positivo de gitleaks y queda conservada en el SHA.
- 179 pruebas unitarias en verde: 19 generales + 19 SUA + 10 herramientas + 41 de evaluación + 90 HTTP.
  Las 24 nuevas del evaluador comprueban también que detecta respuestas alteradas y estados HTTP erróneos.
- Seis lecturas literales por HTTP conservan página, edición y SHA: REBT 109, SUA 36,
  Madrid 18, País Vasco 21 y Málaga 16/33.
- Cuatro formulaciones municipales adicionales, ocho peticiones entre `/contexto` y `/buscar`:
  Madrid y Sevilla se abstienen sin entregar evidencia de otra jurisdicción. Las dos variantes
  que ya se abstenían conservan el comportamiento; las otras dos quedan corregidas.
- Sondeo N06, proceso nuevo y caché del SO sin controlar: la variante HTTP sin pre cálculo se
  desconecta a 15061 ms con Timer de 15 s; la respuesta final es 200 en 3094.4 ms, Timer sin
  dispararse y contexto con SHA igual. No es benchmark.

## Límites

- La referencia no es un gold independiente de corrección normativa: compara contra la captura previa de la misma API.
- Sin ahorro cuantificado, sin RAM medida y sin certificación de vigencia.
- Corpus, fixtures y oráculos anteriores sin alterar.
- Implementación y pruebas: OpenCode (NaN); revisión, corrección y ejecución: Codex.
- Sin commit, push ni despliegue en este encargo; CI remota pendiente de ejecución.
