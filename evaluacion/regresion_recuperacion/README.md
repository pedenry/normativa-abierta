# Regresión de recuperación (REBT/SUA)

Suite fija de regresión para el motor de recuperación: 15 consultas naturales (8 precisas REBT, 1 amplia, 6 SUA) sobre dos documentos, con 14 referencias de página física. La referencia de páginas es independiente del ranking y se mantuvo sin cambios durante toda la comparación: no se ajustó ninguna para hacer pasar un brazo. Ejecución con `AdaptadorContexto` real, `max_resultados=2`, presupuesto 20000 tokens, sin API.

> **Estado actual (2026-11-16, tras la corrección de palabras partidas):** la suite pasa 14/14 en contexto con SUA-02 resuelto (primarias 12/14); la tabla de «Resultados históricos» refleja el estado anterior a la corrección. Informe vigente: [resultados-sua-2026-11-16.json](resultados-sua-2026-11-16.json).

## Ejecución

```powershell
python -B evaluacion/regresion_recuperacion/ejecutar.py
```

Runner y casos: [ejecutar.py](ejecutar.py) y [casos.json](casos.json) en esta carpeta.

- Opciones: `--contenido contenido` (ruta del corpus) y `--salida .local/regresion-recuperacion/actual.json` (ruta del informe de salida).
- Estado actual (corrección de palabras partidas, 2026-11-16): SUA-02 está resuelto, por lo que todas las 14 referencias son obligatorias en ambos modos; el modo normal también retorna 1 si se pierde cualquier referencia (estado y capturas comprobados por Codex). Véase «Última corrección».

No regresión y cobertura completa son criterios distintos: pasar sin regresión no equivale a recuperar todo el gold.

Suite del evaluador:

```powershell
python -m unittest discover -s evaluacion/regresion_recuperacion -p "test_*.py" -v
```

## Resultados históricos (antes de la corrección de palabras partidas)

| Condición | En contexto (de 14) | Primarias (de 14) | Fallos |
| --- | --- | --- | --- |
| original46 | 13/14 | 12/14 | SUA-02 |
| original149 | 13/14 | 12/14 | SUA-02 |
| propuesta46 (IDF local) | 11/14 | 10/14 | REBT-01, REBT-02, SUA-02 |
| propuesta149 (IDF local) | 11/14 | 10/14 | REBT-01, REBT-02, SUA-02 |
| final149 (motor original restaurado) | 13/14 | 12/14 | SUA-02 |

Notas de evidencia:

- En los brazos con propuesta, REBT-01 (p. 103) y REBT-02 (p. 109) quedan fuera de contexto y primarias; el original las mantiene en ambas colecciones. Propuesta descartada y revertida: el motor restaurado es idéntico por SHA al previo, y la igualdad de texto y páginas en original149 está comprobada.
- Consulta amplia (REBT-09, sin referencia de página): primarias [107, 103] en original46 frente a [107, 109] en original149, propuesta y final. p. 103 (ITC-BT12: definición, límites y componentes de instalaciones de enlace) y p. 109 (inicio ITC-BT14: LGA conecta CGP con centralización) son pertinentes; el cambio no demuestra pérdida semántica.
- Condiciones de locales (contadores): gold en páginas 115–117 (REBT-05 a REBT-08), emplazamiento y condiciones de concentraciones.
- Las dos referencias que no son primarias son SUA-02 y SUA-03; esta última sí aparece en contexto.
- Comparación por colección: no se exige igualdad de puntuaciones entre original46 y original149; son colecciones distintas. `GlobalIDF` por sí solo no es bug: el IDF global es diseño declarado; la repetibilidad se exige dentro de la misma colección y el aislamiento por candidatos/filtros.

## Verificación de integridad

El verificador coteja SHA-256 exacto, ruta, página, edición y literal, y registra por página; solo acepta la ausencia de espacios finales al final global por el comportamiento `rstrip` ya existente en el adaptador; no se permite recorte sustantivo. La primera ejecución del evaluador produjo 6 falsos fallos de integridad por esa presentación; la comprobación real final de Codex verifica integridad OK: 15 estados ok, 13/14 del gold en contexto y 12/14 primarias, 0 pérdidas nuevas, texto y páginas iguales a original149, con 6 ajustes de whitespace terminal reportados; no fue cambio de motor. Resultado: exit 0 en modo normal y exit 1 con `--estricto` exclusivamente por SUA-02 pendiente.

## Última corrección (2026-11-16): palabras partidas — estado actual

Estado vigente tras la corrección de `tokenizar` en `acceso.py` (pequeño cambio de ~15 líneas, solo en tokenizar; sin aritmética IDF ni pesos nuevos y sin tocar el texto literal fuente). Lo de "motor original restaurado / sin cambios" corresponde a la comparación de filtrado anterior; esta corrección sí modifica el motor.

- Causa de SUA-02: el PDF oficial parte palabras a fin de línea («Vivien-\nda» en p. 36) y el tokenizador las trataba como fragmentos. La corrección une las letras a ambos lados del guion + salto (LF/CRLF, con espacios horizontales) antes de puntuar; solo letras, no números.
- Comprobación real de Codex: 89 pruebas unittest en verde (19 tests + 19 piloto SUA + 33 HTTP + 10 herramientas + 8 del evaluador), 4 nuevas en [test_palabras_partidas.py](../../experimentos/http-local/tests/test_palabras_partidas.py).
- Batería original ([casos.json](casos.json)): contexto 13/14 → **14/14**; primarias 12/14 sin cambiar (SUA-02 entrega la p. 36 como auxiliar en contexto, no primaria). Cero pérdidas de referencias previas; integridad OK.
- Fixture adicional independiente del ranking ([casos-sua-residencial.json](casos-sua-residencial.json)): 5/6 → **6/6** en contexto y primarias. Conjunta: 21 casos, 19 consultas distintas (2 controles repetidos). Sin independencia estadística ni dictamen de calidad global.
- Gold intacto: ni consultas ni referencias de página cambiadas por resultados; SUA-02 pasa de fallo conocido a guarda obligatoria (`fallo_conocido=false`, esperado 14/14).
- Informe nuevo de Codex: [resultados-sua-2026-11-16.json](resultados-sua-2026-11-16.json); [resultados-2026-11-16.json](resultados-2026-11-16.json) queda como histórico sin sobrescribir.
- Límite: sin consumo API medido; los guiones compuestos reales a fin de línea también se unen en la vista de búsqueda (no altera el texto entregado).

Comandos (modo estricto para ambas fixtures):

```powershell
python -B evaluacion/regresion_recuperacion/ejecutar.py --estricto
python -B evaluacion/regresion_recuperacion/ejecutar.py --fixture evaluacion/regresion_recuperacion/casos-sua-residencial.json --estricto --salida .local/regresion-recuperacion/actual-sua-residencial.json
```

## Corrección de recuperación territorial (2026-11-16): señal de pasaje

Tras la corrección de palabras partidas, una segunda corrección de recuperación añade señal de pasaje en la vista de puntuación (mejor pasaje por operación y predicado definitorio, sin IDs, páginas ni regiones fijadas; ranking primario BM25 intacto). La suite territorial pasa de 18/21 a 21/21 en contexto (17/17 autonómicas, 4/4 Málaga) y la conjunta de 48 casos y 47 referencias llega a 47/47 en contexto con 38/47 primarias, sin pérdidas previas; los tres lotes territoriales y el fixture de contraste retornan exit 0 en `--estricto`. Detalle, tabla antes/después y repro: [territorial/README.md](territorial/README.md) · Informe de Codex: [territorial/resultados-correccion-2026-11-16.json](territorial/resultados-correccion-2026-11-16.json) · Changelog: [../../changelog/2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md](../../changelog/2026-11-16-pedenry-evaluacion-correccion-recuperacion-territorial.changelog.md).

## Fallo conocido (historia, resuelto el 2026-11-16)

SUA-02 (anchura libre en zonas comunes de Residencial Vivienda, p. 36) fallaba en todos los brazos de la comparación anterior. Era preexistente y visible: no se ocultó ni se ajustó el gold. Estado tras la corrección de palabras partidas: SUA-02 cubre la p. 36 en contexto (auxiliar) y `--estricto` retorna 0; véase «Última corrección».

## Límites

- La presencia de la página en contexto no certifica respuesta completa ni fidelidad de toda la extracción; no se certifica calidad global ni vigencia.
- Sin medición de tokens API ni de ahorro económico.
- Muestra de dos documentos (REBT y DB-SUA): no prueba calidad equivalente en el corpus ampliado.
- Comprobaciones verificadas por Codex: 85 pruebas en verde (19 tests + 19 piloto SUA + 29 HTTP + 10 herramientas + 8 del evaluador). Nuevas en esta revisión: 23 (15 de motor/adaptador + 8 del evaluador), con subTests negativos incluidos. El total figura en [resultados-2026-11-16.json](resultados-2026-11-16.json). 6 pruebas HTTP con socket requirieron salir de la sandbox por WinError 10013 y luego pasaron.

## Enlaces

- Informe depurado con casos y SHA: [resultados-2026-11-16.json](resultados-2026-11-16.json)
- Test de estabilidad: [../../experimentos/http-local/tests/test_estabilidad_recuperacion.py](../../experimentos/http-local/tests/test_estabilidad_recuperacion.py)
