#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ejecutar_libres.py — regresión de búsqueda libre territorial (multidocumento).

Fixture casos-libres.json: 21 consultas libres (L-01..L-21) adaptadas de casos-territorial-1/2/3.json
con el MISMO gold (doc/versión/página) congelado antes del ranking y sin retoques para el éxito;
consultas con solo necesidad y territorio. Importa el AdaptadorContexto REAL: preparar(consulta,
documento=None, version=None, presupuesto_tokens=20000, max_resultados=2), SIN filtro de documento;
los campos esperado_* JAMÁS llegan al adaptador ni filtran candidatos, y el evaluador no resuelve
ni enruta la consulta. La resolución de ámbito del motor (si la emite) se conserva TAL CUAL en
busqueda.resolucion_ambito, junto a los argumentos pasados (documento=None, version=None en esta
suite), sin interpretarla.

Integridad por página con metadata propia (ruta bajo docs/<doc>/<versión>__/pagina/, número ==
nombre de archivo, sha256 local == texto_sha256, texto completo en contexto; única excepción
documentada: rstrip final si la página cerró el texto entregado). Las carpetas legacy cuyo nombre
no empieza por la fecha (p. ej. sin-fecha__<hash>) se aceptan SOLO si el doc.json de ESA MISMA
carpeta declara id==documento, version==versión reclamada, version_dir==nombre de carpeta y
distribute True, y son la candidata única para esa edición (varias afirmando la misma edición ->
edicion_ambigua, rechazada). Además, por cada DOCUMENTO
devuelto se valida su metadata propia doc.json (distribute True y versión declarada igual a la
usada por el motor) y se registran jurisdicción y municipio: doc.json ausente o ilegible,
distribute false o versión declarada distinta son incidencias de integridad
(metadata_incoherente), trazadas por documento y sin filtrar páginas.

Criterio de ámbito (evaluado DESPUÉS de obtener resultados, nunca desde la consulta): con
caso.jurisdiccion declarado, una fuente nacional (doc.json sin jurisdicción ni municipio) es
complementaria y se permite; una fuente autonómica solo si su jurisdicción equivale a la del caso;
una fuente municipal solo si su municipio equivale a caso.municipio y, con caso.jurisdiccion
declarada, también su jurisdicción equivale a la del caso (evita homónimos de ciudades). Otra CCAA
u otro municipio son incompatibles y se registran en documentos_ambito_incompatible por caso y en
el resumen, sin filtrar páginas ni resultados. La equivalencia territorial usa normalización genérica (tildes,
puntuación y descriptores administrativos genéricos), sin tablas de regiones ni identificadores;
no unifica denominaciones históricas distintas sin prefijo genérico (p. ej. Euskadi vs País Vasco).
Los casos SIN jurisdicción declarada en la fixture (controles tipo G01/G02) no evalúan ámbito:
se exige gold+integridad y no se inventa expectativa a partir de la consulta.

Gold EXACTO: cubre solo con doc/versión esperados + integridad ok + texto en contexto; primaria
aparte; sin textos completos en la salida; sin fallos conocidos admitidos. Un acierto exige gold
completo + integridad ok + ámbito compatible; la mezcla de ámbito invalida el acierto aunque el
gold esté presente. exit 1 si estado != ok, gold faltante, mezcla de ámbito o incidencia de
integridad (o inconsistencia fixture/registros), 0 si todo ok. La cobertura por presencia de
página no acredita calidad global ni fidelidad sustantiva. De ejecutar.py solo funciones puras
sin filtro de documento (_sha_fichero, _pagina_legible); registro por caso propio (el de allí
asume búsqueda de 1 documento).

Adjudicaciones posteriores (OPT-IN explícito, --alternativas RUTA): archivo JSON esquema
'alternativas-evidencia/1' con fixture_sha256 del fixture cargado, revision {fecha, motivo,
posterior_a_resultados true} y casos {id, consulta, documento, version, adjudicacion, paginas:
[{pagina, archivo, texto_sha256}]}. Contrato global roto (esquema, revision, hash de fixture que
no coincida con el fixture cargado, archivo sin casos) -> exit 2; entradas de caso inválidas ->
rechazo VISIBLE (sin aceptación silenciosa). El helper puro _aplicar_alternativas anota
evidencias_alternativas_validas SOLO cuando la página ya devuelta por la respuesta REAL tiene
ruta_ok, pagina_coincide_archivo, sha_coincide, texto_en_contexto y metadata_ok del documento,
coincidiendo pagina/archivo/SHA además de doc/version; NUNCA cambia cobertura.faltantes ni gold
ni filtra páginas. _acierto permite gold original completo O adjudicación validada (siempre con
estado ok + integridad ok + ámbito compatible). Con flag: la salida usa esquema
'regresion-recuperacion-libres/3-adjudicada/1', conserva resumen_original (gold exclusivo,
calculado ANTES de aplicar) y la aplicación visible, y muestra cobertura gold exacta y casos por
alternativa POR SEPARADO (no finge gold exacto completo). Sin flag: comportamiento exactamente
el actual (gold exclusivo); los controles no cambian. Uso: python
evaluacion/regresion_recuperacion/territorial/ejecutar_libres.py [--contenido RUTA]
[--fixture RUTA] [--salida RUTA] [--alternativas RUTA] (sin API ni red).
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
HTTP_LOCAL = RAIZ / "experimentos" / "http-local"
CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent))  # para reutilizar ejecutar.py
from ejecutar import _pagina_legible, _sha_fichero  # puras, sin filtro de doc

FIXTURE_DEFECTO = CARPETA / "casos-libres.json"
SALIDA_DEFECTO = RAIZ / ".local" / "busqueda-libre" / "actual.json"
CONTENIDO_DEFECTO = RAIZ / "contenido"
PRESUPUESTO, MAX_RESULTADOS = 20000, 2
ESQUEMA = "regresion-recuperacion-libres/3"
ESQUEMA_ADJUDICADA = "regresion-recuperacion-libres/3-adjudicada/1"
ESQUEMA_ALTERNATIVAS = "alternativas-evidencia/1"
CLAVES_PAGINA = ("doc", "version", "pagina", "motivo", "archivo", "texto_sha256",
                 "etiqueta_impresa", "url_fuente")
# Descriptores administrativos GENÉRICOS que se ignoran al comparar territorios
# (no es una tabla de regiones ni un mapeo de nombres: solo vocabulario general
# y conectivas; el núcleo del nombre decide la equivalencia).
_GENERICOS = {"comunidad", "comunitat", "generalitat", "principado", "region",
              "provincia", "ciudad", "pais", "illes", "islas", "isla", "foral",
              "autonoma", "autonomico", "de", "del", "la", "las", "el", "los",
              "y", "e"}


def _normalizar_territorio(texto):
    """Normalización genérica de un nombre territorial: sin tildes, casefold,
    sin puntuación y sin descriptores administrativos genéricos; devuelve los
    tokens restantes ordenados para comparación. Sin tablas de regiones ni IDs."""
    if not isinstance(texto, str) or not texto.strip():
        return ""
    plano = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in plano if not unicodedata.combining(c)).casefold()
    plano = re.sub(r"[^a-z0-9\s]", " ", plano)
    tokens = plano.split()
    nucleo = [t for t in tokens if t not in _GENERICOS]
    return " ".join(sorted(nucleo or tokens))


def _territorios_equivalentes(a, b):
    """Equivalencia genérica entre dos nombres territoriales declarados."""
    na, nb = _normalizar_territorio(a), _normalizar_territorio(b)
    return bool(na) and bool(nb) and na == nb


def _tipo_ambito_meta(jur, mun):
    """Clasificación de la fuente SOLO por su metadata propia: municipal si
    declara municipio; autonómica si declara jurisdicción; nacional si no
    declara ninguna (p. ej. REBT, sin jurisdiccion en doc.json)."""
    if mun:
        return "municipal"
    if jur:
        return "autonomico"
    return "nacional"


def _ambito_compatible_meta(jur, mun, caso_jur, caso_mun):
    """Regla del encargo aplicada SOLO a la metadata del documento devuelto
    (no infiere ni enruta la consulta): nacional sin jurisdicción -> permitida
    (complementaria); autonómica -> solo si equivale a caso_jur; municipal ->
    municipio equivalente a caso_mun y, con caso_jur declarada, jurisdicción
    también equivalente (evita homónimos de ciudades; una fuente municipal sin
    jurisdicción declarada no puede verificarlo y no equivale). Otra CCAA u
    otro municipio -> incompatible."""
    tipo = _tipo_ambito_meta(jur, mun)
    if tipo == "nacional":
        return True
    if tipo == "municipal":
        if not caso_mun or not _territorios_equivalentes(mun, caso_mun):
            return False
        return (not caso_jur) or _territorios_equivalentes(jur, caso_jur)
    return bool(caso_jur) and _territorios_equivalentes(jur, caso_jur)


def _carpeta_edicion(contenido, doc, version, memo=None):
    """Localiza la carpeta real de una edición (doc, version) SIN asumir que el
    nombre de carpeta empieza por la fecha: es candidata cualquier carpeta cuyo
    doc.json declare id==documento, version==reclamada, version_dir==nombre de
    carpeta y distribute True. Una única candidata -> esa; varias afirmando la
    misma edición -> error "edicion_ambigua" (sin primer candidato arbitrario).
    Devuelve (carpeta|None, error|None). memo: caché opcional por llamada."""
    if not doc or not version:
        return None, "documento o version ausentes"
    clave = (str(doc), str(version))
    if memo is not None and clave in memo:
        return memo[clave]
    resultado = _carpeta_edicion_calc(contenido, str(doc), str(version))
    if memo is not None:
        memo[clave] = resultado
    return resultado


def _carpeta_edicion_calc(contenido, doc, version):
    """Búsqueda real de la carpeta de una edición: escanea las carpetas del
    documento y valida la metadata declarada de cada una; diagnóstico fino de
    por qué ninguna carpeta es válida (distribute_false, version_declarada_
    distinta, version_dir_distinto, id_distinto, doc_json_ausente)."""
    raiz_doc = contenido / "docs" / doc
    try:
        carpetas = sorted(p for p in raiz_doc.iterdir() if p.is_dir())
        regulares = [p for p in carpetas
                     if p.name.startswith(version + "__")
                     and (p / "doc.json").is_file()]
    except OSError:
        return None, "doc_json_ausente"
    estrictas, declaran_version = [], []
    for carp in carpetas:
        ruta_dj = carp / "doc.json"
        if not ruta_dj.is_file():
            continue
        try:
            dj = json.loads(ruta_dj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(dj, dict) or dj.get("id") != doc \
                or dj.get("version") != version:
            continue
        declaran_version.append((carp, dj))
        if dj.get("distribute") is True and dj.get("version_dir") == carp.name:
            estrictas.append(carp)
    if len(estrictas) == 1:
        return estrictas[0], None
    if len(estrictas) > 1 or len(declaran_version) > 1:
        return None, "edicion_ambigua"
    if len(regulares) == 1:
        try:
            dj = json.loads((regulares[0] / "doc.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None, "doc_json_ilegible"
        if not isinstance(dj, dict):
            return None, "doc_json_ilegible"
        if dj.get("distribute") is not True:
            return None, "distribute_false"
        if dj.get("version") != version:
            return None, "version_declarada_distinta"
        if dj.get("version_dir") != regulares[0].name:
            return None, "version_dir_distinto"
        if dj.get("id") != doc:
            return None, "id_distinto"
        return None, "doc_json_ausente"
    if len(regulares) > 1:
        return None, "edicion_ambigua"
    if declaran_version:
        carp, dj = declaran_version[0]
        if dj.get("distribute") is not True:
            return None, "distribute_false"
        return None, "version_dir_distinto"
    return None, "doc_json_ausente"


def _pagina_legible_libre(contenido, archivo, doc, version, memo=None):
    """Valida la ruta RESUELTA de una página sin modificar el helper compartido:
    primero la ruta regular (_pagina_legible, comportamiento intacto); si
    falla, permite SOLO docs/<doc>/<version_dir>/pagina/pNNNN.md cuando la
    carpeta declarada es exactamente la candidata única de la edición según
    _carpeta_edicion (doc.json de ESA MISMA carpeta coherente; ambigüedad ->
    rechazo). Exige ruta resuelta bajo docs/<doc>, archivo pNNNN.md y número
    derivado del nombre; devuelve (ruta_ok, texto, numero_archivo)."""
    if doc is None or version is None:
        return False, None, None
    ruta_ok, texto, numero = _pagina_legible(contenido, archivo, doc, version)
    if ruta_ok:
        return ruta_ok, texto, numero
    if not isinstance(archivo, str) or not archivo or "\\" in archivo:
        return False, None, None
    rel = Path(archivo)
    if rel.is_absolute():
        return False, None, None
    try:
        destino = (contenido / rel).resolve()
        base = (contenido / "docs" / doc).resolve()
        partes = destino.relative_to(base).parts
    except (ValueError, OSError):
        return False, None, None
    if len(partes) != 3 or partes[1] != "pagina":
        return False, None, None
    m = re.fullmatch(r"p(\d{4})\.md", partes[2])
    if not m:
        return False, None, None
    carpeta_ed, _err = _carpeta_edicion(contenido, doc, version, memo)
    if carpeta_ed is None or carpeta_ed.name != partes[0]:
        return False, None, None
    try:
        return True, destino.read_text(encoding="utf-8"), int(m.group(1))
    except OSError:
        return True, None, int(m.group(1))


def _metadata_doc(contenido, doc, version, memo=None):
    """Metadata propia del doc.json REAL de una edición (regular o legacy
    declarada): distribute True y versión declarada; expone jurisdicción/
    municipio y la carpeta usada para el criterio de ámbito. Solo lectura;
    nunca filtra resultados ni cambia el gold."""
    vacia = {"doc_json": None, "carpeta": None, "version_declarada": None,
             "distribute": None, "jurisdiccion": None, "municipio": None,
             "metadata_ok": False, "error": None}
    if not doc or not version:
        vacia["error"] = "documento o version ausentes en la pagina devuelta"
        return vacia
    carpeta, err = _carpeta_edicion(contenido, doc, version, memo)
    if carpeta is None:
        vacia["error"] = err
        return vacia
    try:
        dj = json.loads((carpeta / "doc.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        vacia["error"] = "doc_json_ilegible"
        return vacia
    vacia.update({
        "doc_json": (carpeta / "doc.json").relative_to(contenido).as_posix(),
        "carpeta": carpeta.name,
        "version_declarada": dj.get("version"),
        "distribute": dj.get("distribute"),
        "jurisdiccion": dj.get("jurisdiccion"),
        "municipio": dj.get("municipio"),
    })
    if dj.get("distribute") is not True:
        vacia["error"] = "distribute_false"
    elif dj.get("version") != version:
        vacia["error"] = "version_declarada_distinta"
    else:
        vacia["metadata_ok"] = True
    return vacia


def _cargar_alternativas(ruta, fixture_sha, datos):
    """Carga y valida el contrato alternativas-evidencia/1 contra el fixture
    cargado. Contrato global roto (esquema, revision sin posterior_a_resultados
    true, fixture_sha256 que no coincida con el hash real del fixture cargado,
    archivo sin casos) -> ValueError (exit 2 en main). Entradas de caso
    inválidas -> rechazo VISIBLE en casos_rechazados, sin aceptación silenciosa."""
    alt = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(alt, dict) or alt.get("esquema") != ESQUEMA_ALTERNATIVAS:
        raise ValueError("esquema debe ser '%s'" % ESQUEMA_ALTERNATIVAS)
    rev = alt.get("revision")
    if not isinstance(rev, dict) or rev.get("posterior_a_resultados") is not True \
            or not str(rev.get("fecha") or "").strip() \
            or not str(rev.get("motivo") or "").strip():
        raise ValueError("revision malformada: exige fecha, motivo y "
                         "posterior_a_resultados true (adjudicacion posterior)")
    if str(alt.get("fixture_sha256") or "") != str(fixture_sha or ""):
        raise ValueError("fixture_sha256 no coincide con el fixture cargado: "
                         "las alternativas deben anclarse al mismo gold congelado")
    casos, rechazados = [], []
    indice = {str(c.get("id") or ""): c for c in (datos.get("casos") or [])}
    for i, ca in enumerate(alt.get("casos") or []):
        cid, motivo = None, None
        if not isinstance(ca, dict):
            rechazados.append({"indice": i, "id": None, "motivo": "malformada"})
            continue
        cid = str(ca.get("id") or "")
        base = indice.get(cid)
        pags = ca.get("paginas")
        if base is None:
            motivo = "id_inexistente_en_fixture"
        elif not isinstance(pags, list) or not pags:
            motivo = "paginas_malformadas"
        elif not str(ca.get("adjudicacion") or "").strip():
            motivo = "adjudicacion_ausente"
        elif str(ca.get("consulta") or "") != str(base.get("consulta") or ""):
            motivo = "consulta_distinta"
        elif str(ca.get("documento") or "") != str(base.get("esperado_documento") or ""):
            motivo = "doc_distinto_del_esperado"
        elif str(ca.get("version") or "") != str(base.get("esperada_version") or ""):
            motivo = "version_distinta_de_la_esperada"
        else:
            pags_ok, paginas_mal = [], False
            for pg in pags:
                if not isinstance(pg, dict) or not isinstance(pg.get("pagina"), int) \
                        or not str(pg.get("archivo") or "").strip() \
                        or not str(pg.get("texto_sha256") or "").strip():
                    paginas_mal = True
                    break
                pags_ok.append({"pagina": pg["pagina"], "archivo": str(pg["archivo"]),
                                "texto_sha256": str(pg["texto_sha256"])})
            if paginas_mal:
                motivo = "paginas_malformadas"
            else:
                casos.append({"id": cid, "consulta": str(ca["consulta"]),
                              "documento": str(ca["documento"]),
                              "version": str(ca["version"]), "paginas": pags_ok,
                              "adjudicacion": str(ca["adjudicacion"])})
        if motivo:
            rechazados.append({"indice": i, "id": cid or None, "motivo": motivo})
    if not casos and not rechazados:
        raise ValueError("archivo de alternativas sin casos: no hay adjudicacion "
                         "que aplicar (no se acepta en silencio)")
    return {"esquema": ESQUEMA_ALTERNATIVAS, "revision": dict(rev),
            "fixture_sha256": str(alt.get("fixture_sha256") or ""),
            "casos": casos, "casos_rechazados": rechazados}


def _aplicar_alternativas(registros, datos, alternativas):
    """Helper PURO (sin I/O, determinista): valida cada alternativa contra la
    respuesta REAL ya registrada y anota evidencias_alternativas_validas y
    adjudicacion_posterior en el registro. La fila devuelta se localiza por
    pagina Y doc==ca.documento Y version==ca.version (una respuesta
    multidocumento puede traer el mismo número de página de OTRO documento
    antes que la esperada; casar solo por numero daria falso negativo).
    Por página exige: coincidencia de
    pagina/archivo/texto_sha256 con lo devuelto, doc/version esperados del caso
    (coincide_esperado), integridad real (ruta_ok, pagina_coincide_archivo,
    sha_coincide, texto_en_contexto) y metadata_ok del documento. NUNCA cambia
    cobertura.faltantes ni gold ni filtra páginas. La concordancia contra el
    fixture (hash/id/consulta/doc-version) se valida en _cargar_alternativas y
    se REPITE aquí contra el registro para que el helper sea seguro aislado.
    Devuelve (aplicacion_visible, registros)."""
    por_id = {r["id"]: r for r in registros}
    apl = {"esquema": ESQUEMA_ALTERNATIVAS,
           "revision": dict(alternativas.get("revision") or {}),
           "fixture_sha256": alternativas.get("fixture_sha256"),
           "casos_solicitados": len(alternativas.get("casos") or []),
           "casos_rechazados": [dict(x) for x in (alternativas.get("casos_rechazados") or [])],
           "casos_adjudicados": [], "casos_no_adjudicados": [],
           "evidencias_validas": 0, "evidencias_rechazadas": []}
    for ca in alternativas.get("casos") or []:
        reg = por_id.get(ca["id"])
        esp = (reg or {}).get("esperado") or {}
        rechazo_caso = None
        if reg is None:
            rechazo_caso = "registro_inexistente"
        elif str(reg.get("consulta") or "") != ca["consulta"]:
            rechazo_caso = "consulta_distinta"
        elif esp.get("documento") != ca["documento"]:
            rechazo_caso = "doc_distinto_del_esperado"
        elif esp.get("version") != ca["version"]:
            rechazo_caso = "version_distinta_de_la_esperada"
        if rechazo_caso:
            apl["casos_no_adjudicados"].append({"id": ca["id"], "adjudicacion": ca["adjudicacion"],
                                                "motivo": rechazo_caso})
            continue
        evid, rechazos = [], []
        for pg in ca["paginas"]:
            # Localizar la fila por pagina Y doc Y version: en multidocumento,
            # la misma pagina de OTRO documento puede aparecer antes y casar
            # solo por numero producira falso negativo; el resto no cambia.
            fila = next((f for f in reg.get("paginas") or []
                         if f.get("pagina") == pg["pagina"]
                         and f.get("doc") == ca["documento"]
                         and f.get("version") == ca["version"]), None)
            motivo = None
            if fila is None:
                motivo = "pagina_no_devuelta"
            elif fila.get("archivo") != pg["archivo"]:
                motivo = "archivo_distinto"
            elif fila.get("texto_sha256") != pg["texto_sha256"]:
                motivo = "sha_distinto"
            elif fila.get("coincide_esperado") is not True:
                motivo = "doc_version_distinto_del_esperado"
            elif fila.get("ruta_ok") is not True:
                motivo = "ruta_invalida"
            elif fila.get("pagina_coincide_archivo") is not True:
                motivo = "pagina_no_coincide_archivo"
            elif fila.get("sha_coincide") is not True:
                motivo = "sha_invalido_en_respuesta"
            elif fila.get("texto_en_contexto") is not True:
                motivo = "texto_ausente_en_contexto"
            elif not any(d.get("documento") == ca["documento"]
                         and d.get("version") == ca["version"]
                         and (d.get("metadata") or {}).get("metadata_ok") is True
                         for d in reg.get("documentos") or []):
                motivo = "metadata_incoherente"
            if motivo:
                rechazos.append({"id": ca["id"], "pagina": pg["pagina"], "motivo": motivo,
                                 "adjudicacion": ca["adjudicacion"]})
            else:
                evid.append({"pagina": pg["pagina"], "archivo": pg["archivo"],
                             "texto_sha256": pg["texto_sha256"],
                             "adjudicacion": ca["adjudicacion"]})
        reg["evidencias_alternativas_validas"] = evid
        reg["adjudicacion_posterior"] = {"referencia": ca["adjudicacion"],
                                         "validada": bool(evid) and not rechazos,
                                         "paginas_validadas": [e["pagina"] for e in evid],
                                         "paginas_rechazadas": [x["pagina"] for x in rechazos]}
        apl["evidencias_validas"] += len(evid)
        apl["evidencias_rechazadas"].extend(rechazos)
        if evid and not rechazos:
            apl["casos_adjudicados"].append({"id": ca["id"], "adjudicacion": ca["adjudicacion"],
                                             "paginas": [e["pagina"] for e in evid]})
        else:
            apl["casos_no_adjudicados"].append({"id": ca["id"], "adjudicacion": ca["adjudicacion"],
                                                "motivo": ("evidencias_rechazadas" if rechazos
                                                           else "sin_evidencias_validas")})
    return apl, registros


def _cargar_fixture(ruta):
    """Valida lo mínimo: casos con id único, consulta y gold esperado. Los casos
    SIN jurisdicción declarada (controles) son válidos: no evalúan ámbito."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    casos = datos.get("casos")
    if not isinstance(casos, list) or not casos:
        raise ValueError("fixture sin lista 'casos'")
    ids = set()
    for c in casos:
        cid = str(c.get("id") or "")
        if not cid or cid in ids or any(not c.get(k) for k in
                ("consulta", "esperado_documento", "esperada_version",
                 "esperadas_paginas")):
            raise ValueError("caso invalido o id duplicado: %r" % cid)
        ids.add(cid)
    return datos


def _registro_caso(caso, res, contenido):
    """Registro multidocumento PROPIO (el de ejecutar.py asume filtro de 1 doc):
    traza todas las páginas devueltas, valida integridad por página y por
    documento (doc.json propio), evalúa el ámbito DESPUÉS de los resultados y
    exige el gold exacto para cubrir. Ningún campo esperado llega al motor."""
    doc_esp, ver_esp = caso.get("esperado_documento"), caso.get("esperada_version")
    caso_jur, caso_mun = caso.get("jurisdiccion"), caso.get("municipio")
    # Un caso sin jurisdicción declarada (controles tipo G01/G02) no evalúa
    # ámbito: ni expectativa inventada desde la consulta, ni equivalencias.
    ambito_evaluado = bool(caso_jur)
    gold = [int(g) for g in (caso.get("esperadas_paginas") or [])]
    ctx = res.get("texto_contexto") or ""
    reg = {"id": caso["id"], "consulta": caso["consulta"],
           "esperado": {"documento": doc_esp, "version": ver_esp, "paginas": gold},
           "busqueda": {"documento": None, "version": None,
                        "resolucion_ambito": res.get("resolucion_ambito")},
           "estado": res.get("estado"), "excedido": bool(res.get("excedido")),
           "tokens_contexto": res.get("tokens_contexto"),
           "texto_contexto_sha256": hashlib.sha256(ctx.encode("utf-8")).hexdigest() if ctx else None,
           "texto_contexto_longitud": len(ctx),
           "primarias": [], "paginas": [], "documentos": [],
           "documentos_no_esperados": [], "documentos_ambito_incompatible": [],
           "cobertura": {"contexto": [], "primaria": [], "faltantes": list(gold)},
           "integridad_ok": True, "integridad_incidencias": [],
           "error": res.get("error_preparar")}
    for r in (res.get("recuperacion") or {}).get("resultados") or []:
        reg["primarias"].append({"documento": r.get("documento"), "id_tecnico": r.get("id_tecnico"),
                                 "ruta_oficial": r.get("ruta_oficial"), "titulo": r.get("titulo"),
                                 "puntuacion_bm25": r.get("puntuacion_bm25"),
                                 "paginas": list(r.get("paginas") or []),
                                 "paginas_entregadas": list(r.get("paginas_entregadas") or [])})
    docs_meta = {}
    memo_ed = {}  # caché de lookup de edición por (doc, versión), por caso
    for p in res.get("paginas") or []:
        fila = {k: p.get(k) for k in CLAVES_PAGINA}
        incs = reg["integridad_incidencias"]
        # Integridad con metadata PROPIA de la página (su doc/su versión);
        # helper local: ruta regular + única carpeta legacy declarada.
        ruta_ok, texto, numero = _pagina_legible_libre(
            contenido, fila["archivo"], fila["doc"], fila["version"], memo_ed)
        fila["ruta_ok"], fila["numero_archivo"] = ruta_ok, numero
        fila["pagina_coincide_archivo"] = bool(ruta_ok) and isinstance(fila["pagina"], int) and numero == fila["pagina"]
        hay_texto = texto is not None and bool(texto.strip())
        literal = bool(hay_texto and ctx and texto in ctx)
        # Excepción documentada (la de ejecutar.py): rstrip global del adaptador,
        # admitido SOLO si la página cerró el texto entregado.
        final_rstrip = bool(hay_texto and ctx and not literal and ctx.endswith(texto.rstrip() + "\n"))
        fila["literal_en_contexto"], fila["ajuste_espacios_finales"] = literal, final_rstrip
        fila["texto_en_contexto"] = True if (literal or final_rstrip) else (False if texto is not None else None)
        fila["sha256_local"] = hashlib.sha256(texto.encode("utf-8")).hexdigest() if texto is not None else None
        fila["sha_coincide"] = bool(fila["sha256_local"]) and fila["sha256_local"] == fila["texto_sha256"]
        fila["longitud_texto"] = len(texto) if texto is not None else None
        # Coincidencia contra lo esperado: se registra y marca, NO filtra.
        fila["coincide_documento_esperado"] = fila["doc"] == doc_esp
        fila["coincide_version_esperada"] = fila["version"] == ver_esp
        fila["coincide_esperado"] = fila["coincide_documento_esperado"] and fila["coincide_version_esperada"]
        reg["paginas"].append(fila)
        if fila["doc"] != doc_esp and fila["doc"]:
            reg["documentos_no_esperados"].append(fila["doc"])
        # Metadata propia del DOCUMENTO devuelto (una vez por doc+versión):
        # doc.json (distribute True y versión declarada) + jurisdicción/municipio.
        clave = (fila["doc"], fila["version"])
        if clave not in docs_meta:
            meta = _metadata_doc(contenido, fila["doc"], fila["version"], memo_ed)
            jur, mun = meta["jurisdiccion"], meta["municipio"]
            compatible = (_ambito_compatible_meta(jur, mun, caso_jur, caso_mun)
                          if ambito_evaluado else None)
            docs_meta[clave] = {"documento": fila["doc"], "version": fila["version"],
                                "metadata": meta,
                                "tipo_ambito": _tipo_ambito_meta(jur, mun),
                                "ambito_compatible": compatible}
            if not meta["metadata_ok"]:
                incs.append({"documento": fila["doc"], "tipo": "metadata_incoherente",
                             "detalle": meta["error"]})
            if compatible is False:
                reg["documentos_ambito_incompatible"].append(
                    "%s|%s" % (fila["doc"], fila["version"]))
        if not ruta_ok:
            incs.append({"pagina": fila["pagina"], "tipo": "ruta_fuera_documento_edicion", "detalle": fila["archivo"]})
        elif texto is None:
            incs.append({"pagina": fila["pagina"], "tipo": "archivo_no_leible", "detalle": fila["archivo"]})
        else:
            if not fila["pagina_coincide_archivo"]:
                incs.append({"pagina": fila["pagina"], "tipo": "pagina_no_coincide_archivo",
                             "detalle": "afirma %r, archivo %s" % (fila["pagina"], Path(fila["archivo"]).name)})
            if not hay_texto:
                incs.append({"pagina": fila["pagina"], "tipo": "sin_evidencia_textual", "detalle": "página vacía o solo espacios"})
            else:
                if not fila["sha_coincide"]:
                    incs.append({"pagina": fila["pagina"], "tipo": "sha_texto_distinto"})
                if not fila["texto_en_contexto"]:
                    incs.append({"pagina": fila["pagina"], "tipo": "texto_no_en_contexto"})
    reg["documentos"] = sorted(docs_meta.values(),
                               key=lambda d: (str(d["documento"]), str(d["version"])))
    reg["documentos_no_esperados"] = sorted(set(reg["documentos_no_esperados"]))
    reg["documentos_ambito_incompatible"] = sorted(set(reg["documentos_ambito_incompatible"]))
    # Criterio de ámbito: DESPUÉS de los resultados; sin filtrar páginas.
    reg["ambito"] = {
        "evaluado": ambito_evaluado,
        "caso_jurisdiccion": caso_jur, "caso_municipio": caso_mun,
        "estado": ("no_evaluado_sin_territorio" if not ambito_evaluado else
                   ("mezcla_ambito" if reg["documentos_ambito_incompatible"] else
                    ("compatible" if docs_meta else "sin_documentos"))),
        "documentos_ambito_incompatible": reg["documentos_ambito_incompatible"],
    }
    for g in gold:
        elegibles = [f for f in reg["paginas"] if f["pagina"] == g and f["coincide_esperado"]
                     and f["ruta_ok"] and f["pagina_coincide_archivo"] is True
                     and f["sha_coincide"] is True and f["texto_en_contexto"] is True]
        if elegibles:
            reg["cobertura"]["contexto"].append(g)
            if any(f["motivo"] == "primaria" for f in elegibles):
                reg["cobertura"]["primaria"].append(g)
            reg["cobertura"]["faltantes"].remove(g)
    reg["integridad_ok"] = not reg["integridad_incidencias"]
    return reg


def _acierto(r):
    """Acierto = estado ok + integridad ok + (gold original completo O
    adjudicación posterior validada) + ámbito compatible cuando el caso declara
    territorio. Sin --alternativas, adjudicacion_posterior no existe en los
    registros -> criterio gold exclusivo (controles sin cambio)."""
    if r["estado"] != "ok" or not r["integridad_ok"]:
        return False
    amb = r.get("ambito") or {}
    if amb.get("evaluado") and amb.get("estado") != "compatible":
        return False
    if not r["cobertura"]["faltantes"]:
        return True
    adj = r.get("adjudicacion_posterior") or {}
    return bool(adj.get("validada") and (r.get("evidencias_alternativas_validas") or []))


def _resumen(registros, datos, adjudicacion_activa=False):
    """Resumen con aciertos, fallos, estados, integridad y criterio de ámbito.
    Con adjudicacion_activa True (flag --alternativas), separa aciertos gold
    exacto de aciertos por adjudicación y añade cobertura alternativa; la
    cobertura_contexto sigue siendo SOLO gold exacto (no se finge gold)."""
    aciertos = [r["id"] for r in registros if _acierto(r)]
    fallos = [{"id": r["id"], "estado": r["estado"], "faltantes": r["cobertura"]["faltantes"],
               "integridad": r["integridad_incidencias"],
               "ambito": (r.get("ambito") or {}).get("estado")}
              for r in registros if r["id"] not in aciertos]
    estados = {e: sum(1 for r in registros if r["estado"] == e) for e in {r["estado"] for r in registros}}
    amb_estados = {e: sum(1 for r in registros if (r.get("ambito") or {}).get("estado") == e)
                   for e in {"compatible", "mezcla_ambito", "no_evaluado_sin_territorio",
                             "sin_documentos"} if any((r.get("ambito") or {}).get("estado") == e
                                                      for r in registros)}
    mezcla = [r["id"] for r in registros
              if (r.get("ambito") or {}).get("estado") == "mezcla_ambito"]
    esperado = dict(datos.get("esperado") or {})
    paginas_gold = sum(len(r["esperado"]["paginas"]) for r in registros)
    inconsistencias = []
    for clave, observado in (("casos", len(registros)), ("paginas_gold", paginas_gold)):
        declarado = esperado.get(clave)
        if declarado is not None and int(declarado) != observado:
            inconsistencias.append({"campo": "esperado.%s" % clave, "declarado": declarado,
                                    "observado": observado})
    ids_fixture = [str(c.get("id") or "") for c in (datos.get("casos") or [])]
    if ids_fixture != [r["id"] for r in registros]:
        inconsistencias.append({"campo": "casos_ids", "declarado": ids_fixture,
                                "observado": [r["id"] for r in registros]})
    resumen = {
        "casos_total": len(registros), "estados": estados,
        "aciertos": aciertos, "total_aciertos": len(aciertos),
        "fallos": fallos, "total_fallos": len(fallos), "paginas_gold": paginas_gold,
        "cobertura_contexto": sum(len(r["cobertura"]["contexto"]) for r in registros),
        "cobertura_primaria": sum(len(r["cobertura"]["primaria"]) for r in registros),
        "ambito": {"evaluados": sum(1 for r in registros if (r.get("ambito") or {}).get("evaluado")),
                   "estados": amb_estados, "casos_mezcla_ambito": mezcla,
                   "documentos_ambito_incompatible": sorted({
                       d for r in registros
                       for d in (r.get("ambito") or {}).get("documentos_ambito_incompatible") or []})},
        "documentos_no_esperados": sorted({d for r in registros for d in r["documentos_no_esperados"]}),
        "nota_ambito": ("el ámbito se evalúa DESPUÉS de los resultados contra la metadata propia "
            "doc.json: nacional sin jurisdicción = complementaria permitida; autonómica solo si "
            "equivale a caso.jurisdiccion; municipal solo si equivale a caso.municipio y, con "
            "caso.jurisdiccion declarada, también a caso.jurisdiccion (evita homónimos); otra "
            "CCAA u otro municipio = incompatible; sin filtrar páginas; casos sin jurisdicción "
            "declarada (controles) no evalúan ámbito ni inventan expectativa desde la consulta"),
        "esperado": esperado, "inconsistencias": inconsistencias,
        "fallos_conocidos_admitidos": False,
        "limites": ["la cobertura por presencia de página no acredita calidad global ni fidelidad "
                    "sustantiva; tokens_contexto es recuento local, no usage de API",
                    "la normalización territorial es genérica y no unifica denominaciones históricas "
                    "distintas sin prefijo genérico (p. ej. Euskadi vs País Vasco)",
                    "carpetas legacy (nombre sin fecha) aceptadas solo si el doc.json de esa misma "
                    "carpeta declara id/version/version_dir/distribute coherentes y es candidata "
                    "única para la edición; la ambigüedad se rechaza sin elegir candidato arbitrario",
                    "busqueda.resolucion_ambito se conserva tal como la emite el motor y no se "
                    "interpreta en el evaluador"]}
    if adjudicacion_activa:
        gold_exactos = {r["id"] for r in registros
                        if r["estado"] == "ok" and r["integridad_ok"]
                        and not r["cobertura"]["faltantes"]
                        and (not (r.get("ambito") or {}).get("evaluado")
                             or (r.get("ambito") or {}).get("estado") == "compatible")}
        resumen["aciertos_gold_exacto"] = sorted(gold_exactos)
        resumen["aciertos_adjudicados"] = [
            {"id": r["id"],
             "adjudicacion": (r.get("adjudicacion_posterior") or {}).get("referencia"),
             "paginas": [e["pagina"] for e in (r.get("evidencias_alternativas_validas") or [])]}
            for r in registros if r["id"] in aciertos and r["id"] not in gold_exactos]
        resumen["cobertura_alternativa"] = sum(
            len(r.get("evidencias_alternativas_validas") or []) for r in registros)
        resumen["nota_adjudicacion"] = ("criterio adjudicado: gold original completo O evidencia "
            "alternativa validada (siempre estado ok + integridad ok + ambito compatible); el gold "
            "y los faltantes originales NO se modifican y cobertura_contexto sigue siendo SOLO "
            "gold exacto; resumen_original conserva la evaluacion gold exclusivo previa a aplicar "
            "alternativas; la cobertura por alternativa no es cobertura gold exacta")
    return resumen, (1 if (fallos or inconsistencias or mezcla) else 0)


def _imprimir(registros, resumen, salida_ruta, codigo, resumen_original=None,
              aplicacion=None):
    w = sys.stdout.write
    w("== Busqueda libre territorial: %d casos ==\n" % resumen["casos_total"])
    for r in registros:
        w("%-5s estado=%-21s gold=%-5s ctx=%-5s primaria=%-5s faltan=%-5s ambito=%-28s integridad=%s\n"
          % (r["id"], str(r["estado"]), "%s" % r["esperado"]["paginas"],
             "%s" % (r["cobertura"]["contexto"] or "-"), "%s" % (r["cobertura"]["primaria"] or "-"),
             "%s" % (r["cobertura"]["faltantes"] or "-"), str((r.get("ambito") or {}).get("estado")),
             "ok" if r["integridad_ok"] else "INTEGRIDAD"))
    w("-- Resumen --\n")
    w("Aciertos: %d/%d | fallos: %s\n" % (resumen["total_aciertos"], resumen["casos_total"],
       [f["id"] for f in resumen["fallos"]] or "(ninguno)"))
    w("Cobertura contexto: %d/%d paginas gold | primaria: %d/%d\n" % (
        resumen["cobertura_contexto"], resumen["paginas_gold"], resumen["cobertura_primaria"], resumen["paginas_gold"]))
    w("Ambito: %s\n" % json.dumps(resumen["ambito"], ensure_ascii=False))
    w("Documentos no esperados (trazados, no filtrados): %s\n" % (resumen["documentos_no_esperados"] or "(ninguno)"))
    w("Inconsistencias: %s\n" % (resumen["inconsistencias"] or "(ninguna)"))
    if resumen_original is not None:
        w("-- Resumen ORIGINAL (gold exclusivo, ANTES de adjudicaciones) --\n")
        w("Aciertos gold exclusivo: %d/%d | fallos originales: %s\n" % (
            len(resumen_original["aciertos"]), resumen_original["casos_total"],
            [f["id"] for f in resumen_original["fallos"]] or "(ninguno)"))
        w("Cobertura gold exacta ORIGINAL: %d/%d paginas\n" % (
            resumen_original["cobertura_contexto"], resumen_original["paginas_gold"]))
    if aplicacion is not None:
        w("-- Adjudicacion posterior (%s) --\n" % aplicacion.get("esquema"))
        w("Revision: %s | fixture_sha256: %s\n" % (
            json.dumps(aplicacion.get("revision") or {}, ensure_ascii=False),
            aplicacion.get("fixture_sha256")))
        w("Casos solicitados: %d | adjudicados: %s | no adjudicados: %s | rechazados por contrato: %s\n"
          % (aplicacion["casos_solicitados"],
             json.dumps(aplicacion["casos_adjudicados"], ensure_ascii=False),
             json.dumps(aplicacion["casos_no_adjudicados"], ensure_ascii=False),
             json.dumps(aplicacion["casos_rechazados"], ensure_ascii=False)))
        w("Evidencias validas: %d | rechazadas: %s\n" % (
            aplicacion["evidencias_validas"],
            json.dumps(aplicacion["evidencias_rechazadas"], ensure_ascii=False)))
        w("Cobertura por alternativa (paginas validadas, NO gold exacto): %d\n"
          % resumen.get("cobertura_alternativa", 0))
    w("Salida: %s | exit %d\n" % (salida_ruta, codigo))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regresion de busqueda libre territorial (multidocumento).")
    ap.add_argument("--contenido", default=str(CONTENIDO_DEFECTO))
    ap.add_argument("--fixture", default=str(FIXTURE_DEFECTO))
    ap.add_argument("--salida", default=str(SALIDA_DEFECTO))
    ap.add_argument("--alternativas", default=None,
                    help="JSON de adjudicaciones posteriores (alternativas-evidencia/1); "
                         "OPT-IN: sin esta flag el criterio es gold exclusivo, como siempre")
    args = ap.parse_args(argv)
    try:
        datos = _cargar_fixture(Path(args.fixture))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("fixture invalida (%s): %s\n" % (args.fixture, exc))
        return 2
    contenido = Path(args.contenido).resolve()
    if not (contenido / "indice" / "apartados.jsonl").exists():
        sys.stderr.write("sin indice de corpus en %s\n" % contenido)
        return 2
    salida_ruta = Path(args.salida) if Path(args.salida).is_absolute() else RAIZ / args.salida
    alternativas = None
    if args.alternativas:
        # OPT-IN: solo con --alternativas se cargan adjudicaciones posteriores;
        # el contrato exige el hash del fixture cargado (gold congelado anclado).
        try:
            alternativas = _cargar_alternativas(Path(args.alternativas),
                                                _sha_fichero(Path(args.fixture)), datos)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            sys.stderr.write("alternativas invalidas (%s): %s\n" % (args.alternativas, exc))
            return 2
    sys.path.insert(0, str(HTTP_LOCAL))
    import adaptador_contexto  # import REAL; sin parches de ranking ni oráculos
    ad = adaptador_contexto.AdaptadorContexto(str(contenido))
    cfg = datos.get("config") or {}
    presupuesto = int(cfg.get("presupuesto_tokens") or PRESUPUESTO)
    max_resultados = int(cfg.get("max_resultados") or MAX_RESULTADOS)
    registros = []
    for caso in datos["casos"]:
        # Busqueda libre: documento=None/version=None; ningún campo esperado
        # llega al adaptador y el evaluador no resuelve territorio.
        try:
            res = ad.preparar(caso["consulta"], documento=None, version=None,
                              presupuesto_tokens=presupuesto, max_resultados=max_resultados)
        except Exception as exc:  # estado no-ok; la corrida continúa
            res = {"estado": "error_preparar", "texto_contexto": "", "excedido": False,
                   "tokens_contexto": None, "paginas": [], "recuperacion": {"resultados": []},
                   "error_preparar": "%s: %s" % (type(exc).__name__, exc)}
        registros.append(_registro_caso(caso, res, contenido))
    resumen_original = aplicacion = None
    esquema_salida = ESQUEMA
    if alternativas:
        # resumen_original ANTES de aplicar: gold exclusivo, se conserva visible.
        resumen_original, _codigo_original = _resumen(registros, datos)
        aplicacion, registros = _aplicar_alternativas(registros, datos, alternativas)
        resumen, codigo = _resumen(registros, datos, adjudicacion_activa=True)
        esquema_salida = ESQUEMA_ADJUDICADA
    else:
        resumen, codigo = _resumen(registros, datos)
    actual = {
        "esquema": esquema_salida, "generado_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "python": sys.version, "plataforma": sys.platform,
            "hashes": {
                "runner": _sha_fichero(Path(__file__)),
                "motor_acceso": _sha_fichero(HTTP_LOCAL / "acceso.py"),
                "motor_adaptador_contexto": _sha_fichero(HTTP_LOCAL / "adaptador_contexto.py"),
                "fixture": {"archivo": Path(args.fixture).name, "sha256": _sha_fichero(Path(args.fixture))},
                "manifiesto_publico": {"archivo": "manifest_publico.json", "sha256": _sha_fichero(contenido / "manifest_publico.json")},
                "indice_apartados": {"archivo": "indice/apartados.jsonl", "sha256": _sha_fichero(contenido / "indice" / "apartados.jsonl")}},
            "busqueda": {"presupuesto_tokens": presupuesto, "max_resultados": max_resultados,
                         "modo_tokens": ad.modo_contadores, "encoders": sorted(ad.encs),
                         "filtro_documento": None, "sin_api_red": True}},
        "config": {"contenido": str(contenido), "salida": str(salida_ruta)},
        "resumen": resumen, "casos": registros,
    }
    if alternativas:
        actual["resumen_original"] = resumen_original
        actual["alternativas"] = aplicacion
    salida_ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(salida_ruta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(actual, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    _imprimir(registros, resumen, salida_ruta, codigo, resumen_original, aplicacion)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
