# Ingesta: ampliación BOE (primera tanda)

Recopilación reproducible de normativa española de edificación **adicional al CTE/RITE/RSCIEI** desde las páginas oficiales del BOE. Esta carpeta documenta el mecanismo de ingesta y su **integración local** de la primera tanda al corpus mediante `extraer_boe.py` e `integrar_boe.py`; los scripts de esta carpeta no publican nada. La integración de las 15 fuentes BOE ya está realizada (recuentos en «Integración local»). La generación y publicación del visor es un **proceso separado**, autorizado el 2026-11-15 y descrito en [Generación y publicación del visor](../docs/generacion-visor.md); su ejecución y comprobación remota se registran por separado.

## Alcance de la primera tanda

15 documentos legales definidos en [`fuentes-ampliacion.json`](fuentes-ampliacion.json) (fuente de verdad de las semillas). Los identificadores fueron verificados por Codex contra las páginas `act.php` (encargo 2026-11-15); los `tema` son etiquetas informativas del encargo y **no sustituyen al título real**, que el script extrae de cada página.

| ID | Tema (etiqueta del encargo) |
| --- | --- |
| BOE-A-1999-21567 | LOE: Ley de Ordenación de la Edificación |
| BOE-A-2021-13681 | Código Estructural (enlaza PDF **original**, sin consolidado) |
| BOE-A-2002-18099 | REBT: Reglamento electrotécnico para baja tensión |
| BOE-A-2011-5834 | ICT (denominación exacta por confirmar en la página) |
| BOE-A-2017-6606 | RIPCI: Reglamento de instalaciones de protección contra incendios |
| BOE-A-2024-7258 | Ascensores (denominación exacta por confirmar) |
| BOE-A-2021-9176 | Certificación energética de edificios (denominación exacta por confirmar) |
| BOE-A-2008-2486 | Residuos de construcción y demolición (denominación exacta por confirmar) |
| BOE-A-1997-22614 | Seguridad y salud en obras de construcción (denominación exacta por confirmar) |
| BOE-A-2007-18397 | Ruido (denominación exacta por confirmar) |
| BOE-A-2023-628 | Agua: consumo en edificios (denominación exacta por confirmar) |
| BOE-A-2015-11723 | Suelo y rehabilitación (denominación exacta por confirmar) |
| BOE-A-2021-13488 | Orden TMA/851/2021: accesibilidad en espacios públicos urbanizados (alcance distinto de interiores de edificios) |
| BOE-A-2022-10297 | RD 487/2022: legionelosis (denominación exacta por confirmar) |
| BOE-A-2006-15345 | RD 919/2006: gas (denominación exacta por confirmar) |

## Comandos

Requisitos: Python 3.12 o posterior (solo biblioteca estándar). Ejecutar desde la raíz del checkout o desde cualquier carpeta (la salida por defecto se resuelve desde la ubicación del script):

```sh
# Tanda completa (15 fuentes)
python ingesta/recopilar_boe.py

# Solo las N primeras fuentes
python ingesta/recopilar_boe.py --limite 3

# Una fuente concreta (debe figurar en fuentes-ampliacion.json)
python ingesta/recopilar_boe.py --solo-id BOE-A-2021-13681

# Directorio de salida alternativo (NUNCA apuntar a rutas públicas)
python ingesta/recopilar_boe.py --salida .local/ampliacion-boe
```

Códigos de salida: `0` todo ok · `1` alguna fuente con error · `2` error de configuración (JSON ausente, `--solo-id` desconocido, ID con formato inesperado). Los errores quedan registrados por fuente en sus `metadatos.json` y en `resumen.json`/`resumen.md`. Si se combinan `--solo-id` y `--limite`, prevalece `--solo-id`.

La ejecución de este script la hace **Codex** (red y shell); la elaboración del agente fue solo de archivos.

## Salida

Por defecto `.local/ampliacion-boe` en la raíz del checkout (gitignored). Estructura:

```text
.local/ampliacion-boe/
  BOE-A-2021-13681/
    20261115T101500Z__ab12cd34/          # fecha UTC de captura + hash PDF (8 caracteres)
      act.html                           # HTML original, bytes sin modificar
      BOE-A-2021-13681-original.pdf      # PDF sin modificar, firma %PDF- validada
      metadatos.json                     # SHA-256, enlaces fuente, disposicion literal,
                                         # titulo real, fechas, tipo, licencia, pendientes
  BOE-A-1999-21567/
    20261115T101502Z__9f87e321/
      act.html
      BOE-A-1999-21567-consolidado.pdf
      metadatos.json
  resumen.json                           # reporte de la ultima ejecucion
  resumen.md                             # tabla IDs/titulos/tipos/fechas/errores + alcance
```

Cada snapshot vive en una carpeta por fecha UTC de captura + hash del PDF: **nunca se sobrescribe** un snapshot previo distinto (si la carpeta exacta existiera, se añade sufijo `-2`, `-3`, …). Si la fuente falla, la carpeta usa el sufijo `__sin-pdf` y conserva el HTML y los errores; si no hay enlace PDF en la página, se registra el fallo y **no se inventa consolidado**.

## Método de captura

- Página oficial `https://www.boe.es/buscar/act.php?id={ID}` analizada con `html.parser.HTMLParser` (sin dependencias externas). Metadatos: ELI, título real (h1, con `<title>` como alternativa declarada), fecha de publicación, fecha del documento, fecha de versión/actualización; todo campo no localizado queda `null` con aviso de cotejo contra el HTML guardado.
- PDF: primer enlace cuyo href contenga el ID y `consolidado.pdf` (tipo `consolidado`); si no existe, enlace con `ID.pdf` (tipo `original`). URL relativa resuelta con `urljoin`; si no hay enlace válido, error por fuente.
- Límites: solo HTTPS en `www.boe.es`/`boe.es` (validado también tras cada redirección), tamaño máximo 60 MB, pausa ≥ 1 s entre solicitudes, timeout de 30 s, hasta 2 reintentos para errores transitorios (HTTP 408/429/5xx, cortes de red) con espera creciente de 2 s y 4 s. Descarga secuencial.
  - Límite observado en la tanda: `BOE-A-2021-13681` (Código Estructural, original) pesa **67 353 218 bytes** y supera el máximo de 60 MB del recopilador. Su captura ya fue realizada por Codex con un límite de 80 MB, antes de la integración local. **No se afirma** que el recopilador actual descargue los 15 documentos correctamente sin ajustar ese límite.
- La API de datos abiertos (`/legislacion-consolidada/id/{ID}/metadatos` y `/texto`, documentada en https://www.boe.es/datosabiertos/api/api.php) respondió **HTTP 400/404** en la verificación de Codex del 2026-11-15; por eso se usa scraping de `act.php`. El retest de la API queda pendiente y se registra en cada `metadatos.json`.

## Licencias y atribución

- Aviso legal del BOE (https://www.boe.es/informacion/aviso_legal/index.php): permite la extracción y reordenación con atribución, indicando fechas y transformaciones. El consolidado es **informativo y sin valor oficial**. Cotejado por Codex el 2026-11-15 contra la página oficial (condición cuarta, apartados 2, 3, 5 y 7).
- Atribución obligatoria al reutilizar, según el material:
  - PDF sin transformar (evidencia conservada byte a byte): «Fuente de los datos: [Agencia Estatal Boletín Oficial del Estado](https://www.boe.es)».
  - Extracción de texto y derivados (segmentos del corpus): «Basado en datos de la [Agencia Estatal Boletín Oficial del Estado](https://www.boe.es)».
- Quedan excluidos los textos UNE (licencia propia) y las obras recopilatorias de Biblioteca Jurídica (condiciones de licencia distintas). Ver [LICENCIAS.md](../LICENCIAS.md).

## Límites declarados

- **No se afirma vigencia** ni aplicabilidad: cada `metadatos.json` deja `aplicabilidad` y `transitorio` como PENDIENTES hasta verificar ámbito y régimen transitorio por fuente.
- **Fidelidad NO cotejada**: la extracción de metadatos es automática y sin revisión técnica humana. El HTML y el PDF originales se conservan byte a byte para permitir el cotejo de tablas, notas, umbrales y excepciones contra la fuente.
- Los campos con `null` pueden existir en la página y no haberse localizado: cotejar contra el `act.html` guardado antes de dar por cierta una ausencia.
- El script no ejecuta shell ni accede a la red más allá de las descargas descritas; es stdlib y determinista salvo las horas UTC de captura.

## Mantenimiento del entorno

La extracción de texto de los PDF de la tanda usa `pypdf` (dependencia externa, a diferencia del recopilador, que es stdlib):

```sh
pip install -r ingesta/requirements.txt
```

Las salidas ya integradas viven en `contenido/` y son suficientes para consultar el corpus (el adaptador por defecto **no** lee `.local/`); no requieren `pypdf` ni reextracción. Los JSON intermedios en `.local/` son privados y solo sirven para mantener la ingesta. Solo hacen falta instalar dependencias y reextraer si se ejecutan los comandos de la sección «Integración local».

## Uso con adaptador

Consulta puntual sobre un documento del corpus con el adaptador experimental, sin regenerar el visor:

```sh
python -B experimentos/http-local/adaptador_contexto.py --consulta 'Instalaciones de enlace centralizacion contadores' --documento BOE-A-2002-18099 --version 2025-09-03 --presupuesto 20000 --max 3
```

## Integración local

Integración de la tanda de 15 documentos (2 742 páginas físicas) al corpus mediante `ingesta/extraer_boe.py` e `ingesta/integrar_boe.py` (creados por otros encargos). No regenera el visor ni publica nada.

**Normalización previa (obligatoria antes de extraer).** Preparar localmente `.local/integracion-boe/normalizado.json` con una clave `fuentes[]` por documento: `id`, `titulo`, `materia`, `tipo`, `version` en ISO (`version_label_literal` extraído tal cual), `fecha_publicacion`, `sha256_pdf`, `paginas_fisicas`, `ruta_pdf` absoluta local, `url_pdf`, `url_fuente` y `capturado_en_utc`. Los 15 metadatos deben **cotejarse contra el PDF** antes de ejecutar, no tomarse como ciertos.

Importante: la normalización de fechas fue un **paso de verificación de Codex**, no automatizado por el recopilador; no se afirma que `recopilar_boe.py` lo produzca directamente. Si el PDF indica «sin modificaciones», la fecha de publicación queda corroborada como fecha del texto; en particular, el Código Estructural (`BOE-A-2021-13681`) corresponde a la versión original **2021-08-10** y no al consolidado.

```sh
python -B ingesta/extraer_boe.py --origen .local/integracion-boe/normalizado.json --salida .local/integracion-boe/extraido.json
python -B ingesta/integrar_boe.py --origen .local/integracion-boe/extraido.json
```

**Idempotencia:** reejecutar con el mismo hash es idempotente; un hash distinto exige revisión, no sustitución del contenido existente.

**Resultados tras la integración:** 46 documentos, 4 324 páginas, 5 775 segmentos en el corpus.

## Segmentación y límites de fidelidad

- La segmentación sigue la **página física del PDF**, sin jerarquía normativa (no hay detección de artículos, capítulos ni títulos).
- Las etiquetas impresas (p. ej. «Página», «BOE núm. …») se dejan como **desconocidas** (`null`), no se separan del texto.
- El layout conserva el **texto girado** con advertencia de formato degradado; no se reconstruyen columnas.
- Tablas, fórmulas, figuras y notas **no disponen de cotejo completo** ni de OCR: la fidelidad del texto extraído queda limitada por `pypdf` y sin revisión humana.
- La licencia de la evidencia integrada queda registrada **por hash** en `licencias/ampliacion-boe-2026-11-15.json`.

## Revisión y publicación

La integración local de la tanda de 15 documentos (2 742 páginas) al corpus ya está realizada mediante `extraer_boe.py` e `integrar_boe.py`, con los recuentos de la sección «Integración local». Quedan pendientes:

1. Cotejo visual de tablas y pasajes críticos frente al PDF (fuera del alcance de la extracción automática; sin OCR).
2. Retest de la API `/legislacion-consolidada` como fuente alternativa de metadatos.
3. Verificar emisor, ámbito, edición aplicable y régimen transitorio por fuente antes de afirmar cualquier vigencia.

La generación y publicación del visor con la tanda integrada está **autorizada** (Pedro, encargo 2026-11-15). Es un proceso separado de la ingesta, descrito en [Generación y publicación del visor](../docs/generacion-visor.md). Su registro debe acreditar el commit publicado y la comprobación remota; la autorización por sí sola no acredita un despliegue.

Registrado como verificado: `.local/` permanece gitignored (comprobado en encargo anterior).
