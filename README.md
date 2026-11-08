# Normativa Abierta

Objetivo futuro: normativa de edificación más allá del CTE, con cobertura real y trazable. Hoy el paquete publicable contiene **31 PDF redistribuibles**: **15 disposiciones legales** (Parte I, los 11 DB, RD 314/2006, RITE y RSCIEI) más **16 guías con permiso editorial expreso**. El inventario de trabajo tiene 88 fuentes, pero **50 PDF privados no se incluyen**; otras 7 fuentes son sólo fichas HTML. No es «toda la normativa».

Estado publicado: **1582 páginas** y **3033 segmentos** de los 31 documentos. Navegación: `index.html` → `site/materia` → documento → apartado/página. Contenido en `contenido/docs/{ID}/{versión_SHA}/`; índices y manifiestos en `contenido/indice/` y cada documento; condiciones en `LICENCIAS.md` y `licencias/`; cambios en `changelog/`.

## Uso desde un modelo

Instrucción técnica: abra directamente la URL pública, sin instalar MCP ni usar una cuenta de GitHub. **No se afirma que el fetch real en ChatGPT/Claude esté probado.** Use el índice y las páginas literales; conserve siempre la URL de origen, versión, SHA256, apartado, página física, notas, tablas y condiciones aplicables. Si un dato no aparece, declare la ausencia; no lo complete por inferencia.

Ejemplos de pregunta, sin respuestas esperadas: «¿Qué exige la exigencia básica SE 2 sobre aptitud al servicio?»; «¿Se considera el empuje pasivo en cimentaciones directas?». Una respuesta útil debe citar la fuente y no equivale a verificación íntegra de cumplimiento.

## Fuentes y derechos

Textos basados en el portal del CTE y el BOE; las guías conservan la atribución editorial de los JSON de permisos. Cada documento indica versión, SHA256 y URL de origen. `LICENSE-CODE` cubre sólo el código original, no la normativa ni documentos de terceros; no se aplica una licencia MIT global. El aviso del portal CTE y el art. 13 TRLPI no son un permiso global. Atribución BOE cuando proceda: «Basado en datos de la Agencia Estatal Boletín Oficial del Estado».

## Validación y límites

Validación local previa: 31/31 con documento, páginas, citas y versión; 6/6 condiciones de fuente; 12/12 variantes por fuente. El evaluador léxico legacy queda en 27/31, con cuatro flags visibles (SA01, SI01, T02, T07), sin ocultarlos.

Baseline B sobre texto ya extraído del documento pertinente: ratio mediano **1,01059** (no es ahorro mediano demostrado); flujo rico CLI **1.979.859** total / **2.133.119** base. No es consumo real de un modelo. El preprocesado ya está hecho y evita reextraer PDF, pero **no se atribuye porcentaje de tokens** a la comparación A (PDF multimodal vs preparado), que **no está medida**; no se usó API pagada. Fuentes: https://developers.openai.com/api/docs/guides/file-inputs y https://platform.claude.com/docs/en/build-with-claude/pdf-support (admiten texto+imagen de PDF; no demuestran chats).

Límites: segmentación y jerarquía automáticas no verificadas humanamente; celdas, fórmulas y semántica pueden requerir contraste con el PDF. El mecanismo de conservación ignora espacios, no orden ni semántica. El PDF original y los hashes siguen siendo la referencia.

## Publicación

URL de Pages prevista: https://pedenry.github.io/normativa-abierta/ — **pendiente de verificación del despliegue actual**. Entrada relativa: `index.html`. Sin publicación de tests, respuestas esperadas, herramientas internas ni rutas privadas.
