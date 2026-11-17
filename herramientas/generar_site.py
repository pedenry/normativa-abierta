#!/usr/bin/env python3
"""Genera el visor público desde contenido/, sin fuentes privadas ni red.

La salida es un candidato con index.html y site/. Los enlaces a contenido/ se
comprueban contra el corpus de entrada sin copiarlo. Nunca escribe en la raíz
del repositorio: la promoción del candidato validado es un paso separado.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys
import unicodedata
from urllib.parse import quote, unquote, urlsplit


CSS = """body{font-family:Georgia,'Times New Roman',serif;max-width:64rem;margin:2rem auto;
padding:0 1rem;color:#1d1d1f;line-height:1.55;background:#fdfdfc}
a{color:#0b4f8a;text-decoration:none}a:hover{text-decoration:underline}
h1,h2,h3{font-family:system-ui,Segoe UI,Arial,sans-serif;line-height:1.25}
header.meta{font-size:.9rem;color:#444;border-bottom:1px solid #ddd;padding-bottom:.6rem;
margin-bottom:1.2rem}nav{font-size:.95rem;margin:.6rem 0 1.2rem}
table{border-collapse:collapse;font-size:.95rem}td,th{border:1px solid #ccc;padding:.25rem .45rem;
vertical-align:top}pre.literal{white-space:pre-wrap;background:#f6f6f4;border-left:3px solid #bbb;
padding:1rem;font-family:inherit;font-size:1rem;overflow-wrap:anywhere}
ul.apartados{list-style:none;padding-left:0}ul.apartados li{margin:.15rem 0}
ul.apartados .n1{font-weight:bold}ul.apartados .n2{padding-left:1rem}
ul.apartados .n3{padding-left:2rem}ul.apartados .n4{padding-left:3rem}
.aviso{background:#fff4e5;border:1px solid #e5b877;padding:.6rem .8rem;font-size:.9rem}
.cita{background:#eef4fa;border:1px solid #b9cfe3;padding:.6rem .8rem;font-size:.95rem}
footer{margin-top:3rem;font-size:.8rem;color:#666;border-top:1px solid #ddd;padding-top:.6rem}
img.figura{max-width:100%;height:auto;border:1px solid #ccc;margin:.4rem 0}
.tabla-scroll{overflow-x:auto}code{overflow-wrap:anywhere}h1{overflow-wrap:anywhere}
.territorio-indice ul{display:flex;flex-wrap:wrap;gap:.5rem 1rem;list-style:none;padding:0}
.territorio-indice a{text-decoration:underline}
details.territorio{border:1px solid #ccc;border-radius:.4rem;margin:.75rem 0}
details.territorio>summary{cursor:pointer;padding:.75rem 1rem;line-height:1.4;
font-family:system-ui,Segoe UI,Arial,sans-serif;font-weight:600;background:#eef4fa}
details.territorio>summary:hover{background:#e2edf6}
.territorio-contenido{padding:.5rem 1rem 1rem;min-width:0}
.territorio-sub{margin:.5rem 0}
.territorio-indice a:focus-visible,details.territorio>summary:focus-visible{
outline:3px solid #0b4f8a;outline-offset:3px}
@media(max-width:420px){.territorio-indice ul{display:grid;gap:.4rem}
details.territorio>summary{padding:.65rem .75rem}.territorio-contenido{padding:.5rem .65rem}
.territorio table{min-width:32rem;table-layout:fixed;width:100%}
.territorio th:first-child{width:50%}.territorio th:nth-child(2){width:22%}
.territorio th:nth-child(3){width:12%}.territorio th:nth-child(4){width:16%}
.territorio td:nth-child(2){white-space:nowrap}}
"""
GENERAL_WARNING = (
    "Extracción automática sin revisión técnica humana completa. Contraste tablas, "
    "fórmulas, notas y excepciones con el PDF. La edición disponible no determina "
    "la vigencia ni la aplicabilidad a un proyecto."
)
MATTER_ROUTES = {
    "Parte I": "parte-i", "Seguridad Estructural": "se",
    "Seguridad en caso de incendio": "si",
    "Seguridad utilización y accesibilidad": "sua", "Ahorro de energía": "he",
    "Protección frente al ruido": "hr", "Salubridad": "hs",
}


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def slug(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result:
        raise ValueError("Identificador sin caracteres válidos")
    return result


def hash_file(path):
    """SHA-256 por bloques; propuesta del especialista revisada contra el esquema."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def link(url, label):
    """Los datos no pueden convertir un enlace en javascript: ni en HTML."""
    parsed = urlsplit(str(url))
    if parsed.scheme and parsed.scheme not in ("https", "http"):
        return esc(label)
    if parsed.netloc and not parsed.scheme:
        return esc(label)
    return f'<a href="{esc(url)}">{esc(label)}</a>'


def relative(source, target):
    return quote(posixpath.relpath(target, posixpath.dirname(source) or "."), safe="/-_.")


def page_html(title, body, route):
    css = relative(route, "site/estilo.css")
    return (f'<!doctype html>\n<html lang="es"><head><meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{esc(title)}</title><link rel="stylesheet" href="{css}">\n'
            f'</head><body>\n{body}\n'
            '<footer>Generado estáticamente desde el corpus normalizado; sin JavaScript '
            'ni servicios externos. El HTML es una vista reproducible; conserve la fuente '
            'y la edición al citar.</footer>\n</body></html>\n')


def doc_route(doc):
    return f"site/doc/{doc['slug']}.html"


def part_route(doc, part):
    return f"site/apartado/{doc['slug']}__{part['id']}.html"


def source_page_route(doc, number):
    return f"site/pagina/{doc['slug']}__p{number:04d}.html"


def corpus_link(route, path, label, fragment=""):
    return link(relative(route, "contenido/" + path) + fragment, label)


def nav(route, doc=None):
    items = [link(relative(route, "site/index.html"), "Índice")]
    if doc:
        items.append(link(relative(route, doc_route(doc)), doc["meta"].get("code", doc["id"])))
    return '<nav>' + ' › '.join(items) + '</nav>\n'


def boe_source(doc):
    meta = doc["meta"]
    domains = {"boe.es", "www.boe.es", "boe.gob.es", "www.boe.gob.es"}
    return str(doc.get("id", "")).startswith("BOE-") or any(
        isinstance(meta.get(key), str) and urlsplit(meta[key]).hostname in domains for key in ("url", "landing"))


def consolidated(doc):
    note = doc["meta"].get("nota_capa")
    first_page = doc.get("pages", [{}])[0].get("text", "") if doc.get("pages") else ""
    return note == "consolidado" or bool(re.search(r"LEGISLACI[ÓO]N\s+CONSOLIDADA", first_page, re.I))


def warnings(doc):
    meta = doc["meta"]
    values = [GENERAL_WARNING]
    declared = meta.get("advertencias")
    declared = declared if isinstance(declared, list) else []
    for value in [meta.get("nota_capa"), *declared]:
        if isinstance(value, str) and value.strip() and value not in values:
            values.append(value)
    if boe_source(doc) and consolidated(doc):
        notice = "Consolidado meramente informativo, sin valor oficial."
        if notice not in values:
            values.append(notice)
    if meta.get("metodo_segmentacion") == "pagina_fisica":
        values.append("Segmentación por página física. No es una jerarquía de artículos verificada.")
    return '<div class="aviso"><strong>Alcance y límites</strong><ul>' + ''.join(
        f'<li>{esc(value)}</li>' for value in values) + '</ul></div>'


def editorial_credits(doc, route):
    evidence = doc["meta"].get("license_evidence")
    if not isinstance(evidence, list):
        return ""
    result = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        credits, permission = item.get("credits_page_text"), item.get("permission_text")
        if not isinstance(credits, str) or not credits.strip():
            continue
        number = item.get("page")
        source = corpus_link(route, doc["path"] + "/fuente.pdf", "Créditos y autoría en el PDF fuente",
                             f"#page={number}" if type(number) is int and number in doc["page_numbers"] else "")
        result.append('<div class="cita"><p>' + source + '. Reproducción con cita de fuente y autores.</p>')
        if isinstance(permission, str) and permission:
            result.append(f'<p>Permiso literal: {esc(permission)}</p>')
        result.append('<details><summary>Leer los créditos completos y la autoría</summary>'
                      f'<pre class="literal">{esc(credits)}</pre></details></div>')
    return '\n'.join(result)


def metadata(doc, route, number=None):
    meta = doc["meta"]
    source = meta.get("url") or meta.get("landing")
    parts = [f'<header class="meta"><p><strong>{esc(meta.get("title", doc["id"]))}</strong>'
             f' · edición {esc(meta.get("version"))} · capa {esc(meta.get("layer"))}</p>',
             f'<p>Documento <code>{esc(doc["id"])}</code> · SHA-256 del PDF '
             f'<code>{esc(meta.get("sha256"))}</code></p>']
    if number is not None:
        parts.append(f'<p>Página física {number} de {len(doc["pages"])}.</p>')
    fragment = f"#page={number}" if number else ""
    parts.append('<p>' + corpus_link(route, doc["path"] + "/fuente.pdf", "Copia fiel del PDF fuente", fragment)
                 + (' · ' + link(source, "Fuente oficial") if source else '') + '</p>')
    if meta.get("landing") and meta["landing"] != source:
        parts.append('<p>' + link(meta["landing"], "Ficha de la disposición en la fuente oficial") + '</p>')
    if meta.get("capturado_en_utc"):
        parts.append(f'<p>Captura de la fuente (UTC): {esc(meta["capturado_en_utc"])}</p>')
    if boe_source(doc):
        boe = link("https://www.boe.es", "Agencia Estatal Boletín Oficial del Estado")
        parts.append(f'<p>Texto extraído y reorganizado: Basado en datos de la {boe}. '
                     f'PDF reproducido: Fuente de los datos: {boe}.</p>')
    elif meta.get("creditos"):
        parts.append(f'<p>{esc(meta["creditos"])}</p>')
    parts.append(editorial_credits(doc, route))
    parts.append(warnings(doc) + '</header>')
    return '\n'.join(parts)


def sequential_nav(route, entries, index, make_route, label):
    links = []
    if index:
        links.append(link(relative(route, make_route(entries[index - 1])), "← " + label(entries[index - 1])))
    if index + 1 < len(entries):
        links.append(link(relative(route, make_route(entries[index + 1])), label(entries[index + 1]) + " →"))
    return '<nav>' + ' · '.join(links) + '</nav>'


def part_title(part):
    meta = part["meta"]
    return meta.get("titulo_navegacion") or meta.get("ruta_semantica") or meta.get("titulo") or part["id"]


def figure(doc, route, number):
    asset = doc["assets"].get(f"figura/p{number:04d}.png")
    if not asset:
        return ""
    href = relative(route, "contenido/" + asset)
    return (f'<figure><a href="{href}"><img class="figura" src="{href}" '
            f'alt="Página física {number}"></a><figcaption>Página visual {number}, '
            'para contrastar fórmulas, tablas y figuras.</figcaption></figure>')


def table_links(doc, route, number=None):
    tables = [path for name, path in doc["assets"].items() if name.startswith("tabla/")
              and name.endswith(".json") and (number is None or name.startswith(f"tabla/p{number:04d}_"))]
    if not tables:
        return ""
    return '<h2>Tablas extraídas</h2><p>Datos candidatos: compruebe celdas y notas en el PDF.</p><ul>' + ''.join(
        '<li>' + corpus_link(route, path, PurePosixPath(path).name) + '</li>' for path in tables) + '</ul>'


def render_doc(doc):
    route, meta = doc_route(doc), doc["meta"]
    body = [nav(route), f'<h1>{esc(meta.get("title", doc["id"]))}</h1>', metadata(doc, route)]
    ambito = meta.get("ambito_literal")
    body.append('<h2 id="ambito">Ámbito literal</h2>')
    if isinstance(ambito, dict) and ambito.get("texto"):
        body.append(f'<pre class="literal">{esc(ambito["texto"])}</pre>')
    else:
        body.append('<p>No se ha incorporado un ámbito literal contrastado. Consulte el PDF y su régimen transitorio.</p>')
    if doc["navigation"]:
        body.append('<h2>Recorrido por encabezados de la fuente</h2><p>Localización registrada en el corpus; '
                    'no constituye una revisión técnica humana.</p><ul class="apartados">')
        for node in doc["navigation"]:
            number = node.get("pagina")
            if number in doc["page_numbers"]:
                body.append('<li>' + link(relative(route, source_page_route(doc, number)),
                            f'{node.get("titulo_literal", "Encabezado")} · p. {number}') + '</li>')
        body.append('</ul>')
    body.append('<h2>Páginas físicas</h2><ul class="apartados">')
    for item in doc["pages"]:
        body.append('<li>' + link(relative(route, source_page_route(doc, item["n"])), f'Página {item["n"]}') + '</li>')
    body.append('</ul><h2>Segmentos de texto</h2><p>Identificadores técnicos; no implican una jerarquía normativa validada.</p><ul class="apartados">')
    for part in doc["parts"]:
        body.append('<li>' + link(relative(route, part_route(doc, part)), f'{part["id"]} · {part_title(part)}') + '</li>')
    body.append('</ul>' + table_links(doc, route))
    return route, page_html(meta.get("title", doc["id"]), '\n'.join(body), route)


def render_page(doc, item, index):
    number = item["n"]
    route = source_page_route(doc, number)
    title = f'{doc["meta"].get("code", doc["id"])} · Página física {number}'
    body = [nav(route, doc), f'<h1>{esc(title)}</h1>', metadata(doc, route, number),
            sequential_nav(route, doc["pages"], index, lambda p: source_page_route(doc, p["n"]), lambda p: f'Página {p["n"]}'),
            '<p>Formato: ' + corpus_link(route, item["file"], "Texto de la página (Markdown)") + '</p>']
    for name in (f"bloque/p{number:04d}.json",):
        if name in doc["assets"]:
            body.append('<p>' + corpus_link(route, doc["assets"][name], "JSON de bloques") + '</p>')
    body.append(f'<pre class="literal">{esc(item["text"])}</pre>')
    body.append(figure(doc, route, number) + table_links(doc, route, number))
    body.append('<h2>Segmentos que incluyen esta página</h2><ul>')
    for part in doc["parts"]:
        if number in part["pages"]:
            body.append('<li>' + link(relative(route, part_route(doc, part)), f'{part["id"]} · {part_title(part)}') + '</li>')
    body.append('</ul>')
    return route, page_html(title, '\n'.join(body), route)


def render_part(doc, part, index):
    route, title = part_route(doc, part), part_title(part)
    body = [nav(route, doc), f'<h1>{esc(title)}</h1>', metadata(doc, route),
            f'<div class="cita">ID técnico {esc(part["id"])} · páginas físicas '
            + ', '.join(link(relative(route, source_page_route(doc, number)), str(number)) for number in part["pages"])
            + '</div>', sequential_nav(route, doc["parts"], index, lambda p: part_route(doc, p), lambda p: p["id"]),
            '<p>Formatos: ' + corpus_link(route, part["file"], "JSON del segmento")]
    if part.get("markdown"):
        body[-1] += ' · ' + corpus_link(route, part["markdown"], "Markdown")
    body[-1] += '</p>'
    body.append(f'<pre class="literal">{esc(part["text"])}</pre>')
    for number in part["pages"]:
        body.append(figure(doc, route, number))
    return route, page_html(title, '\n'.join(body), route)


def document_table(docs, route):
    rows = ['<div class="tabla-scroll"><table><tr><th>Documento</th><th>Edición</th><th>Páginas</th><th>Capa</th></tr>']
    for doc in docs:
        meta = doc["meta"]
        rows.append('<tr><td>' + link(relative(route, doc_route(doc)), meta.get("title", doc["id"]))
                    + f'</td><td>{esc(meta.get("version"))}</td><td>{len(doc["pages"])}</td>'
                    + f'<td>{esc(meta.get("layer"))}</td></tr>')
    return '\n'.join(rows) + '</table></div>'


def document_groups(docs, route):
    """Agrupa metadatos territoriales declarados, sin deducir ubicación ni vigencia.

    Conserva la tabla anterior en materias sin territorio. Las provincias y los
    municipios solo aparecen cuando constan en los metadatos de la fuente.
    """
    def value(doc, key):
        raw = doc["meta"].get(key)
        return raw.strip() if isinstance(raw, str) else ""

    def order(name):
        return (unicodedata.normalize("NFKD", name).casefold(), name)

    def count(items):
        return f'{len(items)} documento' + ('s' if len(items) != 1 else '')

    def details(label, items, content, anchor=None):
        attr = f' id="{esc(anchor)}"' if anchor else ''
        return (f'<details class="territorio"{attr}><summary>{esc(label)} · {count(items)}</summary>'
                f'<div class="territorio-contenido">{content}</div></details>')

    def municipalities(items):
        groups = {}
        for doc in items:
            groups.setdefault(value(doc, "municipio"), []).append(doc)
        if not any(groups):
            return document_table(items, route)
        body = []
        for name in sorted(groups, key=order):
            selected = groups[name]
            if name:
                body.append(details('Municipio: ' + name, selected, document_table(selected, route)))
            else:
                body.append('<h3>Ámbito general</h3>' + document_table(selected, route))
        return ''.join(body)

    def subdivisions(items):
        general, provinces = [], {}
        for doc in items:
            province, town = value(doc, "provincia"), value(doc, "municipio")
            if not province and not town:
                general.append(doc)
            else:
                provinces.setdefault(province, []).append(doc)
        body = []
        if general:
            if provinces:
                body.append('<h3>Ámbito general de la comunidad</h3>')
            body.append(document_table(general, route))
        for name in sorted(provinces, key=order):
            selected = provinces[name]
            content = municipalities(selected)
            body.append(details('Provincia: ' + name, selected, content) if name else content)
        return ''.join(body)

    if not any(value(doc, key) for doc in docs for key in ('jurisdiccion', 'provincia', 'municipio')):
        return document_table(docs, route)
    groups = {}
    for doc in docs:
        name = value(doc, 'jurisdiccion')
        if not name:
            name = ('Territorio no indicado' if value(doc, 'provincia') or value(doc, 'municipio')
                    else 'Sin territorio indicado')
        groups.setdefault(name, []).append(doc)
    ordered = sorted(groups, key=order)
    anchors = {name: f'territorio-{i}' for i, name in enumerate(ordered, 1)}
    links = ''.join('<li>' + link('#' + anchors[name], f'{name} ({len(groups[name])})') + '</li>'
                    for name in ordered)
    body = ['<p>Elige un territorio para desplegar sus documentos. Se conserva la edición de cada fuente.</p>',
            '<nav class="territorio-indice" aria-label="Comunidades autónomas"><ul>' + links + '</ul></nav>']
    body.extend(details(name, groups[name], subdivisions(groups[name]), anchors[name]) for name in ordered)
    return '\n'.join(body)


def render_indices(docs, fichas):
    outputs = {}
    scopes = sorted({str(d["meta"].get("scope") or "Otras disposiciones") for d in docs})
    routes = {scope: "site/materia/" + MATTER_ROUTES.get(scope, slug(scope)) + ".html" for scope in scopes}
    if len(set(routes.values())) != len(routes):
        raise ValueError("Colisión entre rutas de materias")
    for scope, route in routes.items():
        selected = [doc for doc in docs if (doc["meta"].get("scope") or "Otras disposiciones") == scope]
        outputs[route] = page_html(scope, nav(route) + f'<h1>{esc(scope)}</h1>' + document_groups(selected, route), route)
    route = "site/index.html"
    body = ['<nav>Inicio</nav><h1>Normativa Abierta — acceso estático</h1>',
            '<p class="aviso">Vista pública: solo se reproduce contenido redistribuible. Las fuentes restringidas '
            'aparecen únicamente como ficha y enlace. No es un catálogo completo de normativa vigente.</p>',
            f'<p>{len(docs)} documentos · {sum(len(d["pages"]) for d in docs)} páginas físicas · '
            f'{sum(len(d["parts"]) for d in docs)} segmentos. Acceso sin JavaScript, servicios ni cuentas.</p>',
            '<h2>Materias</h2><ul>']
    for scope, target in routes.items():
        label = "Urbanismo por comunidad autónoma" if scope == "urbanismo" else scope
        body.append('<li>' + link(relative(route, target), label) + '</li>')
    body.append('</ul><h2>Todos los documentos</h2>' + document_table(docs, route))
    body.append('<h2>Índices</h2><ul><li>' + link("apartados.html", "Índice de segmentos de texto") + '</li><li>'
                + link("fichas.html", "Fichas de fuentes y complementos") + '</li></ul>')
    outputs[route] = page_html("Normativa Abierta — acceso estático", '\n'.join(body), route)
    route = "site/apartados.html"
    body = [nav(route), '<h1>Índice de segmentos de texto</h1><p>Rutas técnicas; los segmentos BOE corresponden a páginas físicas.</p>']
    for doc in docs:
        body.append(f'<h2>{esc(doc["meta"].get("title", doc["id"]))}</h2><ul>')
        for part in doc["parts"]:
            body.append('<li>' + link(relative(route, part_route(doc, part)), f'{part["id"]} · {part_title(part)}') + '</li>')
        body.append('</ul>')
    outputs[route] = page_html("Índice de segmentos", '\n'.join(body), route)
    route = "site/fichas.html"
    body = [nav(route), '<h1>Fichas de fuentes</h1><p>Una ficha no implica permiso de reproducción. '
            'Solo los documentos expresamente redistribuibles tienen texto y PDF en este visor.</p><ul>']
    by_id = {doc["id"]: doc for doc in docs}
    for ficha in fichas:
        title = ficha.get("title") or ficha.get("titulo") or ficha.get("id")
        rendered = esc(title)
        doc = by_id.get(ficha.get("id"))
        if doc:
            rendered = link(relative(route, doc_route(doc)), title)
        source = ficha.get("url") or ficha.get("landing")
        if source:
            rendered += ' · ' + link(source, "Fuente")
        status = "contenido redistribuible" if doc else "solo ficha y enlace; no se reproduce el contenido"
        body.append(f'<li id="{esc(slug(ficha["id"]))}">{rendered} · {esc(ficha.get("version"))} · {status}</li>')
    body.append('</ul>')
    outputs[route] = page_html("Fichas de fuentes", '\n'.join(body), route)
    outputs["index.html"] = page_html("Normativa Abierta", '<h1>Normativa Abierta</h1><p>'
        + link("site/index.html", "Abrir el visor de normativa") + '</p><p>Texto, procedencia y edición de '
        f'{len(docs)} documentos. Consulta por materias y páginas físicas.</p><p class="aviso">'
        + GENERAL_WARNING + '</p>', "index.html")
    return outputs


def contained(root, path):
    """Resuelve un fichero sin permitir enlaces simbólicos ni salir de root."""
    root = root.resolve()
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    try:
        lexical = path.absolute().relative_to(root)
    except ValueError as exc:
        raise ValueError("Ruta fuera del corpus") from exc
    if ".." in lexical.parts:
        raise ValueError("No se admiten componentes ..")
    cursor = root
    for component in lexical.parts:
        cursor /= component
        if cursor.is_symlink():
            raise ValueError("No se admiten enlaces simbólicos en el corpus")
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Ruta fuera del corpus")
    return resolved


class Corpus:
    def __init__(self, root):
        root = Path(root)
        if root.is_symlink():
            raise ValueError("El corpus no puede ser un enlace simbólico")
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ValueError("No existe el directorio de contenido")
        self.hashes = {}

    def read(self, path):
        path = contained(self.root, path)
        data = path.read_bytes()
        self.hashes[path.relative_to(self.root).as_posix()] = hashlib.sha256(data).hexdigest()
        return data

    def json(self, path):
        return json.loads(self.read(path).decode("utf-8-sig"))

    def load(self):
        docs, routes = [], set()
        for filename in sorted((self.root / "docs").glob("*/*/doc.json")):
            meta = self.json(filename)
            if meta.get("distribute") is not True:
                continue  # Nunca abrir los textos/PDF de un documento restringido.
            directory = contained(self.root, filename.parent)
            doc_id = meta["id"]
            if doc_id != directory.parent.name or meta.get("version_dir") != directory.name:
                raise ValueError("ID o edición incoherentes con la carpeta del documento")
            name = slug(doc_id + "-" + directory.name)
            if name in routes:
                raise ValueError("Colisión de rutas de documento")
            routes.add(name)
            pdf = contained(self.root, directory / "fuente.pdf")
            pdf_digest = hash_file(pdf)
            self.hashes[pdf.relative_to(self.root).as_posix()] = pdf_digest
            with pdf.open("rb") as handle:
                signature = handle.read(5)
            if signature != b"%PDF-" or pdf_digest != meta.get("sha256"):
                raise ValueError(f"PDF o SHA-256 incorrecto: {doc_id}")
            pages = []
            for path in sorted((directory / "pagina").glob("*.md")):
                if not re.fullmatch(r"p[0-9]{4,}", path.stem):
                    raise ValueError("Nombre de página inválido")
                pages.append({"n": int(path.stem[1:]), "file": path.relative_to(self.root).as_posix(),
                              "text": self.read(path).decode("utf-8-sig")})
            page_numbers = {p["n"] for p in pages}
            if page_numbers != set(range(1, len(pages) + 1)):
                raise ValueError(f"Páginas no consecutivas: {doc_id}")
            parts, part_ids = [], set()
            for path in sorted((directory / "apartado").glob("*.json")):
                item = self.json(path)
                info = item.get("apartado", item)
                part_id = info["id_tecnico"]
                if not re.fullmatch(r"[a-zA-Z0-9_-]+", part_id) or part_id in part_ids:
                    raise ValueError("ID de segmento inválido o duplicado")
                part_ids.add(part_id)
                numbers = item.get("paginas", info.get("paginas", []))
                if any(type(n) is not int or n not in page_numbers for n in numbers):
                    raise ValueError(f"Segmento referencia una página ausente: {doc_id}/{part_id}")
                text = item.get("texto", "")
                if not isinstance(text, str):
                    raise ValueError("Texto de segmento inválido")
                markdown = contained(self.root, path.with_suffix(".md"))
                parts.append({"id": part_id, "meta": info, "text": text, "pages": numbers,
                              "file": path.relative_to(self.root).as_posix(),
                              "markdown": markdown.relative_to(self.root).as_posix() if markdown.is_file() else None})
            counts = meta.get("conteos", {})
            if counts.get("paginas") != len(pages) or counts.get("apartados") != len(parts):
                raise ValueError(f"Recuentos incoherentes: {doc_id}")
            assets = {}
            for folder, suffix in (("figura", ".png"), ("tabla", ".json"), ("bloque", ".json")):
                for path in sorted((directory / folder).glob("*" + suffix)):
                    path = contained(self.root, path)
                    assets[path.relative_to(directory).as_posix()] = path.relative_to(self.root).as_posix()
            navigation_file = contained(self.root, directory / "navegacion_fuente.json")
            navigation = self.json(navigation_file).get("nodos", []) if navigation_file.is_file() else []
            docs.append({"id": doc_id, "meta": meta, "path": directory.relative_to(self.root).as_posix(),
                         "slug": name, "pages": pages, "page_numbers": page_numbers, "parts": parts,
                         "assets": assets, "navigation": navigation})
        fichas = [self.json(p) for p in sorted((self.root / "fichas").glob("*.json"))]
        return docs, fichas

    def digest(self):
        serialized = json.dumps(self.hashes, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()


class LinksParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value is not None:
                self.links.append(value)
            elif name == "id" and value is not None:
                self.ids.add(value)


def validate_links(outputs, content):
    """Valida el árbol candidato virtual y los enlaces al corpus original."""
    parsers = {}
    for route, value in outputs.items():
        if route.endswith(".html"):
            parser = LinksParser()
            parser.feed(value)
            parsers[route] = parser
    broken, outside, total = [], [], 0
    checked_sources = set()
    for route, parser in parsers.items():
        for raw in parser.links:
            total += 1
            try:
                url = urlsplit(raw)
                if url.scheme in ("http", "https"):
                    continue
                if url.scheme or url.netloc or unquote(url.path).startswith(("/", "\\")):
                    outside.append({"desde": route, "enlace": raw})
                    continue
                decoded = unquote(url.path)
                if "\\" in decoded:
                    raise ValueError("Separador inválido")
                target = posixpath.normpath(posixpath.join(posixpath.dirname(route), decoded)) if decoded else route
                if target == ".." or target.startswith("../"):
                    outside.append({"desde": route, "enlace": raw})
                    continue
                if target in outputs:
                    if url.fragment and target.endswith(".html") and unquote(url.fragment) not in parsers[target].ids:
                        broken.append({"desde": route, "enlace": raw, "motivo": "ancla ausente"})
                elif target.startswith("contenido/"):
                    if target not in checked_sources:
                        source = contained(content, target[len("contenido/"):])
                        if not source.is_file():
                            raise FileNotFoundError(target)
                        checked_sources.add(target)
                else:
                    raise FileNotFoundError(target)
            except (ValueError, OSError):
                broken.append({"desde": route, "enlace": raw, "motivo": "destino ausente o no permitido"})
    return {"enlaces_verificados": total, "enlaces_rotos": len(broken),
            "links_fuera_raiz": len(outside), "ejemplos_rotos": broken[:20], "ejemplos_fuera_raiz": outside[:20]}


def prepare(content):
    corpus = Corpus(content)
    docs, fichas = corpus.load()
    outputs = render_indices(docs, fichas)
    outputs["site/estilo.css"] = CSS
    for doc in docs:
        route, value = render_doc(doc)
        outputs[route] = value
        for index, item in enumerate(doc["pages"]):
            route, value = render_page(doc, item, index)
            outputs[route] = value
        for index, part in enumerate(doc["parts"]):
            route, value = render_part(doc, part, index)
            outputs[route] = value
    validation = validate_links(outputs, corpus.root)
    report = {"herramienta": "herramientas/generar_site.py", "version_formato": 1,
              "generador_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "entrada_sha256": corpus.digest(), "documentos": len(docs),
              "apartados": sum(len(d["parts"]) for d in docs),
              "paginas_fuente_html": sum(len(d["pages"]) for d in docs),
              "fichas": len(fichas), "paginas_html": sum(r.endswith(".html") for r in outputs),
              "bytes_generados_sin_informe": sum(len(t.encode("utf-8")) for t in outputs.values()),
              "privado": False, "rutas_generadas": sorted([*outputs, "site/_informe.json"]), **validation}
    if validation["enlaces_rotos"] or validation["links_fuera_raiz"]:
        raise ValueError("Validación de enlaces fallida: " + json.dumps(validation, ensure_ascii=False))
    outputs["site/_informe.json"] = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return outputs, report


def write_candidate(outputs, destination, content):
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError("La salida no puede ser un enlace simbólico")
    destination, content = destination.resolve(), Path(content).resolve()
    if destination == content.parent or destination.is_relative_to(content) or content.is_relative_to(destination):
        raise ValueError("La salida debe ser un candidato separado del corpus y de la raíz publicada")
    previous = set()
    manifest = contained(destination, "site/_informe.json")
    if manifest.is_file():
        old = json.loads(manifest.read_text(encoding="utf-8"))
        if old.get("herramienta") != "herramientas/generar_site.py":
            raise ValueError("La salida contiene un informe de otra herramienta")
        previous = set(old.get("rutas_generadas", []))
    if destination.exists():
        actual = set()
        for path in destination.rglob("*"):
            if path.is_symlink():
                raise ValueError("No se admiten enlaces simbólicos en la salida")
            if path.is_file():
                actual.add(path.relative_to(destination).as_posix())
        if actual - previous:
            raise ValueError("La salida contiene archivos ajenos al generador; use un directorio vacío")
    # Comprobar todas las rutas antes de escribir o retirar archivos de una generación previa.
    for route in previous | outputs.keys():
        if route != "index.html" and not route.startswith("site/"):
            raise ValueError("Ruta inesperada en el informe previo")
        contained(destination, route)
    destination.mkdir(parents=True, exist_ok=True)
    for route, value in sorted(outputs.items()):
        path = contained(destination, route)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8", newline="\n")
    for route in sorted(previous - outputs.keys()):
        path = contained(destination, route)
        if path.is_file():
            path.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contenido", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        outputs, report = prepare(args.contenido)
        write_candidate(outputs, args.salida, args.contenido)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({k: v for k, v in report.items() if k != "rutas_generadas"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
