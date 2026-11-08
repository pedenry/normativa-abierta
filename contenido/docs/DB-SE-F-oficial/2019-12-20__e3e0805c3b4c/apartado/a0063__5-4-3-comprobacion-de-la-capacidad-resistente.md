---

documento: "DB-SE-F Fábrica"
id: "DB-SE-F-oficial"
capa: "oficial"
version: "2019-12-20"
id_tecnico: "a0063"
ruta_oficial: "5.4.3"
ruta_semantica: "5.4.3  Comprobación de la capacidad resistente"
parent_id: null
nivel: 1
titulo: "5.4.3  Comprobación de la capacidad resistente"
paginas_fisicas: "28-28"
paginas_impresas: "3-3"
sha256_documento: "e3e0805c3b4c307519c26dc34c3fdbf143d842edd013c91b0f52d2c73403d91c"
tipos: "referencias, formulas, figuras"
seccion_estimada: "5.4.3  Comprobación de la capacidad resistente"
titulo_navegacion: "5.4.3  Comprobación de la capacidad resistente"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "9bef80843cb9a2b2aec483ac34e6213acd2c91f5e00ce52c911907584c8c3eac"
referencias_auto_md: "sin_cambio_en_MD; usar referencias_filtradas del JSON"
---

# a0063 5.4.3  Comprobación de la capacidad resistente

5.4.3  Comprobación de la capacidad resistente
1
Es aceptable el uso de cualquier procedimiento que dé como resultado un conjunto de esfuerzos en
equilibrio con las acciones consideradas.
2
En cualquier dirección, el momento de cálculo aplicado, MSd, será menor o igual que el momento
resistente, MRd, es decir:
MSd MRd
(5.25)
3
Como valor de MRd puede tomarse:
como pieza a flexión, si no hay compresión:
MRd = fxd · Z
(5.26)
pieza a flexión, si hay compresión:
MRd = (fxd + d) · Z
(5.27)
como arco con relación longitud a canto mayor de 35
MRd = E·(td3 / L2)·r/8
(5.28a)
como arco con relación longitud a canto menor de 35
MRd = (fd·td – fd2L2/ tdE)·r/2
(5.28b)
siendo:
Z
módulo resistente elástico a flexión de la sección bruta, igual a t2/6; en un muro apilastrado,
se adoptará como longitud de resalto no más del décimo de la altura, para los sustentados
en cabeza y base, y un quinto para los libres en cabeza.
d
valor de cálculo de la tensión media de compresión del muro, en la sección que corres-
ponda
r
altura del arco, según 5.4.4
4
Como viga vertical, si no puede contarse con la resistencia a tracción, como es el caso de muros de
carga, en donde el fracaso del muro puede suponer el colapso de la estructura, o con acción sísmica:
MRd1 = Nd · (t-2·e-Nd/fd)/2
(5.29)
siendo:
Nd
valor de cálculo de la compresión vertical del muro debida a acciones verticales
t
el grueso del muro
e
la excentricidad de la compresión, con su signo, debida a las acciones verticales
5
En otro caso, se podrá proceder análogamente, bien por reparto de los momentos isostáticos en cada
dirección, de acuerdo a la relación de capacidades resistentes, tal como se ha hecho en (5.23) y
(5.24), o por equilibrio límite en la situación de agotamiento por flexión, a partir de esos mismos pa-
rámetros.
6
Cuando en uno de los bordes exista una barrera antihumedad, no será necesario considerarla si la
carga vertical sobre la barrera asegura que, por causa del momento aplicado, no se supera la resis-
tencia a la flexión (véase apartado 4.5.2.3). En otro caso se considerará como tendel hueco.

## Referencias detectadas (literal)

- apartado 4.5.2.3

## Figuras / fórmulas

- figura/p0028.png (página visual; fórmulas extraídas pendientes de verificación)
