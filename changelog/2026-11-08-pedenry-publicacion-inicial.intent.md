---
fecha: 2026-11-08T21:51:03+01:00
zona: Europe/Madrid
titulo: Publicación inicial de Normativa Abierta
tipo: intent
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex mediante GitHub CLI; autenticación de push con cuenta pedenry
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: pendiente del primer commit y de la publicación
estado: preparación local; sin push ni despliegue desde esta fase
---

## Propósito

Publicar una base de normativa de edificación más allá del CTE, con cobertura real declarada y fuentes trazables. El paquete estable contiene 31 PDF redistribuibles y su visor estático; no incluye los 50 PDF privados ni las 7 fichas HTML restantes.

## Alcance

- 31 PDF: 15 disposiciones legales (Parte I, 11 DB, RD 314/2006, RITE y RSCIEI) y 16 guías con permiso editorial.
- 1582 páginas y 3033 segmentos publicables.
- Estructura `index.html` → materia → documento → apartado/página; corpus, índices, licencias y changelog.
- ZIP estable SHA256 `5425a80cf69b7d467b6670eb235364b5e23bc45a93747ee508681a2fe2f35682`, 16110 archivos, 405195851 bytes.

## Criterios y exclusiones

No se publican respuestas esperadas, tests, herramientas internas, rutas privadas, código HTTP experimental ni el índice experimental. La publicación no se atribuye a NaN ni a Codex como persona. La fecha y el usuario GitHub están verificados; la identidad Git local prevista para el commit es técnica, no una cuenta humana verificada. Los pasos históricos de modelos individuales no confirmados no se atribuyen.

## Estado

Preparación documental local. La URL de Pages está prevista como https://pedenry.github.io/normativa-abierta/ y queda pendiente de verificación del despliegue. No se declara éxito de publicación.

## Resultado observado

Publicación verificada posteriormente: commit de contenido `d6424d99a5e406c002bc3aa5360ba20a306b6788`, Pages activo en https://pedenry.github.io/normativa-abierta/ (workflow SUCCESS `42523296620`, pusher real `pedenry`). El detalle y los pendientes están en el handoff.
