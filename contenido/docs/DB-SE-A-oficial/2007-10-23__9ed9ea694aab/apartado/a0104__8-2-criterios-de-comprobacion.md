---

documento: "DB-SE-A Acero"
id: "DB-SE-A-oficial"
capa: "oficial"
version: "2007-10-23"
id_tecnico: "a0104"
ruta_oficial: "8.2"
ruta_semantica: "8.2 Criterios de comprobación"
parent_id: null
nivel: 1
titulo: "8.2 Criterios de comprobación"
paginas_fisicas: "61-63"
paginas_impresas: "61-63"
sha256_documento: "9ed9ea694aabfbda3bfbbef40dfe9223fde05d13c35bc2ba9751e5a96a22a64f"
tipos: "referencias, formulas, figuras"
seccion_estimada: "8.2 Criterios de comprobación"
titulo_navegacion: "8.2 Criterios de comprobación"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "20529b634248d2f0f428c1e4ddc62a088551cccb91ae9086c03f5412680c29ca"
referencias_auto_md: "sin_cambio_en_MD; usar referencias_filtradas del JSON"
---

# a0104 8.2 Criterios de comprobación

8.2 Criterios de comprobación
1
Las uniones se comprobarán a resistencia. Además se comprobará la capacidad de rotación de las
uniones en las que se prevea la formación de rótulas plásticas en el análisis global.
2
En toda unión debe verificarse que los valores de cálculo de los efectos de las acciones, Ed para
cualquiera de las situaciones de cálculo (o combinaciones de acciones relevantes), no superan la
correspondiente resistencia de cálculo, Rd, obtenida según el apartado 8.4, esto es:
d
d
R
E
≤
(8.1)
debiéndose dimensionar con capacidad para resistir los mínimos siguientes:
a)
en el caso de nudos rígidos y empalmes la mitad de la resistencia última de cada una de las
piezas a unir;
b)
en el caso de uniones articuladas la tercera parte del axil o el cortante último (según el caso)
de la pieza a unir.
3
El reparto de los esfuerzos sobre la unión entre los elementos que la componen puede realizarse
mediante métodos elásticos o plásticos. En cualquier caso:
a)
los esfuerzos sobre los elementos de la unión equilibrarán los aplicados a la propia unión;
b)
la distribución de esfuerzos será coherente con la de rigideces;
c)
si se utilizan criterios de distribución en régimen plástico, se supondrán mecanismos de fallo
razonables, por ejemplo los basados en la rotación como sólido rígido de una de las partes de
la unión;
d)
si se utilizan criterios de distribución en régimen plástico, se comprobará la capacidad de de-
formación de los elementos.
4
Debe tenerse en cuenta la excentricidad existente en una unión. En el caso de uniones de angula-
res atornilladas con al menos dos tornillos en una de las alas se podrán considerar las líneas de
gramil de los tornillos como ejes de gravedad, considerando sólo la parte de sección de los angula-
res cuyo eje de gravedad coincide con ellos.
5
Se deben considerar las tracciones adicionales debidas al “efecto palanca” (véase figura 8.1.a)) si
la naturaleza de la unión hace que éstas aparezcan. En la evaluación de las tracciones debidas al
efecto palanca, Q, se considerarán las rigideces relativas de las chapas de la unión y la geometría
de la misma. El efecto palanca puede evitarse aumentando la rigidez de los elementos (chapa fron-
tal) de la unión (figura 8.1.b)). Se admite convencionalmente que no hay efecto palanca si la longi-
tud de alargamiento del tornillo o perno Lb (igual a la distancia entre la mitades de la cabeza y la
tuerca, -o en caso de anclajes a cimientos, el punto a 8 diámetros desde la superficie de inserción
en la zapata- ) supera el valor siguiente:
3
ef
3
2
b
t
l
m
d
9,6
L
≥
(8.2)
siendo (ver figura 8.1.b):
lef
la longitud eficaz en flexión de ala de la T, correspondiente al tornillo considerado.
d
diámetro del tornillo o perno

DocumentoBásico SE-A Acero
SE-A-60
t
espesor de ala de la T
m
distancia del tornillo a la línea de formación de la rótula plástica (o charnela).
En la figura 8.1.c. se representa dicha condición límite para tornillos en uniones con chapa frontal,
de espesor de ala y chapa frontal similares, y para pernos de anclaje a cimentación. Los métodos
de comprobación establecidos en 8.8.3, y siguientes. tienen en cuenta implícitamente el efecto pa-
lanca.
6
En las uniones soldadas sólo se considerarán las tensiones que intervienen en la transmisión de
esfuerzos y no las residuales, como, por ejemplo, aquellas tensiones normales paralelas al cordón
de soldadura.
7
En las uniones de perfiles conformados y chapas plegadas es admisible el empleo de elementos
no contemplados en este DB (tornillos autorroscantes, soldaduras por puntos, fijación mediante
conectadores de estructuras mixtas, etc.) siempre que:
a)
cuenten con el respaldo experimental suficiente, garantizado por el correspondiente sello;
b)
se respeten las prescripciones de uso (distancias al borde, densidad de puntos, etc.);
c)
aseguren una forma dúctil de fallo (por ejemplo, que la capacidad del tornillo supere la de la
chapa a desgarro).

DocumentoBásico SE-A Acero
SE-A-61
0
1
2
3
4
5
1
2
3
4
5
6
7
8
9
10
11
12
m/t
leff/t
d/t=0,25
d/t=0,50
d/t=0,25
d/t=1
d/t=0,50
d/t=2
d/t=1
d/t=2
Tornillos
Anclajes
Figura 8.1 Efecto palanca (condición límite)

## Referencias detectadas (literal)

- apartado 8.4

## Figuras / fórmulas

- figura/p0061.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0063.png (página visual; fórmulas extraídas pendientes de verificación)
