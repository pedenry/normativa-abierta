---

documento: "DB-SE-M Madera"
id: "DB-SE-M-oficial"
capa: "oficial"
version: "2019-12-20"
id_tecnico: "a0056"
ruta_oficial: "5.3.3"
ruta_semantica: "5.3.3  Pórticos y arcos planos"
parent_id: null
nivel: 1
titulo: "5.3.3  Pórticos y arcos planos"
paginas_fisicas: "25-26"
paginas_impresas: "None-2"
sha256_documento: "26b5819839ebfda78b0b119c5e76a0a37773b0d763c05688541870075df93718"
tipos: "figuras"
seccion_estimada: "5.3.3  Pórticos y arcos planos"
titulo_navegacion: "5.3.3  Pórticos y arcos planos"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "2e48946cd8aef827df2d22c1c111d5738cede94849acd5bada68fc384ceda45b"
---

# a0056 5.3.3  Pórticos y arcos planos

5.3.3  Pórticos y arcos planos
1
Cuando los esfuerzos generados como consecuencia del desplazamiento de la estructura no sean
despreciables, debe relizarse un análisis de segundo orden como sucede con algunos pórticos tras-
lacionales en los que los esfuerzos axiales de compresión no están muy alejados de las cargas críti-
cas de pandeo. Los esfuerzos deben determinarse considerando, además, las posibles imperfeccio-
nes geométricas y estructurales, es decir, las desviaciones entre los ejes geométricos y el centro
elástico de la sección transversal, debidas, por ejemplo, a la falta de homogeneidad del material, y
las combaduras previas de las piezas. Éstas se estiman de la manera siguiente:
a) pórticos planos; la forma imperfecta de la estructura puede considerarse como equivalente a una
desviación inicial que es una aproximación a la deformada real, obtenida mediante la aplicación
de ángulos de giro Φ en los soportes de la estructura junto con una combadura inicial de forma
sinusoidal entre nudos de la estructura definida por la excentricidad máxima e.
El valor mínimo de , en radianes, debe ser:
 = 0,005
para h5 m
(5.6)
h
5
005
,0 =

para h>5m
(5.7)
siendo:
h
longitud del soporte, [m];
el valor mínimo de e debe ser:
e = 0,0025·l
(5.8)
siendo:
l
longitud de la viga, [m].
b) Arcos; para tener en cuenta las desviaciones en el análisis lineal de segundo orden se tomarán
las deformaciones iniciales siguientes (figura 5.2).
El valor mínimo de e debe ser:
e = 0,0025·l1  para carga simétrica
(5.9)
e = 0,0025·l2  para carga no simétrica
(5.10)
siendo:

DocumentoBásico SE-M Madera
SE-M 20
l1 y l2  longitud de la cuerda, desde el punto de apoyo al punto de intersección de la directriz del
arco con su deformada en análisis de primer orden, para carga simétrica y no simétrica,
respectivamente.
a) Definición de la geometría inicial
b) Desviación correspondiente a carga simétrica
c) Desviación correspondiente a carga asimétrica
Figura 5.2 Ejemplo de desviaciones iniciales de la geometría de un pórtico a dos aguas y de un arco

## Figuras / fórmulas

- figura/p0025.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0026.png (página visual; fórmulas extraídas pendientes de verificación)
