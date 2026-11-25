---
fecha: 2026-11-25
zona: Europe/Madrid
titulo: Consolidación de ramas en main
tipo: handoff
usuario_github_verificado: pedenry (id 35270581, metadatos del merge base)
solicitante: Pedro
ejecutor: Codex
commits: base 0b52fb1e, merges de PR 1 a 5
estado: main verificada como única rama local y en GitHub
---

## Estado de la integración

Los cinco tips de los PR son ancestros de `main`. Antes de retirar las ramas se simularon las 21 fusiones por pares entre las siete referencias locales, todas sin conflictos. Se cambió a `main` y se retiraron las seis ramas locales con `git branch --delete`. Tras publicar `main` en `2e29ce55`, se comprobó que incluía los cinco tips remotos y se eliminaron esas ramas en una sola operación. La consulta posterior a GitHub devolvió únicamente `main`. Los enlaces a los PR y los commits de merge permiten localizar los cambios aunque se retiren esas ramas.

## Qué reutilizar de cada rama

### `docs/uso-colaboracion-seguridad`

El merge `24ca346f` incorpora las guías de uso y colaboración, el piloto SUA depurado y el refuerzo del servidor HTTP. Empezar por [uso local](../docs/uso-local.md), [contribución](../CONTRIBUTING.md), [seguridad](../SECURITY.md) y [el piloto SUA](../evaluacion/piloto_sua/README.md). El commit `e8b451cc` cubre el plazo absoluto HTTP y el caso de fallo al arrancar el temporizador. Para repetir las pruebas del piloto sin una clave API, ejecutar `python -B -m unittest discover -s evaluacion/piloto_sua -p "test_*.py" -v` desde la raíz. [PR #1](https://github.com/pedenry/normativa-abierta/pull/1)

### `codex/publicar-ampliacion-boe`

El merge `e96163ab` incorpora quince fuentes del BOE con edición, licencias y huellas, y el generador reproducible del visor. La validación previa registró 46 documentos en total y preservó la conducta para ediciones ausentes. Para reconstruir un candidato desde el corpus público, ejecutar `python -B herramientas/generar_site.py --contenido contenido --salida .local/visor-candidato`. Consultar la [guía de generación](../docs/generacion-visor.md) y la [validación de publicación](2026-11-15-pedenry-evaluacion-publicacion-boe.changelog.md). [PR #2](https://github.com/pedenry/normativa-abierta/pull/2)

### `codex/cierre-territorial-recuperacion`

El merge `b2b2d423` incorpora la tanda territorial y las mejoras de recuperación. El cierre registró 149 documentos distribuibles, cobertura de las 17 comunidades autónomas y una incorporación municipal, Málaga. La recuperación filtra mediante metadatos y solicita ubicación cuando es necesaria. La CI reúne consultas con documento, consultas libres ubicadas y consultas sin ubicación. El commit `35d1cd90` registra en `.gitleaksignore` falsos positivos revisados. Consultar el [cierre territorial](2026-11-16-pedenry-evaluacion-cierre-territorial.changelog.md) y la [batería territorial](../evaluacion/regresion_recuperacion/territorial/README.md). [PR #3](https://github.com/pedenry/normativa-abierta/pull/3)

### `codex/http-aclaracion-territorial`

El merge `1adea4c7` lleva la aclaración territorial a HTTP. `/buscar` sin documento pide la ubicación cuando corresponde y evita sustituir una ordenanza municipal por una fuente de otra jurisdicción. La [guía HTTP](../experimentos/http-local/README.md) describe el servicio experimental. Para repetir la regresión contra el servidor local, usar `python -B evaluacion/regresion_recuperacion/territorial/ejecutar_http.py --servidor local`. El [registro HTTP](2026-11-17-pedenry-evaluacion-http-territorial.changelog.md) enlaza resultados y referencia. [PR #4](https://github.com/pedenry/normativa-abierta/pull/4)

### `codex/visor-territorios`

El merge `0b52fb1e` agrupa Urbanismo por comunidad autónoma y facilita navegar por el territorio en móvil. La entrada sigue en [Urbanismo](../site/materia/urbanismo.html). Para adaptar la agrupación, partir de [generar_site.py](../herramientas/generar_site.py) y revisar [las pruebas del visor](../tests/test_visor_territorios.py) y [su registro de evaluación](2026-11-17-pedenry-evaluacion-visor-territorios.changelog.md). Los grupos reflejan las fuentes incluidas en el corpus. [PR #5](https://github.com/pedenry/normativa-abierta/pull/5)

### `codex/reglas-hs5-residuales`

La rama apuntaba a la misma base que `main`. El trabajo sin commit se conservó en el directorio de trabajo de `main`. El lote se incorporó después a `main` mediante un commit propio. Incluye una exportación del DB HS 5 edición 2022-06-14 para las tablas 4.1, 4.3, 4.4 y 4.5, y datos de acometidas del artículo 95 de la ordenanza municipal de Madrid. El [registro HS5](2026-11-25-pedenry-recuperacion-tablas-hs5.changelog.md) y la [guía de reglas](../contenido/reglas/README.md) documentan la exportación y la huella pendiente del PDF de Madrid. Se verificó la reproducción con `python -B herramientas/exportar_hs5_residuales.py --comprobar`.

## Pendiente y límites

- El responsable autorizado puede retirar las cinco referencias de GitHub tras volver a verificar que sus tips están incluidos en `origin/main`.
- Los resultados funcionales enlazados corresponden a las validaciones históricas. En esta consolidación se comprobó el historial y el estado de Git, y se verificó la reproducción de las tablas HS5.
- La recuperación y el visor aportan evidencia documental. La cobertura municipal es parcial y la aplicabilidad a un expediente exige verificar ámbito y régimen transitorio.
