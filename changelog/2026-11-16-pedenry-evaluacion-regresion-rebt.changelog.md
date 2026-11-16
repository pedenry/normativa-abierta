# 2026-11-16 — pedenry — evaluación: revisión de recuperación REBT/SUA y ampliación de pruebas

## Ámbito

Revisión de la regresión de recuperación REBT/SUA y ampliación de las pruebas del evaluador. Resultado: motor original conservado exacto (idéntico por SHA) y variante de IDF local descartada. Sin commit, sin despliegue y sin corpus modificado.

## Historia de la revisión

1. Motor original idéntico por SHA al anterior (comprobado por Codex).
2. Suite fija: 15 consultas naturales (8 precisas REBT, 1 amplia, 6 SUA), 14 con gold de página física. La referencia de páginas es independiente del ranking y se mantuvo sin cambios durante la comparación; ningún gold se ajustó para hacer pasar un brazo.
3. Propuesta de IDF local: estabilizaba el ranking pero dejaba fuera de contexto y primarias REBT-01 (p. 103) y REBT-02 (p. 109). Descartada y revertida.
4. Consulta amplia (REBT-09): primarias [107, 103] en original46 frente a [107, 109] en el resto de brazos. Ambas páginas pertinentes (p. 103: ITC-BT12, definición y componentes de instalaciones de enlace; p. 109: inicio ITC-BT14, LGA conecta CGP con centralización): el cambio no demuestra pérdida semántica.
5. Condiciones de locales (contadores): gold en páginas 115–117.
6. SUA-02 (anchura en zonas comunes Residencial Vivienda, p. 36): falla en todos los brazos; se reporta, no se oculta.
7. `GlobalIDF` por sí solo no es bug: el IDF global es diseño declarado; se exige repetibilidad dentro de la misma colección y aislamiento por candidatos/filtros.

## Decisión rechazada (conservada con métricas)

- Propuesta: IDF local sobre candidatos elegibles para estabilizar el ranking.
- Métricas: 11/14 en contexto y 10/14 primarias en sus brazos (REBT-01, REBT-02 y SUA-02 fuera), frente a 13/14 y 12/14 del original en ambas colecciones.
- Reversión completa: motor restaurado idéntico por SHA (`acceso.py` b7943f30…, `adaptador_contexto.py` 0e524472…) e igualdad de texto y páginas en original149 comprobada. Los resultados de la propuesta se conservan como evidencia en el informe.

## Ajuste de criterio

- Versión: 2 — Fecha: 2026-11-16 — Razón: la versión inicial exigía por error igualdad de ranking/puntuaciones entre colecciones distintas, incluso con IDF global declarado; colecciones distintas no son comparables en puntuación. — Efecto: comparación por colección, repetibilidad dentro de la misma colección y aislamiento de candidatos; la referencia de páginas de los 15 casos no cambió para hacer pasar ningún brazo.

## Verificador de integridad

- El verificador coteja SHA-256 exacto, ruta, página, edición y literal, y registra por página; solo acepta la ausencia de espacios finales al final global por el comportamiento `rstrip` ya existente en el adaptador; no se permite recorte sustantivo.
- La primera ejecución del evaluador produjo 6 falsos fallos de integridad por esa presentación. Comprobación real final verificada por Codex: integridad OK, 15 estados ok, 13/14 del gold en contexto, 12/14 primarias y 0 pérdidas nuevas; texto y páginas iguales a original149, con 6 ajustes de whitespace terminal reportados; no fue cambio de motor. Resultado: exit 0 en modo normal y exit 1 con `--estricto` exclusivamente por SUA-02 (fallo previo pendiente).

## Comprobaciones

- 77 pruebas base verificadas por Codex: 19 tests + 19 piloto SUA + 29 HTTP (15 nuevas) + 10 herramientas; 6 HTTP con socket de localhost requirieron salir de la sandbox por WinError 10013 y la repetición autorizada pasó.
- Controles del evaluador (`test_ejecutar.py`): 8/8 en verde, verificados por Codex (incluye subTests negativos). Total verificado: 85 = 19 tests + 19 piloto SUA + 29 HTTP + 10 herramientas + 8 del evaluador; nuevas en esta revisión: 23 (15 de motor/adaptador + 8 del evaluador). El total del informe JSON ya es 85.
- Comando de la suite del evaluador: `python -m unittest discover -s evaluacion/regresion_recuperacion -p "test_*.py" -v`.

## Inventario final

- `experimentos/http-local/tests/test_estabilidad_recuperacion.py` (con las 15 pruebas nuevas).
- `evaluacion/regresion_recuperacion/ejecutar.py`, `evaluacion/regresion_recuperacion/casos.json` y `evaluacion/regresion_recuperacion/test_ejecutar.py`.
- `evaluacion/regresion_recuperacion/resultados-2026-11-16.json` (informe depurado).
- `evaluacion/regresion_recuperacion/README.md` y `changelog/2026-11-16-pedenry-evaluacion-regresion-rebt.changelog.md`.
- Motor original conservado exacto; variante descartada. Sin commit, despliegue ni corpus modificado.

## Fallos y límites

- SUA-02 (p. 36) falla en todos los brazos: preexistente, visible, no oculto; solo bloquea con `--estricto`. SUA-03 sí aparece en contexto pero no como primaria.
- La presencia de página no certifica respuesta completa ni fidelidad de la extracción; sin dictamen de vigencia o cumplimiento.
- Sin medición de tokens API ni ahorro económico; muestra de dos documentos, no extrapolable al corpus ampliado.
