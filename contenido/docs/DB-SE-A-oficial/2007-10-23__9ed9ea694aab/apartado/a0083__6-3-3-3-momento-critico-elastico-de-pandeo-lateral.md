---

documento: "DB-SE-A Acero"
id: "DB-SE-A-oficial"
capa: "oficial"
version: "2007-10-23"
id_tecnico: "a0083"
ruta_oficial: "6.3.3.3"
ruta_semantica: "6.3.3.3 Momento crítico elástico de pandeo lateral"
parent_id: null
nivel: 1
titulo: "6.3.3.3 Momento crítico elástico de pandeo lateral"
paginas_fisicas: "45-46"
paginas_impresas: "45-46"
sha256_documento: "9ed9ea694aabfbda3bfbbef40dfe9223fde05d13c35bc2ba9751e5a96a22a64f"
tipos: "referencias, formulas, tablas, figuras"
seccion_estimada: "6.3.3.3 Momento crítico elástico de pandeo lateral"
titulo_navegacion: "6.3.3.3 Momento crítico elástico de pandeo lateral"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "8fba3b940884ab0927f6b44e2bf50a6aec140d3c8e37a583960753c79dadf703"
referencias_auto_md: "sin_cambio_en_MD; usar referencias_filtradas del JSON"
---

# a0083 6.3.3.3 Momento crítico elástico de pandeo lateral

6.3.3.3 Momento crítico elástico de pandeo lateral
1
en la mayoría de los casos prácticos es admisible un cálculo simplificado del momento crítico elás-
tico de pandeo lateral, a pesar de las diferencias en las condiciones de apoyo, la introducción de
las cargas y la distribución de los momentos flectores.
2
En los casos en los que los apoyos en los extremos de una barra impidan su deformación por tor-
sión, y si la carga actúa en el eje de la barra, el momento crítico elástico de pandeo lateral se po-
drá determinar según la ecuación:
2
LTw
2
LTv
CR
M
M
M
+
=
(6.35)
siendo:
MLTv
componente de MCR que representa la resistencia por torsión uniforme de la barra (S. Ve-
nant)
MLTw
componente de MCR que representa la resistencia por torsión no uniforme de la barra.
3
La componente MLTv del momento crítico elástico de pandeo lateral se podría determinar a partir
de la ecuación:
z
T
C
1
LTv
EI
GI
L
C
M
π
=
(6.36)
siendo:
C1
factor que depende de las codiciones de apoyo y de la ley de momentos flectores que so-
liciten y la viga
Lc
longitud de pandeo lateral (distancia entre apoyos laterales que impidan el pandeo lateral)
G
módulo de elasticidad transversal
E
módulo de elasticidad
IT
constante de torsión uniforme
IZ
momento de inercia de la sección respecto al eje z
Para las vigas con secciones esbeltas (apartado 5.2.3) se adoptará MLTv=0.
4
La componente MLTw del momento crítico elástico de pandeo lateral viene determinada por la car-
ga crítica elástica de pandeo del soporte comprimido del perfil. Este soporte está formado por el
ala comprimida y la tercera parte de la zona comprimida del alma, adyancente al ala comprimida.
La componente MLTw se podrá determinar a partir de la ecuación;
2
z,f
1
2
C
2
y
,
el
LTw
i
C
L
E
W
M
π
=
(6.37)
siendo
Wel,y
módulo resistente elástico de la sección, según el eje de fuerte inercia, correspondiente a
la fibra más comprimida
if,z
radio de giro, con respecto al eje de menor inercia de la sección, del soporte formado por
el ala comprimida y la tercera parte de la zona comprimida del alma, adyacente al ala
comprimida
Las características mecánicas de la sección del soporte comprimido arriba mencionado se deter-
minarán para la sección eficaz.
5
El factor C1 tiene en cuenta las condiciones de apoyo y la ley de momentos flectores que solicitan
la viga. Los valores indicados en la tabla 6.7 son válidos para tramos de vigas en cuyos extremos

DocumentoBásico SE-A Acero
SE-A-44
el giro torsional esté totalmente coaccionado y a lo largo de los cuales el momento flector varia li-
nealmente
Tabla 6.7 Valor del factor C1 correspondiente a los valores del factor kϕ (kw=1)
Condiciones de apoyo y tipo de solicita-
ción
Diagrama de momentos flectores
C1
1
1,14
1,32
1,56
1,88
2,28
2,7
2,93
2,75

## Referencias detectadas (literal)

- apartado 5.2.3

## Tablas en estas páginas

- tabla/p0045_t01.json (.csv y .json con celdas y coordenadas)

## Figuras / fórmulas

- figura/p0045.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0046.png (página visual; fórmulas extraídas pendientes de verificación)
