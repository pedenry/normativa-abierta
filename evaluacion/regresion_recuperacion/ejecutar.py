#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ejecutar.py — regresión de recuperación REAL sobre fixture congelada.

Contrato (sin tocar motor, corpus ni gold):
- Importa el AdaptadorContexto REAL de experimentos/http-local (sin parches de
  ranking, sin tocar encs, sin corpus de prueba) y ejecuta cada caso de la
  fixture congelada casos.json con preparar(consulta, documento, version,
  20000, 2): consulta y gold EXACTOS del caso; el runner no reescribe
  consultas ni ajusta el gold en función de los resultados.
- La referencia de páginas (gold) es independiente del ranking del buscador
  y se conservó INTACTA durante la comparación de propuestas: no se cambió
  ninguna página ni consulta para hacer pasar los resultados (que la fixture
  se fijara ANTES de la propuesta no puede demostrarse y no se afirma):
  REBT = BOE-A-2002-18099 / 2025-09-03; SUA = DB-SUA-oficial / 2022-06-14.
  Solo SUA-02 lleva fallo_conocido; REBT-09 no tiene gold exclusivo y no
  puntúa. Esperado declarado: cobertura 13/14.
- Por caso registra: consulta, documento, version, gold, estado, resultados
  primarios (id/ruta/puntuación/páginas), TODAS las páginas devueltas
  (doc/versión/página/motivo/archivo/etiqueta) con sha256 del texto y
  longitud, cobertura de cada página gold en contexto (página devuelta con
  doc/edición y ruta correctas, sha256 local == devuelto y texto literal de
  la página presente en texto_contexto) y en primaria (motivo == "primaria").
  No se persiste ningún texto completo (ni texto_contexto ni texto de
  página): solo sha256, longitudes y metadatos.
- Integridad por página devuelta respecto del caso: documento y edición
  solicitados, ruta RESUELTA dentro de docs/<documento>/<version>__
  (pagina/pXXXX.md, sin escapes fuera de ese documento/edición), número
  entero de "pagina" IGUAL al del nombre pXXXX.md (p. ej. archivo p0113.md
  que afirma pagina 110 se registra como página_no_coincide_archivo), sha256
  del texto leído del corpus == texto_sha256 devuelto y presencia literal del
  texto en texto_contexto. Una página local vacía o de solo espacios jamás
  cuenta como cobertura y se registra sin_evidencia_textual.
- Excepción de presentación (documentada, no calidad): el adaptador construye
  texto_final = "\n".join(partes).rstrip() + "\n", que elimina SOLO el
  whitespace al FINAL global del texto entregado; cuando la página es la
  última parte del texto, su whitespace final desaparece (p. ej. SUA-01
  p. 42: texto literal de 1851 chars incompleto solo en espacios finales,
  texto.rstrip() sí presente, sha256 de origen coincidente; sin pérdida
  sustantiva). El evaluador comprueba PRIMERO el literal completo
  (literal_en_contexto) y, exclusivamente para esa situación de final de
  texto, acepta ctx.endswith(texto_leido.rstrip() + "\n")
  (ajuste_espacios_finales): ningún carácter sustantivo ni espacio interno
  puede faltar. Ambos bool se registran por página; texto_en_contexto es
  válido si alguno es True. NO se aplica normalización global ni strip a
  fragmentos no finales; donde hubo rstrip no se afirma literal absoluto.
  La primera corrida con 6 incidencias (SUA-01 p.42, SUA-02 p.14, SUA-03
  p.37, SUA-04/05 p.16, SUA-06 p.42) se conserva como falso positivo del
  evaluador, no del motor.
- Metadata: hashes de motor (acceso.py, adaptador_contexto.py), manifiesto
  público, índice y fixture; versión de Python; modo de contadores;
  presupuesto y max_resultados.
- Código de salida:
  * 1 si algún estado != "ok", o pérdida NUEVA de referencia (gold no
    cubierta en contexto en un caso sin fallo_conocido), o fallo de
    integridad en cualquier caso, o inconsistencia de cardinalidad entre
    fixture y registros (esperado con claves presentes: referencias_
    evaluables/referencias_totales; e ids de casos completos en registros).
  * 0 si no hay pérdida nueva; el fallo conocido (SUA-02) se muestra de
    forma destacada (falta o mejora registrada, gold sin modificar). La
    mejora del fallo conocido sigue admitida: los contrastes de
    cardinalidad no fuerzan total==13.
  * con --estricto, CUALQUIER referencia faltante (incluida SUA-02) da 1.
- Limitación declarada: la cobertura por presencia de página NO acredita
  calidad global de la respuesta ni fidelidad sustantiva; solo trazabilidad
  de que la página del gold entró íntegra y verificada en lo entregado.
Errores de fixture/config: stderr y código 2 (sin resultados fiables).

Uso (desde la raíz del checkout):
    python evaluacion/regresion_recuperacion/ejecutar.py [--contenido RUTA]
        [--salida RUTA] [--fixture RUTA] [--estricto]
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
HTTP_LOCAL = RAIZ / "experimentos" / "http-local"
FIXTURE_DEFECTO = Path(__file__).resolve().parent / "casos.json"
SALIDA_DEFECTO = RAIZ / ".local" / "regresion-recuperacion" / "actual.json"
CONTENIDO_DEFECTO = RAIZ / "contenido"

PRESUPUESTO = 20000
MAX_RESULTADOS = 2
ESQUEMA = "regresion-recuperacion-actual/1"

CLAVES_PAGINA = ("doc", "version", "pagina", "motivo", "archivo",
                 "texto_sha256", "etiqueta_impresa", "url_fuente")


def _sha_fichero(ruta):
    """sha256 por bytes del fichero; None si no existe o no se puede leer."""
    try:
        h = hashlib.sha256()
        with open(ruta, "rb") as fh:
            for bloque in iter(lambda: fh.read(65536), b""):
                h.update(bloque)
        return h.hexdigest()
    except OSError:
        return None


def _cargar_fixture(ruta):
    """Carga y valida lo mínimo: lista de casos con ids únicos y consultas."""
    with open(ruta, encoding="utf-8") as fh:
        datos = json.load(fh)
    casos = datos.get("casos")
    if not isinstance(casos, list) or not casos:
        raise ValueError("fixture sin lista 'casos'")
    ids = set()
    for c in casos:
        cid = str(c.get("id") or "")
        if not cid or cid in ids:
            raise ValueError("caso sin id o duplicado: %r" % cid)
        ids.add(cid)
        if not str(c.get("consulta") or "").strip():
            raise ValueError("caso %s sin consulta" % cid)
        for clave in ("documento", "version"):
            if not str(c.get(clave) or "").strip():
                raise ValueError("caso %s sin '%s'" % (cid, clave))
    return datos


def _validacion_editorial(contenido, casos):
    """Solo secciones pertinentes: doc.json de los documentos del fixture.

    Localiza docs/<id>/<version>__*/doc.json y extrae id/version/distribute/
    layer para diagnosticar desalineaciones fixture-corpus; no cambia el gold
    ni el estado del caso (de eso responde el adaptador).
    """
    vistas, salida = set(), {}
    for c in casos:
        documento, version = c.get("documento"), c.get("version")
        clave = (documento, version)
        if clave in vistas:
            continue
        vistas.add(clave)
        entra = {"id": documento, "version_solicitada": version,
                 "version_declarada": None, "distribute": None,
                 "layer": None, "doc_json": None}
        try:
            coincidencias = sorted((contenido / "docs" / documento).glob(
                "%s__*/doc.json" % version))
        except OSError:
            coincidencias = []
        if coincidencias:
            try:
                dj = json.loads(coincidencias[0].read_text(encoding="utf-8"))
                entra["version_declarada"] = dj.get("version")
                entra["distribute"] = dj.get("distribute")
                entra["layer"] = dj.get("layer")
                entra["doc_json"] = coincidencias[0].relative_to(
                    contenido).as_posix()
            except (OSError, ValueError):
                pass
        salida["%s|%s" % (documento, version)] = entra
    return salida


def _registro_error(caso, exc):
    """Registro homogéneo cuando preparar lanza excepción (estado no-ok)."""
    gold = [int(g) for g in (caso.get("referencias_paginas") or [])]
    return {
        "id": caso["id"],
        "consulta": caso["consulta"],
        "documento": caso.get("documento"),
        "version": caso.get("version"),
        "gold": {"referencias_paginas": gold,
                 "fallo_conocido": bool(caso.get("fallo_conocido")),
                 "puntua": bool(gold)},
        "estado": "error_preparar",
        "excedido": False,
        "tokens_contexto": None,
        "limite_tokens": None,
        "texto_contexto_sha256": None,
        "texto_contexto_longitud": 0,
        "nota": caso.get("nota"),
        "primarias": [],
        "paginas": [],
        "cobertura": {"referencias": gold, "contexto": [], "primaria": [],
                      "faltantes": list(gold), "puntua": bool(gold)},
        "integridad_ok": False,
        "integridad_incidencias": [{"tipo": "excepcion_preparar",
                                    "detalle": "%s: %s"
                                               % (type(exc).__name__, exc)}],
        "error_preparar": "%s: %s" % (type(exc).__name__, exc),
    }


def _pagina_legible(contenido, archivo, documento, version):
    """Valida la ruta RESUELTA de una página y devuelve
    (ruta_ok, texto, numero_archivo).

    ruta_ok exige que la ruta resuelta esté dentro de
    docs/<documento>/<version>__ (componentes pagina/pXXXX.md) y con la
    parte de directorio bajo el documento indicado, sin escapes fuera de ese
    documento/edición. numero_archivo es el entero derivado del nombre
    pXXXX.md (None si la ruta no es válida): permite contrastar el número de
    página que afirma el resultado contra el archivo realmente devuelto.
    ruta_ok True con texto None significa ruta válida pero ilegible (se
    registrará como archivo_no_leible). Nunca lee ficheros fuera de ese
    documento/edición.
    """
    if documento is None or version is None:
        return False, None, None
    if not isinstance(archivo, str) or not archivo or "\\" in archivo:
        return False, None, None
    rel = Path(archivo)
    if rel.is_absolute():
        return False, None, None
    try:
        destino = (contenido / rel).resolve()
        base = (contenido / "docs" / documento).resolve()
        partes = destino.relative_to(base).parts
    except (ValueError, OSError):
        return False, None, None
    if len(partes) != 3 or not partes[0].startswith(version + "__"):
        return False, None, None
    if partes[1] != "pagina":
        return False, None, None
    m = re.fullmatch(r"p(\d{4})\.md", partes[2])
    if not m:
        return False, None, None
    numero = int(m.group(1))
    try:
        return True, destino.read_text(encoding="utf-8"), numero
    except OSError:
        return True, None, numero


def _registro_caso(caso, res, contenido):
    """Registro por caso SIN textos completos (solo metadatos, sha y longitudes)."""
    documento = caso.get("documento")
    version = caso.get("version")
    gold = [int(g) for g in (caso.get("referencias_paginas") or [])]
    ctx = res.get("texto_contexto")
    ctx = ctx if isinstance(ctx, str) else ""
    registro = {
        "id": caso["id"],
        "consulta": caso["consulta"],
        "documento": documento,
        "version": version,
        "gold": {"referencias_paginas": gold,
                 "fallo_conocido": bool(caso.get("fallo_conocido")),
                 "puntua": bool(gold)},
        "estado": res.get("estado"),
        "excedido": bool(res.get("excedido")),
        "tokens_contexto": res.get("tokens_contexto"),
        "limite_tokens": res.get("limite_tokens"),
        "texto_contexto_sha256": (hashlib.sha256(
            ctx.encode("utf-8")).hexdigest() if ctx else None),
        "texto_contexto_longitud": len(ctx),
        "nota": caso.get("nota"),
        "primarias": [],
        "paginas": [],
        "cobertura": {"referencias": gold, "contexto": [], "primaria": [],
                      "faltantes": [], "puntua": bool(gold)},
        "integridad_ok": True,
        "integridad_incidencias": [],
        "error_preparar": None,
    }
    for r in (res.get("recuperacion") or {}).get("resultados") or []:
        registro["primarias"].append({
            "documento": r.get("documento"),
            "id_tecnico": r.get("id_tecnico"),
            "ruta_oficial": r.get("ruta_oficial"),
            "titulo": r.get("titulo"),
            "puntuacion_bm25": r.get("puntuacion_bm25"),
            "paginas": list(r.get("paginas") or []),
            "paginas_entregadas": list(r.get("paginas_entregadas") or []),
        })
    for p in res.get("paginas") or []:
        fila = {clave: p.get(clave) for clave in CLAVES_PAGINA}
        doc_ok = (documento is None) or (fila["doc"] == documento)
        edicion_ok = (version is None) or (fila["version"] == version)
        ruta_ok, texto_leido, numero_archivo = _pagina_legible(
            contenido, fila["archivo"], documento, version)
        fila["ruta_ok"] = ruta_ok
        fila["numero_archivo"] = numero_archivo
        pagina_coincide = bool(ruta_ok) and isinstance(numero_archivo, int) \
            and isinstance(fila["pagina"], int) \
            and numero_archivo == fila["pagina"]
        fila["pagina_coincide_archivo"] = pagina_coincide
        hay_texto = texto_leido is not None and bool(texto_leido.strip())
        # Literal completo primero; EXCEPCIÓN de presentación solo si la
        # página cerró el texto entregado (rstrip global del adaptador): la
        # cola de ctx debe ser texto_leido.rstrip() + "\n", sin perder
        # ningún carácter sustantivo ni espacio interno.
        literal_en_contexto = bool(hay_texto and ctx and texto_leido in ctx)
        ajuste_espacios = bool(
            hay_texto and ctx and not literal_en_contexto and
            ctx.endswith(texto_leido.rstrip() + "\n"))
        fila["literal_en_contexto"] = literal_en_contexto
        fila["ajuste_espacios_finales"] = ajuste_espacios
        fila["sha256_local"] = (hashlib.sha256(
            texto_leido.encode("utf-8")).hexdigest()
            if texto_leido is not None else None)
        fila["sha_coincide"] = bool(fila["sha256_local"]) and \
            fila["sha256_local"] == fila["texto_sha256"]
        fila["longitud_texto"] = len(texto_leido) if texto_leido is not None \
            else None
        fila["texto_en_contexto"] = True if (literal_en_contexto or
                                             ajuste_espacios) else (
            False if texto_leido is not None else None)
        fila["edicion_ok"] = doc_ok and edicion_ok
        registro["paginas"].append(fila)
        if not doc_ok:
            registro["integridad_incidencias"].append(
                {"pagina": fila["pagina"], "tipo": "doc_distinto",
                 "detalle": fila["doc"]})
        if not edicion_ok:
            registro["integridad_incidencias"].append(
                {"pagina": fila["pagina"], "tipo": "edicion_distinta",
                 "detalle": fila["version"]})
        if not ruta_ok:
            registro["integridad_incidencias"].append(
                {"pagina": fila["pagina"], "tipo": "ruta_fuera_documento_edicion",
                 "detalle": fila["archivo"]})
        elif texto_leido is None:
            registro["integridad_incidencias"].append(
                {"pagina": fila["pagina"], "tipo": "archivo_no_leible",
                 "detalle": fila["archivo"]})
        else:
            if not pagina_coincide:
                registro["integridad_incidencias"].append(
                    {"pagina": fila["pagina"],
                     "tipo": "pagina_no_coincide_archivo",
                     "detalle": "afirma %r pero el archivo es %s"
                                % (fila["pagina"],
                                   Path(fila["archivo"]).name)})
            if not hay_texto:
                registro["integridad_incidencias"].append(
                    {"pagina": fila["pagina"], "tipo": "sin_evidencia_textual",
                     "detalle": "pagina vacia o solo espacios: sin evidencia "
                                "textual para esta suite de paginas normativas"})
            else:
                if not fila["sha_coincide"]:
                    registro["integridad_incidencias"].append(
                        {"pagina": fila["pagina"],
                         "tipo": "sha_texto_distinto"})
                if not fila["texto_en_contexto"]:
                    registro["integridad_incidencias"].append(
                        {"pagina": fila["pagina"],
                         "tipo": "texto_no_en_contexto"})
    for g in gold:
        # Cobertura ESTRICTA: edición/ruta correctas, número de página
        # contrastado con el archivo, sha256 local == devuelto y texto
        # presente y no vacío en texto_contexto (literal completo, o
        # exclusivamente la excepción de presentación documentada:
        # espacios finales de la página que cerró el texto entregado).
        # Evidencia ilegible o vacía no contabiliza cobertura (la integridad
        # falla, y por separado).
        elegibles = [f for f in registro["paginas"]
                     if f["pagina"] == g and f["edicion_ok"] and f["ruta_ok"]
                     and f["pagina_coincide_archivo"] is True
                     and f["sha_coincide"] is True
                     and f["texto_en_contexto"] is True]
        if elegibles:
            registro["cobertura"]["contexto"].append(g)
            if any(f["motivo"] == "primaria" for f in elegibles):
                registro["cobertura"]["primaria"].append(g)
        else:
            registro["cobertura"]["faltantes"].append(g)
    registro["integridad_ok"] = not registro["integridad_incidencias"]
    return registro


def _resumen(registros, datos, estricto):
    """Resumen separado: cobertura esperada, fallo conocido, pérdidas y mejoras."""
    casos_ok = [r["id"] for r in registros if r["estado"] == "ok"]
    no_ok = [{"id": r["id"], "estado": r["estado"]}
             for r in registros if r["estado"] != "ok"]
    con_gold = [r for r in registros if r["gold"]["puntua"]]
    referencias_totales = sum(len(r["gold"]["referencias_paginas"])
                              for r in con_gold)
    evaluables = [r for r in con_gold if not r["gold"]["fallo_conocido"]]
    refs_evaluables = sum(len(r["gold"]["referencias_paginas"])
                          for r in evaluables)
    cubiertas_ctx = sum(len(r["cobertura"]["contexto"]) for r in evaluables)
    cubiertas_primaria = sum(len(r["cobertura"]["primaria"]) for r in evaluables)
    cubiertas_ctx_total = sum(len(r["cobertura"]["contexto"]) for r in con_gold)
    cubiertas_primaria_total = sum(len(r["cobertura"]["primaria"])
                                   for r in con_gold)
    perdidas_nuevas = [{"id": r["id"], "pagina": g}
                       for r in evaluables for g in r["cobertura"]["faltantes"]]
    integridad_fallos = [{"id": r["id"],
                          "incidencias": r["integridad_incidencias"]}
                         for r in registros if not r["integridad_ok"]]
    registro_conocidos, mejoras = [], []
    faltantes_conocidas = []
    for r in registros:
        if not r["gold"]["fallo_conocido"]:
            continue
        faltan = list(r["cobertura"]["faltantes"])
        cubiertas = list(r["cobertura"]["contexto"])
        registro_conocidos.append({
            "id": r["id"],
            "referencias_paginas": r["gold"]["referencias_paginas"],
            "cubiertas": cubiertas, "faltantes": faltan,
            "resultado": "falta" if faltan else "cubre"})
        if faltan:
            faltantes_conocidas.extend(
                {"id": r["id"], "pagina": g} for g in faltan)
        else:
            mejoras.append({"id": r["id"], "paginas": cubiertas})
    faltantes_todas = perdidas_nuevas + faltantes_conocidas
    esperado = dict(datos.get("esperado") or {})
    # Evitar éxito vacuo: cardinalidad declarada en esperado vs observada en
    # los registros (solo claves presentes; no se exigen campos ausentes en
    # fixtures sintéticas) e ids de registros contra TODOS los casos del
    # fixture. La mejora del caso con fallo_conocido sigue admitida: estos
    # contrastes son de cardinalidad, no de cobertura.
    inconsistencias = []
    for clave, contador in (("referencias_evaluables", refs_evaluables),
                            ("referencias_totales", referencias_totales)):
        declarado = esperado.get(clave)
        if declarado is not None and int(declarado) != contador:
            inconsistencias.append({"campo": "esperado.%s" % clave,
                                    "declarado": declarado,
                                    "observado": contador})
    if isinstance(datos.get("casos"), list):
        ids_fixture = [str(c.get("id") or "") for c in datos["casos"]]
        ids_registros = [r["id"] for r in registros]
        if ids_fixture != ids_registros:
            inconsistencias.append({"campo": "casos_ids",
                                    "declarado": ids_fixture,
                                    "observado": ids_registros})
    resumen = {
        "casos_total": len(registros),
        "casos_ok": casos_ok,
        "casos_no_ok": no_ok,
        "referencias_totales": referencias_totales,
        "referencias_evaluables": refs_evaluables,
        "cobertura_contexto_evaluable": cubiertas_ctx,
        "cobertura_primaria_evaluable": cubiertas_primaria,
        "cobertura_contexto_total": cubiertas_ctx_total,
        "cobertura_primaria_total": cubiertas_primaria_total,
        "esperado": esperado,
        "cumple_esperado_contexto": bool(
            esperado and cubiertas_ctx == refs_evaluables
            and refs_evaluables == esperado.get("referencias_evaluables")),
        "fallo_conocido": registro_conocidos,
        "perdidas_nuevas": perdidas_nuevas,
        "mejoras": mejoras,
        "integridad_fallos": integridad_fallos,
        "inconsistencias": inconsistencias,
        "estricto": bool(estricto),
        "limites": [
            "la cobertura por presencia de página no acredita calidad global "
            "de la respuesta ni fidelidad sustantiva del apartado",
            "el gold evaluable excluye el caso marcado fallo_conocido y los "
            "casos sin gold; el gold no se modifica por los resultados",
        ],
    }
    codigo = 1 if (no_ok or integridad_fallos or perdidas_nuevas or
                   inconsistencias or
                   (estricto and faltantes_todas)) else 0
    return resumen, codigo


def _imprimir(registros, resumen, salida_ruta, codigo):
    """Resumen legible en stdout; el fallo conocido se muestra destacado."""
    w = sys.stdout.write
    w("== Regresión recuperación: %d casos ==\n" % resumen["casos_total"])
    for r in registros:
        g = r["cobertura"]["referencias"]
        cubiertas = r["cobertura"]["contexto"]
        falta = r["cobertura"]["faltantes"]
        integ = "ok" if r["integridad_ok"] else "INTEGRIDAD"
        w("%-7s estado=%-21s gold=%-6s ctx=%-8s faltan=%-6s integridad=%s\n" % (
            r["id"], str(r["estado"]), ("%s" % g if g else "-"),
            ("%s" % cubiertas if cubiertas else "-"),
            ("%s" % falta if falta else "-"), integ))
    for fc in resumen["fallo_conocido"]:
        if fc["resultado"] == "cubre":
            w("FALLO CONOCIDO SUPERADO (mejora; gold sin modificar): %s cubre %s\n"
              % (fc["id"], fc["cubiertas"]))
        else:
            w("FALLO CONOCIDO (esperado, no nueva pérdida): %s falta %s\n"
              % (fc["id"], fc["faltantes"]))
    w("-- Resumen --\n")
    w("Casos ok: %d/%d · no ok: %s\n" % (
        len(resumen["casos_ok"]), resumen["casos_total"],
        ("%s" % [x["id"] for x in resumen["casos_no_ok"]]
         if resumen["casos_no_ok"] else "(ninguno)")))
    w("Cobertura contexto evaluable: %d/%d (esperado %s; fallo conocido fuera)\n"
      % (resumen["cobertura_contexto_evaluable"],
         resumen["referencias_evaluables"],
         resumen["esperado"].get("cobertura_contexto", "?")))
    w("Cobertura primaria evaluable: %d/%d\n" % (
        resumen["cobertura_primaria_evaluable"],
        resumen["referencias_evaluables"]))
    w("Cobertura contexto TOTAL: %d/%d · primaria TOTAL: %d/%d (incluido el fallo conocido)\n"
      % (resumen["cobertura_contexto_total"], resumen["referencias_totales"],
         resumen["cobertura_primaria_total"], resumen["referencias_totales"]))
    w("Pérdidas nuevas: %s\n" % (resumen["perdidas_nuevas"] or "(ninguna)"))
    w("Mejoras: %s\n" % (resumen["mejoras"] or "(ninguna)"))
    w("Integridad: %s\n" % (resumen["integridad_fallos"] or "ok en todos"))
    w("Inconsistencias (cardinalidad/casos): %s\n" % (
        resumen["inconsistencias"] or "(ninguna)"))
    if resumen["estricto"] and resumen["fallo_conocido"] and \
            any(fc["faltantes"] for fc in resumen["fallo_conocido"]):
        w("--ESTRICTO-- referencia conocida faltante (SUA-02 incluida): exit 1\n")
    w("Límite: la cobertura por presencia de página no acredita calidad global.\n")
    w("Salida: %s · exit %d\n" % (salida_ruta, codigo))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Regresión de recuperación REAL con fixture congelada.")
    ap.add_argument("--contenido", default=str(CONTENIDO_DEFECTO),
                    help="raíz del corpus (por defecto <checkout>/contenido)")
    ap.add_argument("--salida", default=str(SALIDA_DEFECTO),
                    help="JSON de resultados (por defecto .local/regresion-recuperacion/actual.json)")
    ap.add_argument("--fixture", default=str(FIXTURE_DEFECTO),
                    help="fixture congelada de casos (por defecto casos.json junto a este runner)")
    ap.add_argument("--estricto", action="store_true",
                    help="exit 1 por CUALQUIER referencia faltante (incluida SUA-02)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fixture_ruta = Path(args.fixture)
    try:
        datos = _cargar_fixture(fixture_ruta)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("fixture invalida (%s): %s\n" % (fixture_ruta, exc))
        return 2
    contenido = Path(args.contenido).resolve()
    if not (contenido / "indice" / "apartados.jsonl").exists():
        sys.stderr.write("sin indice de corpus en %s\n" % contenido)
        return 2
    salida_ruta = Path(args.salida)
    if not salida_ruta.is_absolute():
        salida_ruta = RAIZ / salida_ruta
    if str(HTTP_LOCAL) not in sys.path:
        sys.path.insert(0, str(HTTP_LOCAL))
    import adaptador_contexto  # import REAL; sin parches de ranking ni encs
    ad = adaptador_contexto.AdaptadorContexto(str(contenido))
    presupuesto = int((datos.get("config") or {}).get("presupuesto_tokens")
                      or PRESUPUESTO)
    max_resultados = int((datos.get("config") or {}).get("max_resultados")
                         or MAX_RESULTADOS)
    casos = datos["casos"]
    registros = []
    for caso in casos:
        try:
            res = ad.preparar(caso["consulta"],
                              documento=caso.get("documento"),
                              version=caso.get("version"),
                              presupuesto_tokens=presupuesto,
                              max_resultados=max_resultados)
            registros.append(_registro_caso(caso, res, contenido))
        except Exception as exc:  # estado no-ok; la corrida continúa
            registros.append(_registro_error(caso, exc))
    resumen, codigo = _resumen(registros, datos, args.estricto)
    actual = {
        "esquema": ESQUEMA,
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "python": sys.version,
            "plataforma": sys.platform,
            "hashes": {
                "motor_acceso": _sha_fichero(HTTP_LOCAL / "acceso.py"),
                "motor_adaptador_contexto": _sha_fichero(
                    HTTP_LOCAL / "adaptador_contexto.py"),
                "manifiesto_publico": {
                    "archivo": "manifest_publico.json",
                    "sha256": _sha_fichero(
                        contenido / "manifest_publico.json")},
                "indice_apartados": {
                    "archivo": "indice/apartados.jsonl",
                    "sha256": _sha_fichero(
                        contenido / "indice" / "apartados.jsonl")},
                "fixture": {"archivo": fixture_ruta.name,
                            "sha256": _sha_fichero(fixture_ruta)},
            },
            "busqueda": {"presupuesto_tokens": presupuesto,
                         "max_resultados": max_resultados,
                         "modo_tokens": ad.modo_contadores,
                         "encoders": sorted(ad.encs)},
            "fixture": {
                "referencia_conservada_durante_comparacion": bool(
                    datos.get("referencia_conservada_durante_comparacion")),
                "nota_referencia": datos.get("nota_referencia"),
                "documento_rebt": (datos.get("documentos") or {}).get("REBT"),
                "documento_sua": (datos.get("documentos") or {}).get("SUA"),
            },
            "validacion_editorial": _validacion_editorial(contenido, casos),
        },
        "config": {"estricto": bool(args.estricto),
                   "contenido": str(contenido),
                   "salida": str(salida_ruta)},
        "resumen": resumen,
        "casos": registros,
    }
    salida_ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(salida_ruta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(actual, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    _imprimir(registros, resumen, salida_ruta, codigo)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
