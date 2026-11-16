# 2026-11-16 — pedenry — Evaluación de ampliación territorial

- **Fecha ISO:** 2026-11-16T11:04:28+00:00
- **Ejecución:** Codex para shell y revisión; OpenCode con perfiles `fuentes-pdf-territoriales`, `integracion-territorial` y `evaluacion-normativa` (nan/glm5.3-flash).
- **Usuario GitHub:** pedenry
- **Commit base:** sin commit nuevo, push ni despliegue. Integración local.

## Resultado

- 103 PDF territoriales integrados en local: 102 normas autonómicas de 17 CCAA (BOE) más 1 ordenanza municipal de Málaga (BOP 2025-12-29, art. 13 TRLPI).
- Adición: 5357 páginas. Corpus resultante: 149 PDF distribuibles, 9681 páginas, 11132 segmentos.
- Integridad: 103 hashes SHA-256 y 5357 páginas verificadas; 0 páginas vacías; idempotencia real pasada; cambios ajenos de ingesta conservados.
- Validación en [`contenido/validacion/territorial-2026-11-16-verificacion.json`](../contenido/validacion/territorial-2026-11-16-verificacion.json); derechos en [`licencias/territorial-2026-11-16.json`](../licencias/territorial-2026-11-16.json).
- Descarga de candidatos: 424 URLs, 345 ok, 342 SHA únicos, 17 errores, 62 pendientes por límite de tanda (2 GiB, proyectos en información pública). Los 345 descargados no equivalen a 345 normas ni a cobertura completa. Disco: 106 copias idénticas unificadas, 107 MiB recuperados sin eliminar PDF únicos; reserva de 128 MiB en el descargador.
- Pruebas: 38 pasadas (19 territoriales, 19 previas), sin red. 3 consultas de edición correctas.
- Muestra visual por IA en 2 páginas: BOA-d-2014-90410 p. 18 física y MUN-MALAGA-OMLU-2025 p. 1 física (impresa 70).

## Límites

- Vigencia, ámbito aplicable y régimen transitorio pendientes por caso; fidelidad de extracción sin cotejo integral.
- Málaga sin consolidar; Madrid no descargado por robots; Zaragoza MIAU pendiente de separar anuncios.
- Revisión automática y por IA, no humana ni dictamen jurídico. Sin ahorro de tokens medido.
- Visor no regenerado ni publicado.
