# Licencias y condiciones de uso

Este documento resume las condiciones aplicables. No sustituye la revisión jurídica de cada fuente.

## Aviso del portal CTE

El aviso legal del portal, **sección 3.4** (https://www.codigotecnico.org/pdf/avisoLegalCTE.pdf), restringe la reproducción salvo autorización expresa o permiso legal. No se presume autorización.

## Textos legales y TRLPI

El artículo 13 del Texto Refundido de la Ley de Propiedad Intelectual (https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930#a13) excluye de la protección las disposiciones legales y reglamentarias. Esa exclusión **no** es un permiso global para reproducir guías, comentarios u otros documentos.

## BOE

Las condiciones del aviso legal del BOE (https://www.boe.es/informacion/aviso_legal/index.php) permiten la extracción y reordenación con atribución, indicando fechas y transformaciones. El consolidado es informativo y no tiene valor oficial.

Atribución aplicable, según la condición cuarta, apartados 2 y 3, del aviso legal oficial del BOE (cotejada el 2026-11-15), con enlace a https://www.boe.es:

- **PDF sin transformar** (original o consolidado, según la fuente):

  > Fuente de los datos: [Agencia Estatal Boletín Oficial del Estado](https://www.boe.es)

- **Extracción o reordenación de datos** (texto convertido y páginas preparadas para consulta):

  > Basado en datos de la [Agencia Estatal Boletín Oficial del Estado](https://www.boe.es)

Conservar las fechas de actualización presentes en la fuente e identificar las transformaciones realizadas. La atribución no convierte un texto consolidado en publicación oficial.

## UNE y signos oficiales

No se incluyen textos UNE licenciados ni logos propios de organismos oficiales. Las fichas no reproducen documentos restringidos.

## Código

MIT solo para scripts originales; ver `LICENSE-CODE`. No se aplica a normativa, fichas ni documentos de terceros.

## Regla operativa

| Capa | Entradas | PDF | Tratamiento |
|---|---:|---:|---|
| Documentos legales | 30 | 30 | Texto completo; `distribute=true` |
| Complementos sin permiso | 23 | 23 | Local privado; no se distribuyen |
| Guías con permiso editorial | 16 | 16 | Contexto publicable citando fuente y autores |
| Guías/subdocs sin permiso | 27 | 27 | Local privado; no se distribuyen |
| Páginas HTML de guía | 7 | 0 | Ficha; sin reproducción |
| **Total** | **103** | **96** | |

**46 PDF redistribuibles**: 30 legales + 16 con permiso editorial expreso. Evidencia en `licencias/permisos-editoriales.json` y, para la ampliación BOE de 2026-11-15, en `licencias/ampliacion-boe-2026-11-15.json` (hashes por documento). El 2026-11-15, Pedro autorizó publicar las 15 fuentes BOE integradas y actualizar el visor. Los 50 PDF restantes siguen privados.

El art. 13 TRLPI no es una licencia global. Una guía queda en **UNKNOWN** salvo permiso expreso; no se reescala por título, sección o parecido. Si cambia el SHA, se invalida la evidencia anterior y se revisa el nuevo documento.

## Publicación anterior

Historial, previo a la ampliación BOE de 2026-11-15: publicación autorizada de los **31 PDF de contexto publicable** (15 legales + 16 con permiso editorial) con base en la evidencia de `licencias/permisos-editoriales.json` y `LICENCIAS.md`. Se mantienen fuera los 50 PDF privados y el contenido de las 7 páginas HTML de guía; sus fichas pueden conservar metadatos y enlaces. Cualquier cambio de SHA invalida la evidencia anterior y exige revisión del nuevo documento; las guías o comentarios no quedan amparados sólo por estar relacionados con normativa.

## Ampliación BOE 2026-11-15

Integración de **15 disposiciones BOE** adicionales (14 consolidados informativos + 1 publicación original del Código Estructural), que añaden 15 PDF redistribuibles a los 31 anteriores (corpus 46 PDF = 30 legales + 16 guías).

- Fuente, fecha, hash SHA-256 por documento y registro de la transformación página a página: `licencias/ampliacion-boe-2026-11-15.json`.
- Redistribución amparada por el aviso legal del BOE (https://www.boe.es/informacion/aviso_legal/index.php), con **atribución obligatoria** según el tratamiento, conforme a la condición cuarta, apartados 2 y 3, del aviso legal oficial (cotejada el 2026-11-15):
  - PDF sin transformar (original o consolidado, según la fuente): «Fuente de los datos: Agencia Estatal Boletín Oficial del Estado» (https://www.boe.es).
  - Extracción o reordenación de datos (texto convertido): «Basado en datos de la Agencia Estatal Boletín Oficial del Estado» (https://www.boe.es), indicando fechas y transformaciones.
- Los consolidados son **meramente informativos y sin valor oficial**. La publicación original no incorpora correcciones posteriores.
- Pendiente: cotejo de fidelidad de tablas, fórmulas y notas; comprobación de ámbito aplicable y régimen transitorio. Cada salida debe conservar la atribución correspondiente al PDF íntegro o al texto extraído, según su registro de transformación.
- Sin licencia MIT global ni textos UNE. Las comprobaciones de la entrega se registran en [el historial de publicación](changelog/2026-11-15-pedenry-evaluacion-publicacion-boe.changelog.md).
