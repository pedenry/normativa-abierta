# 2026-11-17 · pedenry · navegación territorial del visor

Urbanismo presentaba 102 documentos en una sola tabla. Se agrupa ahora por
las 17 comunidades indicadas en las fuentes, con accesos rápidos, recuentos
y bloques desplegables accesibles por teclado, sin JavaScript.

El generador conserva las tablas con edición, páginas y capa. Las materias
sin datos territoriales mantienen su HTML anterior. Los municipios y las
provincias solo se muestran cuando constan explícitamente: actualmente hay
un municipio incorporado y ninguna provincia declarada. No se deducen del
título ni se asigna una provincia a una norma autonómica.

Comprobaciones locales:

- 25 pruebas generales y 10 del generador pasan; seis son nuevas de navegación.
- Antes de publicar pasan las 185 pruebas unitarias de las cinco suites del proyecto.
- 149 documentos, 9.681 páginas físicas y 11.132 segmentos conservados.
- Corpus de entrada con el mismo digest que el visor anterior.
- 20.994 salidas cotejadas por hash: solo cambian cinco archivos de presentación
  e informe; las 20.813 vistas de páginas y segmentos permanecen idénticas.
- Cero enlaces rotos o fuera de la raíz. Informe: [site/_informe.json](../site/_informe.json).
- Revisión por IA en escritorio y a 390 × 844: desplegables, acceso rápido,
  apertura por teclado y navegación al documento de Madrid correctos. El
  desplazamiento horizontal de las tablas queda dentro de su contenedor.

OpenCode/NaN propuso la agrupación y redactó pruebas. Su perfil no permitió
leer el generador; Codex adaptó la propuesta al esquema real, corrigió las
pruebas, ejecutó la generación y promovió únicamente las cinco salidas cambiadas.
No cambian el recuperador, los PDF, las ediciones ni las fuentes.
Pedro autorizó publicar esta versión en GitHub Pages el 2026-11-17.
Los resultados de CI y del despliegue se registran en la PR de publicación.
