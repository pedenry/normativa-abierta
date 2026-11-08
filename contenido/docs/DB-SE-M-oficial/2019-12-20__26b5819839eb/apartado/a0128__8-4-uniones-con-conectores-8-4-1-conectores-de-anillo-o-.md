---

documento: "DB-SE-M Madera"
id: "DB-SE-M-oficial"
capa: "oficial"
version: "2019-12-20"
id_tecnico: "a0128"
ruta_oficial: "8.4"
ruta_semantica: "Fragmento de PDF p67"
parent_id: null
nivel: 1
titulo: "8.4  Uniones con conectores 8.4.1  Conectores de anillo o de placa"
paginas_fisicas: "67-70"
paginas_impresas: "3-None"
sha256_documento: "26b5819839ebfda78b0b119c5e76a0a37773b0d763c05688541870075df93718"
tipos: "notas, referencias, figuras"
seccion_estimada: "Fragmento de PDF p67"
titulo_navegacion: "Fragmento de PDF p67"
ruta_fuente: "fragmento_sin_jerarquia"
clasificacion_navegacion: "no_encabezado"
es_encabezado_navegacion: false
sha256_body_normativo: "427836b6a7ad5f0b4a42b5f0c7a6f3edfbcbfff693f2d391779827ab93cc5e57"
referencias_auto_md: "sin_cambio_en_MD; usar referencias_filtradas del JSON"
---

# a0128 Fragmento de PDF p67

8.4  Uniones con conectores 8.4.1  Conectores de anillo o de placa
8.4.1  Conectores de anillo o de placa
1
En uniones realizadas con conectores de anillo de tipo A (madera-madera) o conectores de placa de
tipo B (acero-madera) según norma UNE-EN 912:2011, y con diámetro no mayor que 200 mm, el va-
lor característico de la capacidad de carga para una fuerza paralela a la fibra, Fv,0,Rk, por conector y
por plano de cortadura se obtiene de la siguiente expresión:






)
d
5,
31
(
h
k
k
)
d
35
(
k
k
k
k
min
F
c
e
3
1
5
,1
c
4
3
2
1
Rk
,
0
,v
(8.65)
siendo:
Fv,0,Rk
valor característico de la capacidad de carga paralela a la fibra, en [N];
dc
diámetro del conector, [mm];
he
profundidad de inserción, [mm];
ki
factores de modificación, con i = 1 a 4, definidos a continuación.
Nota.- El primer término de la expresión (8.65) representa el fallo por cortadura y el segundo el fallo
por aplastamiento.
2
El diámetro del perno auxiliar se elegirá de acuerdo con la tabla 8.7.
Tabla 8.7 Requisitos geométricos de los pernos auxiliares de conectores
Tipo de conector
(ver UNE-EN 912:2011)
dc
(mm)
d mínimo
(mm)
d máximo
(mm)
A – A5
 130
12
24
A1, A4, A5
> 130
0,1dc
24
B
d - 1
d
dc
diámetro del conector, [mm]
d
diámetro del perno, [mm].
El proyectista indicará el tipo de conector usado en la unión. La definición exacta del conector no se-
rá necesaria si la geometría definida es compatible con los productos comerciales disponibles para
ese tipo de conector. No obstante, y dado el limitado repertorio comercial de estos sistemas, se re-
comienda incluir en el proyecto la definición geométrica completa del conector o la marca de referen-
cia que sirva para establecer un producto igual o similar.
3
El espesor mínimo de las piezas externas de madera debe ser igual a 2,25·he, y el de la pieza inter-
na de madera debe ser igual a 3,75·he, donde he es la profundidad de inserción (véase figura 8.13).

DocumentoBásico SE-M Madera
SE-M 62
Figura 8.13 Espesores mínimos de las piezas.
4
El factor k1, depende de los espesores de las piezas t1 y t2 y de la profundidad de inserción he de la
unión, y su valor se define en la siguiente expresión:
e
2
e
1
1
h
5
/
t
h
3
/
t
1
min
k
(8.66)
5
El factor k2 depende de la distancia a la testa cargada a3,t de la unión y se aplica únicamente en
uniones con testa cargada (es decir, -30º  30º; con alfa según lo definido en 8.3.2.1.2), y se ob-
tiene de la siguiente expresión:
c
t,
3
a
2
d
2
a
k
min
k

(8.67)
ka  = 1,25   en uniones con un conector por plano de cortadura
ka  = 1,00   en uniones con más de un conector por plano de cortadura
(8.68)
a3,t  se define en la tabla 8.8.
Para otros valores de , el factor k2 se tomará igual a 1,0.
6
El factor k3 depende de la densidad de la madera y se obtiene de la siguiente expresión:
350
75
,1
min
k
k
3


(8.69)
siendo:
k
valor característico de la densidad de la madera, [kg/m3].
7
El factor k4 depende de los materiales unidos, y toma los siguientes valores:
k4 = 1,0
para uniones madera-madera;
(8.70)
k4 = 1,1
para uniones acero-madera.
(8.71)
8
En las uniones con un solo conector por plano de cortadura trabajando sin que exista testa cargada
(150º  210º), la primera condición de la ecuación 8.59 puede despreciarse.
9
El valor característico de la capacidad de carga para una fuerza que forma un `` la dirección de la
fibra, F,Rk, por conector y por plano de cortadura debe calcularse con la siguiente expresión:






2
2
90
Rk
,
0
,v
Rk
,
cos
sen
k
F
F
(8.72)
con:
k90 = 1,3 + 0,001  dc
(8.73)

DocumentoBásico SE-M Madera
SE-M 63
siendo:
Fv,0,Rk
valor característico de la capacidad de carga de un conector sometido a una fuerza para-
lela a la fibra, definido anteriormente;
dc
diámetro del conector, [mm].
10 Las separaciones y distancias mínimas deben ajustarse a las especificaciones de la tabla 8.8, con
los símbolos definidos en la figura 8.7.
Tabla 8.8 Separaciones y distancias mínimas para conectores de anillo y de placa.
Separaciones y distancias
(véase figura 6.3.2.1b)
Ángulo
Distancia mínima
a1 (paralela a la fibra)
0º  360º
(1,2 + 0,8 cos )  dc
a2 (perpendicular a la fibra)
0º  360º
1,2  dc
a3,t (testa cargada)
-90º  90º
1,5  dc
a3,c (testa no cargada)
90º  < 150º
(0,4 + 1,6 sen )  dc
150º  < 210º
1,2  dc
210º  270º
(0,4 + 1,6 sen )  dc
a4,t (borde cargado
0º  180º
(0,6 + 0,2 sen )  dc
a4,c (borde no cargado)
180º  360º
0,6  dc
11 Cuando los conectores se disponen al tresbolillo (véase figura 8.14), las distancias mínimas de sepa-
ración paralela y perpendicular a la fibra, a1 y a2 respectivamente, se pueden reducir por unos coefi-
cientes (kai) siempre que se cumpla la condición:
(ka1)2 + (ka2)2 1
(8.74)
con
0  ka1 1
0  ka2 1
siendo:
ka1
factor de reducción de la distancia mínima paralela a la fibra;
ka2
factor de reducción de la distancia mínima perpendicular a la fibra.
Figura 8.14 Distancias reducidas en conectores.
12 La distancia paralela a la fibra ka1a1 puede, además, reducirse hasta un 50 %, siempre que la capa-
cidad de carga se reduzca proporcionalmente hasta el 40 %.
13 Cuando existe una fila de conectores dispuestos paralelos a la fibra y se encuentran cargados con
una fuerza paralela a la fibra, el número eficaz de conectores se obtendrá de la siguiente expresión:
nef = 2 + (1 – n/20)  (n – 2 )
(8.75)
siendo:

DocumentoBásico SE-M Madera
SE-M 64
nef
número eficaz de conectores;
n
número de conectores situados en una línea paralela a la fibra.
Los conectores se consideran alineados con la fibra cuando ka2a2 < 0,5·ka1a1.

## Referencias detectadas (literal)

- UNE-EN

## Figuras / fórmulas

- figura/p0067.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0068.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0069.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0070.png (página visual; fórmulas extraídas pendientes de verificación)
