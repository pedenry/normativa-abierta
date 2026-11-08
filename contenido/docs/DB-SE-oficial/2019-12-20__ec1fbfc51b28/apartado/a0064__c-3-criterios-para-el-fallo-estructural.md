---

documento: "DB-SE Seguridad estructural"
id: "DB-SE-oficial"
capa: "oficial"
version: "2019-12-20"
id_tecnico: "a0064"
ruta_oficial: null
ruta_semantica: "C.3 Criterios para el fallo estructural"
parent_id: null
nivel: 1
titulo: "C.3 Criterios para el fallo estructural"
paginas_fisicas: "29-31"
paginas_impresas: "None-3"
sha256_documento: "ec1fbfc51b28c4d62667aec480585b76fe31727ccf1615015a5d2d2677763f8f"
tipos: "formulas, figuras"
seccion_estimada: "C.3 Criterios para el fallo estructural"
titulo_navegacion: "C.3 Criterios para el fallo estructural"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "906110debaa7b2cb4527d51a04dd2c6e13b0b721a2e705b268f2cfa6ded0e23b"
---

# a0064 C.3 Criterios para el fallo estructural

C.3 Criterios para el fallo estructural
C.3.1 Estados límite últimos
1
Se supone que el criterio de fallo de una estructura o de un elemento estructural se rige según una
función g(X) de las variables básicas X, de manera que:
a)
Para el estado deseado
g(X) > 0
(C.1a)
b)
Para el estado límite
g(X) = 0
(C.1b)
c)
Para el estado no deseado
g(X) < 0
(C.1c)
Figura C.1 Representación de la función g(X) para el caso con dos variables básicas X1 y X2; X= (X1,
X2)
2
Las variables básicas X pueden depender del tiempo (por ejemplo las acciones ambientales extre-
mas pueden variar con el tiempo, los materiales constitutivos pueden estar afectados por mecanis-
mos de deterioro en función del tiempo, la resistencia puede disminuir con el tiempo debido a pro-
cesos de fatiga).
En general, algunas de las variables de X se deben representar mediante procesos estocásticos.
En particular, la variabilidad con el tiempo significa que los máximos y mínimos de las variables de
X no se producen al mismo tiempo.
La dependencia del tiempo implica que la probabilidad de fallo está asociada con un periodo de re-
ferencia elegido, t0.
3
El fallo de una estructura o de un elemento estructural se asocia con su transición de un estado
deseado a un estado no deseado. Para la mayoría de los estados límite últimos, la probabilidad de
fallo se puede representar a través de la relación:
Pf = [g(X) < 0]
(C.2)
La probabilidad de que no exista fallo de una estructura o de un elemento estructural (probabilidad
de supervivencia, Ps, o fiabilidad) es el complemento de la probabilidad de fallo:
Ps = 1 - Pf
(C.3)
4
Si se analiza la fiabilidad de un elemento estructural o de una sección transversal con respecto a un
determinado mecanismo de fallo y una determinada combinación de acciones e influencias, la fun-
ción g(X) se puede describir, normalmente, a través de una expresión única derivada del compor-
tamiento mecánico. En estos casos, el análisis se puede considerar como un análisis de un elemen-
to (en este contexto, elemento se emplea desde el punto de vista probabilista de la palabra).
5
En los casos en los que se contemple más de un mecanismo de fallo para un elemento estructural,
o si se estudian simultáneamente varios elementos estructurales, la función g(X) puede considerar-
se como una función compuesta por varias funciones g1(X), g2(X)... .

Documento Básico SE Seguridad Estructural
SE - 24
Un análisis que tenga en cuenta simultáneamente varias condiciones gi(X) < 0 se denomina análisis
de un sistema. La definición de la función g(X) depende fuertemente de las características del sis-
tema (sistemas en los que el fallo de una sección conduce al fallo total; sistemas redundantes; sis-
temas con un comportamiento combinado).
Figura C.2 Dominios de fallo para un ejemplo con dos funciones g1(X1, X2) y g2(X1, X2) con dos varia-
bles básicas X1 y X2. a) Fallo del sistema producido por el de una sección; b) Fallo de un sistema re-
dundante
6
En una aplicación directa de los métodos probabilistas explícitos se debe demostrar que en el pe-
riodo de referencia, t0, la probabilidad de fallo de la estructura o del elemento estructural, Pf, no su-
pera la probabilidad de fallo admisible, Pf,0
0
,f
f
P
P

(C.4)
C.3.2 Estados límite de servicio
1
Para algunos estados límite de servicio, la transición de un estado deseado a un estado no desea-
do corresponde a un límite que puede estar acotado al estar asociado con una realidad mecánica.
Para otros estados límite de servicio, sin embargo, esta transición se produce en condiciones poco
acotadas y difusas. En estos casos, la transición está relacionada con una disminución más o me-
nos rápida del grado de la aptitud al servicio.
2
En términos generales, se puede definir un grado de la aptitud al servicio, , en función de un pará-
metro relacionado con el comportamiento en servicio,  (por ejemplo la deformación de una viga, la
intensidad de las vibraciones de un forjado)
0 ≤ () ≤ 1
(C.5)
Para el parámetro  se pueden establecer dos límites
a)
1: la obra se puede usar sin restricciones
b)
2: la obra no se puede usar.
Figura C.3 Grado de la aptitud al servicio, μ, en función del parámetro de servicio, 

Documento Básico SE Seguridad Estructural
SE - 25
3
En algunos casos, a efectos de una optimización económica, el grado de la aptitud al servicio se
puede expresar en términos económicos.

## Figuras / fórmulas

- figura/p0029.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0030.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0031.png (página visual; fórmulas extraídas pendientes de verificación)
