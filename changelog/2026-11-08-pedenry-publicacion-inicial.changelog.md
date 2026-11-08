---
fecha: 2026-11-08T21:51:03+01:00
zona: Europe/Madrid
titulo: Publicación inicial de Normativa Abierta
tipo: changelog
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex mediante GitHub CLI
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: contenido estable d6424d99a5e406c002bc3aa5360ba20a306b6788; este registro se consulta en el historial
estado: publicado y verificado; commit sólo-docs posterior pendiente
---

## Hechos verificados

- Identidad GitHub: `gh api user` devuelve login `pedenry`, id `35270581`; `gh auth status` indica sesión activa con push/admin.
- ZIP estable: SHA256 `5425a80cf69b7d467b6670eb235364b5e23bc45a93747ee508681a2fe2f35682`; 16110 archivos; 405195851 bytes; 31 PDF (máximo 33753794 bytes); 4657 HTML; 88126 enlaces, 0 rotos.
- Excluidos del paquete: 50 PDF privados, respuestas/test, scripts, experimentos y rutas privadas.
- Validación local estable: 31/31 con documento, páginas, citas y versión; 6/6 condiciones de fuente; 12/12 variantes por fuente. Legacy léxico 27/31, con flags SA01, SI01, T02, T07 visibles.
- Baseline B: mediana 1,01059; flujo rico CLI 1.979.859 total / 2.133.119 base; no es consumo real de modelo.
- Comparación A PDF multimodal vs preparado: no medida; sin API pagada. El preprocesado ya existe y evita reextracción.
- Publicación observada: commit d6424d99a5e406c002bc3aa5360ba20a306b6788; pusher real `pedenry`; Pages workflow SUCCESS (`actions/runs/42523296620`); URL https://pedenry.github.io/normativa-abierta/ verificada el 2026-11-08T22:06:52+01:00. PDF de fuente con SHA original y JSON F correctos; 31 PDF y 0 `site/consulta` ni `herramientas`.

## Límites registrados

La ruta experimental estática midió 10/12 variantes y no se incluye. El prototipo HTTP local no se evaluó, no se publicó y se pospone. No se promete ahorro.

## Verificación

Documentos preparados para el commit; la URL de Pages y el SHA observado del commit se completaron tras el push. La publicación queda verificada; el commit sólo-docs posterior se trazará por el historial.
