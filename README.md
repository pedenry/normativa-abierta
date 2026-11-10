# Normativa Abierta

Normativa de edificación preparada para consultar textos y experimentar con recuperación de evidencia para asistentes de IA. Conserva fuente, edición, hash y páginas. **No es un certificador automático de cumplimiento ni un catálogo completo de normativa vigente.**

[Visor público](https://pedenry.github.io/normativa-abierta/) · [Uso local con agentes](docs/uso-local.md) · [Colaborar](CONTRIBUTING.md) · [Seguridad](SECURITY.md) · [Licencias](LICENCIAS.md)

## Qué contiene

El corpus público tiene **31 PDF redistribuibles**, 1.582 páginas y 3.033 segmentos: 15 documentos legales y 16 guías con permiso editorial. La evidencia de reutilización está en [licencias](licencias/). Las fuentes privadas del inventario de trabajo no forman parte de la entrega.

Las páginas y apartados de `contenido/` permiten localizar el texto; el PDF original sigue siendo la referencia para tablas, fórmulas y dibujos. La extracción automática no ha recibido una revisión técnica humana completa. Una edición disponible no determina por sí sola su aplicabilidad a un proyecto.

## Cómo utilizarlo

| Necesidad | Entrada | Función |
| --- | --- | --- |
| Leer normativa | [Visor](https://pedenry.github.io/normativa-abierta/) | Navegar por materia, documento, apartado y página. |
| Recuperar evidencia con un agente local | [Guía](docs/uso-local.md) y [adaptador](experimentos/http-local/adaptador_contexto.py) | Buscar y entregar páginas literales al asistente. No requiere clave API para recuperar texto. |
| Repetir la comparación con un modelo | [Piloto SUA](evaluacion/piloto_sua/README.md) | Ensayo por API frente a PDF indexado, con gasto y permisos explícitos. |

Pegar un enlace en un chat no ejecuta el adaptador. Para el uso local, el asistente debe poder ejecutar Python y acceder a la carpeta. Su interfaz puede bastar: no hace falta desplegar una web propia. Usar un modelo remoto puede enviarle planos y textos; recuperación local no significa modelo local.

## Primera consulta

Requisitos: Git y Python 3.12 o posterior. Descarga el repositorio:

```sh
git clone https://github.com/pedenry/normativa-abierta.git
cd normativa-abierta
```

La [guía de uso](docs/uso-local.md) explica el entorno y el contador opcional. Esta consulta funciona sin clave API:

```sh
python -B experimentos/http-local/adaptador_contexto.py --consulta "Anchura libre de paso de un pasillo en itinerario accesible de uso Administrativo" --documento DB-SUA-oficial --version 2022-06-14 --presupuesto 20000 --max 3
```

Usa `python3` si así se llama el ejecutable en tu equipo. El resultado es JSON con estado, páginas y `texto_contexto`. Recupera normativa: no analiza por sí solo planos ni comprueba un edificio entero. No sustituye una edición ausente.

## Qué se ha medido

El [piloto SUA](changelog/2026-11-10-pedenry-evaluacion-adaptador-pdf-sua.changelog.md) comparó 8 casos sintéticos, 3 repeticiones por método y el mismo modelo:

| Evaluación | Adaptador | PDF indexado |
| --- | ---: | ---: |
| Tokens API: entrada + salida | 252.776 | 423.093 |
| Veredicto esperado | 24/24 | 23/24 |
| Rúbrica completa, incluidas citas aplicables | 23/24 | 3/24 |

El consumo bruto fue **40,3 % menor**. Solo 3 de las 24 parejas superan todos los criterios en ambos métodos: todas son abstenciones por una edición ausente. No demuestra ahorro con calidad equivalente en comprobaciones completas de proyectos reales. Gran parte de la diferencia de calidad procede de páginas citadas incorrectamente. La revisión fue por IA, no por un técnico humano.

Los [resultados depurados](evaluacion/piloto_sua/resultados-publicos/) conservan respuestas, recuperación y contadores, junto a la [referencia](evaluacion/piloto_sua/referencia.md) y el [protocolo](evaluacion/piloto_sua/protocolo.md). Los ensayos anteriores permanecen en [changelog](changelog/). Estos resultados no se trasladan automáticamente a ChatGPT, Codex, Claude u otro modelo o interfaz.

## Colaboración y estructura

[CONTRIBUTING.md](CONTRIBUTING.md) explica propuestas, agentes y pull requests. [AGENTS.md](AGENTS.md) contiene instrucciones portables; no obliga a un proveedor concreto.

- `contenido/`: fuentes públicas, índices, páginas y apartados.
- `site/` e `index.html`: visor estático.
- `experimentos/http-local/`: recuperador, adaptador y servidores experimentales.
- `evaluacion/piloto_sua/`: casos sintéticos, pruebas y evidencia depurada.
- `docs/`: uso y revisión de publicación.
- `licencias/` y `LICENCIAS.md`: derechos por fuente.
- `changelog/`: cambios y mediciones fechados.

## Derechos y seguridad

[LICENSE-CODE](LICENSE-CODE) cubre el código original. **No hay una licencia MIT global para los documentos.** Revisa [LICENCIAS.md](LICENCIAS.md) y cada ficha antes de redistribuir. Conserva créditos y, cuando proceda, «Basado en datos de la Agencia Estatal Boletín Oficial del Estado».

No publiques planos de clientes, claves, conversaciones privadas ni resultados crudos de API. Los fallos de seguridad se comunican por el [canal privado](https://github.com/pedenry/normativa-abierta/security/advisories/new), según [SECURITY.md](SECURITY.md).
