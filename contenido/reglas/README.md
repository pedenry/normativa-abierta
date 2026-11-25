# Tablas de saneamiento para herramientas de cálculo

La [ficha municipal de Madrid](../fichas/MADRID-ANM-2011-146.json) enlaza el capítulo de acometidas de la ordenanza. La [regla del artículo 95](madrid-acometidas-art95-2011-04-08.json) registra 300 mm nominales, autorización expresa para diámetros mayores, pendiente uniforme entre 2 % y 4 % y resalto entre 0,40 y 0,80 m. El resalto se mide en el receptor. El ámbito es el municipio de Madrid y el tramo de acometida. Se cotejó el artículo en HTML y en la página física 32 del PDF oficial. El corpus incorpora la ficha con referencia y los parámetros cuantitativos. La descarga automatizada de los bytes del PDF respondió HTTP 403, por lo que su huella queda pendiente. [PDF oficial consolidado](https://sede.madrid.es/eli/es-md-01860896/odnz/2006/06/21/%282%29/con/20110408/spa/pdf#page=32)

El archivo [DB HS 5 · aguas residuales](db-hs-5-residuales-2022-06-14.json) proporciona las tablas 4.1, 4.3, 4.4 y 4.5 de la edición de 14 de junio de 2022. Incluye esquema, edición, hash del PDF y página física de cada tabla. El PDF descargado del portal del CTE el 25 de noviembre de 2026 tenía el mismo SHA-256 que el del corpus. La aplicabilidad a cada proyecto exige comprobar el ámbito y el régimen transitorio. [Original oficial](https://www.codigotecnico.org/pdf/Documentos/HS/DBHS.pdf#page=117)

Las filas de aparatos declaran las unidades de desagüe y los diámetros en milímetros en el orden de columnas del JSON. Los grupos completos de baño y aseo son alternativas a sus aparatos individuales. Los guiones del original se representan mediante nulos. Las pendientes del 1 %, 2 % y 4 % son columnas discretas del documento. Las reglas de diseño, las excepciones y el contexto aplicable se consultan en el PDF. El JSON es una fuente de datos para cálculos reproducibles.

Para regenerar o comprobar el artefacto local, desde la raíz:

```sh
python -B herramientas/exportar_hs5_residuales.py
python -B herramientas/exportar_hs5_residuales.py --comprobar
```

El exportador exige el PDF de origen con el hash fijado. Coteja las celdas de las tablas de capacidad entre CSV y texto de página, y el orden de las cargas de aparatos entre ambas extracciones. Los identificadores de aparatos siguen el orden y los rótulos de la tabla 4.1. Las tablas de otras disciplinas requieren un cotejo específico antes de usarlas en cálculos.
