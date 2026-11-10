# Colaborar

Puedes aportar documentación, fuentes, recuperación o evaluación usando tus agentes habituales. El autor de la PR revisa el diff y las pruebas: una respuesta de un agente no es evidencia de corrección.

## Flujo de trabajo

1. Lee README.md, AGENTS.md y la guía del componente. Para cambios amplios, abre una issue con problema, resultado, alcance y comprobación prevista; sin datos confidenciales.
2. Haz un fork y crea una rama. Mantén una finalidad concreta por pull request.
3. Da al agente la tarea, los archivos pertinentes y los criterios de aceptación. Fragmenta encargos grandes; evita adjuntar el corpus completo.
4. Revisa cambios y pruebas, distinguiendo comprobado, inferido y pendiente.
5. Abre una PR hacia `main` con la plantilla. Explica resultados, límites y agentes utilizados. No adjuntes conversaciones ni secretos.

Encargo de ejemplo:

> Lee AGENTS.md. Corrige [problema] en [archivos]. Conserva edición, páginas, notas y excepciones. Respeta cambios ajenos. Si cambia el comportamiento, añade una prueba que reproduzca el fallo. Devuelve archivos, comprobación y bloqueo. No ejecutes llamadas de pago ni publiques nada.

No necesitas los perfiles privados de OpenCode del mantenedor. Configura permisos y credenciales de tu herramienta fuera de Git. Los roles de AGENTS.md describen responsabilidades, no agentes que deban estar instalados.

## Fuentes

- Propón emisor, URL oficial, jurisdicción, edición, ámbito y motivo de incorporación.
- Aporta evidencia de redistribución para ese documento exacto. Una guía no hereda el permiso de la norma a la que acompaña. No subas documentos restringidos para que se revisen después.
- Calcula SHA-256 y conserva créditos. Un cambio de bytes exige revisar la evidencia asociada.
- Mantén disposición, página física y enlace al original. Coteja tablas, unidades, umbrales, notas y excepciones; indica extracción y correcciones.
- Actualiza coherentemente fichas, índices y manifiestos. No están incluidos todos los generadores originales: acuerda el procedimiento antes de regenerar el corpus.
- Para afirmar vigencia o aplicabilidad, verifica ámbito y régimen transitorio; la fecha de edición no basta.

Revisa [LICENCIAS.md](LICENCIAS.md). El código original se integra bajo [LICENSE-CODE](LICENSE-CODE); terceros conservan sus derechos.

## Comprobaciones

Sin clave API, desde la raíz:

```sh
python -B -m unittest discover -s evaluacion/piloto_sua -p "test_*.py" -v
```

Ejecuta además las pruebas del componente modificado. En recuperación, incluye edición ausente y notas/excepciones. En seguridad, usa pruebas sintéticas, sin exponer servicios ni datos reales.

Para nuevas mediciones, fija casos, referencia y rúbrica antes de abrir respuestas; separa desarrollo y evaluación. Distingue recuperación de razonamiento y proxy local de `usage` API. Conserva fallos y reintentos; documenta cambios de criterio. No entregues el resultado esperado al modelo.

Los ensayos de pago requieren autorización y presupuesto propios. La CI no dispone de claves API. Publica evidencia depurada según [la guía del piloto](evaluacion/piloto_sua/README.md).

## Antes de enviar

- Revisa `git status`, `git diff` y `git diff --cached`; añade archivos explícitamente.
- Excluye claves, planos de clientes, rutas personales, conversaciones, crudos API y documentos sin permiso. `.gitignore` no retira archivos ya versionados.
- Describe pruebas y límites, sin afirmar revisión humana inexistente.
- Añade changelog fechado para mediciones y decisiones importantes; no reescribas resultados históricos para mejorar cifras.
- Comunica vulnerabilidades mediante [SECURITY.md](SECURITY.md), no una issue pública con el detalle explotable.
