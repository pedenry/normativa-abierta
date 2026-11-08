---

documento: "DB-SE-A Acero"
id: "DB-SE-A-oficial"
capa: "oficial"
version: "2007-10-23"
id_tecnico: "a0084"
ruta_oficial: "6.3.3.4"
ruta_semantica: "6.3.3.4 Abolladura del alma por cortante"
parent_id: null
nivel: 1
titulo: "6.3.3.4 Abolladura del alma por cortante"
paginas_fisicas: "46-48"
paginas_impresas: "46-48"
sha256_documento: "9ed9ea694aabfbda3bfbbef40dfe9223fde05d13c35bc2ba9751e5a96a22a64f"
tipos: "referencias, formulas, tablas, figuras"
seccion_estimada: "6.3.3.4 Abolladura del alma por cortante"
titulo_navegacion: "6.3.3.4 Abolladura del alma por cortante"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "6fd799d8c8a9a2070855527e7f79be8125faaef3a25d67aa4a5d4a526ecf116e"
referencias_auto_md: "sin_cambio_en_MD; usar referencias_filtradas del JSON"
---

# a0084 6.3.3.4 Abolladura del alma por cortante

6.3.3.4 Abolladura del alma por cortante
1
No es preciso comprobar la resistencia a la abolladura del alma en las barras en las que se cum-
pla:
ε
⋅
<
70
t
d
(6.36)
ni en aquellas en las que, disponiendo de rigidizadores en sus extremos (e intermedios, en su ca-
so), se cumpla:
τ
⋅
ε
⋅
<
k
30
t
d
(6.37)
siendo
d, t
dimensiones del alma (altura y espesor);

DocumentoBásico SE-A Acero
SE-A-45
y
ref
f
f
=
ε
con fref = 235 N/mm2.
kτ es igual:
-
kτ =
2
d
a
34
,5
4






+
Si existen rigidizadores separados una distancia  a<d
-
kτ =
2
d
a
4
34
,5






+
Si existen rigidizadores separados una distancia  a ≥ d
-
kτ=5,34
Si existen rigidizadores sólo en las secciones extremas
2
La inercia Is de la sección formada por el rigidizador más una anchura de alma a cada lado del ri-
gidizador igual a 15 twε,  con relación a su fibra neutra, paralela al plano del alma, ha de ser:
2
d
a
si
a
t
d
5,1
l
2
3
3
s
<
⋅
≥
(6.38)
2
d
a
si
t
d
75
,0
l
3
s
≥
⋅
⋅
≥
(6.39)
3
La resistencia del alma a abolladura por cortante se obtiene de:
1
M
b
Rd
,
b
t
d
V
γ
τ
⋅
⋅
=
(6.40)
siendo








λ
⋅
=
τ












−
λ
⋅
−
⋅
=
τ
=
τ
w
_
y
b
w
_
y
b
y
b
9,0
3
f
8,0
625
,0
1
3
f
3
f
si
w
_
w
_
w
_
2,1
2,1
8,0
8,0
λ
≤
<
λ
<
≤
λ
donde
τ
ε
=
λ
k
4
,
37
t/
d
w
4
Cada rigidizador intermedio se dimensionará como un soporte solicitado por el esfuerzo de com-
presión:
Rd
,
b
Ed
Ed
V
V
N
−
=
(6.41)
siendo
VEd
valor de cálculo del esfuerzo cortante
Vb,Rd
valor de cálculo de la resistencia a abolladura por cortante

DocumentoBásico SE-A Acero
SE-A-46
En caso de existir cargas exteriores que puedan actuar directamente sobre el rigidizador, éstas se
añadirán al valor de NEd. La sección resistente incluirá el rigidizador mas una anchura de alma a
cada lado del rigidizador, igual a 10 twε. La verificación de la seguridad estructural del rigidizador
se llevará a cabo de acuerdo con los métodos del apartado 6.3.2, utilizando la curva de pandeo c
con una longitud de pandeo de 0,8 d.

## Referencias detectadas (literal)

- apartado 6.3.2

## Tablas en estas páginas

- tabla/p0047_t01.json (.csv y .json con celdas y coordenadas)
- tabla/p0048_t01.json (.csv y .json con celdas y coordenadas)

## Figuras / fórmulas

- figura/p0046.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0047.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0048.png (página visual; fórmulas extraídas pendientes de verificación)
