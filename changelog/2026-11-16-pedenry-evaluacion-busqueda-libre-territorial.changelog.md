# 2026-11-16 — pedenry — evaluación — búsqueda libre territorial (cierre verificado)

- **Tipo:** cierre de evaluación ya verificado por Codex; documentado sin ejecutar shell, conservando la evaluación original.
- **Registrado por:** evaluación-normativa (nan / glm5.3-flash), 2026-11-16.
- **Alcance:** 21 consultas libres (17 CCAA + 4 municipales Málaga); la API recibe `(consulta, None, None, 20000, 2)`. Golds y queries congelados intactos.

## Resultados por criterio

- Criterio de evidencia revisado tras los resultados por cotejo independiente p33/p16, con adjudicación versionada explícita y aplicado por igual antes y después; gold/queries y resumen original intactos.
- Fuente + edición + evidencia suficiente + integridad + ámbito: 10/21 → 21/21.
- Gold exclusivo original: 9/21 → 20/21.
- Páginas exactas: 17/21 → 20/21.
- Mezcla CCAA: 10 casos → 0.

## Hallazgo y decisión

- Málaga L18: la discrepancia no era recuperación incorrecta. p33 art. 31.1 contiene la misma regla de entrada (documentación completa REGMálaga) que p16 art. 9.3; cotejo posterior independiente y hashes medidos. La evaluación original (20/21) queda visible y sin modificar.
- Alternativas solo con flag opt-in `--alternativas` y archivo [alternativas-libres-2026-11-16.json](../evaluacion/regresion_recuperacion/territorial/alternativas-libres-2026-11-16.json), documentadas en [adjudicacion-libres-2026-11-16.json](../evaluacion/regresion_recuperacion/territorial/adjudicacion-libres-2026-11-16.json); no se fuerza el motor a p16.

## Motor

- Enrutado desde metadata pública: sin IDs ni golds en producción; nacionales complementarias; solo la comunidad/municipio pedidos y el padre desde la propia fuente; municipal explícita ausente → abstiene (Madrid, Sevilla); unión Aragón/Navarra verificada.
- Scoring auxiliar original restaurado: solo `acceso._pasa_filtro` y `buscar_bm25` existentes cambiados (puerta de candidatos después del IDF global); tokenizar y selector previo intactos.
- Evaluator corregido para carpeta legacy HS sin fecha usando metadata propia (version/version_dir), sin alterar corpus.

## Verificación

- Controles CTE sin documento: 2/2 antes y después; exclusión nacional V1 rechazada.
- 48 consultas anteriores: 47 referencias intactas (primarias/puntuaciones); páginas/SHA y los 48 contextos completos con SHA idénticos.
- 116 unittest verdes: 19 generales + 19 piloto SUA + 10 herramientas + 15 evaluador + 53 HTTP.
- Rehash de 20 PDF fuente y de 8 archivos protegidos (corpus/fixtures): iguales.

## Consumo (proxy)

- Presupuesto 20k; max principal 2; aux 2; sin ampliar. Máximo de contexto observado (proxy caracteres/4): 11547 en el lote territorial de 21; 11877 en controles CTE 2; no son tokens de resultados primarios ni pronóstico.
- El informe conserva recuentos locales antes/después; no miden latencia, coste API ni ahorro OpenCode. Recuentos de texto como proxy, no facturación.

## Reproducción (desde el checkout)

```powershell
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_libres.py --alternativas evaluacion/regresion_recuperacion/territorial/alternativas-libres-2026-11-16.json --salida .local/busqueda-libre/repeticion.json
python -B evaluacion/regresion_recuperacion/territorial/ejecutar_libres.py --fixture evaluacion/regresion_recuperacion/territorial/casos-libres-controles.json --salida .local/busqueda-libre/repeticion-controles.json
```

- Salida declarada: sin flag, la discrepancia original L18 devuelve exit 1; con flag, 21/21 y exit 0; control 2/2 y exit 0.
- Informe: [resultados-libres-2026-11-16.json](../evaluacion/regresion_recuperacion/territorial/resultados-libres-2026-11-16.json), con metadata de fuentes por caso.

## Límites

- No se afirma vigencia, aplicabilidad ni calidad global; municipal solo Málaga incorporado.
- Los recuentos locales antes/después conservados en el informe no cubren latencia, coste API ni ahorro OpenCode; muestra de 21 consultas libres y 2 controles, sin repeticiones múltiples.
- Sin publicación ni commit; la verificación previa corresponde a Codex.
