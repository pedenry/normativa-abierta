# Piloto SUA · Protocolo

## Diseño
- Brazos: V0 = file_search sobre el TEXTO del PDF normativo (no visual); V1 = adaptador BM25 (texto). Ambos brazos reciben además el PDF de proyecto completo (2 páginas) con visión.
- Recuperación separada de la respuesta y su razonamiento: trazas aparte.
- Dev: 4 casos × 1 réplica × 2 brazos = 8 responses. Eval: 8 casos × 3 réplicas × 2 brazos = 48 responses. Las réplicas no son proyectos independientes (no son 24).
- Orden de brazos A/B alternado por índice de caso + réplica.
- Gold ([referencia.md](referencia.md)) no se muestra al modelo ni entra en la recuperación.

## Config final (congelada 2026-11-10, tras dev; antes de abrir respuestas de evaluación)
- Modelo gpt-5.4-mini-2026-03-17; razonamiento low; output 3500; schema y prompt fijos; store false; truncation disabled.
- V1: adaptador BM25, max 3 recuperaciones, presupuesto 20k (texto completo); registrar estado overflow.
- V0: file_search, chunk 800 / overlap 400, max 20 fragmentos, límite 3 tool calls. (Dev se ejecutó con max 5; el cambio a 20 salió de la calibración D03.)
- Filtros de versión en V0: usar la edición EXACTA solicitada por el caso (incluye 2010-03-11, ausente en la base → sin resultados); NO fijar siempre filtro 2022.
- Congelación (2026-11-10): snapshot (razonamiento low, output 3500), V1 (max 3 recuperaciones, 20k) y filtros sin cambios; único cambio dev→final: V0 max 5 → 20 fragmentos.

## Calibración D03 (2026-11-10)
- Config ANTES (dev, ejecutada): V0 file_search `max_num_results: 5`. Config final: V0 `max_num_results: 20` — seleccionada y congelada el 2026-11-10 tras dev (antes figuraba como candidata aún sin ejecutar); el resto del body sin cambios (modelo, prompt, schema, 3 tool calls, filtros, candidato).
- Motivo (calibración D03): con max 5, las 3 solicitudes con file_search completadas no trajeron 4.3.1 y el baseline se abstuvo (no_comprobable).
- Se conservan las 8 respuestas dev originales (no se borran ni sobrescriben).
- Calibración dev SOLO PDF con max 20 (ejecutada): los cuatro estados son correctos; D01/D02 citan 35 y la condición está en 36 (fallo de trazabilidad); D03/D04 correctos con 14. Mejora D03 frente a PDF 5 (antes se abstuvo por ausencia de pendientes).
- Gasto dev anterior observado (estimado): 0.12388375 USD. Consumo conservado: 8 dev originales + 4 calibración = 12 responses; 165262 tokens API; coste estimado registrado 0.197401 USD (suma redondeada). Tope TOTAL: 4 USD. Recursos de los 3 runs dev borrados por API.
- Resultados de calibración registrados (rúbrica aplicada por Codex con evidencia); config final seleccionada y congelada. Evaluación final completada (48/48): informe en ../../changelog/2026-11-10-pedenry-evaluacion-adaptador-pdf-sua.changelog.md.

## Reintentos y fallos
- Sin auto-reintentos; los fallos se conservan; no repetir el run seleccionando solo éxitos.
- Los intentos adicionales por incidencia de infraestructura se autorizan para esta tarea y se documentan SIN borrar el original; nunca ocultar fallos reales del modelo.

## Rúbrica manual (aplicada por Codex con evidencia; NO humana)
Por caso y criterio: pasa / falla / NA con evidencia concreta; separar hallazgo, texto recuperado y respuesta.
1. Estado esperado correcto (cumple / no_cumple / no_comprobable).
2. Todas las condiciones: umbrales, unidades y excepciones (p. ej. zona común de Residencial Vivienda).
3. Datos del proyecto exactos y ausencias reconocidas (null declarado, no inventado).
4. Cita de norma con edición, disposición y página física + URL. E08: cita de norma NA (no citar la edición 2022 como fuente de la edición 2010).
5. Referencia al proyecto: página, elemento y archivo (PDFID.pdf p2 · elemento). En estos casos p2 es la del plano; una cita a otra página debe corresponder al dato realmente usado.
6. Alcance acotado al elemento consultado (no edificio entero).
- Error crítico: falso cumple, citas inventadas y cotas inventadas (valores dimensionales fabricados), excepción esencial omitida.

## Medición y ahorro
- Tokens: usage de entrada + salida; caché como subparte de entrada y razonamiento como subparte de salida (no se añaden aparte). Setup/index interno no observable: no registrar como 0.
- Coste registrado aparte; cap 4 USD para dev + eval.
- Ahorro solo en pares V0/V1 del mismo caso y réplica que aprueban TODOS los criterios aplicables en ambos brazos; mostrar también fracasos, tokens brutos de todos los runs y fracción elegible. Si 0 pares: sin cifra de ahorro.
- Registro por run: modelo, orden A/B, config, fuente, fallos y reintentos; contadores usage observados; recuentos de texto etiquetados como proxy con sus límites.

## Estado
- Clave API creada y recogida localmente. Dev ejecutado: 8 originales + 4 calibración = 12 responses (dev con V0 max 5; calibración con V0 max 20). Evaluación completada: 48/48 responses; total de la tarea: 12 dev + 48 final = 60 responses.
- Coste estimado acumulado de la tarea: 0.798868 USD (cap: 4 USD).
- Recursos de API borrados tras finalizar. El cierre público del run es cierre_publico.json (cuentas y estados de borrado sin IDs opacos); los crudos locales (recursos.json, cleanup.json, requests y logs) permanecen ignorados y conservados y no se enlazan como evidencia.
- Evidencia pública: resultados-publicos/evaluacion-20261110, copia depurada del crudo con la misma estructura; los originales en resultados/ quedan ignorados por Git y conservados sin editar.
- Pruebas: los 10 tests unitarios originales siguen vigentes (fixtures y pruebas sin tocar); la revisión de publicación añade otras pruebas.
- revision_codex.json: revisión manual asistida con IA, no humana.
- Informe de evaluación (resultados, rúbrica y ahorro): ../../changelog/2026-11-10-pedenry-evaluacion-adaptador-pdf-sua.changelog.md.
