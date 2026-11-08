---
fecha: 2026-11-09
zona: Europe/Madrid
titulo: Experimento HTTP local de consulta
tipo: intent
usuario_github_verificado: pedenry (id 35270581)
solicitante: usuario humano de la sesión en contexto pedenry
ejecutor: Codex para comandos, prueba crítica y verificación; preparación OpenCode
herramienta: OpenCode con NaN; modelo nan/deepseek-v4-flash verificado por tool run
commits: repositorio estable sincronizado en b12ab29a6e54d78e7bd762d5b1a563cc6dcebb2d; este experimento aún no se publica
estado: preparación local; sin prueba crítica ejecutada ni publicación
---

## Propósito

Probar si una consulta HTTP local read-only reduce la transferencia de índices sin perder recuperación, páginas, citas ni condiciones. El cliente no descarga el índice completo: pide `/buscar`, recibe tarjetas y sigue enlaces `/leer` literales.

## Hipótesis y alcance

- Hipótesis: quitar del cliente los índices completos y servir sólo búsqueda + lecturas necesarias reduce tokens frente a B (texto completo del documento pertinente + entrada).
- Se conservan páginas literales completas, ámbito, notas, definiciones, excepciones, referencias y enlaces a fuentes.
- Gate inicial: 6 casos críticos originales (SA01, SC02, SI01, SI02, T02, T07) y exactamente 2 variantes existentes (P-SA01, C-T02); documento, página, citas y versión/SHA, más condiciones según evidencia.
- Los 6 controles quedan fuera del ajuste. Legacy 27/31 y umbral 40 % se informan separados; no bloquean si documental/fuente son correctos.

## Exclusiones

No se usa BetterChecker, BC, S3, los 50 PDF privados, API pagada ni el servidor publicado. No se copian fixtures, respuestas esperadas ni rutas privadas al repositorio público. La comparación A (PDF multimodal vs preparado) no se mide; B usa el baseline congelado de texto extraído.

## Estado

Runtime y evaluador preparados localmente. Sin resultados de la prueba crítica, sin commit, push ni despliegue.

## Alcance histórico posterior

Se añadió un filtro opt-in de edición (`doc+version` o `doc+version_antes_de`) para distinguir versiones indexadas. No decide vigencia jurídica ni infiere ediciones desde el texto de la consulta. La prueba de corte explícito y la conservación del camino `q` ordinario se registran en el changelog.
