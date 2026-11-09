---
fecha: 2026-11-09T01:53:31+01:00
zona: Europe/Madrid
titulo: Servicio HTTPS público de consulta
tipo: handoff
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry; cuenta autenticada para push
ejecutor: Codex (verificaciones, despliegue temporal y prueba ChatGPT); OpenCode con NaN (adaptador, guía y registros)
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash
autor_git_tecnico: Codex <codex@local.invalid>
commits: base 3dbdc56c98872e2cf42ae3f6a55cc022b7df93d6; el commit propio se consulta en el historial
estado: verificado en local y HTTPS temporal; pendiente host estable con proxy TLS y sesión de chat
---

## Estado observado

- El primer encargo de OpenCode/NaN agotó pasos sin archivos. La continuación escribió el intent y el adaptador; el ajuste de límites y evidencia quedó verificado, sin fallback.
- No se identificó host persistente autorizado: el repositorio sólo usa Pages y la búsqueda en GCP no encontró un proyecto correspondiente.
- El adaptador quedó en `experimentos/http-local/servicio_publico.py` y la guía en `experimentos/http-local/ALOJAMIENTO.md`. Sólo sirve `GET /`, `/buscar`, `/leer` y `/robots.txt`, con 31 documentos y 3033 filas, validación de `distribute` y rutas, 8 conexiones, timeout de 15 s, target de 2048 bytes y `q` de 400. No hay archivos arbitrarios ni trazas de excepciones.
- Cloudflare Quick Tunnel oficial 2026.10.7, con SHA del release verificado e instancia aislada al loopback. URL histórica, ya retirada y no activa: https://frontpage-seattle-nissan-sheffield.trycloudflare.com. Estuvo activa desde las 01:50:39 hasta las 01:53:31 (unos 2m51s); se detuvieron servidor y túnel y el cierre dio un 530 externo. Fuente: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
- HTTPS sin sesión validó 9 controles de rutas y límites, 8 enlaces estables, el 404 histórico sin reemplazo, la edición exacta y texto más SHA. Hubo 119 solicitudes 200 y 103 lecturas; 8/8 críticos documentales y 8/8 de condiciones, con legacy separado 2/8.
- La comparación de 8 búsquedas idénticas y 103 lecturas idénticas sólo difirió en URL fuente y referencias; no se repitió la batería de 43 por paridad. Tres trazas se contrastaron con cuerpo y target reales.
- cl100k textual: 172.550 / 682.230 (−74,71 %; mediana 0,253027×, peor 0,500638×), incluyendo cuerpo, ruta/consulta y entrada según protocolo. El mismo subconjunto local había medido 155.205; la diferencia es del envoltorio y referencias. Los 43 históricos (−76,4 %) se informan aparte y no se extrapolan.
- Los SHA oficiales de DB-SI (2025-03-04) y DB-SE-F (2019-12-20) coinciden con el corpus. Fuentes: https://www.codigotecnico.org/pdf/Documentos/SI/DBSI.pdf y https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-F.pdf.

## Chat real

- ChatGPT web, sesión personal existente con plan Gratis, chat nuevo por modalidad. El control usó 2 archivos de texto completo extraído (69.706 + 45.377 = 115.083 tokens del archivo, no del chat), las mismas 2 preguntas y fichas ficticias SI-01 y T-02 ampliadas con la nota (1), y la misma configuración inicial automática.
- El control acertó ocupaciones, excepciones, nota SI, cálculo y nota SE-F; confundió página impresa y física en SE-F (14 frente a 18) y citó sólo 25 para ocupaciones más nota SI (24–25).
- La ruta por URL no quedó probada: ChatGPT reportó 403 para ambos enlaces y ni la búsqueda ni `/leer` marcados llegaron al origen. Un chat nuevo con búsqueda web explícita también informó acceso denegado: 0 peticiones marcadas en los dos intentos. No se atribuye el 403 a una capa concreta.
- Claude web pidió autenticación y el escritorio no presentó una sesión utilizable; no se creó cuenta nueva.
- El ahorro en chat por enlace y la preservación con ruta de chat NO están comprobados. No se midieron multimodal, razonamiento ni imágenes, y no se publican prompts, respuestas, chats ni logs.

- Control local: un recurso tabla JSON existente respondió HTTP 200; la 9.ª conexión concurrente devolvió 503 y el servicio se recuperó después. La comprobación CLI con servidor simulado pasó loopback por defecto y `0.0.0.0:10000` sin abrir sockets.

## Comparación con adjunto (calidad, no enlace)

- 5 cuerpos JSON exactos del servicio HTTPS (2 búsquedas + 3 lecturas físicas 24–25/18) reproducidos por SHA256 del cuerpo observado, unidos por 8 bytes de separadores y sin respuestas esperadas: 26.329 bytes y 8.723 tokens cl100k en adjunto frente a 115.083 de textos completos (−92,42 % del texto facilitado; sin prompts, razonamiento ni medidor interno). SHA del adjunto: 05cdcf33b5631dfde67367ced4ae850a8f028f13145621f4b451d633a6ede685.
- Nuevo chat real, misma sesión ChatGPT Gratis y configuración automática, mismas preguntas ficticias y sólo cambio de fuente a adjunto. El modelo exacto de backend no es visible; se mantuvo la configuración visible automática. Resultado 2/2: nota y cálculo correctos, con ocupaciones/excepciones, extinción automática, nota extraordinaria por categorías, ediciones y citas literales válidas. Páginas físicas correctas DB-SI 24–25 y DB-SE-F 18 (impresa 14).
- El control completo había confundido la página SE-F y citado sólo 25 para SI. Es calidad con contexto servido ADJUNTO, no recuperación por enlace; no hubo consumo interno observado y el 403 permanece. No se publican adjunto, respuestas del chat ni prompts.

## Render candidato

Render Native Python queda preparado, no desplegado ni probado allí. La creación del Web Service Free ya está autorizada; el panel oficial https://dashboard.render.com/login-next, comprobado en Chrome, pide iniciar sesión: ése es el requisito externo, con cuenta propia y sin compartir credenciales, en un workspace sin medio de pago. Alternativa: un host Python ya autorizado con proxy TLS. URL estable `*.onrender.com`; Python 3.12 (`PYTHON_VERSION=3.12.14`), build `python -m pip install tiktoken==0.14.0`, start `python -B experimentos/http-local/servicio_publico.py --host 0.0.0.0 --port "$PORT"` y health `GET /`; sin secretos, disco persistente, OAuth a GitHub ni método de pago. Documentación verificada el 2026-11-09: https://render.com/docs/web-services y https://render.com/docs/free. No hay garantía de acceso del chat.

## Pendiente

1. Disponer de un host Python detrás de un proxy TLS con URL estable y de una sesión de chat capaz de recuperar esa URL, o crear el Web Service Free de Render iniciando sesión en el panel oficial https://dashboard.render.com/login-next con cuenta propia, en un workspace sin medio de pago; después repetir ambas preguntas de enlace y comprobar las trazas. No se afirma publicación futura observada.
2. Decidir la persistencia sin comprar ni activar planes; el servicio y el túnel actuales están detenidos.
3. Mantener la URL temporal retirada y fuera del README raíz y del visor.
4. Codex verificará el nuevo CLI `--host` localmente; no se atribuye despliegue futuro en Render.

## Límites

No se atribuye el 403 de ChatGPT a una capa concreta. No se midieron multimodal, razonamiento ni imágenes. No se publican prompts, respuestas, chats ni logs. El ahorro de 43 casos no se extrapola a los 8 medidos por HTTPS. El commit propio no se declara aquí; se consulta en el historial sobre la base 3dbdc56c98872e2cf42ae3f6a55cc022b7df93d6.
