---
fecha: 2026-11-09
zona: Europe/Madrid
titulo: Prueba de Render para consulta normativa
tipo: intent
usuario_github_verificado: pedenry (id 35270581), verificado por Codex
solicitante: pedenry
ejecutor: Codex para despliegue y pruebas; preparación de texto OpenCode con NaN
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash
commits: base main fc8c79a9a84da79b674352f989331d603fd28581; el commit propio se consulta en el historial
estado: intención autorizada; pendiente de login en Render
---

## Propósito

Probar la hipótesis del intent de un único URL para consulta normativa mediante un
Render Web Service Free creado desde el repositorio público, rama `main`, con los
comandos ya registrados en `experimentos/http-local/ALOJAMIENTO.md`. No se usa OAuth
a GitHub ni se introducen datos privados.

## Verificación prevista

- HTTPS y salud del servicio.
- Búsqueda y lectura exactas, incluida la versión histórica ausente.
- Un chat nuevo de ChatGPT con la nota de DB-SI y evidencia de la URL.
- Distinguir contexto servido de consumo interno o de acceso directo por enlace.

No se supone ningún resultado. El panel de Render muestra login y el usuario debe
entrar con su cuenta propia. No se modifican el intent de objetivo ni otros archivos.
