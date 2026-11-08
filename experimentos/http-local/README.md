# Experimento HTTP local

Runtime de consulta read-only sobre el corpus público de Normativa Abierta. No es el sitio publicado ni sustituye a Pages. Sólo escucha en loopback; no escribe.

## Requisitos

Python 3.12 y `tiktoken==0.14.0` (versión usada en la medición). `acceso.py` se reutiliza íntegro junto a `http_consulta.py`; no se copian fixtures, resultados ni respuestas esperadas.

## Arranque

Windows:

```
python -B experimentos/http-local/http_consulta.py --port 31117
```

Linux/macOS:

```
python3 -B experimentos/http-local/http_consulta.py --port 31117
```

Desde la raíz del repositorio. El servidor usa `contenido/` y `site/`; no acepta corpus externo.

## Consulta

```
curl http://127.0.0.1:31117/
curl "http://127.0.0.1:31117/buscar?q=ejemplo%20de%20consulta"
curl "http://127.0.0.1:31117/buscar?q=ejemplo&doc=ID&version=AAAA-MM-DD"
curl "http://127.0.0.1:31117/buscar?q=ejemplo&doc=ID&version_antes_de=AAAA-MM-DD"
```

La consulta es ilustrativa. `/buscar` devuelve tarjetas y un plan; siga **todos** los `href` de `/leer?doc=...&page=N` y los respaldos visibles. El filtro opt-in exige `doc`; `version` es edición exacta y `version_antes_de` estrictamente anterior. No decide vigencia jurídica. Cada documento indexado expone hoy una versión en su `doc.json` del corpus; inspeccione `contenido/docs/<ID>/<versión_SHA>/doc.json`.

El respaldo PDF se enlaza como `/estatico?path=contenido/<doc_base>/fuente.pdf#page=N`; no se afirma que el JSON `pdf` incluya el fragmento. `/leer` entrega la página literal completa y el ámbito; no descarga el índice completo.

## Cómo se contó

Para reproducir el coste: tokenice cada cuerpo UTF-8 y cada path/query por separado, sume los tokens y añada la pregunta/ficha una vez; no sume bytes como tokens. Use `cl100k_base` y `o200k_base`. No se cuentan gzip, cabeceras ni transporte que el cliente no inyecta. Las imágenes y la salida del modelo no se observan.

## Límites

No sustituye al visor estable ni se ha desplegado. No se midieron A (PDF multimodal), imágenes, wrappers ni uso real en ChatGPT/Claude. La paridad textual no certifica tablas/ejes/fórmulas visuales. Resultados de evaluación y fixtures quedan fuera de este paquete. Véase el [changelog](../../changelog/2026-11-09-pedenry-experimento-http.changelog.md) y el [handoff](../../changelog/2026-11-09-pedenry-experimento-http.handoff.md).
