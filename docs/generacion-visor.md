# Generar y publicar el visor estático

El visor es una representación de `contenido/`. El generador público conserva las rutas existentes y produce HTML estático, sin servidor de consulta ni dependencias de terceros. Los cambios del adaptador local y la publicación del visor se comprueban por separado.

## Generar un candidato

Desde la raíz del checkout, con Python 3.12 o posterior:

```sh
python -B herramientas/generar_site.py --contenido contenido --salida .local/visor-candidato
```

La salida contiene `index.html` y el directorio `site/`: portadas, índices, documentos, segmentos, páginas físicas, estilos e informe `site/_informe.json`. El candidato no copia los PDF ni el corpus. Los enlaces a `contenido/` se validan contra el origen y están preparados para su ubicación final en la raíz del repositorio.

La generación no depende de la hora del reloj: con las mismas entradas debe producir los mismos archivos. El informe registra los recuentos, las huellas de las entradas, los tamaños y la comprobación de enlaces. Un error de hash de PDF, enlace o ruta fuera de la raíz debe resolverse antes de promover la salida.

## Qué puede aparecer

- El texto y los PDF se incluyen únicamente para documentos con `distribute=true`. Las fuentes restringidas conservan solo ficha y enlace externo, sin reproducir su contenido.
- Cada documento y página conserva la edición, procedencia, referencia al PDF y advertencias de la fuente. La copia del PDF mantiene su SHA-256.
- La ampliación BOE de 2026-11-15 añade 15 disposiciones y 2.742 páginas; el corpus contiene 46 documentos, 4.324 páginas y 5.775 segmentos. Sus segmentos nuevos son páginas físicas, no artículos o apartados oficiales validados.
- Los textos consolidados del BOE se identifican como informativos. El Código Estructural incorporado es la publicación original de 2021-08-10 y conserva el aviso sobre correcciones posteriores. Las atribuciones se describen en [LICENCIAS.md](../LICENCIAS.md).

Estos controles de publicación no comprueban por sí solos la fidelidad completa de tablas, fórmulas o notas, ni la vigencia o aplicabilidad de una norma a un proyecto.

## Comprobar y promover localmente

Pruebas locales sin llamadas a modelos:

```sh
python -B -m unittest discover -s herramientas/tests -p "test_*.py" -v
python -B -m unittest discover -s evaluacion/piloto_sua -p "test_*.py" -v
python -B -m unittest discover -s experimentos/http-local/tests -p "test_*.py" -v
```

1. Ejecutar las pruebas del generador y las suites del adaptador; revisar `site/_informe.json`, con cero enlaces rotos o fuera de la raíz. Comprobar que todas las rutas previamente publicadas siguen disponibles.
2. Comparar dos generaciones con las mismas entradas para confirmar determinismo. Comprobar los hashes de los PDF y los recuentos del corpus.
3. Revisar el diff candidato y conservar los cambios locales ajenos. La promoción copia únicamente `.local/visor-candidato/index.html` a `index.html` y `.local/visor-candidato/site/` a `site/` en la raíz del checkout. No copiar `.local/` ni regenerar los documentos fuente como parte de este paso.
4. Revisar el visor promovido con un servidor local en escritorio y móvil: portada, materia, documento REBT, Código Estructural y una página de texto. Abrir enlaces a PDF y comprobar que edición y avisos son visibles.
5. Revisar el diff final y ejecutar `git diff --check`. Añadir a Git rutas explícitas del encargo, sin incorporar carpetas privadas, archivos de trabajo o configuraciones personales.

La tanda actual conserva los documentos anteriores. Si en otra actualización se retira una fuente, copiar encima de `site/` puede dejar HTML antiguo: hay que identificar y retirar expresamente sus salidas tras revisar las rutas, los derechos y los enlaces afectados.

## Publicación y comprobación remota

La publicación autorizada de esta tanda abarca los 15 PDF BOE y sus derivados públicos, junto con la actualización del visor y la documentación. El responsable ejecuta Git y la publicación después de las comprobaciones. El generador y los scripts de ingesta no realizan esas acciones.

GitHub Pages sirve la rama `main`, desde la raíz del repositorio. Tras incorporar el cambio, comprobar que las comprobaciones de GitHub pasan y que Pages ha terminado de publicar el mismo SHA. Abrir la portada y páginas nuevas desde la URL pública, y verificar una descarga PDF contra su hash registrado.

El registro de publicación debe indicar el commit, las pruebas realmente ejecutadas, la comprobación remota y los límites pendientes. Preparar un candidato o registrar autorización no acredita que un despliegue haya finalizado.
