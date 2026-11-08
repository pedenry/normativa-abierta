---
fecha: 2026-11-09T00:26:21+01:00
zona: Europe/Madrid
titulo: Experimento HTTP local de consulta
tipo: changelog
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex (copia exacta, comandos, pruebas y publicación autorizada tras revisión)
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: base b12ab29a6e54d78e7bd762d5b1a563cc6dcebb2d; este registro se consulta en el historial
estado: experimento local verificado; no desplegado
---

## Etapas

1. **Primera ejecución inválida:** 12 casos en vez de 8, 0/12 documental y `/leer` cortaba por una ruta global relativa; no hay ahorro válido en esa medición.
2. **Críticos corregidos:** 8/8 condiciones y documental; 154.860 / 682.230 tokens cl100k; mediana 0,230126; 103 páginas literales.
3. **Primera batería:** 31/31 originales, 11/12 variantes, 17/18 condiciones; 765.980 / 3.201.561; mediana 0,246552. No aceptada.
4. **Diagnóstico P-T-02:** el prefiltro HTTP excluía 16 guías públicas (15 documentos/2387 filas frente a 31/3033), alterando el IDF global antes de filtrar candidatos.
5. **Restauración del índice público íntegro**, sin tocar consultas, tests, oráculo, pesos, umbrales ni `acceso.py`. Retest focal: 5/5 condiciones, recuperación, cita, páginas y versión correctas.
6. **Batería repetida de 44:** 43 medidos; originales 31/31; variantes 12/12 (6/6 controles reservados); condiciones 18/18; legacy 27/31 con los mismos cuatro flags (SA-01, SI-01, T-02, T-07); combinado legacy 33/43. Sin fallos de gate.

## HTTP y coste final

- 595 requests HTTP 200, 0 fallos; 507 lecturas con paridad exacta de texto, ámbito, versión/SHA y respaldo PDF local; 324 páginas únicas; 15 documentos con PDF local.
- cl100k_base: **756.344 / 3.201.561**, −76,38 % total, mediana **0,241862**. Crece PI-01 (1,1257).
- o200k_base: **675.356 / 2.819.516**, −76,05 %, mediana **0,247410**. Crecen PI-01 (1,1519) y T-01 (1,0030).
- Categorías cl100k: input 2.198; protocolo 2.580; objetivos 9.183; búsqueda 48.085; lectura 694.298.
- 4 negativos sintéticos detectan omisión de condición, nota, eje y valor con cita intacta; autotest fuente previo pasado.
- Tokenizador 0.14.0; `acceso.py` SHA256 `b7943f309999847ce1609c93b163248ef6ed2d1242f2f02078563ac662f21a39`; `http_consulta.py` SHA256 `1b99da8dd1c5f34f444578f64dc935a04d15239380825988abd1029e11fefb38`.

## Contrato de versión (opt-in)

- Antes del filtro, la consulta `q` de T-08 devolvía 3 tarjetas y 13 lecturas vigentes; no declaraba ausencia.
- Con `version_antes_de` explícito y corte comprobado: 404 `version_no_disponible`, cero tarjetas y cero lecturas; no se llamó al buscador.
- Edición incluida exacta: 200, 3 tarjetas y 10 lecturas literales con versiones correctas.
- Verificación final observada el 2026-11-09T00:32:24+01:00: corte histórico 404 sin tarjetas/lecturas; edición incluida 200 con 3 tarjetas y 10 lecturas; 11 rechazos esperados adicionales (ausencia exacta, parámetros vacíos/duplicados/inválidos, corte estricto y ayuda sin q); 2 casos `q`-only con 35 cuerpos idénticos. Runtime final SHA256 `65a8d971623a5b4951e52f5d15f706fa0b94f2584128cfb81a9ce2359b3a2fa3`, distinto del SHA `1b99…` del binario medido; recorrido ordinario intacto, sin repetir batería. Servidor local detenido.
- El filtro compara fechas ISO indexadas; no infiere vigencia legal ni ediciones desde `q`. El SHA del runtime medido es `1b99da8dd1c5f34f444578f64dc935a04d15239380825988abd1029e11fefb38`; el commit final se traza en el historial.

## Transparencia

- T-08: versión histórica ausente; evaluador `no_disponible` sin tokens ni baseline. HTTP devolvió 3 tarjetas y 13 páginas vigentes; no se afirma que la API declare ausencia ni que pase un negativo de disponibilidad.
- No desplegado; Pages y corpus estable intactos. No se midieron imágenes, extracción multimodal A, wrappers ni uso real en ChatGPT/Claude.
- La paridad textual no certifica tablas, ejes o fórmulas visuales; el PDF fuente íntegro sigue siendo la referencia (`#page=N`; no se afirma que `/estatico` sirva PNG si no se probó).
- Historial previo intacto: B mediana 1,01×, índice estático fallido 1,240× y variantes 10/12.
