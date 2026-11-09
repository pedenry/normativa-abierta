---
fecha: 2026-11-09
zona: Europe/Madrid
titulo: Servicio HTTPS público de consulta
tipo: intent
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex para instalación, túnel y prueba externa; preparación local
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado
commits: base local 3dbdc56c98872e2cf42ae3f6a55cc022b7df93d6; baseline 43 casos 756.344/3.201.561 cl100k
estado: preparación local; sin túnel, prueba HTTPS/chat ni despliegue
---

## Propósito

Preparar una entrada pública aislada y read-only para consultar el corpus público
desde HTTPS y chats que sólo pueden abrir URLs. Debe reutilizar `/buscar` y `/leer`
del runtime HTTP local, conservar consultas, documentos, versiones, SHA, texto y
ámbito, y enlazar las fuentes estables de GitHub Pages.

## Alcance

- Adaptador `experimentos/http-local/servicio_publico.py` sobre `http_consulta.Handler`.
- Sólo loopback por defecto; túnel Quick Tunnel oficial para una prueba limitada.
- Rutas GET explícitas: `/`, `/buscar`, `/leer`, `/robots.txt`; `/estatico` bloqueado.
- Límites de target, consulta, página, campos, socket y concurrencia.
- Validación de los 31 `doc.json` con `distribute: true` y de las referencias del índice.
- Evidencia opt-in con identificador `prueba` alfanumérico; sin query, texto, IP ni cookies.

## Exclusiones

No se compra ni activa ningún plan, no se despliega, no se publica la URL temporal en
README ni visor y no se sirven archivos arbitrarios, admin, secretos ni APIs externas.
No se modifican `corpus/`, visor, índice ni `acceso.py`.

## Estado

Preparación local. No se ha ejecutado el túnel, ni una prueba HTTPS/chat, ni un push.
El baseline local de referencia es 43 casos, 756.344/3.201.561 tokens cl100k.
