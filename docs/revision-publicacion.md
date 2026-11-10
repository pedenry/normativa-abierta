# Revisión de publicación · 2026-11-10

Solicitante: pedenry. Integración, comandos y comprobaciones: Codex. Revisión especializada y parches: OpenCode, perfiles `fuentes-normativas`, `recuperacion-normativa` y `evaluacion-normativa`, modelo `nan/glm5.3-flash`. Es una revisión asistida por IA, no una auditoría externa ni una certificación de seguridad.

## Alcance

Base publicada: `07133b3067d5d8e3f73231c495e1739a987fa0c1`, 8 commits accesibles en el historial revisado. Se examinaron archivos públicos, cambios locales candidatos a publicación, código de recuperación/HTTP y evaluación. No se abrieron las carpetas privadas exteriores ni se probaron ataques contra servicios remotos.

## Datos y secretos

- Gitleaks 8.30.1, binario oficial verificado mediante SHA-256: escaneo de los 8 commits, aproximadamente 86,74 MB, sin secretos detectados.
- El escaneo del árbol local completo produjo cuatro avisos: eran valores SHA-256 del archivo `cliente_api.py` en manifiestos, no claves API. Se verificó el campo y el formato, sin imprimir credenciales.
- Revisión adicional del árbol versionado: no se detectaron rutas personales de Windows/macOS/Linux ni archivos de credenciales con los nombres y extensiones comprobados.
- Los crudos del piloto, todavía locales, sí incluían rutas personales, identificadores y respuestas con contenido opaco. Se excluyen mediante `.gitignore`; los originales se conservan para auditoría local.
- La exportación pública mantiene las 60 respuestas semánticamente idénticas y los contadores sin cambios: 841.131 tokens entre desarrollo y evaluación. Se comprobaron los `usage` y los JSON de respuesta uno a uno. Excluye requests, logs, claves de metadatos opacos e identificadores; sustituye rutas personales.
- Los hashes de código se representan como pares `archivo`/`sha256` para evitar el falso positivo señalado, sin desactivar reglas del escáner.
- Se verificó la conservación de los 22 hashes originales. Un aviso adicional del paquete correspondía al marcador ficticio de una prueba de seguridad; se simplifica ese dato de prueba, sin excluir la prueba del escaneo.
- Los correos de autoría de los ocho commits revisados usan el dominio sintético `local.invalid`; no se encontró una dirección personal en esos metadatos.
- El paquete preparado para publicación pasó un nuevo escaneo con Gitleaks: aproximadamente 84,56 MB, sin hallazgos después de tratar los falsos positivos descritos.

El exportador está diseñado para este piloto sintético: no debe considerarse un anonimizador universal para datos de clientes.

## Corpus y derechos

Se verificaron 31 documentos con `distribute` booleano verdadero y 31 PDF fuente. Los hashes de las 16 evidencias de permiso editorial coinciden con los documentos asociados. No se alteraron fuentes ni atribuciones. El inventario puede mencionar fuentes de origen público que no están redistribuidas: una ficha o un enlace no equivale a incluir ese PDF.

No se hizo una nueva revisión jurídica de los permisos ni una validación visual completa de las 1.582 páginas. Se conservan las limitaciones de extracción, tablas y aplicabilidad normativa ya documentadas.

## Código y medidas de protección

| Hallazgo | Tratamiento |
| --- | --- |
| El HTTP local no comprobaba el Host recibido | Validación de loopback y puerto real; el handler público la desactiva explícitamente porque opera tras un proxy. |
| Búsquedas locales sin límite propio de consulta | Límite de caracteres antes de invocar el buscador. |
| El cargador HTTP no filtraba `distribute` | Filtra documentos y filas con el mismo criterio del adaptador; los 31 documentos actuales ya cumplen. |
| Excepciones internas enviadas como texto al cliente | Errores genéricos; diagnóstico solo en el proceso servidor. |
| El estático aceptaba extensiones no declaradas | Lista de tipos permitidos y rechazo de componentes ocultos, manteniendo contención y rechazo de symlinks. |
| Timeout público de inactividad sin plazo absoluto | Se añade un plazo absoluto por conexión para impedir retener indefinidamente los slots mediante goteo de cabeceras. |

No se encontró ejecución de comandos a partir de entradas HTTP. La revisión del control de rutas no identificó una vía confirmada de traversal hacia `.git` o carpetas exteriores. Las pruebas de regresión acompañan los cambios; no son una demostración de ausencia de toda vulnerabilidad.

Las búsquedas todavía pueden consumir recursos al recorrer el corpus. El servidor sigue siendo experimental: no aporta autenticación, cuotas por usuario, protección integral contra abuso ni un despliegue de producción. No se ha actualizado ni certificado el servicio remoto de Render. Un servicio público futuro necesita revisar estos límites y la protección de su proxy/plataforma.

## Prevención y colaboración

- `.gitignore` excluye credenciales, cachés, proyectos privados, configuración personal de agentes y crudos de API; no elimina nada ya versionado.
- GitHub: escaneo de secretos y protección de push ya estaban habilitados. Se habilitó la comunicación privada de vulnerabilidades y se confirmó su estado.
- Se añaden guías de uso, contribución y seguridad, instrucciones portables para agentes y plantilla de PR.
- La CI ejecuta pruebas sin API, recalcula contadores públicos y escanea el historial con Gitleaks. Actions y el binario del escáner quedan fijados; el token solo tiene lectura de contenido y no se mantiene en el checkout. No usa `pull_request_target` ni credenciales de modelos.

## Evidencia reproducible

Comprobaciones locales ejecutadas: 19 pruebas del piloto y exportación; 6 pruebas HTTP; consulta del README sobre el corpus real; simulación de las 48 solicitudes sin llamadas API. También se comprobó con un socket local que el plazo absoluto corta una conexión pese al goteo de cabeceras y permite atender la siguiente petición. La exportación se contrastó contra los originales: 60 respuestas y filas de consumo, 841.131 tokens y 22 hashes, sin cambios semánticos en las respuestas ni en los contadores.

Los PDF se marcan como binarios en `.gitattributes`; los archivos de texto nuevos se normalizan para trabajar desde Windows y Linux sin modificar el contenido de los PDF.

- [Piloto y comandos](../evaluacion/piloto_sua/README.md).
- [Exportador](../evaluacion/piloto_sua/exportar_publico.py) y [manifest de exportación](../evaluacion/piloto_sua/resultados-publicos/manifest_export.json).
- [Consumo final](../evaluacion/piloto_sua/resultados-publicos/evaluacion-20261110/resumen_consumo.json) y [rúbrica por respuesta](../evaluacion/piloto_sua/resultados-publicos/evaluacion-20261110/revision_codex.json).
- [Pruebas HTTP](../experimentos/http-local/tests/) y [workflow](../.github/workflows/comprobaciones.yml).

Un escaneo puede omitir formatos binarios, patrones desconocidos o información sensible sin apariencia de secreto. No se inspeccionaron todos los datos dentro de imágenes/PDF como si fueran documentos privados; se mantuvo el corpus público previamente seleccionado. No se reescribió el historial ni se eliminaron los crudos locales porque no se confirmó una credencial publicada que exigiera esas medidas.
