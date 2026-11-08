---

documento: "DB-SE Seguridad estructural"
id: "DB-SE-oficial"
capa: "oficial"
version: "2019-12-20"
id_tecnico: "a0068"
ruta_oficial: null
ruta_semantica: "C.6 Métodos basados en la determinación de los valores de cálculo"
parent_id: null
nivel: 1
titulo: "C.6 Métodos basados en la determinación de los valores de cálculo"
paginas_fisicas: "34-35"
paginas_impresas: "None-2"
sha256_documento: "ec1fbfc51b28c4d62667aec480585b76fe31727ccf1615015a5d2d2677763f8f"
tipos: "tablas, figuras"
seccion_estimada: "C.6 Métodos basados en la determinación de los valores de cálculo"
titulo_navegacion: "C.6 Métodos basados en la determinación de los valores de cálculo"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "504bbac138cecad1f8c5b7f1ee96daaea876080fbf87912345c7b6f5cc55457f"
---

# a0068 C.6 Métodos basados en la determinación de los valores de cálculo

C.6 Métodos basados en la determinación de los valores de cálculo
C.6.1 Generalidades
1
El estado límite considerado podrá establecerse mediante un modelo de cálculo en términos de una
o varias funciónes g(...) de un conjunto de variables X1, X2, ... Xn relativas a las acciones, las carac-
terísticas de los materiales, etc. En este caso, la condición de ausencia del fallo de la estructura
asociado con el estado límite considerado, se podrá expresar en la forma
 

0
X
...,
,
X
,
X
g
n
2
1

(C.13)
2
A efectos de la verificación del estado límite considerado, la condición (C.13) se podrá expresar en
términos de los valores de cálculo de las variables
 

0
x
...,
,
x
,
x
g
nd
d
2
d
1

(C.14)
x1d, x2d, ..., xnd
valores de cálculo de las variables X1, X2, ..., Xn (según C.6.2).
C.6.2 Valores de cálculo según el método FORM
1
El valor de cálculo xid de la variable Xi depende de:
a)
los parámetros de la variable Xi;
b)
el tipo de distribución probabilista supuesta;
c)
el índice de fiabilidad, , requerido para el estado límite y la situación de dimensionado consi-
derados;
d)
un factor i que describe la sensibilidad de la probabilidad de fallo, asociada con el estado lími-
te y la situación de dimensionado considerados, con respecto a la variación de Xi.
2
Para una distribución arbitraria F(xi), los valores de cálculo se definen por
 

 






i
id
x
F
(C.15)
Para variables Xi con una distribución normal, se obtiene
 

i
i
i
id
V
1
x







(C.16)
siendo
i
valor medio de la variable Xi
Vi
coeficiente de variación de la variable Xi.
Para variables Xi con una distribución lognormal, se obtiene


i
i
e
x
i
id








(C.17)

Documento Básico SE Seguridad Estructural
SE - 29
donde
2
i
i
i
V
1 




## Tablas en estas páginas

- tabla/p0035_t01.json (.csv y .json con celdas y coordenadas)

## Figuras / fórmulas

- figura/p0035.png (página visual; fórmulas extraídas pendientes de verificación)
