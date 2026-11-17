# Recuperación local y servidores experimentales

Para trabajar con planos y un asistente, empieza por [uso local](../../docs/uso-local.md). El adaptador CLI funciona sin servidor ni clave API. El ensayo con un modelo y sus límites están en [el piloto SUA](../../evaluacion/piloto_sua/README.md).

## Componentes

- `acceso.py`: búsqueda e índices del corpus público.
- `adaptador_contexto.py`: páginas completas por consulta, documento y edición; advertencias y metadatos.
- `http_consulta.py`: servidor de consulta local.
- `servicio_publico.py`: entrada experimental separada para pruebas tras un proxy TLS; ver [ALOJAMIENTO.md](ALOJAMIENTO.md). No es una aplicación de revisión de proyectos.

Requisitos: Python 3.12 o posterior. El contador opcional `tiktoken==0.14.0` reproduce el proxy usado en el piloto. Sin él se utiliza una aproximación; ninguno de los dos equivale a tokens API.

## Arrancar el HTTP local

Desde la raíz del repositorio:

```sh
python -B experimentos/http-local/http_consulta.py --port 31117
```

En equipos que lo requieran, usa `python3`. Solo admite escucha en `127.0.0.1` o `localhost`; usa el Host y el puerto de esa escucha. No expongas este proceso mediante túneles ni lo conectes a carpetas privadas.

```sh
curl "http://127.0.0.1:31117/"
curl "http://127.0.0.1:31117/buscar?q=pasillo&doc=DB-SUA-oficial&version=2022-06-14"
curl "http://127.0.0.1:31117/leer?doc=DB-SUA-oficial&page=36"
```

`/buscar` devuelve tarjetas y un plan: sigue todas las lecturas pertinentes, no solo el primer resultado. Con `doc`, conserva el contrato anterior: exige `version` o `version_antes_de`, edición exacta y estrictamente anterior respectivamente. Sin `doc`, usa el adaptador para resolver el ámbito o pedir aclaración; las tarjetas y lecturas proceden de las páginas que entrega ese adaptador. Hoy cada documento indexado expone una edición en su `doc.json`. Seleccionar una edición no determina vigencia.

## Contexto y aclaración por HTTP

`GET /contexto` entrega el resultado completo del adaptador: `estado`, `texto_contexto`, páginas físicas y hashes, recuperación y advertencias. No entrega la ruta absoluta de la carpeta del servidor. Usa un presupuesto local de 20.000 y dos resultados principales; no llama a un modelo. El presupuesto es un recuento proxy, no facturación de API. Si se excede, conserva el contexto y declara `presupuesto_excedido`.

```sh
curl --get --data-urlencode "q=¿Qué documentación necesito para solicitar una licencia de obras?" "http://127.0.0.1:31117/contexto"
curl --get --data-urlencode "q=En Málaga, ¿qué documentación necesito para solicitar una licencia de obras?" "http://127.0.0.1:31117/contexto"
curl --get --data-urlencode "q=¿Qué elementos conecta la línea general de alimentación?" --data-urlencode "doc=BOE-A-2002-18099" --data-urlencode "version=2025-09-03" "http://127.0.0.1:31117/contexto"
```

Cuando falta el lugar necesario, devuelve HTTP 200 con `estado: aclaracion_necesaria`, la pregunta en `aclaracion.pregunta`, los datos que faltan en `aclaracion.campos_requeridos` y cero páginas/resultados. El cliente pregunta al usuario y repite `q` incorporando el lugar. El servidor no mantiene una conversación ni inventa una ubicación. Las consultas nacionales que no la necesitan pueden recuperar evidencia directamente.

`doc` es opcional en `/contexto` y puede usarse solo. `version` requiere `doc`; `version_antes_de` también, y es excluyente con `version`. Una edición o documento ausente devuelve 404; parámetros inválidos, 400; un fallo interno, 500 genérico. Cuando se identifica una petición municipal sin fuente incorporada, devuelve `sin_resultados`, sin sustitución por otra ciudad. Los filtros territoriales, la pregunta de aclaración y la selección de páginas se reutilizan del adaptador. La detección del lugar y la intención sigue siendo heurística; las pruebas no cubren todas las formulaciones posibles.

Los dos servidores comparten este flujo. El servicio público conserva sus límites de longitud, métodos, parámetros y plazo; en sus ejemplos sustituye el puerto por 31118. La implementación local no acredita un despliegue HTTP público. GitHub Pages sigue siendo un visor estático.

El arranque HTTP prepara las estadísticas globales y las vistas de puntuación del corpus una vez para reutilizarlas entre peticiones. El IDF sigue calculándose sobre todas las fuentes públicas y los filtros se aplican después. El corpus queda fijado para ese proceso: reinicia el servidor tras actualizarlo. Esta preparación no cambia los valores predeterminados de la API ni de la CLI, y no amplía el plazo absoluto del servidor público.

`/leer` entrega la página literal y su ámbito. `/estatico` solo entrega tipos permitidos dentro de las áreas públicas. Estas protecciones no autorizan guardar allí secretos o documentación privada.

## Límites y comprobaciones

El corpus es público y se filtra por `distribute === true`. Las búsquedas pueden resultar costosas; los servidores siguen siendo experimentales, sin autenticación ni controles completos de un servicio de producción. La entrada pública necesita además protección operativa del proveedor/proxy. Consulta [seguridad](../../SECURITY.md) y [la revisión de publicación](../../docs/revision-publicacion.md).

Pruebas locales sin API:

```sh
python -B -m unittest discover -s experimentos/http-local/tests -p "test_*.py" -v
```

La conservación de texto no certifica la interpretación de tablas, imágenes o fórmulas. Los recuentos HTTP históricos medían cuerpos y rutas tokenizados, no consumo real de un chat. El piloto posterior sí registra uso API, pero no valida automáticamente otras interfaces.
