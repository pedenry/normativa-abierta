---
fecha: 2026-11-16
zona: Europe/Madrid
titulo: "Aclaración previa en consultas sin ubicación: 20 casos y rúbrica v2"
tipo: changelog
usuario: pedenry
solicitante: pedenry
ejecutor: Codex
herramienta_modelo: OpenCode especialistas nan/glm5.3-flash (evaluación y recuperación)
estado: completado
---

# Aclaración previa en consultas sin ubicación: 20 casos y rúbrica v2

## Resultados

20 consultas nuevas sin documento, edición, CCAA ni municipio, vía API local (`AdaptadorContexto.preparar`, llamada `preparar(consulta, None, None, 20000, 2)`) y CLI; no el servicio HTTP `buscar`. Antes → después: territoriales 0/14 → 14/14 piden aclaración; nacionales 4/6 → 6/6 recuperan evidencia literal/edición sin pedir lugar; total 4/20 → 20/20. Aclaración verificada: campos correctos según intención, pregunta no vacía, cero páginas/resultados, sin región inventada. Informe: [resultados-sin-ubicacion-2026-11-16.json](../evaluacion/regresion_recuperacion/territorial/resultados-sin-ubicacion-2026-11-16.json); documento de cierre: [SIN-UBICACION.md](../evaluacion/regresion_recuperacion/territorial/SIN-UBICACION.md).

## Mecanismo

- Nuevo estado `aclaracion_necesaria` con `aclaracion.campos_requeridos` (comunidad autónoma y municipio según intención) y `aclaracion.pregunta`; no todo sin ubicación se bloquea: se distingue marco solo estatal de mixto estatal/autonómico (CTE/REBT respondibles), el estado de expediente no es Estado nacional y sin fallback a CCAA si faltan nacionales.
- Enfoques entidad-relación y conceptual solo en `auto_sin_doc_sin_ubicacion`; origen/pregunta original conservados y `vista_busqueda` trazada; conceptual estatal dinámico por frase-entidad entre fuentes nacionales públicas, sin IDs/páginas/casos en reglas. `acceso.py` exactamente igual (IDF global, ranking y helper auxiliar intactos).

## Rúbrica y comprobación

- Rúbrica v1 → v2 por bug: v1 aceptaba subconjuntos de campos incompletos; v2 exige igualdad de conjunto requerido sin extras ni duplicados. V1 original y captura inicial conservadas; casos/golds/consultas sin retocar; v2 aplicada a las capturas del motor anterior y del motor corregido.
- 132 unittest (19 generales + 19 piloto SUA + 10 herramientas + 17 evaluador + 67 HTTP) con unidades nuevas de aclaración y de la suite sin ubicación.
- 71 casos previos (48 filtrados por documento + 21 libres ubicados + 2 CTE) con estados, SHA de contexto, páginas/SHA y primarios BM25 idénticos; las 47 referencias evaluables de las 48 consultas con documento se conservan y la alternativa Málaga queda sin alterar; 11 archivos protegidos intactos y SHA de los 19 PDF medidos en la verificación final y cotejados con los metadatos registrados (doc.json); sondas Madrid/Sevilla y unión Aragón/Navarra pasan.

## Límites

- Muestra curada por heurística, no independencia estadística; corpus municipal incorporado solo Málaga; no dictamen de vigencia ni aplicabilidad.
- Sin cálculo de ahorro de API ni latencia; recuentos de texto proxy, no facturación; sin commit ni publicación en este cierre.
- Repetición: `python -B evaluacion/regresion_recuperacion/territorial/ejecutar_sin_ubicacion.py --salida .local/sin-ubicacion/repeticion.json`. Fixture: [casos-sin-ubicacion.json](../evaluacion/regresion_recuperacion/territorial/casos-sin-ubicacion.json).
