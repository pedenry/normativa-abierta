---
fecha: 2026-11-08T21:51:03+01:00
zona: Europe/Madrid
titulo: Publicación inicial de Normativa Abierta
tipo: handoff
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex mediante GitHub CLI
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: pendiente del primer commit; referencia el último commit observado cuando exista
estado: listo para commit y despliegue; no verificado aún
---

## Estado observado

- Repositorio remoto vacío (main, público) clonado; copia estable en curso.
- `README.md`, `LICENCIAS.md`, `LICENSE-CODE`, `contenido/` y sitio estable copiados; no se toca corpus ni la fuente experimental.
- 31 PDF redistribuibles; 50 PDF privados y 7 fichas HTML fuera; 31/31 documental, 6/6 condiciones, 12/12 variantes por fuente; legacy 27/31 con cuatro flags.
- ZIP estable intacto: SHA256 `5425a80cf69b7d467b6670eb235364b5e23bc45a93747ee508681a2fe2f35682`.

## Pendiente

1. Codex configura Git local, crea el commit y hace push con autenticación de `pedenry`; no desde NaN.
2. Verificar el SHA del commit observado y completar este registro sin autorreferencia.
3. Activar GitHub Pages y comprobar la URL https://pedenry.github.io/normativa-abierta/ antes de declarar éxito.
4. No publicar el índice experimental ni el prototipo HTTP. La siguiente evaluación, si se autoriza, será gating de casos críticos y 31+12 con datos congelados, sin prometer ahorro.

## Límites

No se incluyen conversaciones, prompts, rutas privadas, secretos ni respuestas de tests. La identidad local de Git es técnica; no es una persona verificada.
