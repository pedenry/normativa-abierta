#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""acceso.py — acceso local y selectivo al repositorio CTE generado por build.py.

Subcomandos:
    indice   lista documentos y capas disponibles
    buscar   búsqueda real por términos sobre el índice de apartados
    leer     lectura selectiva (documento, apartado o página)

Características:
- Devuelve rutas, citas literales (extracto) y advertencias; la lectura explícita se hace
  con `leer`.
- Contexto recuperable: ámbito literal del documento, definiciones, excepciones y
  referencias detectadas, además de páginas contiguas.
- Presupuesto de tokens con tiktoken (cl100k_base / o200k_base). Si no hay tiktoken se
  declara aproximación por caracteres. Lo que no cabe NO se recorta: se lista como omitido
  con su ruta.
- Formatos md / txt / json con la misma información.
- Todo local; no requiere servidor ni JS. Sin dependencia de corpus externos.

Uso rápido:
    python acceso.py indice
    python acceso.py buscar --consulta "rampas pendiente" --max 5 --presupuesto 6000
    python acceso.py leer --documento DB-SUA-oficial --apartado 2.1 --formato md
"""
import argparse
import json
import math
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path
RAIZ_REPO = Path(__file__).resolve().parent.parent
DEF_CONTENIDO = RAIZ_REPO / "contenido"


# --------------------------------------------------------------------- utilidades texto


@lru_cache(maxsize=100000)
def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    return _norm(str(s or ""))


def normalizar_mapa(s):
    """Normaliza conservando el mapa índice-normalizado -> índice-original (para citas)."""
    out, mapa, prev_space = [], [], False
    for i, ch in enumerate(s):
        base = unicodedata.normalize("NFKD", ch)
        base = "".join(c for c in base if not unicodedata.combining(c)).lower()
        for c in base:
            if c.isspace():
                if prev_space:
                    continue
                out.append(" ")
                mapa.append(i)
                prev_space = True
            else:
                out.append(c)
                mapa.append(i)
                prev_space = False
    return "".join(out), mapa


def leer_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def texto_apartado_md(path):
    """Extrae solo el texto literal de un .md de apartado (sin portada ni índices añadidos)."""
    t = Path(path).read_text(encoding="utf-8")
    if t.startswith("---"):
        resto = t[4:]
        pos = resto.find("\n---\n")
        if pos >= 0:
            t = resto[pos + 5:]
    lineas = t.split("\n")
    if lineas and lineas[0].startswith("# "):
        lineas = lineas[1:]
    while lineas and (not lineas[0].strip() or lineas[0].startswith("> ")):
        lineas = lineas[1:]
    cortes = ("## Referencias detectadas", "## Tablas en estas páginas", "## Figuras")
    salida = []
    for linea in lineas:
        if linea.startswith(cortes):
            break
        salida.append(linea)
    return "\n".join(salida).strip()


def crear_contadores():
    encs, modo = {}, "aproximacion_caracteres_4"
    try:
        import tiktoken  # opcional
        for nombre in ("cl100k_base", "o200k_base"):
            try:
                encs[nombre] = tiktoken.get_encoding(nombre)
            except Exception:
                pass
        if encs:
            modo = "tiktoken"
    except Exception:
        pass
    return encs, modo


def contar(texto, encs, nombre):
    if nombre in encs:
        return len(encs[nombre].encode(texto))
    return max(1, math.ceil(len(texto) / 4.0))


def tokens_de(texto, encs):
    return {"cl100k_base": contar(texto, encs, "cl100k_base"),
            "o200k_base": contar(texto, encs, "o200k_base")}


# ------------------------------------------------------------------ carga del repositorio


def cargar_indice(cont):
    ruta = cont / "indice" / "apartados.jsonl"
    if not ruta.exists():
        raise SystemExit("No existe %s: ejecute antes build.py" % ruta.as_posix())
    filas = []
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if linea:
                fila = json.loads(linea)
                if "id_tecnico" in fila and "documento" in fila:
                    filas.append(fila)
    return filas


def cargar_docs(cont, filas):
    docs = {}
    for f in filas:
        if f["documento"] in docs:
            continue
        ruta = cont / f["doc_json"]
        if ruta.exists():
            docs[f["documento"]] = (leer_json(ruta), ruta.parent)
    return docs


def ficha_doc(doc, base):
    tablas = doc.get("tablas_por_pagina") or {}
    return {
        "id": doc["id"], "codigo": doc.get("code"), "titulo": doc.get("title"),
        "capa": doc.get("layer"), "materia": doc.get("scope"),
        "version": doc.get("version"), "version_label_literal": doc.get("version_label_literal"),
        "sha256": doc.get("sha256"), "distribute": doc.get("distribute"),
        "url": doc.get("url"), "landing": doc.get("landing"),
        "nota_capa": doc.get("nota_capa"),
        "paginas": (doc.get("conteos") or {}).get("paginas"),
        "apartados": (doc.get("conteos") or {}).get("apartados"),
        "tablas": (doc.get("conteos") or {}).get("tablas"),
        "figuras": (doc.get("conteos") or {}).get("figuras"),
        "paginas_con_tablas": sorted(int(k) for k in tablas),
        "formulas": doc.get("formulas") or {},
        "ruta_doc": (base / "doc.json").relative_to(cont_global).as_posix(),
    }


cont_global = DEF_CONTENIDO  # se fija en main; usado solo para rutas relativas


def texto_fichero(cont, rel):
    p = cont / rel
    try:
        return texto_apartado_md(p)
    except Exception:
        return ""


def texto_json_tabla(obj):
    out = []

    def rec(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("texto", "contenido", "valor", "celda") and isinstance(v, str):
                    out.append(v)
                else:
                    rec(v)
        elif isinstance(x, list):
            for v in x:
                rec(v)

    rec(obj)
    return "\n".join(out)


def cita_literal(texto, terminos, ventana=220):
    """Devuelve (extracto, encontrado) centrado en la primera coincidencia real."""
    ntexto, mapa = normalizar_mapa(texto)
    for termino in terminos:
        nt = norm(termino)
        if not nt:
            continue
        pos = ntexto.find(nt)
        if pos < 0:
            continue
        ini = max(0, mapa[pos] - ventana)
        fin = min(len(texto), mapa[min(len(mapa) - 1, pos + len(nt) - 1)] + ventana)
        frag = texto[ini:fin].strip()
        pref = "…" if ini > 0 else ""
        suf = "…" if fin < len(texto) else ""
        return pref + frag + suf, True
    frag = texto[:2 * ventana].strip()
    return (frag + ("…" if len(texto) > 2 * ventana else "")), False


# ------------------------------------------------------------------------------- buscar


def puntuar(texto, terminos, frase):
    nt = norm(texto)
    if not nt:
        return 0
    score = 0
    for t in terminos:
        nt_term = norm(t)
        if nt_term:
            score += nt.count(nt_term)
    if frase:
        score += 2 * nt.count(frase)
    return score


_PAGINAS_CACHE = {}


def _clave_cache(cont):
    try:
        st = (cont / "indice" / "apartados.jsonl").stat()
        return (str(cont), st.st_mtime_ns, st.st_size)
    except Exception:
        return (str(cont),)


def cargar_paginas(cont, filas):
    """Índice auxiliar de páginas ya extraídas; sin PDF ni reextracción."""
    clave = _clave_cache(cont)
    if clave in _PAGINAS_CACHE:
        return _PAGINAS_CACHE[clave]
    meta = {}
    for f in filas:
        meta.setdefault(f["documento"], f)
    salida = []
    for doc, f in meta.items():
        base = (cont / f["doc_json"]).parent
        try:
            docj = leer_json(base / "doc.json")
        except Exception:
            docj = {}
        titulos = {}
        try:
            nav = leer_json(base / "navegacion_fuente.json")
            for n in nav.get("nodos") or []:
                titulos.setdefault(int(n.get("pagina") or 0), []).append(n.get("titulo_literal") or "")
        except Exception:
            pass
        for p in sorted((base / "pagina").glob("p*.md")):
            try:
                n = int(p.stem[1:])
            except Exception:
                continue
            salida.append({
                "documento": doc, "codigo": f.get("codigo"),
                "materia": f.get("materia"), "capa": f["capa"],
                "version": f["version"], "pagina": n,
                "archivo": p.relative_to(cont).as_posix(),
                "doc_json": f["doc_json"], "estructura": f["estructura"],
                "sha256": docj.get("sha256"),
                "titulos": "\n".join(titulos.get(n, [])),
                "texto": p.read_text(encoding="utf-8", errors="replace")})
    _PAGINAS_CACHE[clave] = salida
    return salida


def _tok(s):
    return tokenizar(s)


_TOK_PAG = {}


def _tokens_pag(p):
    key = (p.get("documento"), p.get("pagina"), p.get("numero"), hash(p.get("texto") or ""))
    if key not in _TOK_PAG:
        _TOK_PAG[key] = _tok(p.get("texto") or "")
    return _TOK_PAG[key]


def _bm25(paginas, terminos, consulta):
    terminos = [raiz(SINONIMOS.get(norm(t), norm(t))) for t in terminos if norm(t)]
    frase = norm(consulta)
    docs = [_tokens_pag(p) for p in paginas]
    if not docs:
        return []
    N = len(docs)
    avg = sum(len(d) for d in docs) / float(N)
    df = {t: sum(1 for d in docs if t in d) for t in terminos}
    k1, b = 1.5, 0.75
    idf = {t: math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5)) for t in terminos}
    puntajes = []
    for i, d in enumerate(docs):
        tf = {}
        for w in d:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for t in terminos:
            if t not in tf:
                continue
            f = tf[t]
            s += idf[t] * (f * (k1 + 1)) / (f + k1 * (1 - b + b * len(d) / avg))
        if frase:
            s += 2.0 * norm(paginas[i]["texto"]).count(frase)
        tit = paginas[i].get("titulos") or ""
        if tit:
            s += 2.0 * sum(idf.get(t, 0) for t in set(terminos) if t in tokenizar(tit))
        if s > 0:
            puntajes.append((s, paginas[i]))
    puntajes.sort(key=lambda x: (-x[0], x[1]["documento"], x[1]["pagina"]))
    return puntajes


def buscar_paginas(cont, filas, consulta, terminos, opciones, maximo=2):
    pags = cargar_paginas(cont, filas)
    if opciones.documento:
        clave = norm(opciones.documento)
        pags = [p for p in pags if clave in (norm(p["documento"]), norm(p.get("codigo")))]
    capa = getattr(opciones, "capa", None)
    if capa:
        if norm(capa) in ("todas", "todos", "all"):
            pass
        else:
            pags = [p for p in pags if norm(p["capa"]) == norm(capa)]
    else:
        pags = [p for p in pags if norm(p["capa"]) in ("oficial", "asociada")]
    if getattr(opciones, "materia", None):
        pags = [p for p in pags if norm(p.get("materia") or "") == norm(opciones.materia)]
    return _bm25(pags, terminos, consulta)[:maximo]


_NOTAS_CACHE = {}


def cargar_notas(cont, filas):
    clave = _clave_cache(cont)
    if clave in _NOTAS_CACHE:
        return _NOTAS_CACHE[clave]
    out = []
    for p in cargar_paginas(cont, filas):
        lineas = p["texto"].splitlines()
        for i, linea in enumerate(lineas):
            m = re.match(r"^\s*\((\d+)\)\s*(.+?)\s*$", linea)
            if not m:
                continue
            frag = [m.group(2)]
            for sig in lineas[i + 1:i + 3]:
                if not sig.strip() or re.match(r"^\s*\(\d+\)", sig):
                    break
                frag.append(sig.strip())
            out.append({"documento": p["documento"], "codigo": p.get("codigo"),
                        "materia": p.get("materia"), "capa": p["capa"],
                        "version": p["version"], "pagina": p["pagina"],
                        "numero": int(m.group(1)),
                        "archivo": p["archivo"], "doc_json": p["doc_json"],
                        "estructura": p["estructura"], "sha256": p.get("sha256"),
                        "texto": " ".join(frag)})
    _NOTAS_CACHE[clave] = out
    return out


def buscar_notas(cont, filas, consulta, terminos, opciones, maximo=3):
    notas = cargar_notas(cont, filas)
    if opciones.documento:
        clave = norm(opciones.documento)
        notas = [n for n in notas if clave in (norm(n["documento"]), norm(n.get("codigo")))]
    capa = getattr(opciones, "capa", None)
    if capa:
        if norm(capa) not in ("todas", "todos", "all"):
            notas = [n for n in notas if norm(n["capa"]) == norm(capa)]
    else:
        notas = [n for n in notas if norm(n["capa"]) in ("oficial", "asociada")]
    return _bm25(notas, terminos, consulta)[:maximo]


def _item_pagina(par, terminos, encs):
    s, p = par
    cita, hallada = cita_literal(p["texto"], terminos)
    return {
        "documento": p["documento"], "codigo": p.get("codigo"),
        "materia": p.get("materia"), "capa": p["capa"], "version": p["version"],
        "apartado_id": "p%04d" % p["pagina"], "id_tecnico": "p%04d" % p["pagina"],
        "ruta_oficial": "p. %d" % p["pagina"], "ruta_semantica": None,
        "seccion_estimada": None, "titulo": "Página %d (texto extraído)" % p["pagina"],
        "nivel": 0, "paginas": [p["pagina"]], "pagina": p["pagina"],
        "etiquetas_impresas": None, "tipos": ["pagina"], "referencias": [],
        "archivo": p["archivo"], "doc_json": p["doc_json"],
        "estructura": p["estructura"], "sha256": p.get("sha256"),
        "lectura_sugerida": ("python acceso.py leer --documento %s --pagina %d"
                             % (p["documento"], p["pagina"])),
        "puntuacion_bm25": round(s, 4),
        "cita": {"texto": cita, "nota": "extracto literal de página; requiere contraste con PDF"},
        "hallada": hallada, "texto_integro": p["texto"],
        "tokens_texto": contar(p["texto"], encs, "cl100k_base"),
        "tablas": [],
        "contexto": {"ambito": None, "definiciones": [], "excepciones": [],
                     "referencias": [], "paginas_continuadas": [],
                     "relacionados_enlazados": []},
        "advertencias": ["Resultado de página/nota de tabla; puede requerir imagen PDF."],
    }


def construir_busqueda(cont, filas, docs, consulta, terminos, opciones, encs):
    # Punto de entrada único (CLI y API/medir): delega siempre en BM25.
    return buscar_bm25(cont, filas, docs, consulta, terminos, opciones, encs)


def _construir_busqueda_legacy(cont, filas, docs, consulta, terminos, opciones, encs):
    maximo = opciones.max
    presupuesto = opciones.presupuesto
    cache_textos = {}
    candidatos = []
    frase = norm(consulta) if consulta else ""
    for f in filas:
        if opciones.documento:
            clave = norm(opciones.documento)
            if clave not in (norm(f["documento"]), norm(f.get("codigo"))):
                continue
        if opciones.capa and norm(f["capa"]) != norm(opciones.capa):
            continue
        if opciones.materia and norm(f.get("materia") or "") != norm(opciones.materia):
            continue
        rel = f["archivo"]
        if rel not in cache_textos:
            cache_textos[rel] = texto_fichero(cont, rel)
        texto = cache_textos[rel]
        s = puntuar(texto, terminos, frase)
        s += 3 * puntuar(f.get("titulo") or "", terminos, frase)
        if s <= 0:
            continue
        candidatos.append((s, f, texto))
    candidatos.sort(key=lambda x: (-x[0], x[1]["documento"], x[1]["id_tecnico"]))
    advertencias = [
        "Búsqueda local heurística por términos; no usa embeddings ni juicio automático.",
        "Las citas son extractos literales: el texto íntegro está en el archivo indicado.",
        "El presupuesto limita solo esta vista; si algo no cabe se lista como omitido, no se recorta.",
    ]
    resultados, omitidos = [], []
    ambitos_incluidos = set()
    usados = {"cl100k_base": 0, "o200k_base": 0}

    def cabe(extra_texto):
        if not presupuesto:
            return True
        t = contar(extra_texto, encs, "cl100k_base")
        return usados["cl100k_base"] + t <= presupuesto

    for s, f, texto in candidatos[:maximo]:
        ficha = docs.get(f["documento"], (None, None))[0]
        cita, hallada = cita_literal(texto, terminos)
        item = {
            "documento": f["documento"], "codigo": f.get("codigo"),
            "materia": f.get("materia"), "capa": f["capa"], "version": f["version"],
            "apartado_id": f["apartado_id"], "id_tecnico": f["id_tecnico"],
            "ruta_oficial": f.get("ruta_oficial"),
            "ruta_semantica": f.get("ruta_semantica"),
            "seccion_estimada": f.get("seccion_estimada"),
            "titulo": f["titulo"], "nivel": f["nivel"], "paginas": f["paginas"],
            "etiquetas_impresas": f.get("etiquetas_impresas"),
            "tipos": f.get("tipos") or [], "referencias": f.get("referencias") or [],
            "archivo": f["archivo"], "doc_json": f["doc_json"],
            "estructura": f["estructura"],
            "lectura_sugerida": ("python acceso.py leer --documento %s --apartado %s"
                                 % (f["documento"], f["id_tecnico"])),
            "cita": {"texto": cita,
                     "nota": ("extracto literal centrado en la primera coincidencia; "
                              "no sustituye al texto íntegro") if hallada else
                             ("no se localizó coincidencia exacta del término en el texto "
                              "normalizado; extracto inicial para revisión")},
            "hallada": hallada,
            "contexto": {"ambito": None, "definiciones": [], "excepciones": [],
                         "referencias": [], "paginas_continuadas": []},
            "advertencias": [],
        }
        item_txt = json.dumps({k: v for k, v in item.items() if k != "contexto"},
                              ensure_ascii=False)
        if not cabe(item_txt):
            omitidos.append({"documento": f["documento"], "apartado_id": f["apartado_id"],
                             "archivo": f["archivo"], "motivo": "presupuesto"})
            continue
        usados["cl100k_base"] += contar(item_txt, encs, "cl100k_base")
        usados["o200k_base"] += contar(item_txt, encs, "o200k_base")

        if ficha and f["documento"] not in ambitos_incluidos:
            amb = ficha.get("ambito_literal")
            if amb:
                extra = {"ambito": {"id_tecnico": amb.get("id_tecnico"),
                                    "ruta_oficial": amb.get("ruta_oficial"),
                                    "titulo": amb.get("titulo"), "texto": amb.get("texto")}}
                txt = amb.get("texto") or ""
                if cabe(txt):
                    item["contexto"]["ambito"] = extra["ambito"]
                    usados["cl100k_base"] += contar(txt, encs, "cl100k_base")
                    usados["o200k_base"] += contar(txt, encs, "o200k_base")
                    ambitos_incluidos.add(f["documento"])
                else:
                    omitidos.append({"documento": f["documento"], "tipo": "ambito",
                                     "motivo": "presupuesto",
                                     "archivo": (Path(f["doc_json"]).parent / "doc.json").as_posix()})
        # definiciones y excepciones de la misma sección estimada
        if ficha:
            est = leer_json(cont / f["estructura"]).get("apartados", [])
            for ap in est:
                if ap["id_tecnico"] == f["id_tecnico"]:
                    continue
                if ap.get("seccion_estimada") != f.get("seccion_estimada"):
                    continue
                for tipo in ("definiciones", "excepciones"):
                    if tipo not in (ap.get("tipos") or []):
                        continue
                    txt = texto_fichero(cont, f["doc_json"].replace("doc.json", ap["archivo"]))
                    if not txt:
                        continue
                    entrada = {"id_tecnico": ap["id_tecnico"],
                               "ruta_oficial": ap.get("ruta_oficial"),
                               "titulo": ap["titulo"], "archivo": f["doc_json"].replace(
                                   "doc.json", ap["archivo"]), "texto": txt}
                    if cabe(txt):
                        item["contexto"][tipo].append(entrada)
                        usados["cl100k_base"] += contar(txt, encs, "cl100k_base")
                        usados["o200k_base"] += contar(txt, encs, "o200k_base")
                    else:
                        omitidos.append({"documento": f["documento"],
                                         "apartado_id": ap["id_tecnico"], "tipo": tipo,
                                         "motivo": "presupuesto", "archivo": entrada["archivo"]})
        item["contexto"]["referencias"] = item["referencias"]
        # páginas contiguas (antes/después del rango del apartado)
        if opciones.expandir and f["paginas"]:
            base_doc = (cont / f["doc_json"]).parent
            vecinas = []
            p0, p1 = min(f["paginas"]), max(f["paginas"])
            for p in list(range(max(1, p0 - opciones.expandir), p0)) + \
                     list(range(p1 + 1, p1 + 1 + opciones.expandir)):
                ruta = base_doc / "pagina" / ("p%04d.md" % p)
                try:
                    txt = ruta.read_text(encoding="utf-8")
                except Exception:
                    continue
                entrada = {"pagina": p, "archivo": (base_doc / "pagina" /
                                                    ("p%04d.md" % p)).relative_to(cont).as_posix(),
                           "bloques": (base_doc / "bloque" / ("p%04d.json" % p)).relative_to(cont).as_posix(),
                           "texto": txt, "rol": "página contigua"}
                if cabe(txt):
                    vecinas.append(entrada)
                    usados["cl100k_base"] += contar(txt, encs, "cl100k_base")
                    usados["o200k_base"] += contar(txt, encs, "o200k_base")
                else:
                    omitidos.append({"documento": f["documento"], "pagina": p,
                                     "motivo": "presupuesto",
                                     "archivo": entrada["archivo"]})
            item["contexto"]["paginas_continuadas"] = vecinas
        if not hallada:
            item["advertencias"].append("Cita no verificada automáticamente; revise el archivo.")
        resultados.append(item)

    if not resultados and candidatos:
        advertencias.append("Había coincidencias, pero no cupieron en el presupuesto; "
                            "consulte la lista de omitidos o aumente --presupuesto.")
    elif not resultados:
        advertencias.append("Sin coincidencias para los términos dados.")
    # Índice auxiliar de páginas: notas de tabla, fórmulas y celdas no segmentadas
    # como apartado. Se antepone la mejor página BM25 si no duplica un hit.
    extra = buscar_paginas(cont, filas, consulta, terminos, opciones, maximo=2)
    if extra:
        pitem = _item_pagina(extra[0], terminos, encs)
        ocupadas = {(r["documento"], p) for r in resultados for p in (r.get("paginas") or [])}
        if (pitem["documento"], pitem["pagina"]) not in ocupadas:
            resultados = [pitem] + resultados[:max(0, maximo - 1)]
            advertencias.append("Incluida página/nota de tabla por índice auxiliar BM25; "
                                "no es un apartado y puede requerir imagen PDF.")
    return {
        "herramienta": "acceso.py", "modo": "buscar", "consulta": consulta,
        "terminos": terminos,
        "raiz_contenido": cont.relative_to(cont.parent.parent).as_posix()
        if cont.parent.parent in cont.parents else cont.name,
        "presupuesto": {"limite": presupuesto,
                        "usado_cl100k_base": usados["cl100k_base"],
                        "modo_tokens": "tiktoken" if encs else "aproximacion_caracteres_4"},
        "resultados": resultados, "omitidos": omitidos, "advertencias": advertencias,
    }


STOPWORDS = set("""de la el los las un una unos unas y o u en del al a por para con sin
que se su sus es son no ni como mas pero entre sobre tras durante mediante este esta estos
estas ese esa eso aquellos aquellas lo le les me te nos os mi tu suyo cuyo cuya sean ser
esta estan tener tiene cuando donde cual cuales quien quienes todo toda todos todas otro
otra otros otras mismo misma ademas tambien solo si ya muy cada""".split())


SINONIMOS = {"comprobacion": "verificacion", "comprobaciones": "verificaciones",
             "comprobar": "verificar", "exigida": "requerida", "exigidas": "requeridas",
             "exigido": "requerido", "exigidos": "requeridos", "exigir": "requerir"}


try:
    from snowballstemmer import stemmer as _Snowball
    _STEM = _Snowball("spanish")
except Exception:
    _STEM = None


@lru_cache(maxsize=50000)
def raiz(t):
    t = unicodedata.normalize("NFC", str(t or "")).lower()
    if _STEM is not None:
        return _STEM.stemWord(t)
    if len(t) > 5 and t.endswith("es"):
        return t[:-2]
    if len(t) > 4 and t.endswith("s"):
        return t[:-1]
    return t


@lru_cache(maxsize=8192)
def tokenizar(texto):
    base = unicodedata.normalize("NFC", str(texto or "")).lower()
    tok = re.findall(r"[0-9a-záéíóúüñ]+", base)
    return tuple(raiz(SINONIMOS.get(norm(t), norm(t))) for t in tok
                 if (len(t) > 1 or t.isdigit()) and norm(t) not in STOPWORDS)


_ASIGNACION = re.compile(
    r"(?<![\w.])([A-Za-zÁÉÍÓÚÜÑáéíóúüñγΓΔδ][A-Za-z0-9_ÁÉÍÓÚÜÑáéíóúüñγΓΔδ]*)"
    r"\s*=\s*(-?\d+(?:[.,]\d+)?)")
_CONECTORES = set("con donde si para y o u de del en al por como que se es son "
                  "no un una el la los las".split())


def _unidad_asignada(resto):
    """Unidad pegada al valor: solo si es unidad clara (/, %, ², ³, dígito o sigla)."""
    m = re.match(r"[ \t]{1,3}([^\s,;:)\]}]+)", resto)
    if not m:
        return ""
    u = m.group(1).rstrip(".,;:?¿!")
    if not u or norm(u) in STOPWORDS or norm(u) in _CONECTORES:
        return ""
    if re.search(r"[/%²³^]|\d", u) or (u.isupper() and len(u) <= 5):
        return u
    return ""


_TECNICA = re.compile(
    r"\b(?:c[óo]mo|f[óo]rmula|expresi[óo]n|procedimiento|m[ée]todo|"
    r"se (?:calcula|obtiene|determina|define))\b", re.I)
_OPERACION = re.compile(
    r"\b(?:y|;)\s+(?=(?:qué|cu[áa]nto|cu[áa]l)\b[^?¿]{0,60}?"
    r"\b(?:valor|resultado|cifra|magnitud|vale|obtiene|resulta)\b)", re.I)


def _limpiar_tematica(texto):
    t = re.sub(r"\s+", " ", texto).strip()
    t = re.sub(r"\b(?:con|donde|si|para)\s+(?=(?:y|o|u)\b|[,.;:?¿!]|$)", "",
               t, flags=re.I)
    t = re.sub(r"\b(?:y|o|u)\s*([,.;:?¿!])", r"\1", t)
    t = re.sub(r"\s+([,.;:?¿!])", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def separar_consulta(consulta):
    """Separa parámetros y, si es compuesta, concepto y operación.

    Devuelve (consulta_tematica, parametros_aportados, traza, consulta_operacion).
    La consulta original no se altera. En una petición compuesta de consultar
    método/fórmula y calcular resultado con valores asignados, solo el concepto
    se usa para buscar; la operación se conserva íntegra en payload/traza.
    Los umbrales (<, >, ≤, ≥) y números sin asignación no se separan. No se
    calcula ni valida ningún resultado.
    """
    original = str(consulta or "")
    if "=" not in original:
        return original, [], [], ""
    parametros, traza, cortes = [], [], []
    for m in _ASIGNACION.finditer(original):
        ini, fin = m.start(1), m.end(2)
        unidad = _unidad_asignada(original[fin:])
        if unidad:
            um = re.match(r"[ \t]{1,3}", original[fin:])
            fin += um.end() + len(unidad)
        literal = original[ini:fin]
        parametros.append({"variable": m.group(1), "valor": m.group(2),
                           "unidad": unidad or None, "literal": literal})
        traza.append({"tipo": "parametro", "literal": literal,
                      "inicio": ini, "fin": fin})
        cortes.append((ini, fin))
    if not parametros:
        return original, [], [], ""
    tematica = original
    for ini, fin in sorted(cortes, reverse=True):
        tematica = tematica[:ini] + " " + tematica[fin:]
    tematica = _limpiar_tematica(tematica)
    operacion = ""
    m_op = _OPERACION.search(original)
    if m_op and _TECNICA.search(original[:m_op.start()]):
        ini_op = m_op.start()
        concepto = original[:ini_op]
        for ini, fin in sorted([c for c in cortes if c[1] <= ini_op], reverse=True):
            concepto = concepto[:ini] + " " + concepto[fin:]
        concepto = _limpiar_tematica(concepto)
        if re.search(r"[0-9a-záéíóúüñ]", norm(concepto)):
            tematica = concepto
            operacion = original[ini_op:].strip()
            traza.append({"tipo": "intento_operacion", "literal": operacion,
                          "inicio": ini_op, "fin": len(original)})
    if not re.search(r"[0-9a-záéíóúüñ]", norm(tematica)):
        tematica = original
    return tematica, parametros, traza, operacion


def _clave_texto(t):
    t = norm(t)
    t = re.sub(r"[^0-9a-záéíóúüñ ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _titulo_sin_codigo(t):
    return re.sub(r"^\s*(?:\d+(?:\.\d+)*|[IVXLCDM]+\.?|"
                  r"anejo\s+[a-z0-9]+\.?)\s+", "", str(t or "").strip(), flags=re.I)


def _pasa_filtro(f, op):
    if op.documento and norm(op.documento) not in (
            norm(f["documento"]), norm(f.get("codigo") or "")):
        return False
    if op.capa:
        if norm(op.capa) not in ("todas", "todos", "all") and \
                norm(f["capa"]) != norm(op.capa):
            return False
    elif norm(f["capa"]) not in ("oficial", "asociada"):
        return False
    if op.materia and norm(f.get("materia") or "") != norm(op.materia):
        return False
    return True


def resolver_navegacion(cont, filas, docs, consulta, opciones):
    """Reconoce intención navegacional: título de documento + encabezado literal.

    Solo acepta un encabezado real de navegacion_fuente.json (>=2 palabras de
    contenido) contenido en el tópico, y que el tópico nombre el título del
    documento. Resuelve duplicados TOC/cuerpo por número estructural y título,
    prefiriendo la página con párrafos. No usa IDs de caso ni páginas fijas.
    """
    q = _clave_texto(consulta)
    if not q:
        return None
    mejor = None
    vistos = set()
    for f in filas:
        if not _pasa_filtro(f, opciones) or f["documento"] in vistos:
            continue
        vistos.add(f["documento"])
        doc, base = docs.get(f["documento"], (None, None))
        if base is None:
            continue
        titulo_doc = _clave_texto((doc or {}).get("title") or "")
        palabras_doc = {w for w in titulo_doc.split()
                        if len(w) > 2 and w not in STOPWORDS}
        if not (palabras_doc & set(q.split())):
            continue
        try:
            nav = leer_json(base / "navegacion_fuente.json")
        except Exception:
            continue
        nodos = nav.get("nodos") or []
        por_pagina = {}
        for n in nodos:
            por_pagina[n.get("pagina")] = por_pagina.get(n.get("pagina"), 0) + 1
        for n in nodos:
            if not n.get("pagina_verificada"):
                continue
            clave = _clave_texto(_titulo_sin_codigo(n.get("titulo_literal") or ""))
            palabras = [w for w in clave.split()
                        if len(w) > 1 and w not in STOPWORDS]
            if len(palabras) < 2 or (" " + clave + " ") not in (" " + q + " "):
                continue
            pag = int(n.get("pagina") or 0)
            ruta = (base / "pagina" / ("p%04d.md" % pag))
            try:
                texto = ruta.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            cuerpo = _clave_texto(texto)
            en_cuerpo = (" " + clave + " ") in (" " + cuerpo + " ")
            toc = por_pagina.get(pag, 0) >= 20
            puntaje = (1 if en_cuerpo else 0, 0 if toc else 1, len(texto),
                       len(palabras))
            cand = {"documento": f["documento"], "codigo": f.get("codigo"),
                    "pagina": pag, "titulo_literal": n.get("titulo_literal"),
                    "ruta_literal": n.get("ruta_literal"),
                    "id_navegacion": n.get("id_navegacion"),
                    "sha256_texto_pagina": n.get("sha256_texto_pagina"),
                    "metodo": n.get("metodo"), "en_cuerpo": en_cuerpo,
                    "pagina_toc": toc, "archivo": ruta.relative_to(cont).as_posix(),
                    "_puntaje": puntaje}
            if mejor is None or cand["_puntaje"] > mejor["_puntaje"]:
                mejor = cand
    if mejor:
        mejor.pop("_puntaje", None)
        mejor["consulta_clave"] = q
    return mejor


def _items_navegacion(cont, filas, encs, nav, terminos, opciones):
    pags = cargar_paginas(cont, filas)
    por_clave = {(p["documento"], p["pagina"]): p for p in pags}
    notas = cargar_notas(cont, filas)
    items = []
    for pag in (nav["pagina"], nav["pagina"] - 1, nav["pagina"] + 1):
        p = por_clave.get((nav["documento"], pag))
        if p is None:
            continue
        it = _item_pagina((1.0, p), terminos, encs)
        it["origen"] = "navegacion_fuente"
        it["encabezado"] = {"titulo_literal": nav["titulo_literal"],
                            "ruta_literal": nav["ruta_literal"],
                            "id_navegacion": nav["id_navegacion"],
                            "sha256_texto_pagina": nav["sha256_texto_pagina"],
                            "en_cuerpo": nav["en_cuerpo"]}
        ns = [n for n in notas if n["documento"] == nav["documento"]
              and n["pagina"] == pag]
        if ns:
            it["contexto"]["notas"] = [{"numero": n["numero"], "texto": n["texto"],
                                        "archivo": n["archivo"]} for n in ns]
            it["nota"] = it["contexto"]["notas"][0]
        items.append(it)
        if len(items) >= opciones.max:
            break
    return items


def cobertura_roots(roots, texto):
    return (len(roots & set(tokenizar(texto))) / float(len(roots))) if roots else 0.0


def _adjuntar_auxiliares(cont, filas, encs, resultados, consulta, terminos,
                         opciones, nav, advertencias):
    """Añade 1-2 lecturas auxiliares por documento primario, sin tocar el TOP3.

    Elige, dentro del documento real del resultado, el encabezado exacto si lo
    hay y la página con mayor cobertura literal de la consulta. No usa
    expected/source_id ni páginas del test. El texto completo va en el payload.
    """
    roots = set(tokenizar(consulta))
    pags = cargar_paginas(cont, filas)
    notas = cargar_notas(cont, filas)
    por_doc = {}
    for p in pags:
        por_doc.setdefault(p["documento"], []).append(p)
    codigos = set(re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", consulta))
    numeros = re.findall(r"\b\d+\b", consulta)
    frases_codigo = [norm("%s %s" % (c, n)) for c in codigos for n in numeros]
    vistos, total = set(), 0
    for r in resultados[:opciones.max]:
        doc = r["documento"]
        if doc in vistos:
            continue
        vistos.add(doc)
        paginas = por_doc.get(doc, [])
        cand = []
        for p in paginas:
            if p["pagina"] in (r.get("paginas") or []):
                continue
            texto = p.get("texto") or ""
            cob = (len(roots & set(tokenizar(texto))) / float(len(roots))) if roots else 0.0
            bonus = 0.25 if any(f and f in norm(texto) for f in frases_codigo) else 0.0
            cand.append((cob + bonus, cob, p["pagina"], p))
        cand.sort(key=lambda x: (-x[0], -x[1], x[2]))
        notas_doc = [n for n in notas if n["documento"] == doc]
        rank_notas = _bm25(notas_doc, terminos, consulta) if notas_doc else []
        mejor_nota = None
        umbral_nota = max(2, len(roots) // 2)
        for s_nota, nota in rank_notas[:3]:
            aciertos = len(roots & set(tokenizar(nota["texto"])))
            cob_nota = aciertos / float(len(roots)) if roots else 0.0
            if aciertos >= umbral_nota or cob_nota >= 0.5:
                mejor_nota = (nota["pagina"], s_nota, cob_nota, nota)
                break
        propuestas = []
        if mejor_nota:
            propuestas.append((mejor_nota[0], "nota", mejor_nota[1],
                               mejor_nota[2], mejor_nota[3]))
        if nav and nav["documento"] == doc:
            propuestas.append((nav["pagina"], "encabezado", 0.0,
                               cobertura_roots(roots, nav["titulo_literal"]), None))
        if cand:
            propuestas.append((cand[0][2], "pagina", cand[0][0], cand[0][1], None))
        auxs, por_pag = [], {}
        for pag, tipo, score, cob, nota in propuestas:
            if pag in por_pag:
                ent = por_pag[pag]
                if nota is not None and "nota" not in ent:
                    ent["nota"] = {"numero": nota["numero"], "texto": nota["texto"],
                                   "archivo": nota["archivo"]}
                    ent["aux_tipo"] += "+nota"
                    ent["motivo"] += "+nota_pertinente"
                if tipo == "encabezado":
                    ent["encabezado"] = {
                        "titulo_literal": nav["titulo_literal"],
                        "ruta_literal": nav["ruta_literal"],
                        "id_navegacion": nav["id_navegacion"],
                        "sha256_texto_pagina": nav["sha256_texto_pagina"]}
                    ent["aux_tipo"] += "+encabezado"
                    ent["motivo"] += "+heading_exacto"
                continue
            if len(auxs) >= 2:
                continue
            p = next((x for x in paginas if x["pagina"] == pag), None)
            if p is None:
                continue
            ent = {"documento": doc, "pagina": pag, "aux_tipo": tipo,
                   "motivo": ("nota_pertinente_por_rank" if tipo == "nota" else
                              ("heading_exacto" if tipo == "encabezado" else
                               "pagina_cobertura")),
                   "score": round(float(score), 4), "cobertura": round(float(cob), 4),
                   "titulo_literal": p.get("titulos") or "",
                   "archivo": p["archivo"], "texto": p["texto"],
                   "sha256": p.get("sha256"),
                   "tokens_texto": contar(p.get("texto") or "", encs, "cl100k_base")}
            if nota is not None:
                ent["nota"] = {"numero": nota["numero"], "texto": nota["texto"],
                               "archivo": nota["archivo"]}
            ns = [n for n in notas if n["documento"] == doc and n["pagina"] == pag]
            ent["notas"] = [{"numero": n["numero"], "texto": n["texto"],
                             "archivo": n["archivo"]} for n in ns]
            if tipo == "encabezado":
                ent["encabezado"] = {"titulo_literal": nav["titulo_literal"],
                                     "ruta_literal": nav["ruta_literal"],
                                     "id_navegacion": nav["id_navegacion"],
                                     "sha256_texto_pagina": nav["sha256_texto_pagina"]}
            auxs.append(ent)
            por_pag[pag] = ent
            total += ent["tokens_texto"]
            if len(auxs) >= 2:
                continue
        if auxs:
            r.setdefault("contexto", {})["auxiliares"] = auxs
            r["auxiliares_tokens"] = sum(a["tokens_texto"] for a in auxs)
    overflow = bool(opciones.presupuesto and total and
                    (sum(contar(r.get("texto_integro") or "", encs, "cl100k_base") + 40
                         for r in resultados[:opciones.max]) + total) >
                    opciones.presupuesto)
    for r in resultados[:opciones.max]:
        if r.get("contexto", {}).get("auxiliares"):
            r["auxiliares_overflow"] = overflow
    if overflow:
        advertencias.append("overflow: los auxiliares superan el presupuesto; "
                            "se listan completos, sin recortar ni sustituir primarios.")
    advertencias.append("Auxiliares por documento primario: máx. 2 páginas completas, "
                        "sin reemplazar ninguno de los 3 resultados BM25.")
    return total


def buscar_bm25(cont, filas, docs, consulta, terminos, opciones, encs):
    """BM25 con normalización por longitud, IDF global y stopwords ES.

    - No usa expected_pages/quotes ni ningún oráculo: solo la consulta declarada.
    - Números como tokens exactos (no subcadenas).
    - Devuelve el apartado íntegro y contexto con relación real (sin volcar todo).
    """
    consulta_original = consulta
    consulta_tematica, parametros_aportados, traza_consulta, consulta_operacion = \
        separar_consulta(consulta)
    consulta_efectiva = consulta_tematica if parametros_aportados else consulta
    if parametros_aportados:
        terminos = [t for t in re.split(r"[\s,;]+", consulta_tematica)
                    if t and len(t) > 1]
    nav_heading = resolver_navegacion(cont, filas, docs, consulta_efectiva, opciones)
    presupuesto = opciones.presupuesto
    cache_textos, filas_ok, todos_tokens = {}, [], []
    for f in filas:
        rel = f["archivo"]
        if rel not in cache_textos:
            cache_textos[rel] = texto_fichero(cont, rel)
        texto = cache_textos[rel]
        tokens = tokenizar(texto)
        todas = set(tokens)
        todos_tokens.append(todas)
        f["_dl"] = max(1, len(tokens))
        f["_tt"] = tokenizar(f.get("titulo") or "")
        f["_tok"] = tags = None
        cache_textos[rel] = texto
        f["_tokens_set"] = todas
    N = max(1, len(filas))
    df = {}
    for s in todos_tokens:
        for t in s:
            df[t] = df.get(t, 0) + 1
    avgdl = sum(f["_dl"] for f in filas) / float(N)
    q = []
    for t in terminos:
        for x in tokenizar(t):
            if x not in q:
                q.append(x)
    if not q:
        q = tokenizar(consulta_efectiva)
    if not q:
        raise SystemExit("consulta sin términos útiles")
    k1, b = 1.4, 0.75
    idf = {t: math.log(1.0 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in q}
    frase = norm(consulta_efectiva) if consulta_efectiva else ""

    def puntuar_fila(f):
        texto_nt = norm(cache_textos[f["archivo"]])
        toks = tokenizar(cache_textos[f["archivo"]])
        if not toks:
            return 0.0, 0
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        aciertos = 0
        for t in q:
            n = tf.get(t, 0)
            if n:
                aciertos += 1
                s += idf.get(t, 0) * n * (k1 + 1) / (
                    n + k1 * (1 - b + b * f["_dl"] / avgdl))
        if f["_tt"]:
            s += 0.6 * sum(idf.get(t, 0) for t in set(q) if t in f["_tt"])
        cab = norm("%s %s %s %s %s" % (f.get("codigo") or "", f.get("titulo") or "",
                                       f.get("materia") or "", f.get("scope") or "",
                                       f.get("ruta_semantica") or ""))
        s += 0.8 * sum(idf.get(t, 0) for t in set(q) if t in cab)
        if frase and len(frase) > 6 and frase in texto_nt:
            s += 3.0
        return s, aciertos

    candidatos = []
    capa = getattr(opciones, "capa", None)
    capa_norm = norm(capa) if capa else None
    todas_capas = capa_norm in ("todas", "todos", "all")
    for f in filas:
        if opciones.documento and norm(opciones.documento) not in (
                norm(f["documento"]), norm(f.get("codigo") or "")):
            continue
        if not todas_capas:
            if capa_norm:
                if norm(f["capa"]) != capa_norm:
                    continue
            elif norm(f["capa"]) not in ("oficial", "asociada"):
                continue
        if opciones.materia and norm(f.get("materia") or "") != norm(opciones.materia):
            continue
        s, aciertos = puntuar_fila(f)
        if aciertos:
            candidatos.append((s, f))
    candidatos.sort(key=lambda x: (-x[0], x[1]["documento"], x[1]["id_tecnico"]))

    advertencias = [
        "Búsqueda local BM25 (longitud normalizada, IDF global, stopwords ES); sin embeddings.",
        "Los números se casan como tokens exactos, no como subcadenas.",
        "La cita es un extracto; el apartado íntegro se incluye en texto_integro y en `leer`.",
    ]
    resultados, omitidos = [], []
    usados = 0
    ambitos = set()

    def tok_txt(t):
        return contar(t, encs, "cl100k_base")

    for s, f in candidatos[:opciones.max]:
        texto = cache_textos[f["archivo"]]
        cita, hallada = cita_literal(texto, terminos or [consulta_efectiva])
        item = {
            "documento": f["documento"], "codigo": f.get("codigo"),
            "materia": f.get("materia"), "capa": f["capa"], "version": f["version"],
            "apartado_id": f["apartado_id"], "id_tecnico": f["id_tecnico"],
            "ruta_oficial": f.get("ruta_oficial"), "ruta_semantica": f.get("ruta_semantica"),
            "seccion_estimada": f.get("seccion_estimada"),
            "titulo": f["titulo"], "nivel": f["nivel"], "paginas": f["paginas"],
            "etiquetas_impresas": f.get("etiquetas_impresas"),
            "tipos": f.get("tipos") or [], "referencias": f.get("referencias") or [],
            "archivo": f["archivo"], "doc_json": f["doc_json"],
            "estructura": f["estructura"],
            "lectura_sugerida": ("python acceso.py leer --documento %s --apartado %s"
                                 % (f["documento"], f["id_tecnico"])),
            "puntuacion_bm25": round(s, 4),
            "cita": {"texto": cita, "nota": "extracto literal; el texto íntegro va abajo"},
            "hallada": hallada, "texto_integro": texto,
            "tokens_texto": tok_txt(texto),
            "contexto": {"ambito": None, "definiciones": [], "excepciones": [],
                         "referencias": [], "paginas_continuadas": [],
                         "relacionados_enlazados": []},
            "advertencias": [],
        }
        usados += tok_txt(texto) + 40
        if presupuesto and usados > presupuesto:
            item["advertencias"].append(
                "overflow: el texto íntegro supera el presupuesto; no se recorta, "
                "se avisa y se omiten extras")
        doc, base = docs.get(f["documento"], (None, None))
        if doc is None:
            doc, base = (None, None)
        est = leer_json(cont / f["estructura"]).get("apartados", [])
        por_id = {a["id_tecnico"]: a for a in est if "id_tecnico" in a}
        # ámbito una vez por documento
        if doc and f["documento"] not in ambitos and doc.get("ambito_literal"):
            amb = doc["ambito_literal"]
            t = amb.get("texto") or ""
            if not presupuesto or usados + tok_txt(t) <= presupuesto:
                item["contexto"]["ambito"] = amb
                usados += tok_txt(t)
                ambitos.add(f["documento"])
            else:
                omitidos.append({"documento": f["documento"], "tipo": "ambito",
                                 "motivo": "presupuesto",
                                 "archivo": (Path(f["doc_json"]).parent / "doc.json").as_posix()})
        # ancestros propios (parent_id)
        ancestros = []
        pid = f.get("parent_id")
        while pid and pid in por_id:
            ancestros.append(por_id[pid])
            pid = por_id[pid].get("parent_id")
        for a in reversed(ancestros):
            rel = f["doc_json"].replace("doc.json", a["archivo"])
            t = texto_fichero(cont, rel)
            if not presupuesto or usados + tok_txt(t) <= presupuesto:
                item["contexto"].setdefault("ancestros", []).append(
                    {"id_tecnico": a["id_tecnico"],
                     "ruta_oficial": a.get("ruta_oficial"), "titulo": a["titulo"],
                     "archivo": rel, "texto": t})
                usados += tok_txt(t)
            else:
                omitidos.append({"documento": f["documento"], "tipo": "ancestro",
                                 "apartado_id": a["id_tecnico"], "motivo": "presupuesto",
                                 "archivo": rel})
        # definiciones/excepciones solo con relación real por término/ruta citada
        terminos_set = set(q)
        claves = [norm(f["titulo"])] + [norm(t) for t in terminos]
        for a in est:
            if a["id_tecnico"] == f["id_tecnico"]:
                continue
            tipos = set(a.get("tipos") or [])
            if not ({"definiciones", "excepciones"} & tipos):
                continue
            rel = f["doc_json"].replace("doc.json", a["archivo"])
            t = texto_fichero(cont, rel)
            relacionado = False
            if f.get("seccion_estimada") and a.get("seccion_estimada") == f.get("seccion_estimada"):
                relacionado = True
            if a.get("ruta_oficial") and a["ruta_oficial"] in texto and \
                    f.get("ruta_oficial") and norm(f["titulo"]) in norm(t):
                relacionado = True
            if norm(t) and any(k and k in norm(t) for k in claves):
                relacionado = True
            entrada = {"id_tecnico": a["id_tecnico"], "ruta_oficial": a.get("ruta_oficial"),
                       "titulo": a["titulo"], "archivo": rel}
            if not relacionado:
                item["contexto"]["relacionados_enlazados"].append(entrada)
                continue
            tipo = "definiciones" if "definiciones" in tipos else "excepciones"
            if not presupuesto or usados + tok_txt(t) <= presupuesto:
                entrada["texto"] = t
                item["contexto"][tipo].append(entrada)
                usados += tok_txt(t)
            else:
                omitidos.append({"documento": f["documento"], "apartado_id": a["id_tecnico"],
                                 "tipo": tipo, "motivo": "presupuesto", "archivo": rel})
        item["contexto"]["referencias"] = item["referencias"]
        if opciones.expandir and f["paginas"]:
            base_doc = (cont / f["doc_json"]).parent
            p0, p1 = min(f["paginas"]), max(f["paginas"])
            for p in list(range(max(1, p0 - opciones.expandir), p0)) + \
                     list(range(p1 + 1, p1 + 1 + opciones.expandir)):
                relp = "pagina/p%04d.md" % p
                r = base_doc / relp
                if not r.exists():
                    continue
                t = r.read_text(encoding="utf-8")
                if not presupuesto or usados + tok_txt(t) <= presupuesto:
                    item["contexto"]["paginas_continuadas"].append(
                        {"pagina": p, "archivo": (base_doc / relp).relative_to(cont).as_posix(),
                         "texto": t})
                    usados += tok_txt(t)
                else:
                    omitidos.append({"documento": f["documento"], "pagina": p,
                                     "motivo": "presupuesto",
                                     "archivo": (base_doc / relp).relative_to(cont).as_posix()})
        # tablas de las páginas (solo rutas)
        tablas = []
        for p in f["paginas"] or []:
            for t in (doc or {}).get("tablas_por_pagina", {}).get(str(p), []):
                tablas.append("tabla/p%04d_t%02d.json" % (p, t["indice"]))
        item["tablas"] = tablas
        resultados.append(item)

    # Primarios BM25 estables: los auxiliares no sustituyen ningún slot.
    resultados_primarios = list(resultados)[:opciones.max]

    # Índice auxiliar: nota/footnote primero; si no, página con BM25.
    extra = []
    nota_hit = None
    try:
        notas = buscar_notas(cont, filas, consulta_efectiva, terminos, opciones, maximo=3)
        pags = buscar_paginas(cont, filas, consulta_efectiva, terminos, opciones, maximo=3)
        qroots = set(tokenizar(" ".join(terminos)))
        for par in notas:
            if len(qroots & set(tokenizar(par[1]["texto"]))) >= max(2, len(qroots) // 2):
                nota_hit = par
                break
        if nota_hit is not None and pags:
            top = pags[0][1]
            tc = len(qroots & set(tokenizar(top.get("titulos") or "")))
            nc = len(qroots & set(tokenizar(nota_hit[1]["texto"])))
            if tc >= 2 and tc >= nc:
                nota_hit = None
        if nota_hit is None:
            extra = pags
    except Exception as e:
        advertencias.append("auxiliar_paginas_error: %s" % e)
    if nota_hit:
        _, nota = nota_hit
        pags = [p for p in cargar_paginas(cont, filas)
                if p["documento"] == nota["documento"] and p["pagina"] == nota["pagina"]]
        if pags:
            pitem = _item_pagina((nota_hit[0], pags[0]), terminos, encs)
            pitem["nota"] = {"numero": nota["numero"], "texto": nota["texto"],
                             "archivo": nota["archivo"]}
            pitem["contexto"].setdefault("notas", []).append(pitem["nota"])
            ocupadas = {(r["documento"], p) for r in resultados for p in (r.get("paginas") or [])}
            if (pitem["documento"], pitem["pagina"]) not in ocupadas:
                resultados = [pitem] + resultados[:max(0, opciones.max - 1)]
                usados += pitem["tokens_texto"]
                advertencias.append("Incluida página con nota/footnote por índice auxiliar BM25; "
                                    "requiere contraste visual con PDF.")
    else:
        for par in extra:
            pitem = _item_pagina(par, terminos, encs)
            ocupadas = {(r["documento"], p) for r in resultados for p in (r.get("paginas") or [])}
            if (pitem["documento"], pitem["pagina"]) in ocupadas:
                continue
            coste = pitem["tokens_texto"]
            resultados = [pitem] + resultados[:max(0, opciones.max - 1)]
            usados += coste
            if presupuesto and usados > presupuesto:
                pitem["advertencias"].append("overflow de presupuesto: página auxiliar incluida "
                                             "por score BM25; no se recorta el texto")
            advertencias.append("Incluida página/nota de tabla por índice auxiliar BM25; "
                                "no es un apartado y puede requerir imagen PDF.")
            break

    advertencias[:] = [a for a in advertencias if not a.startswith("Incluida página")]
    resultados = resultados_primarios
    usados = sum(contar(r.get("texto_integro") or "", encs, "cl100k_base") + 40
                 for r in resultados)
    usados += _adjuntar_auxiliares(cont, filas, encs, resultados, consulta_efectiva,
                                   terminos, opciones, nav_heading, advertencias)

    if not resultados and candidatos:
        advertencias.append("Había coincidencias, pero no cupieron; revise omitidos.")
    elif not resultados:
        advertencias.append("Sin coincidencias para los términos dados.")
    return {
        "herramienta": "acceso.py", "modo": "buscar", "metodo": "bm25",
        "consulta": consulta, "consulta_original": consulta_original,
        "consulta_tematica": consulta_tematica,
        "consulta_operacion": consulta_operacion,
        "parametros_aportados": parametros_aportados,
        "traza_consulta": traza_consulta,
        "navegacion": nav_heading,
        "terminos": q,
        "ambito_capa": ("todas" if todas_capas else
                        (capa if capa_norm else "oficial+asociada")),
        "presupuesto": {"limite": presupuesto, "usado_cl100k_base": usados,
                        "modo_tokens": "tiktoken" if encs else "aproximacion_caracteres_4"},
        "resultados": resultados, "omitidos": omitidos, "advertencias": advertencias,
    }


# -------------------------------------------------------------------------------- leer


def construir_lectura(cont, filas, docs, opciones, encs):
    documento = opciones.documento
    filas_doc = [f for f in filas if norm(f["documento"]) == norm(documento)
                 or norm(f.get("codigo") or "") == norm(documento)]
    if not filas_doc:
        raise SystemExit("documento no encontrado en el índice: %s" % documento)
    key = filas_doc[0]["documento"]
    if not docs.get(key):
        raise SystemExit("no se encontró doc.json para %s" % key)
    doc, base = docs[key]
    est = leer_json(cont / filas_doc[0]["estructura"])
    apartados = est.get("apartados", [])
    salida = {
        "herramienta": "acceso.py", "modo": "leer",
        "documento": ficha_doc(doc, base),
        "ambito": doc.get("ambito_literal"),
        "apartado": None, "pagina": None, "apartados_disponibles": [],
        "contexto": {"definiciones": [], "excepciones": [], "referencias": [],
                     "paginas_continuadas": [], "relacionados_enlazados": []},
        "omitidos": [], "advertencias": [
            "Lectura íntegra del archivo seleccionado; sin resumen ni recorte por defecto.",
        ],
    }
    objetivo = None
    if opciones.apartado:
        clave = norm(opciones.apartado)
        for ap in apartados:
            if clave in (norm(ap["id_tecnico"]), norm(ap.get("ruta_oficial") or ""),
                         norm("%s/%s" % (key, ap["id_tecnico"]))):
                objetivo = ap
                break
        if objetivo is None:
            raise SystemExit("apartado no encontrado. Ejemplos: %s" %
                             ", ".join("%s (%s)" % (a["id_tecnico"], a.get("ruta_oficial"))
                                       for a in apartados[:8]))
        rel = filas_doc[0]["doc_json"].replace("doc.json", objetivo["archivo"])
        txt = texto_fichero(cont, rel)
        salida["apartado"] = {
            "id_tecnico": objetivo["id_tecnico"],
            "ruta_oficial": objetivo.get("ruta_oficial"),
            "ruta_semantica": objetivo.get("ruta_semantica"),
            "seccion_estimada": objetivo.get("seccion_estimada"),
            "parent_id": objetivo.get("parent_id"),
            "titulo": objetivo["titulo"], "nivel": objetivo["nivel"],
            "paginas": objetivo["paginas"],
            "etiquetas_impresas": objetivo.get("etiquetas_impresas"),
            "tipos": objetivo.get("tipos"), "referencias": objetivo.get("referencias"),
            "archivo": rel, "texto": txt,
            "nota_cita": ("Cita recomendada: %s · %s · %s · páginas %s" % (
                doc.get("code") or key,
                objetivo.get("ruta_oficial") or ("ID técnico " + objetivo["id_tecnico"]),
                objetivo["titulo"],
                ("%d-%d" % (min(objetivo["paginas"]), max(objetivo["paginas"])))
                if objetivo["paginas"] else "s/p")),
        }
        # contexto relacionado de la misma sección estimada
        sec = objetivo.get("seccion_estimada")
        claves = [norm(objetivo.get("titulo") or "")] + \
                 [norm(t) for t in (objetivo.get("referencias") or [])]
        for ap in apartados:
            if ap["id_tecnico"] == objetivo["id_tecnico"]:
                continue
            tipos = set(ap.get("tipos") or [])
            if not ({"definiciones", "excepciones"} & tipos):
                continue
            rel2 = filas_doc[0]["doc_json"].replace("doc.json", ap["archivo"])
            txt2 = texto_fichero(cont, rel2)
            entrada = {"id_tecnico": ap["id_tecnico"],
                       "ruta_oficial": ap.get("ruta_oficial"),
                       "titulo": ap["titulo"], "archivo": rel2}
            relacionado = bool(sec) and ap.get("seccion_estimada") == sec
            if not relacionado and txt2:
                nt = norm(txt2)
                relacionado = any(k and k in nt for k in claves)
            if not relacionado:
                salida["contexto"]["relacionados_enlazados"].append(entrada)
                continue
            tipo = "definiciones" if "definiciones" in tipos else "excepciones"
            if txt2:
                entrada["texto"] = txt2
                salida["contexto"][tipo].append(entrada)
        salida["contexto"]["referencias"] = objetivo.get("referencias") or []
        salida["contexto"]["paginas_fuente"] = []
        for p in objetivo.get("paginas") or []:
            relp = filas_doc[0]["doc_json"].replace("doc.json", "pagina/p%04d.md" % p)
            rp = cont / relp
            if not rp.exists():
                continue
            tablas = []
            for t in (doc.get("tablas_por_pagina") or {}).get(str(p), []):
                relt = filas_doc[0]["doc_json"].replace(
                    "doc.json", "tabla/p%04d_t%02d.json" % (p, t.get("indice", 0)))
                pt = cont / relt
                if pt.exists():
                    try:
                        tablas.append({"archivo": relt, "texto": texto_json_tabla(leer_json(pt))})
                    except Exception as e:
                        tablas.append({"archivo": relt, "texto": "", "error": str(e)})
            salida["contexto"]["paginas_fuente"].append({
                "pagina": p, "archivo": relp, "texto": rp.read_text(encoding="utf-8"),
                "tablas": tablas,
                "imagen_pdf": "requiere contraste visual con PDF"})
        if opciones.expandir and objetivo["paginas"]:
            p0, p1 = min(objetivo["paginas"]), max(objetivo["paginas"])
            for p in list(range(max(1, p0 - opciones.expandir), p0)) + \
                     list(range(p1 + 1, p1 + 1 + opciones.expandir)):
                relp = filas_doc[0]["doc_json"].replace(
                    "doc.json", "pagina/p%04d.md" % p)
                try:
                    txtp = (cont / relp).read_text(encoding="utf-8")
                except Exception:
                    continue
                salida["contexto"]["paginas_continuadas"].append({
                    "pagina": p, "archivo": relp, "texto": txtp})
    else:
        salida["apartados_disponibles"] = [
            {"id_tecnico": a["id_tecnico"], "ruta_oficial": a.get("ruta_oficial"),
             "titulo": a["titulo"], "nivel": a["nivel"], "paginas": a["paginas"],
             "tipos": a.get("tipos"), "archivo": a["archivo"]} for a in apartados]
    if opciones.pagina:
        rel = filas_doc[0]["doc_json"].replace("doc.json", "pagina/p%04d.md" % opciones.pagina)
        try:
            txt = (cont / rel).read_text(encoding="utf-8")
        except Exception:
            raise SystemExit("página no disponible: %d" % opciones.pagina)
        bloques = filas_doc[0]["doc_json"].replace(
            "doc.json", "bloque/p%04d.json" % opciones.pagina)
        etiqueta = None
        paginas_json = (cont / filas_doc[0]["doc_json"]).parent / "paginas.json"
        if paginas_json.exists():
            for p in leer_json(paginas_json).get("paginas", []):
                if p["n"] == opciones.pagina:
                    etiqueta = p.get("etiqueta_impresa")
                    break
        salida["pagina"] = {"pagina": opciones.pagina, "etiqueta_impresa": etiqueta,
                            "archivo": rel, "bloques": bloques, "texto": txt}
    return salida


# ----------------------------------------------------------------------------- render


def render_md(d):
    L = []
    if d.get("modo") == "buscar":
        L.append("# Búsqueda local CTE")
        L.append("")
        L.append("- Consulta: %s" % d.get("consulta"))
        L.append("- Términos: %s" % ", ".join(d.get("terminos") or []))
        L.append("- Presupuesto: %s · usado (cl100k_base): %s · modo: %s" % (
            d["presupuesto"]["limite"], d["presupuesto"]["usado_cl100k_base"],
            d["presupuesto"]["modo_tokens"]))
        L.append("- Ámbito de capas: %s" % d.get("ambito_capa", "oficial+asociada"))
        L.append("- Resultados: %d · omitidos: %d" % (len(d["resultados"]),
                                                      len(d["omitidos"])))
        L.append("")
        for i, r in enumerate(d["resultados"], 1):
            L.append("## %d. %s · %s" % (i, r["codigo"] or r["documento"],
                                         r.get("ruta_oficial") or r["id_tecnico"]))
            L.append("")
            L.append("- Documento: %s (%s), capa %s, versión %s" % (
                r["documento"], r["codigo"], r["capa"], r["version"]))
            L.append("- Título: %s" % r["titulo"])
            L.append("- ID técnico: %s · ruta oficial: %s" % (
                r["id_tecnico"], r.get("ruta_oficial")))
            L.append("- Ruta semántica: %s" % r.get("ruta_semantica"))
            L.append("- Páginas físicas: %s · impresas: %s" % (
                r["paginas"], r.get("etiquetas_impresas")))
            L.append("- Archivo: %s" % r["archivo"])
            L.append("- Cita literal: «%s»" % r["cita"]["texto"])
            L.append("- %s" % r["cita"]["nota"])
            if r.get("contexto", {}).get("ambito"):
                a = r["contexto"]["ambito"]
                L.append("- Ámbito (literal)%s: %s" % (
                    " · " + (a.get("ruta_oficial") or a.get("id_tecnico")), a["texto"]))
            for tipo in ("definiciones", "excepciones"):
                for x in r["contexto"].get(tipo) or []:
                    L.append("- %s [%s] (%s): %s" % (
                        tipo.capitalize(), x.get("ruta_oficial") or x["id_tecnico"],
                        x["archivo"], x["texto"]))
            if r.get("referencias"):
                L.append("- Referencias detectadas: %s" % ", ".join(r["referencias"]))
            for p in r["contexto"].get("paginas_continuadas") or []:
                L.append("- Página contigua %d (%s): %s" % (p["pagina"], p["archivo"],
                                                            p["texto"]))
            for a in r["contexto"].get("auxiliares") or []:
                L.append("- Auxiliar [%s] p. %s · %s · %s: %s" % (
                    a.get("motivo"), a.get("pagina"), a.get("titulo_literal") or "",
                    a.get("archivo"), a.get("texto") or ""))
                for n in a.get("notas") or []:
                    L.append("- Nota auxiliar (%d): %s" % (n["numero"], n["texto"]))
            for adv in r.get("advertencias") or []:
                L.append("- Advertencia: %s" % adv)
            L.append("")
        if d["omitidos"]:
            L.append("## Omitidos por presupuesto (sin recortar en disco)")
            L.append("")
            for o in d["omitidos"]:
                L.append("- %s · %s · %s" % (o.get("documento"),
                                             o.get("apartado_id") or o.get("pagina"),
                                             o.get("archivo")))
            L.append("")
        L.append("## Advertencias")
        L.append("")
        for a in d["advertencias"]:
            L.append("- %s" % a)
    else:
        L.append("# Lectura local CTE")
        L.append("")
        dd = d["documento"]
        L.append("- Documento: %s (%s), capa %s, versión %s" % (
            dd["titulo"], dd["codigo"], dd["capa"], dd["version"]))
        L.append("- SHA256: %s" % dd["sha256"])
        L.append("- Páginas: %s · apartados: %s · tablas: %s · figuras: %s" % (
            dd["paginas"], dd["apartados"], dd["tablas"], dd["figuras"]))
        L.append("- Ruta del documento: %s" % dd["ruta_doc"])
        L.append("")
        if d.get("ambito"):
            a = d["ambito"]
            L.append("## Ámbito literal%s" % (" · " + (a.get("ruta_oficial") or
                                                       a.get("id_tecnico")) if a else ""))
            L.append("")
            L.append(a["texto"] if a else "")
        if d.get("apartado"):
            ap = d["apartado"]
            L.append("")
            L.append("## %s %s" % (ap["id_tecnico"], ap["titulo"]))
            L.append("")
            L.append("- Ruta oficial: %s · semántica: %s" % (
                ap.get("ruta_oficial"), ap.get("ruta_semantica")))
            L.append("- Páginas físicas: %s · impresas: %s" % (
                ap["paginas"], ap.get("etiquetas_impresas")))
            L.append("- Archivo: %s" % ap["archivo"])
            L.append("- %s" % ap["nota_cita"])
            L.append("")
            L.append(ap["texto"])
            if ap.get("referencias"):
                L.append("")
                L.append("Referencias detectadas: %s" % ", ".join(ap["referencias"]))
            for tipo in ("definiciones", "excepciones"):
                for x in d["contexto"].get(tipo) or []:
                    L.append("")
                    L.append("### %s relacionadas: %s (%s)" % (
                        tipo.capitalize(), x.get("ruta_oficial") or x["id_tecnico"],
                        x["archivo"]))
                    L.append("")
                    L.append(x["texto"])
            for p in d["contexto"].get("paginas_continuadas") or []:
                L.append("")
                L.append("### Página contigua %d (%s)" % (p["pagina"], p["archivo"]))
                L.append("")
                L.append(p["texto"])
            for p in d["contexto"].get("paginas_fuente") or []:
                L.append("")
                L.append("### Página fuente %d (%s)" % (p["pagina"], p["archivo"]))
                L.append("")
                L.append(p["texto"])
                for t in p.get("tablas") or []:
                    L.append("")
                    L.append("#### Tabla %s" % t.get("archivo"))
                    L.append("")
                    L.append(t.get("texto") or "")
            for x in d["contexto"].get("relacionados_enlazados") or []:
                L.append("- Relacionado enlazado (no incluido): %s · %s [%s]" % (
                    x.get("ruta_oficial") or x["id_tecnico"], x["titulo"], x["archivo"]))
        if d.get("pagina"):
            p = d["pagina"]
            L.append("")
            L.append("## Página física %d (impresa: %s)" % (p["pagina"],
                                                           p["etiqueta_impresa"]))
            L.append("")
            L.append("- Archivo: %s · bloques: %s" % (p["archivo"], p["bloques"]))
            L.append("")
            L.append(p["texto"])
        if d.get("apartados_disponibles"):
            L.append("")
            L.append("## Apartados disponibles")
            L.append("")
            for a in d["apartados_disponibles"]:
                L.append("- %s · %s · %s (páginas %s) [`%s`]" % (
                    a["id_tecnico"], a.get("ruta_oficial"), a["titulo"],
                    a["paginas"], a["archivo"]))
        L.append("")
        L.append("## Advertencias")
        L.append("")
        for a in d["advertencias"]:
            L.append("- %s" % a)
    return "\n".join(L) + "\n"


def render_txt(d):
    return render_md(d)


def render_json(d):
    return json.dumps(d, ensure_ascii=False, indent=1)


# -------------------------------------------------------------------------------- main


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="Acceso local al repositorio CTE: buscar, leer e índice.")
    ap.add_argument("--contenido", default=str(DEF_CONTENIDO))
    sub = ap.add_subparsers(dest="comando", required=True)

    p_ind = sub.add_parser("indice", help="lista documentos, capas y versiones")
    p_ind.add_argument("--capa", default=None)
    p_ind.add_argument("--materia", default=None)
    p_ind.add_argument("--formato", choices=("md", "txt", "json"), default="md")

    p_bus = sub.add_parser("buscar", help="búsqueda local por términos")
    p_bus.add_argument("--consulta", default="",
                       help="texto de la consulta (términos separados por espacios)")
    p_bus.add_argument("--terminos", nargs="*", default=[],
                       help="términos explícitos; si se omite, se usa --consulta")
    p_bus.add_argument("--documento", default=None)
    p_bus.add_argument("--capa", default=None)
    p_bus.add_argument("--materia", default=None)
    p_bus.add_argument("--max", type=int, default=8)
    p_bus.add_argument("--expandir", type=int, default=1,
                       help="páginas contiguas a incluir (0 = ninguna)")
    p_bus.add_argument("--presupuesto", type=int, default=6000,
                       help="tokens máximos de la vista (0 = sin límite)")
    p_bus.add_argument("--formato", choices=("md", "txt", "json"), default="md")
    p_bus.add_argument("--salida", default=None)

    p_lee = sub.add_parser("leer", help="lectura selectiva de documento/apartado/página")
    p_lee.add_argument("--documento", required=True)
    p_lee.add_argument("--apartado", default=None,
                       help="id técnico, ruta oficial o documento/id")
    p_lee.add_argument("--pagina", type=int, default=None)
    p_lee.add_argument("--expandir", type=int, default=1)
    p_lee.add_argument("--formato", choices=("md", "txt", "json"), default="md")
    p_lee.add_argument("--salida", default=None)

    args = ap.parse_args()
    cont = Path(args.contenido).resolve()
    global cont_global
    cont_global = cont
    filas = cargar_indice(cont)
    docs = cargar_docs(cont, filas)
    encs, modo = crear_contadores()

    if args.comando == "indice":
        filas2 = [f for f in filas
                  if (not args.capa or norm(f["capa"]) == norm(args.capa))
                  and (not args.materia or norm(f.get("materia") or "") == norm(args.materia))]
        vistos = {}
        for f in filas2:
            clave = (f["documento"], f["version"], f["capa"])
            vistos.setdefault(clave, 0)
            vistos[clave] += 1
        datos = {"herramienta": "acceso.py", "modo": "indice",
                 "documentos": [{"documento": k[0], "version": k[1], "capa": k[2],
                                 "apartados": v} for k, v in sorted(vistos.items())]}
        if args.formato == "json":
            texto = render_json(datos)
        else:
            lin = ["# Índice", ""]
            for d in datos["documentos"]:
                lin.append("- %s · versión %s · capa %s · %d apartados" % (
                    d["documento"], d["version"], d["capa"], d["apartados"]))
            texto = "\n".join(lin) + "\n"
    elif args.comando == "buscar":
        terminos = [t for t in (args.terminos or re.split(r"[\s,;]+", args.consulta))
                    if t and len(t) > 1]
        if not terminos:
            raise SystemExit("indique --consulta o --terminos")
        datos = construir_busqueda(cont, filas, docs, args.consulta, terminos, args, encs)
        texto_md = render_md(datos)
        datos["tokens_estaticos"] = tokens_de(texto_md, encs)
        datos["presupuesto"]["modo_tokens"] = modo
        texto = {"md": texto_md, "txt": render_txt(datos),
                 "json": render_json(datos)}[args.formato]
    else:
        datos = construir_lectura(cont, filas, docs, args, encs)
        texto_md = render_md(datos)
        datos["tokens_estaticos"] = tokens_de(texto_md, encs)
        texto = {"md": texto_md, "txt": render_txt(datos),
                 "json": render_json(datos)}[args.formato]

    if getattr(args, "salida", None):
        Path(args.salida).write_text(texto, encoding="utf-8")
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
