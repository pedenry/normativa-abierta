---
fecha: 2026-11-09T11:15:10+01:00
zona: Europe/Madrid
titulo: Prueba de Render para consulta normativa
tipo: changelog
usuario_github_verificado: pedenry (id 35270581), verificado por Codex
solicitante: pedenry
ejecutor: Codex (UI, HTTPS y ChatGPT); registros y adaptación preparados con OpenCode y NaN
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash
autor_git_tecnico: Codex
commits: base inicial fc8c79a9a84da79b674352f989331d603fd28581; cambio desplegado 8c8867d6e8a3875a68aefdaec9dba612d3807012; el commit propio se consulta en el historial
estado: desplegado en Render Free; HTTPS verificado; chat sin /leer y causa interna no comprobada
---

## Despliegue

Tras el login del usuario, en un workspace personal de Render y sin servicio previo con ese nombre, se creó `normativa-abierta` como Web Service Free de 0 $/mes, 0,1 CPU y 512 MB, región Frankfurt (EU Central), Python 3.12.14 con tiktoken 0.14.0, fuente Public Git Repository `pedenry/normativa-abierta` rama `main`, health `/`, sin OAuth a GitHub, facturación, plan pago ni datos privados.

URL: https://normativa-abierta.onrender.com/. Primer Live a las 11:07:41+01:00 sobre el commit fc8c79a, con 31 documentos y 3033 filas.

## Verificación HTTPS

Sin sesión se comprobaron la raíz, `/buscar` ordinaria y por edición exacta, `/leer` en las páginas 24 y 25 de DB-SI edición 2025-03-04 con texto y SHA iguales al corpus y recursos p24/p25, el 404 `version_no_disponible` ante una edición anterior a junio de 2022 sin sustituto, y el 404 de `/estatico`.

La primera búsqueda ordinaria tardó 14,50 s; las lecturas, unos 0,13–0,17 s.

## ChatGPT

En un chat nuevo de ChatGPT Gratis con Búsqueda en Internet, con el mismo caso ficticio ya verificado desde el repositorio, las trazas muestran una `/buscar` HTTP 200 de 1402 tokens cl100k de cuerpo y 46 de ruta, y cero `/leer`. El chat identificó DB-SI, versión, tabla y páginas, informó un fallo de acceso y no acreditó condiciones.

Se reprodujo un 200 con el enlace limpio y un 400 con el mismo enlace mostrado con `utm_source=chatgpt.com`. No se afirma que ese parámetro causara el fallo de navegación del modelo.

## Ajuste desplegado

OpenCode modificó `experimentos/http-local/servicio_publico.py` para admitir exclusivamente `utm_source=chatgpt.com` una vez en `/buscar` y `/leer`, ignorándolo para la lógica, y para construir `href` absolutos desde `RENDER_EXTERNAL_URL` validada de Render, nunca desde el `Host` enviado. En local se conservan relativos. Se verificaron 14 enlaces absolutos/relativos, el rechazo de variantes inválidas, la igualdad de cuerpo y el 404 histórico.

El commit 8c8867d incluye el intent y el código; el push lo hizo pedenry. El despliegue manual de latest en el mismo servicio quedó Live a las 11:15:10+01:00.

HTTPS repitió sólo los puntos afectados: 200 con UTM y enlaces absolutos, lectura p24/p25 con SHA intacto, histórico y estático 404. La segunda búsqueda ordinaria tardó 13,11 s (exacta 12,953 s) y las lecturas 0,125 s cada una; los cuerpos de QA de `/buscar` más 2 `/leer` sumaron 5.155 tokens cl100k y las rutas 105, no la lectura del chat.

Un segundo chat nuevo, con la misma pregunta y configuración visible, hizo una `/buscar` HTTP 200 trazada (4.326 bytes, 1.556 tokens de cuerpo y 46 de ruta, cero `/leer`); volvió a localizar edición y página e informó un error de acceso sin dar la condición. La causa interna no está comprobada.

Claude web redirigió a reautenticación y el escritorio no presentó una sesión utilizable; no se cambió de cuenta.

## Transparencia

La prueba directa anterior desde repositorio y Pages sí acreditó la tabla 3.1, nota (1), en las páginas físicas 24–25. Esta prueba de Render no acredita condiciones por chat ni ahorro frente a esa vía, pues no se midieron tokens directos ni internos. Referencias públicas: https://pedenry.github.io/normativa-abierta/site/pagina/db-si-oficial-2025-03-04-0a2e78cd6247__p0024.html y la equivalente `__p0025.html`.

Se mantiene la alternativa voluntaria y no se declara necesario un buscador. El plan Free pausa tras 15 min sin tráfico y puede tardar ~1 min en despertar: https://render.com/docs/free y https://render.com/docs/environment-variables.
