---

documento: "DB-SE-AE Acciones en la edificación"
id: "DB-SE-AE-oficial"
capa: "oficial"
version: "2009-04"
id_tecnico: "a0030"
ruta_oficial: "3.5.4"
ruta_semantica: "3.5.4 Acumulación de nieve"
parent_id: "a0026"
nivel: 1
titulo: "3.5.4 Acumulación de nieve"
paginas_fisicas: "16-17"
paginas_impresas: "16-17"
sha256_documento: "26116e5088955f0c6963a6187270cad282e1e7bf5a53a90f695c8fa50b4e4487"
tipos: "figuras"
seccion_estimada: "3.5.4 Acumulación de nieve"
titulo_navegacion: "3.5.4 Acumulación de nieve"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "6df66986761c1138c298c0fc60a01f166a2a32499bf8dd72f3a3ac588959180c"
---

# a0030 3.5.4 Acumulación de nieve

3.5.4 Acumulación de nieve
1
Adicionalmente, en los faldones limitados inferiormente por limatesas y cuyo coeficiente de forma,
µ, sea menor que la unidad, descargan parte de la nieve aguas abajo. Tal descarga ocasiona acu-
mulaciones de nieve si hay discontinuidades como limahoyas o cambios de nivel en esa dirección.
La descarga total por unidad de longitud, pd, puede evaluarse como:
pd = (1-µ)·L·sk
(3.4)
siendo:
L
proyección horizontal media de la recta de máxima pendiente del faldón.
2
La acumulación de nieve sobre una discontinuidad (limahoya o cambio de nivel) aguas abajo del
faldón se simula mediante una carga lineal, pa, de valor:
pa = min (µi, 1) · pd
(3.5)
que puede suponerse repartida uniformemente en un ancho no mayor que 2,0 m a un lado u otro de
la limahoya o del cambio de nivel.
3
Si queda descarga por repartir (pd > pa), se considerará otra discontinuidad más debajo sometida a
la carga restante, y así sucesivamente hasta repartir la totalidad de la descarga o llegar al perímetro
del edificio. En cualquier caso, la suma de todas las cargas sobre discontinuidades no será mayor
que la descarga total del faldón.
4
Sobre cada discontinuidad se sumarán, en su caso, las descargas que puedan provenir de los dis-
tintos faldones que haya aguas arriba.

Documento Básico SE-AE Acciones en la edificación
SE-AE 13

## Figuras / fórmulas

- figura/p0016.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0017.png (página visual; fórmulas extraídas pendientes de verificación)
