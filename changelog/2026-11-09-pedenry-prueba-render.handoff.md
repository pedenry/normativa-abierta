---
fecha: 2026-11-09T11:15:10+01:00
zona: Europe/Madrid
titulo: Prueba de Render para consulta normativa
tipo: handoff
usuario_github_verificado: pedenry (id 35270581), verificado por Codex
solicitante: pedenry
ejecutor: Codex (UI, HTTPS y ChatGPT); registros y adaptación preparados con OpenCode y NaN
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash
autor_git_tecnico: Codex
commits: base inicial fc8c79a9a84da79b674352f989331d603fd28581; cambio desplegado 8c8867d6e8a3875a68aefdaec9dba612d3807012; el commit propio se consulta en el historial
estado: Live en Render Free; HTTPS verificado; chat sin /leer y causa interna no comprobada
---

## Estado real

- Servicio `normativa-abierta` en https://normativa-abierta.onrender.com/, Web Service Free de 0 $/mes, 0,1 CPU y 512 MB, región Frankfurt (EU Central), Python 3.12.14 con tiktoken 0.14.0, fuente Public Git Repository `pedenry/normativa-abierta` rama `main`, health `/`, sin OAuth a GitHub, facturación, plan pago ni datos privados.
- Primer Live a las 11:07:41+01:00 sobre fc8c79a, con 31 documentos y 3033 filas. Tras el ajuste, Live a las 11:15:10+01:00 sobre 8c8867d.

## Verificación HTTPS

Sin sesión: raíz, `/buscar` ordinaria y por edición exacta, `/leer` páginas 24 y 25 de DB-SI 2025-03-04 con texto y SHA iguales al corpus y recursos p24/p25, 404 `version_no_disponible` para una edición anterior a junio de 2022 sin sustituto, y `/estatico` 404. La primera búsqueda tardó 14,50 s y las lecturas 0,13–0,17 s; tras el ajuste, la segunda búsqueda 13,11 s (exacta 12,953 s) y las lecturas 0,125 s.

## Ruta de chat

- ChatGPT Gratis, chat nuevo con Búsqueda en Internet y el mismo caso ficticio ya verificado desde el repositorio: una `/buscar` HTTP 200 trazada (1402 tokens cl100k de cuerpo y 46 de ruta), cero `/leer`; identificó DB-SI, versión, tabla y páginas, informó fallo de acceso y no acreditó condiciones.
- El enlace limpio reprodujo 200 y el mismo enlace mostrado con `utm_source=chatgpt.com` dio 400. No se atribuye el fallo de navegación del modelo a ese parámetro.
- Segundo chat nuevo, misma pregunta y configuración visible: una `/buscar` HTTP 200 (4.326 bytes, 1.556 tokens de cuerpo y 46 de ruta), cero `/leer`; localizó edición y página e informó error de acceso sin dar la condición. La causa interna no está comprobada.
- Claude web redirigió a reautenticación y el escritorio no presentó sesión utilizable; no se cambió de cuenta.

## Cambio desplegado

OpenCode adaptó `experimentos/http-local/servicio_publico.py` para admitir exclusivamente `utm_source=chatgpt.com` una vez en `/buscar` y `/leer`, ignorándolo para la lógica, y para construir `href` absolutos desde `RENDER_EXTERNAL_URL` validada de Render, nunca desde el `Host` enviado; en local se conservan relativos. Se verificaron 14 enlaces absolutos/relativos, rechazo de variantes inválidas, igualdad de cuerpo y 404 histórico. El commit 8c8867d incluye el intent y el código; el push lo hizo pedenry y el despliegue manual quedó Live a las 11:15:10+01:00.

## Límites y siguiente estado

No hay `/leer` en las trazas de chat y la causa interna no está comprobada. Esta prueba de Render no acredita condiciones por chat ni ahorro frente a la vía directa; no se midieron tokens directos ni internos. La prueba anterior desde repositorio y Pages sí acreditó la tabla 3.1, nota (1), en las páginas físicas 24–25. Referencias: https://pedenry.github.io/normativa-abierta/site/pagina/db-si-oficial-2025-03-04-0a2e78cd6247__p0024.html y la equivalente `__p0025.html`.

Se mantiene la alternativa voluntaria; no se declara necesario un buscador. El plan Free pausa tras 15 min sin tráfico y puede tardar ~1 min en despertar: https://render.com/docs/free y https://render.com/docs/environment-variables.
