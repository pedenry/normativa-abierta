# Consultas sin ubicación (2026-11-16, cierre verificado)

Cierre ya verificado por Codex, documentado aquí sin ejecutar shell ni leer informes largos; los hechos medidos se transcriben del encargo. Evalúa consultas sin documento, edición, CCAA ni municipio resolviéndolas por aclaración previa o por recuperación del marco estatal, no por ubicación inferida. Changelog: [../../../changelog/2026-11-16-pedenry-evaluacion-sin-ubicacion.changelog.md](../../../changelog/2026-11-16-pedenry-evaluacion-sin-ubicacion.changelog.md).

## Alcance

- API local: `AdaptadorContexto.preparar` y CLI; **no** el servicio HTTP `buscar` ni consumo del adaptador vía HTTP.
- 20 consultas nuevas sin documento, edición, CCAA ni municipio; llamada `preparar(consulta, None, None, 20000, 2)`.
- Fixture preparado antes de ejecutar: [casos-sin-ubicacion.json](casos-sin-ubicacion.json); informe de Codex: [resultados-sin-ubicacion-2026-11-16.json](resultados-sin-ubicacion-2026-11-16.json); runner: [ejecutar_sin_ubicacion.py](ejecutar_sin_ubicacion.py).

## Resultados (antes → después)

| Conjunto | Antes | Después | Criterio |
| --- | --- | --- | --- |
| Territoriales (14) | 0/14 | 14/14 | piden aclaración |
| Nacionales (6) | 4/6 | 6/6 | recuperan evidencia literal/edición y no piden lugar |
| **Total** | 4/20 | 20/20 | — |

Verificación por aclaración: campos requeridos correctos según la intención, pregunta no vacía, cero páginas/resultados entregados y sin región inventada.

## Mecanismo

- Nuevo estado `aclaracion_necesaria`; `aclaracion.campos_requeridos` = comunidad autónoma y municipio según la intención; `aclaracion.pregunta` no vacía (ejemplo: licencia de obras pregunta CA y municipio).
- No toda consulta sin ubicación se bloquea: CTE, REBT y marco estatal pueden responderse. Se distingue marco solo estatal de marco mixto estatal/autonómico; el estado de un expediente no es Estado nacional; sin fallback a CCAA cuando faltan nacionales.
- Enfoques de entidad-relación y conceptual solo en `auto_sin_doc_sin_ubicacion`: origen y pregunta original conservados y `vista_busqueda` trazada. El conceptual estatal selecciona documentos por la frase-entidad solicitada entre fuentes nacionales públicas, dinámico, sin IDs, páginas ni casos en reglas.
- `acceso.py` exactamente igual: IDF global, ranking y helper auxiliar intactos.

## Rúbrica v1 → v2 (corregida por bug)

- Bug detectado en la v1: aceptaba campos incompletos como subconjunto del requerido. La v2 exige igualdad de conjunto requerido, sin extras ni duplicados.
- Los criterios sí cambiaron entre versiones. La v1 original y la captura inicial se conservan; mismos casos, golds y consultas sin retocar; la v2 se aplicó a las capturas del motor anterior y del motor corregido.

## Regresión y comprobación

- 132 unittest en verde: 19 generales + 19 piloto SUA + 10 herramientas + 17 evaluador + 67 HTTP, incluidas unidades nuevas [test_aclaracion.py](../../../experimentos/http-local/tests/test_aclaracion.py) y [test_sin_ubicacion.py](../test_sin_ubicacion.py).
- 71 casos previos (48 con filtro de documento + 21 libres ubicados + 2 CTE ubicados) absolutamente idénticos: estados, SHA de contexto, páginas/SHA y primarios BM25.
- Las 47 referencias evaluables de las 48 consultas con documento se conservan; la alternativa Málaga previa sin alterar.
- 11 archivos previos protegidos (manifiesto, índice, fixtures) intactos; los SHA de los 19 PDF devueltos en capturas nuevas medidos en la verificación final y cotejados con los metadatos registrados (doc.json).
- 3 sondas previas Madrid/Sevilla (municipal sin incorporar) y unión Aragón/Navarra pasan.

## Repetición

```powershell
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_sin_ubicacion.py --salida .local/sin-ubicacion/repeticion.json
```

## Límites

- Heurística y muestra curada de 20 casos, sin independencia estadística ni certificado de calidad global.
- Corpus municipal incorporado: solo Málaga; no es dictamen de vigencia ni de aplicabilidad jurídica.
- Recuentos de texto proxy, no facturación de API; sin cálculo de ahorro de API ni de latencia.
- Sin commit, publicación ni cambios en otros archivos en este cierre.
