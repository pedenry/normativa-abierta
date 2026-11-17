"""Pruebas sinteticas del visor de territorios en render_indices.

Evalua el contrato publicado para site/materia/urbanismo.html, no la
implementacion interna, CSS ni texto ornamental.

- El generador real se carga con importlib desde herramientas/generar_site.py
  (sin mocks de agrupacion). Si falta render_indices, el import falla de forma
  sonora: no se usa skip.
- Datos 100% sinteticos: sin corpus, sin nombres ni IDs de normas reales.
- Los recuentos de enlaces/anclas son proxies textuales sobre el HTML generado.
- La materia sin territorio conserva el HTML previo y los documentos se
  mantienen visibles sin atribuirles provincias que no constan en su fuente.
"""

import html
import importlib.util
import re
import unittest
from pathlib import Path

_CLAVE_MATERIA = "site/materia/urbanismo.html"
_RUTA_MATERIA = "materia/urbanismo.html"
_TEXTO_HOME = "Urbanismo por comunidad autónoma"
_SIN_TERRITORIO = ("Territorio no indicado", "Sin territorio indicado")

_RUTA_GENERADOR = Path(__file__).parents[1] / "herramientas" / "generar_site.py"
_spec = importlib.util.spec_from_file_location("generar_site_eval", _RUTA_GENERADOR)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_RUTA_GENERADOR}"
generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generador)
render_indices = generador.render_indices


def _doc(id_, slug, titulo, *, jurisdiccion=None, provincia=None, municipio=None):
    """Documento sintetico con la forma {id, slug, meta, pages, parts}."""
    meta = {"scope": "urbanismo", "title": titulo, "version": "v1-sintetica", "layer": "norma"}
    for clave, valor in (("jurisdiccion", jurisdiccion), ("provincia", provincia), ("municipio", municipio)):
        if valor is not None:
            meta[clave] = valor
    return {"id": id_, "slug": slug, "meta": meta, "pages": [{}], "parts": []}


def _materia(docs):
    salidas = render_indices(docs, [])
    assert _CLAVE_MATERIA in salidas, f"falta {_CLAVE_MATERIA}; claves: {sorted(salidas)}"
    return salidas[_CLAVE_MATERIA]


def _enlaces_doc(pagina):
    return re.findall(r"\.\./doc/([a-z0-9-]+)\.html", pagina)


def _sin_perdidas_ni_duplicados(pagina, docs):
    conteos = _enlaces_doc(pagina)
    for d in docs:
        veces = conteos.count(d["slug"])
        assert veces == 1, f"../doc/{d['slug']}.html aparece {veces} veces (esperado 1)"


def _anclas_validas(pagina, minimo=0):
    ids = re.findall(r'id="([^"]+)"', pagina)
    anclas = re.findall(r'href="#([^"]+)"', pagina)
    assert len(anclas) >= minimo, f"esperaba >= {minimo} anclas de indice rapido; hay {len(anclas)}"
    for ancla in anclas:
        assert ancla in ids, f"ancla #{ancla} sin id correspondiente en la pagina"


def _resumenes(pagina):
    return re.findall(r"<summary>(.+?) · (\d+) documentos?</summary>", pagina)


def _enlace_con_texto(pagina, texto):
    for href, etiqueta in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', pagina, re.S):
        if html.unescape(etiqueta).strip() == texto:
            return href
    return None


def test_mezcla_dos_ccaa_ambito_provincia_municipio_y_sin_territorio():
    docs = [
        _doc("s1", "doc-alfa-general", "Documento Uno", jurisdiccion="Comunidad Alfa"),
        _doc("s2", "doc-alfa-provincia", "Documento Dos", jurisdiccion="Comunidad Alfa", provincia="Provincia Uno"),
        _doc("s3", "doc-beta-municipio", "Documento Tres", jurisdiccion="Comunidad Beta", provincia="Provincia Dos", municipio="Municipio Tres"),
        _doc("s4", "doc-sin-territorio", "Documento Cuatro"),
        _doc("s5", "doc-beta-municipio-solo", "Documento Cinco", jurisdiccion="Comunidad Beta", municipio="Villa Sola"),
    ]
    pagina = _materia(docs)
    resumenes = dict(_resumenes(pagina))
    assert resumenes.get("Comunidad Alfa") == "2", f"resumenes: {resumenes}"
    assert resumenes.get("Comunidad Beta") == "2", f"resumenes: {resumenes}"
    detalles = [tag for tag in re.findall(r'<details\b[^>]*>', pagina) if 'id="' in tag]
    assert len(detalles) >= 2, f"grupos CCAA details.territorio: {len(detalles)}"
    for d in detalles:
        assert 'id="' in d, f"details de territorio sin id: {d}"
    assert any(nombre in pagina for nombre in _SIN_TERRITORIO), "el doc sin jurisdiccion no es visible"
    assert "Provincia Uno" in pagina and "Provincia Dos" in pagina
    assert "Municipio Tres" in pagina and "Villa Sola" in pagina
    for fabricada in ("Provincia Villa", "Provincia Sola", "Municipio Villa"):
        assert fabricada not in pagina, f"metadato territorial fabricado: {fabricada}"
    _anclas_validas(pagina, minimo=2)
    _sin_perdidas_ni_duplicados(pagina, docs)


def test_metadato_con_html_se_escapa_sin_inyeccion():
    docs = [_doc("x1", "doc-inyeccion", "Documento Inyectado", jurisdiccion="<script>alert(1)</script>")]
    pagina = _materia(docs)
    assert "<script" not in pagina, "metadato sin escapar: inyeccion de HTML"
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in pagina, "el nombre escapado debe seguir visible"
    assert any(nombre.startswith("&lt;script&gt;") for nombre, _ in _resumenes(pagina)), "el grupo escapado no aparece en los resumenes"
    _anclas_validas(pagina, minimo=1)
    _sin_perdidas_ni_duplicados(pagina, docs)


def test_colision_slugs_de_territorio_no_duplica_ids():
    docs = [
        _doc("c1", "doc-region-acentos", "Documento Seis", jurisdiccion="Región Á"),
        _doc("c2", "doc-region-llana", "Documento Siete", jurisdiccion="Region A"),
    ]
    pagina = _materia(docs)
    resumenes = dict(_resumenes(pagina))
    assert resumenes.get("Región Á") == "1" and resumenes.get("Region A") == "1", f"resumenes: {resumenes}"
    ids = re.findall(r'id="([^"]+)"', pagina)
    assert len(ids) == len(set(ids)), f"ids duplicados tras colision de slug: {sorted(ids)}"
    _anclas_validas(pagina, minimo=1)
    _sin_perdidas_ni_duplicados(pagina, docs)


def test_materia_sin_metadato_territorial_conserva_html_previo():
    docs = [_doc("n1", "doc-general-uno", "Documento Ocho"), _doc("n2", "doc-general-dos", "Documento Nueve")]
    pagina = _materia(docs)
    assert 'class="territorio"' not in pagina, "grupos territoriales sin metadatos territoriales"
    for nombre in _SIN_TERRITORIO:
        assert nombre not in pagina, f"grupo '{nombre}' fabricado sin docs sin jurisdiccion"
    assert "<nav" in pagina, "falta el nav previo"
    assert "<h1" in pagina, "falta el h1 previo"
    assert "<table" in pagina, "falta document_table previo"
    orden = (pagina.find("<nav"), pagina.find("<h1"), pagina.find("<table"))
    assert -1 not in orden and orden == tuple(sorted(orden)), f"orden nav/h1/table alterado: {orden}"
    _sin_perdidas_ni_duplicados(pagina, docs)
    esperado = generador.page_html('urbanismo', generador.nav(_CLAVE_MATERIA) +
        '<h1>urbanismo</h1>' + generador.document_table(docs, _CLAVE_MATERIA), _CLAVE_MATERIA)
    assert pagina == esperado


def test_home_enlaza_materia_urbanismo_por_comunidad_autonoma():
    docs = [
        _doc("h1", "doc-home-uno", "Documento Diez", jurisdiccion="Comunidad Alfa"),
        _doc("h2", "doc-home-dos", "Documento Once"),
    ]
    salidas = render_indices(docs, [])
    claves_home = [k for k in salidas if k.endswith("index.html")]
    assert claves_home, f"sin index.html en outputs: {sorted(salidas)}"
    href = _enlace_con_texto(salidas[claves_home[0]], _TEXTO_HOME)
    assert href is not None, f"el home no enlaza '{_TEXTO_HOME}'"
    assert href in (_RUTA_MATERIA, "./" + _RUTA_MATERIA), f"ruta del enlace inesperada: {href}"


def test_municipio_sin_provincia_o_comunidad_no_inventa_sus_padres():
    docs = [_doc('m1', 'doc-municipio-solo', 'Documento Local', municipio='Villa Sola'),
            _doc('g1', 'doc-general', 'Documento General')]
    pagina = _materia(docs)
    assert 'Villa Sola' in pagina and 'Territorio no indicado' in pagina
    assert 'Provincia:' not in pagina and 'Comunidad de Villa Sola' not in pagina
    _sin_perdidas_ni_duplicados(pagina, docs)
    _anclas_validas(pagina, minimo=2)


def load_tests(loader, tests, pattern):
    """Integra las funciones de evaluación en el runner unittest del proyecto."""
    suite = unittest.TestSuite()
    for name, function in sorted(globals().items()):
        if name.startswith('test_') and callable(function):
            suite.addTest(unittest.FunctionTestCase(function))
    return suite
