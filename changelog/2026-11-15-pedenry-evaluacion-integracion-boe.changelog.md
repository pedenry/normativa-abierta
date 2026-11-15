# 2026-11-15 — pedenry — Evaluación de integración BOE

- **Fecha ISO:** 2026-11-15T01:40:50+01:00
- **Usuario GitHub:** pedenry (verificado)
- **Solicitante:** Pedro
- **Ejecución:** Codex para shell y revisión; OpenCode con perfiles `fuentes-normativas`, `recuperacion-normativa` y `evaluacion-normativa` (nan/glm5.3-flash; variante low en encargos finales).
- **Commit base observado:** 24ca346. Sin commit nuevo, push ni despliegue. Integración local completada.

## Resultado

- 15 PDF nuevos del BOE: 14 consolidados informativos más el Código Estructural original de 2021-08-10.
- Adición: 2742 páginas. Corpus resultante: 46 documentos, 4324 páginas, 5775 segmentos.
- Fuentes, ediciones, hashes y PDF byte idénticos a lo observado.
- Validación registrada en [`contenido/validacion/ampliacion-boe-2026-11-15.json`](../contenido/validacion/ampliacion-boe-2026-11-15.json); derechos en [`licencias/ampliacion-boe-2026-11-15.json`](../licencias/ampliacion-boe-2026-11-15.json).
- Segmentación: los segmentos nuevos corresponden a páginas físicas sin jerarquía verificada; etiquetas impresas a null.
- Avisos de fuente propagados a contexto y JSON; dedupe y presupuesto final intactos. Edición REBT 1900-01-01 registrada como `version_no_disponible`, sin páginas.

## Comprobaciones reales (Codex)

- 33 pruebas pasadas: 19 del piloto más 14 HTTP (6 sintéticas nuevas sobre avisos, presupuesto, edición y distribución).
- 15 consultas reales con adaptador por defecto, una por fuente nueva, todas correctas en hash, edición, páginas y avisos; presupuesto 30000, máx. 2. Son pruebas de recuperación, no de evaluación legal ni de respuestas de modelo.
- Edición REBT 1900-01-01: `version_no_disponible`, sin páginas (comportamiento esperado).
- Regresión SUA 2022-06-14: mismas 9 páginas antes y después de la integración.
- CLI de ejemplo (REBT versión 2025-09-03, presupuesto 20000, máx. 3): correcta, 9 páginas, 6647 tokens proxy.
- Idempotencia exacta verificada sobre corpus y copias temporales; un hash erróneo fue rechazado en preflight sin tocar el corpus.

## Cobertura y contrastes

- Entradas anteriores intactas: verificación por comparación JSON y prefijo de bytes del índice; 0 páginas nuevas vacías; hashes verificados; sin rutas personales en informes públicos.
- Cotejo visual selectivo limitado a 2 páginas (Código Estructural p. 100 y REBT p. 102). Está lejos de una revisión técnica completa; se conserva el texto girado con layout degradado.

## Límites

- Tablas, fórmulas, notas y figuras no cotejadas globalmente.
- Sin OCR; ámbito, disposiciones transitorias y vigencia pendientes de verificación.
- Correcciones del Código Estructural no incorporadas.
- Sin validación humana; sin ahorro medido ni uso de API medido.
- Visor estático no regenerado ni publicado.
- Los recuentos de texto son proxy de consumo; muestras puntuales, no representativas del corpus completo.
