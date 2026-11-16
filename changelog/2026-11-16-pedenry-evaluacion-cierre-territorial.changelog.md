# 2026-11-16 · Handoff de cierre — tanda territorial (recuperación, visor y sin ubicación)

| Campo | Valor |
| --- | --- |
| Fecha | 2026-11-16 |
| Autor | pedenry |
| Tipo | handoff |
| Ámbito | evaluación · regresión_recuperación · territorial · cierre de tanda |
| Estado | entrega local validada; publicación de rama y CI remota por comprobar tras el commit |
| Preparación | borrador nan/glm5.3-flash con lectura bloqueada; bloqueo documental resuelto con extracto autorizado cotejado por Codex |

## Estado de cierre

- La tanda queda en **candidato validado**. El commit y el push quedan autorizados al responsable; esta preparación no ha observado ningún commit ni push y no registra SHA de commit alguno.
- Revisión de fuentes hecha por Codex sobre el checkout; esta entrada solo recoge lo cotejado.
- Rama de entrega: `codex/cierre-territorial-recuperacion`, desde `e96163ab`. El commit de entrega será el que incorpore esta entrada; se consulta con `git log -1`. Se conserva el flujo de revisión por PR de CONTRIBUTING; este cierre no implica merge a `main` ni despliegue en Pages.

## Verificado por Codex hoy (2026-11-16)

Ingesta e integridad:

- 149 PDF reales verificados por SHA contra `doc.json` y manifiesto.
- 103 licencias nuevas en estado APROBADA en `licencias/territorial-2026-11-16.json`.
- 5357 páginas nuevas con texto, SHA y ficheros md/json coincidentes.
- 17 CCAA; único municipal incorporado: Málaga (OMLU, publicación original 2025-12-29).
- Totales del corpus: 9681 páginas y 11132 segmentos.

Pruebas:

- 132 unittest en verde; el recálculo del consumo publicado termina con exit 0.
- 71 casos anteriores absolutamente idénticos según el informe: estados, SHA de contexto, páginas/SHA y primarios BM25. Las 47 referencias evaluables de las 48 consultas con documento se conservan.
- 20 consultas nuevas pasan: 14 piden aclaración y 6 nacionales recuperan evidencia literal/edición (antes 4/20 → después 20/20).
- Los hashes del código actual coinciden con los del informe.
- Repetición final en un entorno virtual limpio con `ingesta/requirements.txt`: las mismas 132 pruebas pasan. La CLI sin ubicación devuelve 20/20, sin inconsistencias, también sin tokenizador opcional.

Visor:

- Dos generaciones idénticas: 149 documentos, 20992 HTML, 301716 enlaces, cero enlaces rotos y cero fuera de la raíz. SHA-256 del árbol (rutas y hashes ordenados): `9cb5217bef1bdede071621e7a89ee3034c6de2fbf7c4b89c5d1cb675f786097b`.
- Se conservan las 10175 rutas generadas previamente publicadas. Candidato promovido a `index.html` y `site/`.
- Navegador local: portada con 149 documentos, materia Baja tensión, REBT y página física 109, Código Estructural y OMLU de Málaga. Revisadas páginas de texto y metadatos a 390×844 y escritorio; edición, procedencia, SHA y avisos visibles. El PDF de Código Estructural se abre en el navegador. Esto no es un cotejo visual completo de su contenido.

Documentación e integración:

- Índices de documentos y materias y guía de ingesta sincronizados.
- CI ampliada con tests de ingesta y evaluador y un trabajo de recuperación que ejecuta las 91 consultas (48 con documento, 23 libres ubicadas y 20 sin ubicación). Su resultado remoto se comprobará tras el push.
- `.gitattributes` conserva los bytes de la evidencia JSON y exceptúa únicamente los textos literales y sus vistas HTML de las reglas de espacios. No se limpian las extracciones para satisfacer una regla de estilo ni se invalidan sus SHA.

## Explicaciones de cierre

- **REBT**: la consulta amplia pasó de la página física 103 (instalaciones de enlace) a la 109 (línea general de alimentación); ambas resultaron pertinentes. Se conserva el IDF global, sin forzar una página para esa consulta amplia.
- **SUA**: une palabras partidas solo en el scoring; el texto literal queda intacto.
- **Madrid / País Vasco / Málaga**: Madrid (consolidado/no consolidado), País Vasco (máximo/mínimo) y Málaga (inicio/transitoria) se corrigieron por la señal general de pasajes auxiliares, sin ajustes por caso ni gold retocado.
- **Filtros territoriales**: resueltos desde metadatos públicos de la fuente; sin IDs, páginas ni regiones fijados en código.
- **Aclaración sin ubicación**: disponible en `preparar` y en la CLI; el buscador HTTP básico no la consume.
- **Rúbrica v1→v2**: la v1 aceptaba como válido un subconjunto de los campos requeridos (bug); la v2 exige exactamente todos los campos faltantes, sin extras ni duplicados. La v2 se aplicó a las capturas de ambos motores (anterior y corregido) con los mismos casos, golds y consultas; la v1 y su captura inicial se conservan.
- **Búsqueda libre, Málaga L18**: la página 33 (art. 31.1) es alternativa suficiente a la página 16 (art. 9.3), cotejada después de forma independiente. El gold y la evaluación original (20/21) se conservan sin modificar; la adjudicación con el criterio de evidencia revisado es 21/21, solo con el flag opt-in de alternativas y sin forzar el motor a p16. No es una evaluación independiente adicional del caso.

## Evidencia (enlaces relativos desde `changelog/`)

- Suite de regresión: [../evaluacion/regresion_recuperacion/README.md](../evaluacion/regresion_recuperacion/README.md)
- Lotes territoriales: [../evaluacion/regresion_recuperacion/territorial/README.md](../evaluacion/regresion_recuperacion/territorial/README.md)
- Consultas sin ubicación: [../evaluacion/regresion_recuperacion/territorial/SIN-UBICACION.md](../evaluacion/regresion_recuperacion/territorial/SIN-UBICACION.md)
- Verificación de la ingesta territorial: [../contenido/validacion/territorial-2026-11-16-verificacion.json](../contenido/validacion/territorial-2026-11-16-verificacion.json)
- Registro de reutilización: [../licencias/territorial-2026-11-16.json](../licencias/territorial-2026-11-16.json)
- Generación del visor: [../docs/generacion-visor.md](../docs/generacion-visor.md)
- Hilo de la tanda en este mismo directorio: [ampliación territorial](2026-11-16-pedenry-evaluacion-ampliacion-territorial.changelog.md), [corrección de recuperación](2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md), [búsqueda libre](2026-11-16-pedenry-evaluacion-busqueda-libre-territorial.changelog.md), [sin ubicación](2026-11-16-pedenry-evaluacion-sin-ubicacion.changelog.md), [regresión REBT](2026-11-16-pedenry-evaluacion-regresion-rebt.changelog.md), [SUA palabras partidas](2026-11-16-pedenry-evaluacion-sua-palabras-partidas.changelog.md).

## Reproducción (comandos confirmados)

Desde la raíz del checkout:

```sh
python -B -m unittest discover -s tests -p test_*.py -v
```

y las suites de `evaluacion/piloto_sua`, `herramientas/tests`, `evaluacion/regresion_recuperacion` y `experimentos/http-local/tests`.

```sh
python -B evaluacion/regresion_recuperacion/ejecutar.py --estricto
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_sin_ubicacion.py --salida .local/sin-ubicacion/repeticion.json
```

Para el resto de fixtures (lotes territoriales, contraste y libres), remite a los README enlazados arriba, que incluyen los comandos por lote.

## Límites

- Muestra curada sin independencia estadística; sin certificado de calidad global.
- Sin ahorro de API medido: los recuentos de texto son proxy local, no facturación; sin latencia.
- La cobertura por presencia de página no acredita acierto ni fidelidad sustantiva; revisión automática y por IA, no humana.
- Esta entrada no modifica código, casos, gold ni resultados históricos.

## Pendientes fuera de esta tanda

1. Integrar el flujo HTTP (la aclaración sin ubicación no está en el servicio HTTP).
2. Más municipios (solo Málaga incorporado).
3. Fidelidad humana, transitorios, vigencia y aplicabilidad.
4. Muestra independiente.
5. Latencia y consumo API.

Antes de integrar en `main`: verificar la CI de la rama y revisar la PR. Pages seguirá sirviendo `main` hasta esa integración; no se declara publicación web completada.

## Nota de herramientas

El borrador inicial de esta entrada lo redactó NaN con lectura del checkout bloqueada; el bloqueo documental se resolvió mediante un extracto depurado y autorizado, cotejado por Codex. Las pendencias que el borrador marcó por falta de lectura quedan aquí resueltas y no se mantienen como pendientes ficticias. Sin commit ni push observados.
