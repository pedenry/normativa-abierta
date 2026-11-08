---

documento: "DB-SE-M Madera"
id: "DB-SE-M-oficial"
capa: "oficial"
version: "2019-12-20"
id_tecnico: "a0144"
ruta_oficial: "10.2.1.3"
ruta_semantica: "10.2.1.3  Esfuerzos en las piezas de fijación, separadores y presillas"
parent_id: "a0141"
nivel: 1
titulo: "10.2.1.3  Esfuerzos en las piezas de fijación, separadores y presillas"
paginas_fisicas: "84-85"
paginas_impresas: "None-1"
sha256_documento: "26b5819839ebfda78b0b119c5e76a0a37773b0d763c05688541870075df93718"
tipos: "formulas, figuras"
seccion_estimada: "10.2.1.3  Esfuerzos en las piezas de fijación, separadores y presillas"
titulo_navegacion: "10.2.1.3  Esfuerzos en las piezas de fijación, separadores y presillas"
ruta_fuente: "candidato_tipografico_plano"
clasificacion_navegacion: "encabezado"
es_encabezado_navegacion: true
sha256_body_normativo: "9a9a2f1248dabe71a979bca2566707c990f169a163aeb0b816fa23c929784863"
---

# a0144 10.2.1.3  Esfuerzos en las piezas de fijación, separadores y presillas

10.2.1.3  Esfuerzos en las piezas de fijación, separadores y presillas
1
El esfuerzo en las piezas de fijación, separadores y presillas, debe deducirse de acuerdo con lo indi-
cado en la figura 10.4, en función del esfuerzo cortante total en los cordones,Vd ,  obtenido mediante
las expresiones siguientes:
Td=Vd . l1 /a1
Figura 10.4 Distribución de esfuerzos en cordones, separadores y presillas.
c
d
,c
d
k
120
F
V
para  ef < 30
(10.35)
c
ef
d
,c
d
k
3600
F
V


para 30  ef <  60
(10.36)
c
d
,c
d
k
60
F
V
para 60  ef
(10.37)
siendo:
Fc,d
valor de cálculo del esfuerzo axial aplicado;
ef
esbeltez eficaz obtenida de la ecuación (10.31);
kc
coeficiente de pandeo asociado a la esbeltez mecánica ef, obtenido en el punto b) del apar-
tado 10.2.1.2.
2
De la Figura 10.4 se establecen los esfuerzos, así como otras consideraciones relativas a esfuerzos
y deslizamiento de las uniones, a tener en cuenta en el cálculo y dimensionado de cordones, sepa-
radores y presillas.
a) Esfuerzo cortante en el cordón.
Como consecuencia del cortante total, cada cordón deberá resistir un esfuerzo cortante per-
pendicular a la fibra, de valor:
Vd /n
(10.38)
siendo:
Vd
esfuerzo cortante total del soporte según las expresiones (10.35) a (10.37);
n
número de cordones del soporte.
b) Esfuerzos en separadores y presillas.
Cada separador y presilla se calculará para resistir los siguientes esfuerzos:
i) cortante:
-
soporte de dos cordones;
T2,s,d = Vd l1/a1
para cada separador
(10.39)
T2,p,d = 0,5.Vd l1/a1
para cada presilla
(10.40)
-
soporte de tres cordones;

DocumentoBásico SE-M Madera
SE-M 79
T3,s,d = 0,5.Vd l1/a1
para cada separador
(10.41)
T3,p,d = 0,25.Vd l1/a1
para cada presilla
(10.42)
-
soporte de cuatro cordones.
T4,s,e,d = 0,3.Vd l1/a1
para cada separador extremo
(10.43)
T4,s,c,d = 0,4.Vd l1/a1
para cada separador central
(10.44)
T4,p,e,d = 0,15.Vd l1/a1
para cada presilla extrema
(10.45)
T4,p,c,d = 0,2.Vd l1/a
para cada presilla central
(10.46)
ii) momento (solamente para presillas):
-
soporte de dos cordones;
M2,p,d = Td .a1/4
para cada presilla
(10.47)
-
soporte de tres cordones;
M3,p,d = Td .a1/3
para cada presilla
(10.48)
-
soporte de cuatro cordones.
M4,p,d = Td .a1/2,4
para cada presilla
(10.49)
siendo:
Vd
esfuerzo cortante total del soporte definido en el punto a);
Td =
Vd . l1/a1;
l1
separación entre uniones con separadores o presillas (véase figura 10.3);
a1=
a+h;
a y h
separación entre cordones y grueso del cordón, respectivamente, (véase
figura 10.3).
c) Esfuerzos en las uniones (cordón-separador o cordón-presilla).
La unión (cordón-separador o cordón-presilla), tanto encolada como con elementos mecánicos
de fijación, deberá resistir los esfuerzos que le correspondan de los determinados anteriormente,
ecuaciones (10.38) a (10.49).

## Figuras / fórmulas

- figura/p0084.png (página visual; fórmulas extraídas pendientes de verificación)
