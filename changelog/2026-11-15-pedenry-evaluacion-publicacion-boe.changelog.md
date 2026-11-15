# 2026-11-15 — pedenry — Evaluación previa a publicación BOE

- **Fecha:** 2026-11-15.
- **Usuario:** pedenry.
- **Ejecución de validaciones, revisión y aplicación del registro:** Codex.
- **Redacción inicial:** OpenCode, agente `evaluacion-normativa`, modelo `nan/glm5.3-flash`.
- **Estado:** entrega autorizada por Pedro, con corpus y visor comprobados localmente. El despliegue de este commit se verifica por separado en GitHub Pages.

## Alcance

Comprobación de la integración y recuperación de las quince fuentes BOE antes de su publicación. No es una evaluación de aplicabilidad normativa ni una revisión técnica humana del contenido.

## Comprobaciones ejecutadas

- **33 pruebas aprobadas:** 19 del piloto y 14 HTTP. Recalculado el resumen de consumo histórico a partir de resultados guardados, sin nuevas llamadas API.
- **15 consultas correctas**, una por fuente nueva: documento, edición, hash, fuente y avisos esperados en el contexto recuperado.
- Edición REBT `1900-01-01`: estado `version_no_disponible`, sin páginas ni sustitución de edición.
- Regresión SUA: conservadas las nueve páginas anteriores: 15, 35, 36, 37, 33, 34, 40, 41 y 42.
- Corpus: **46 documentos, 4.324 páginas, 5.775 segmentos y 103 fichas**. Las 88 fichas y los 3.033 segmentos anteriores permanecen intactos.
- Los quince PDF coinciden con los hashes de sus documentos, licencias y validación; distribución marcada explícitamente como permitida. La ampliación contiene 2.742 páginas, ninguna vacía.
- Importación de una fuente en un corpus aislado: correcta; repetición idéntica byte a byte; hash incorrecto rechazado sin modificar ese corpus.
- Quince páginas oficiales del BOE: respuesta HTTP 200 e identificador esperado presente.

Evidencia depurada:

- [Verificación del corpus y adaptador](../contenido/validacion/publicacion-boe-2026-11-15-verificacion-corpus-adaptador.json).
- [Comprobación de enlaces oficiales](../contenido/validacion/publicacion-boe-2026-11-15-enlaces-oficiales.json).

## Ejemplo REBT

La consulta «Instalaciones de enlace centralización de contadores», sobre `BOE-A-2002-18099`, edición `2025-09-03`, presupuesto 20.000 y máximo de tres resultados, devuelve nueve páginas físicas: 47, 106, 107, 108, 102, 103, 104, 109 y 110.

Esto comprueba recuperación con procedencia, no una respuesta normativa completa. La página 47 contiene un temario auxiliar y las figuras no quedan reproducidas en el texto extraído.

## Generador público y visor

- Generador reproducible en `herramientas/generar_site.py`, documentado en [la guía de generación](../docs/generacion-visor.md). No requiere carpetas privadas ni acceso a la red.
- **10 pruebas adicionales aprobadas**: restricción de fuentes, escape HTML, hashes, enlaces simbólicos, avisos, créditos, rutas y determinismo mediante doble generación sintética.
- Generación real: **10.173 páginas HTML**, 151.311 enlaces comprobados, cero enlaces rotos o fuera de la raíz. Recuentos completos en [el informe del visor](../site/_informe.json).
- Conservadas las **4.656 rutas HTML anteriores** y el ancla `ambito`. Las 16 guías mantienen sus créditos completos y los documentos BOE históricos conservan atribución y avisos.
- Candidato contrastado con la huella del código generador y su inventario de salidas antes de promoverlo a `index.html` y `site/`. La interfaz del adaptador local no cambia.
- Revisión visual local a 1440 × 900 y 390 × 844: portada, materia, REBT, página física 103, Código Estructural y créditos desplegables de una guía anterior. Navegación comprobada y sin desbordamiento horizontal de página en las vistas móviles revisadas. Esta revisión de interfaz no amplía el cotejo técnico del contenido normativo.
- `git diff --cached --check` sin incidencias en código, documentación y corpus. El HTML generado conserva 1.192 avisos de espacios o retornos de carro dentro de texto literal heredado; se mantiene ese contenido y se excluye únicamente el HTML de esta comprobación de formato. No son enlaces rotos ni fallos de las pruebas.

## Límites y estado pendiente

No se repitió la extracción completa. El cotejo visual previo sigue limitado a dos páginas; tablas, fórmulas, notas y figuras requieren revisión. No hay un benchmark API nuevo ni ahorro medido para esta ampliación.

Este registro recoge las comprobaciones de preparación de la entrega. La confirmación remota debe verificar que GitHub Pages sirve el mismo commit incorporado a `main`; la autorización y la generación local no acreditan por sí solas el despliegue.

OpenCode preparó el texto, pero sus lecturas y escritura fueron denegadas por permisos de ruta. Codex cotejó las cifras contra ambos JSON, corrigió el borrador y aplicó únicamente este nuevo registro; se conserva el changelog anterior.
