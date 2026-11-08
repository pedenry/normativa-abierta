---

documento: "DB-SE-A Acero"
id: "DB-SE-A-oficial"
capa: "oficial"
version: "2007-10-23"
id_tecnico: "a0049"
ruta_oficial: "5.3.1"
ruta_semantica: "5.3.1 Traslacionalidad"
parent_id: "a0048"
nivel: 1
titulo: "5.3.1 Traslacionalidad"
paginas_fisicas: "27-28"
paginas_impresas: "27-28"
sha256_documento: "9ed9ea694aabfbda3bfbbef40dfe9223fde05d13c35bc2ba9751e5a96a22a64f"
tipos: "formulas, figuras"
seccion_estimada: "5.3.1 Traslacionalidad"
titulo_navegacion: "5.3.1 Traslacionalidad"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "8c71ff592be8ff716ecacff65adc07fc10e4ba77104bd5007a020ba5605caadb"
---

# a0049 5.3.1 Traslacionalidad

5.3.1 Traslacionalidad
1
En el caso de las estructuras traslacionales, o no arriostradas, en las que los desplazamientos tie-
nen una influencia sustancial en los esfuerzos, debe utilizarse un método de cálculo que incluya
efectos no lineales y considere las imperfecciones iniciales, o sus acciones equivalentes, sustituto-
rias de las desviaciones geométricas de fabricación y montaje, de las tensiones residuales, de las
deformaciones iniciales, variaciones locales del límite elástico, etc. Dicho método puede consistir
en
a)
Análisis global en segundo orden considerando imperfecciones iniciales globales y en la geo-
metría de las piezas. En este caso en las comprobaciones de resistencia de las piezas no se
considerarán los efectos de pandeo que ya estén representados en el modelo.
b)
Análisis global en segundo orden considerando sólo las imperfecciones iniciales globales. En
este caso  en las comprobaciones de resistencia se considerarán los efectos de pandeo de
las piezas. Una aproximación a los resultados obtenidos por este método se describe en el
apartado siguiente.
2
Una forma de evaluar la influencia de los desplazamientos en la distribución de esfuerzos y, por
tanto, de caracterizar la condición de traslacionalidad, aplicable a estructuras de pórticos planos,
consiste en realizar un primer análisis en régimen elástico lineal y obtener, para cada planta, el co-
eficiente:
h
H
V
r
d
,
H
Ed
Ed
δ
⋅
=
(5.6)
siendo
HEd
valor de cálculo de las cargas horizontales totales (incluyendo las debidas a imperfeccio-
nes) en la planta considerada y en todas las superiores. Coincide con el cortante total en
los pilares de la planta;
VEd
valor de cálculo de las cargas verticales totales en la planta considerada y en todas las su-
periores. Coincide con el axil total en los pilares de la planta;
h
altura de la planta;

DocumentoBásico SE-A Acero
SE-A-26
δH,d
desplazamiento horizontal relativo de la planta (del forjado de techo al de suelo).
Si para alguna planta el valor del coeficiente r es superior a 0,1, la estructura debe considerarse
traslacional y, entonces, el análisis global de la estructura habrá de considerar los efectos de los
desplazamientos en alguna de las siguientes formas:
a)
Análisis en segundo orden, con la ayuda de modelos numéricos que incluyan, al menos, el
efecto de los esfuerzos en la rigidez de la estructura. En el dimensionado de los pilares se uti-
lizarán como longitudes de pandeo las correspondientes al modo intraslacional.
b)
Análisis elástico y lineal pero habiendo multiplicado todas las acciones horizontales sobre el
edificio por el coeficiente de amplificación:
r
1
1
−
(5.7)
Este procedimiento sólo es aplicable cuando r<0,33. En el dimensionado de los pilares se uti-
lizarán como longitudes de pandeo las correspondientes al modo intraslacional. Las reaccio-
nes en cimentación se obtendrán del citado modelo reduciendo las componentes de fuerza
horizontal en el valor del coeficiente de amplificación, de modo que resulten equivalentes a la
resultante horizontal de las acciones de cálculo no amplificadas.

## Figuras / fórmulas

- figura/p0027.png (página visual; fórmulas extraídas pendientes de verificación)
- figura/p0028.png (página visual; fórmulas extraídas pendientes de verificación)
