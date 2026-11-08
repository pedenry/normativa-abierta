---
fecha: 2026-11-08T21:51:03+01:00
zona: Europe/Madrid
titulo: Publicación inicial de Normativa Abierta
tipo: changelog
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex mediante GitHub CLI
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: pendiente del primer commit; este registro se consulta en el historial
estado: paquete estable preparado localmente; despliegue pendiente
---

## Hechos verificados

- Identidad GitHub: `gh api user` devuelve login `pedenry`, id `35270581`; `gh auth status` indica sesión activa con push/admin.
- ZIP estable: SHA256 `5425a80cf69b7d467b6670eb235364b5e23bc45a93747ee508681a2fe2f35682`; 16110 archivos; 405195851 bytes; 31 PDF (máximo 33753794 bytes); 4657 HTML; 88126 enlaces, 0 rotos.
- Excluidos del paquete: 50 PDF privados, respuestas/test, scripts, experimentos y rutas privadas.
- Validación local estable: 31/31 con documento, páginas, citas y versión; 6/6 condiciones de fuente; 12/12 variantes por fuente. Legacy léxico 27/31, con flags SA01, SI01, T02, T07 visibles.
- Baseline B: mediana 1,01059; flujo rico CLI 1.979.859 total / 2.133.119 base; no es consumo real de modelo.
- Comparación A PDF multimodal vs preparado: no medida; sin API pagada. El preprocesado ya existe y evita reextracción.

## Límites registrados

La ruta experimental estática midió 10/12 variantes y no se incluye. El prototipo HTTP local no se evaluó, no se publicó y se pospone. No se promete ahorro.

## Verificación

Documentos preparados para el commit; la URL de Pages y el SHA observado del commit se completarán después del push. La publicación no se declara completada en este registro.
