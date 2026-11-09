---
fecha: 2026-11-09T11:43:10+01:00
zona: Europe/Madrid
titulo: Prueba en ChatGPT con el enlace de GitHub y con PDF adjuntos
tipo: changelog
usuario_github_verificado: pedenry (id 35270581)
solicitante: pedenry
ejecutor: Codex
herramienta_modelo: OpenCode documentos con nan/glm5.3-flash, para preparar la rúbrica y el registro
commit_base_observado: 3a275a83924a0dffbd190e10b2620911bf40414f
estado: completado
---

# Prueba en ChatGPT con el enlace de GitHub y con PDF adjuntos

## Diseño de la prueba

Se intentaron y completaron tres pares con seis respuestas en total, tomando la primera generación de cada chat. Los casos ficticios cubrieron una tabla con nota del DB-SI, el alcance de una reforma según el RITE y la compatibilidad de usos del RSCIEI. Cada brazo se ejecutó en un chat nuevo de Chrome dentro de la misma sesión de ChatGPT Gratis, con Búsqueda en Internet activa al enviar. La interfaz no identificó el modelo concreto. La pregunta fue idéntica dentro de cada par. El brazo A recibió únicamente el enlace a la raíz de GitHub, desde la que se accede al visor. El brazo B recibió únicamente el PDF oficial completo de la edición fijada. Se verificó el SHA-256 de cada PDF local y la presencia de un único adjunto en cada chat B. El orden de envío fue A/B, B/A y A/B. Los criterios se fijaron antes del envío. Codex cotejó la rúbrica preparada por OpenCode contra la fuente, corrigió las referencias de RITE y concretó las excepciones de DB-SI, con cinco criterios binarios por caso y con la trazabilidad evaluada por separado. [Repositorio de la prueba](https://github.com/pedenry/normativa-abierta).

## Ejecución e incidencias

El primer encargo a OpenCode se detuvo sin salida y se repitió con el mismo especialista. Al generar las respuestas, los brazos A de DB-SI y de RITE mostraron un error de carga que se resolvió recargando los chats, sin reenviar ni regenerar. Un clic de envío del brazo B de RSCIEI agotó el tiempo y se repitió tras comprobar que el mensaje seguía en borrador, sin duplicarlo.

## Resultado del caso DB-SI

El caso DB-SI usó la edición 2025-03-04, apartado SI 3 punto 3, tabla 3.1 y nota (1), páginas físicas 24 a 25. A y B alcanzaron 5/5 con cita verificable y la misma edición. A aportó citas de interfaz al visor por página y B citas del adjunto. [PDF oficial](https://www.codigotecnico.org/pdf/Documentos/SI/DBSI.pdf) · [Visor, página 24](https://pedenry.github.io/normativa-abierta/site/pagina/db-si-oficial-2025-03-04-0a2e78cd6247__p0024.html) · [Visor, página 25](https://pedenry.github.io/normativa-abierta/site/pagina/db-si-oficial-2025-03-04-0a2e78cd6247__p0025.html)

## Resultado del caso RITE

El caso RITE usó el consolidado 2022-08-02, artículos 2.2, 2.4 y 2.5, página física 8. A y B alcanzaron 5/5 e identificaron edición, disposición y página esenciales. A indicó la página 8 en el texto y la respaldó con una cita a la ficha del visor. Sus citas de los apartados adicionales apuntaron a las páginas 12, 13 y 14. B mostró el adjunto en el mensaje inicial y dio referencias en el texto de la respuesta, sin una cita clicable al adjunto. Incluyó un enlace al BOE sin evidencia visible de que hubiera consultado esa web. Fuera de la rúbrica, B situó el artículo 10 en la página 11. Está en la página 10 del PDF. La página 8 del visor se verificó de forma independiente. [BOE](https://www.boe.es/eli/es/rd/2007/07/20/1027/con) · [Visor, página 8](https://pedenry.github.io/normativa-abierta/site/pagina/rite-asociada-sin-fecha-ad1680c83bf4__p0008.html)

## Resultado del caso RSCIEI

El caso RSCIEI usó el RD 164/2025, publicado el 2025-04-10, artículo 4.2, página 37. A y B alcanzaron 5/5 y ambas respuestas resultaron trazables a edición, sección y página. A citó la página 37 del visor con la etiqueta de interfaz del artículo 5, cuyo destino contiene el artículo 4.2, junto a un enlace explícito a la página. B citó el adjunto y también la versión web del mismo decreto en el BOE y la interfaz mostró la consulta externa. Esa mezcla impide atribuir el resultado de B exclusivamente al adjunto. B añadió otro precepto de la página 23 e identificó el artículo 4.2 como decisivo. [BOE](https://www.boe.es/eli/es/rd/2025/03/04/164/con) · [Visor, página 37](https://pedenry.github.io/normativa-abierta/site/pagina/rsciei-asociada-sin-fecha-85aa0af25d51__p0037.html)

## Fidelidad de criterios

El enlace conservó los 15 criterios que cubrieron los PDF en los tres casos. La fidelidad medida se limita a esos criterios. El DB-SI fue el único par con citas visibles a ambos insumos y sin consulta externa observada.

## Tokens como indicador descriptivo

El consumo de tokens quedó sin medir en los seis turnos. La interfaz carecía de contador por respuesta y la evidencia visible solo permitía comprobar citas y páginas. La API documenta un recuento para sus propias entradas. [Documentación de OpenAI](https://developers.openai.com/api/docs/guides/token-counting).

Se contó el texto literal extraído por el corpus con `tiktoken` 0.14.0 y `cl100k_base`, sumando por página y excluyendo imágenes y metadatos. Para A se contaron las páginas físicas identificadas en la respuesta y corroboradas. Para B se contó todo el texto disponible en el PDF entregado.

| Caso | Texto de las páginas citadas en A | Texto completo del PDF de B |
| --- | ---: | ---: |
| DB-SI | 1.989 tokens, páginas 24 y 25 | 69.587 tokens, 92 páginas |
| RITE | 3.974 tokens, páginas 8 y 12 a 14 | 98.282 tokens, 97 páginas |
| RSCIEI | 1.060 tokens, página 37 | 114.963 tokens, 108 páginas |

En el RITE, 3.144 de los 3.974 tokens corresponden a páginas con cita directa en la interfaz. En el RSCIEI, ambas cifras describen el tamaño de sus textos y la consulta externa de B impide una atribución al adjunto.
