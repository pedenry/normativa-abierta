# Ingesta territorial: CCAA y municipios

Captura web reproducible de portales oficiales autonómicos y municipales
(edificación, urbanismo, vivienda, accesibilidad, habitabilidad). La captura
HTML y la descarga de PDF van a `.local/`; la integración en corpus exige
entrada revisada y aprobada. **No publica ni integra automáticamente.**

## Comandos (red y shell: Codex)

```sh
python ingesta/recopilar_territorial.py --listar          # sin red
python ingesta/recopilar_territorial.py --limite 2        # prueba corta
python ingesta/recopilar_territorial.py                   # tanda completa
python ingesta/recopilar_territorial.py --reanudar        # usa cache con hash verificado
python ingesta/recopilar_territorial.py --solo-id ES-MD --max-paginas 10 --profundidad 1
```

Opciones: `--catalogo` (defecto `ingesta/fuentes-territoriales.json`),
`--salida` (solo rutas dentro de `.local/`; defecto `.local/territoriales`),
`--limite`, `--solo-id` (prevalece), `--max-paginas` (25), `--profundidad` (2),
`--pausa` (≥1 s), `--timeout` (30 s), `--reanudar`, `--listar`.
Salida: `0` ok · `1` alguna fuente con error · `2` error de configuración.
En `.local/territoriales/{ID}/{marca}/`: páginas HTML sin modificar + `metadata.json`;
`resumen.json`/`resumen.md`; `cache-territorial/` solo con `--reanudar`.

## Garantías del rastreo

- Solo HTTPS y allowlist por fuente, validados en **cada salto** de redirección
  (seguimiento manual: se comprueba esquema, host, robots del destino y pausa
  **antes** de pedir el destino; los 404/410 de robots.txt dejan reglas vacías).
- robots.txt en caché por host; patrones con `*` y `$`, gana el más específico,
  empate → Allow; se evalúa **por ruta+consulta**, no se bloquea el host por `/`.
- robots.txt 200 con cuerpo HTML/captcha → fail-closed del host (no fiable).
- Secuencial, pausa ≥ 1 s (Crawl-delay la sube), máx. 5 MB/página, solo HTML.
- Cache persistente por URL con SHA-256 verificado; solo se usa con
  `--reanudar`; nunca sobrescribe entradas. `--reanudar` es lectura histórica
  de la caché: no comprueba actualización remota, y `capturado_en_utc` refleja
  la ejecución/relectura, no una nueva descarga si sirvió la caché.
- Semillas `http` se actualizan a HTTPS conservando la publicada.

## Descarga de PDF candidatos (red y shell: Codex)

`descubrir_boe_autonomico.py` recorre el índice BOE tipo C (Códigos de
Urbanismo), sigue «Ver contenido»/`&tab=2` y extrae los enlaces `act.php`/`doc.php`
con su identificador y título; sin selección de leyes ni heurísticas.
`descargar_pdf_territorial.py --origen candidatos.json` (opciones con `--help`)
descarga con las garantías del rastreo, valida firma `%PDF-`, SHA-256 y
apertura con pypdf, y guarda originales inmutables en
`.local/pdf-territorial/archivos/{sha}.pdf` con `resumen.json` atómico.

Tanda 2026-11-16 sobre 424 candidatos originales: 345 URLs descargadas
(342 SHA únicos), 17 error, 62 pendientes por límite de 2 GiB. Los candidatos
no son normas: exigen revisión humana.

## Reanudación 2026-11-16

Continuación de la tanda anterior (cifras previas conservadas como históricas).
73 descargas recuperadas (62 pendientes + 11 por exceso del límite de 80 MiB
por PDF): 418 de 424 URLs ok, 415 SHA únicos, 6 HTTP 404 definitivos
([recuperacion-enlaces-pdf-2026-11-16.json](recuperacion-enlaces-pdf-2026-11-16.json)),
ningún pendiente por límite de tanda. Límites usados: 512 MiB por PDF y
8192 MiB por tanda; reserva de disco de 128 MiB mantenida. 10 candidatos
municipales extra Sevilla/Málaga
([fuentes-pdf-municipales-extra.json](fuentes-pdf-municipales-extra.json)):
10 PDF ok, 273 páginas; registro depurado en
[reanudacion-pdf-2026-11-16.json](../contenido/validacion/reanudacion-pdf-2026-11-16.json).
Verificación de aquella reanudación: 425 archivos con SHA-256 correcto y
149 PDF del corpus sin cambio. Las descargas candidatas permanecen privadas
en `.local/`; descargar no equivale a aprobar reutilización ni a integrar.
La integración separada de 103 PDF aprobados se registra en
[territorial-2026-11-16-verificacion.json](../contenido/validacion/territorial-2026-11-16-verificacion.json)
y [licencias/territorial-2026-11-16.json](../licencias/territorial-2026-11-16.json).

## Integración en corpus (encargo aparte)

`integrar_territorial.py --origen fuentes.json [--simular]` valida fail-closed
todo antes de escribir: reutilización `APROBADA` con base jurídica, alcance,
revisión y evidencia HTTPS local cuyo SHA coincide, hash del PDF, versión ISO
o `sin-fecha`, y concordancia de páginas con extracción pypdf por página
física. `--simular` no escribe. La entrada revisada se prepara a mano en
`.local/`: **no se genera automáticamente**. Un documento de naturaleza
desconocida nunca es `APROBADA` por ser PDF; los dudosos quedan privados.
Extracción con pypdf y cryptography fijadas en `requirements.txt`
(pypdf 6.14.2, cryptography 50.0.2). La regeneración del visor y la publicación
remota son pasos separados, no ejecutados por este encargo.

Pendiente: fidelidad, ámbito aplicable, régimen transitorio, vigencia y
revisión humana; los consolidados son informativos y sin valor oficial; la
ordenanza OMLU de Málaga es publicación original (anuncio 5158/2025, BOP
núm. 247, pp. 70-148, 2025-12-29), no consolidada.

## Límites y pendientes

- Semillas autonómicas: URLs del BOE (`otros_diarios_oficiales.php`, consulta
  2026-11-16), sin verificación de cada portal. Municipales: candidatas sin
  verificar, marcadas en el catálogo.
- Toda página sin palabras clave es `portada_indice`: **no** es norma. Los
  candidatos (incluidos PDF solo enlazados) exigen revisión humana.
- `disposicion`, `edición`, `página física`: `null`; vigencia, transitorio,
  licencia y fidelidad: PENDIENTES/NO COTEJADA. Publicación: bloqueada sin
  revisión de licencia por portal.
- Solo HTML en `recopilar_territorial.py`: los PDF y otros binarios nunca se
  descargan ni se encolan (los PDF enlazados con materias quedan como
  candidatos `pdf_no_descargado`; la descarga aparte es
  `descargar_pdf_territorial.py`).
