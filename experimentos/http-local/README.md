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

`/buscar` devuelve tarjetas y un plan: sigue todas las lecturas pertinentes, no solo el primer resultado. Los filtros `version` y `version_antes_de` requieren documento; son edición exacta y estrictamente anterior, no una determinación de vigencia. Hoy cada documento indexado expone una edición en su `doc.json`.

`/leer` entrega la página literal y su ámbito. `/estatico` solo entrega tipos permitidos dentro de las áreas públicas. Estas protecciones no autorizan guardar allí secretos o documentación privada.

## Límites y comprobaciones

El corpus es público y se filtra por `distribute === true`. Las búsquedas pueden resultar costosas; los servidores siguen siendo experimentales, sin autenticación ni controles completos de un servicio de producción. La entrada pública necesita además protección operativa del proveedor/proxy. Consulta [seguridad](../../SECURITY.md) y [la revisión de publicación](../../docs/revision-publicacion.md).

Pruebas locales sin API:

```sh
python -B -m unittest discover -s experimentos/http-local/tests -p "test_*.py" -v
```

La conservación de texto no certifica la interpretación de tablas, imágenes o fórmulas. Los recuentos HTTP históricos medían cuerpos y rutas tokenizados, no consumo real de un chat. El piloto posterior sí registra uso API, pero no valida automáticamente otras interfaces.
