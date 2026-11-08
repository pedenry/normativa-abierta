---
fecha: 2026-11-08T22:06:52+01:00
zona: Europe/Madrid
titulo: Publicación inicial de Normativa Abierta
tipo: handoff
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex (preflight, commit, push, API y HTTP); cuenta de push real pedenry
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commit_contenido_estable: d6424d99a5e406c002bc3aa5360ba20a306b6788
commits: este registro se trazará por el historial; no se inventa su SHA futuro
estado: publicado y verificado
---

## Estado observado

- Publicado en `main` remoto; autor/committer técnico `Codex <codex@local.invalid>`; pusher real `pedenry`. No se atribuye a NaN ni a Codex como persona.
- GitHub Pages activo en `main`/raíz: build `built`, workflow SUCCESS (`actions/runs/42523296620`), URL real https://pedenry.github.io/normativa-abierta/ verificada el 2026-11-08T22:06:52+01:00.
- HTTP sin login: raíz 200; JSON de fuente `F` y PDF accesibles. PDF descargado SHA256 `e3e0805c3b4c307519c26dc34c3fdbf143d842edd013c91b0f52d2c73403d91c`, igual al original; JSON `F` con versión 2019-12-20 y SHA correctos.
- Repositorio: 16114 archivos, 31 PDF, 0 `site/consulta`, 0 `herramientas`; árbol API completo no truncado. ZIP estable intacto (`5425a80cf69b7d467b6670eb235364b5e23bc45a93747ee508681a2fe2f35682`).
- Preflight: 16108 hashes base idénticos; 2 documentos intencionales (README, LICENCIAS) y 4 changelog; 405203929 bytes; máximo 33753794 bytes; 88126 enlaces, 0 rotos; 31 documentos con permiso verificado, 0 avisos/errores. Cumple límites de Pages (1 GB) y GitHub (100 MiB por archivo).
- Sin privados, fixtures, respuestas, experimentos ni servidor. 7 fuentes HTML del inventario son sólo fichas/enlaces, no originales redistribuidos.
- Validación estable: 31/31 documental, 6/6 condiciones, 12/12 variantes por fuente; legacy 27/31 con flags SA01, SI01, T02, T07. Baseline B 1,01059; no ahorro mediano demostrado; A no medida; preprocesado ya hecho evita reextraer PDF.

## Pendiente

1. Compatibilidad real en interfaces ChatGPT/Claude: no probada.
2. Optimización de tokens posterior; HTTP local es prototipo preparado, no ejecutado ni incluido.
3. Codex hará un commit sólo de documentos y verificará el despliegue posterior.

## Límites

No se incluyen conversaciones, prompts, rutas privadas, secretos ni respuestas de tests. La identidad local de Git es técnica, no una persona verificada.
