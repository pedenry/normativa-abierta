#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ejecutar_sin_ubicacion.py — regresión de consultas SIN ubicación (aclaración + nacionales).

Encargo (evaluación-normativa, 2026-11-16; revisión del contrato 2026-11-16): fixture
casos-sin-ubicacion.json FIJADA ANTES de ejecutar motores (rúbrica v2; historial v1->v2
dentro del propio fixture, sin tocar casos/consultas/gold). 14 consultas territoriales
sin ciudad/CCAA/documento/edición esperan estado aclaracion_necesaria con
aclaracion.campos_requeridos IGUALES en conjunto a TODOS los campos requeridos del caso
(key 'campos_requeridos_permitidos' conservada por compatibilidad), aclaracion.pregunta
no vacía, cero páginas/resultados y sin inventar territorio; 6 nacionales técnicas esperan
estado ok con fuente/página/edición literales y sin pedir territorio. El runner llama SOLO
a la API REAL: ad.preparar(consulta, None, None, 20000, 2); ningún campo esperado llega al
motor y el evaluador no resuelve ni enruta la consulta.

Helpers de integridad de ejecutar_libres.py reutilizados SOLO para scoring:
_pagina_legible_libre, _metadata_doc, _sha_fichero y CLAVES_PAGINA. Ningún filtro de
documento; la evaluación de integridad y de coincidencia con lo esperado ocurre DESPUÉS
de la respuesta, sin filtrar páginas ni resultados.

Criterio idéntico antes/después DENTRO de una misma versión de rúbrica: sin modos
alternativos ni adjudicaciones, y la salida registra rubrica_version. v1 (subconjunto no
vacío de campos) y v2 (IGUALDAD: todos los campos requeridos, sin extras) NO se declaran
criterio congelado idéntico: v2 corrige el falsoacierto lógico de v1 (pedir SOLO municipio
cuando hacen falta CA+municipio); la evaluación v1 y la captura API de baseline las
conserva Codex y los mismos casos se reevalúan v2 antes/después. Un caso SIN ubicación solo es acierto si TODOS sus
criterios son ok; un estado ok o una entrega de páginas NO se convierte en acierto cuando
faltan la pregunta o el estado esperado (se distingue error, omisión y pendiente por
criterio, con evidencia concreta; ver clases en la rúbrica del fixture).

«No inventar territorio» se comprueba SOLO cuando el motor emite aclaración: ningún nombre
territorial del corpus (jurisdiccion/municipio de los doc.json distribute=true; lectura de
metadatos, sin texto de páginas) puede aparecer como subcadena normalizada en
aclaracion.pregunta o texto_contexto. Heurística declarada; falsos positivos posibles con
topónimos cortos homófonos de palabras comunes.

Salida: esquema regresion-recuperacion-sin-ubicacion/1 con SHA-256 de páginas verificadas
(sin texto completo), tokens_contexto por caso, pregunta/campos/estado de aclaración
observados, documentos devueltos y ajenos (trazados, no filtrados), hashes de
runner/motor/fixture/corpus y notas de límites. Uso:
    python evaluacion/regresion_recuperacion/territorial/ejecutar_sin_ubicacion.py
        [--contenido RUTA] [--fixture RUTA] [--salida RUTA]
Sin API ni red, sin procesos externos. Exit 0 si todos los casos son acierto y sin
inconsistencias; 1 si falla CUALQUIER caso o hay inconsistencia fixture/registros; 2 si el
fixture o el corpus son inválidos. tokens_contexto es recuento local (proxy de texto:
tiktoken o chars/4), NO usage de API; sin desglose entrada/salida/caché (no disponible en
este motor). No se calcula ahorro: no hay pares con cobertura y trazabilidad comparables
aquí. Una llamada por caso, sin reintentos; excepciones de preparar quedan capturadas como
estado error_preparar con el caso fallido.
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
sys.path.insert(0, str(CARPETA))
# helpers de integridad de ejecutar_libres.py, SOLO scoring (no filtran candidatos):
import ejecutar_libres as EL

FIXTURE_DEFECTO = CARPETA / "casos-sin-ubicacion.json"
SALIDA_DEFECTO = RAIZ / ".local" / "sin-ubicacion" / "actual.json"
CONTENIDO_DEFECTO = RAIZ / "contenido"
PRESUPUESTO, MAX_RESULTADOS = 20000, 2
ESQUEMA = "regresion-recuperacion-sin-ubicacion/1"
ESTADO_ACLARACION = "aclaracion_necesaria"
CAMPOS_TERRITORIO = ("comunidad_autonoma", "municipio")


def _normalizar(texto):
    """Normalización genérica para la heurística de territorio inventado:
    sin tildes, casefold, sin puntuación; solo para comparar subcadenas."""
    if not isinstance(texto, str) or not texto.strip():
        return ""
    plano = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in plano if not unicodedata.combining(c)).casefold()
    plano = re.sub(r"[^a-z0-9\s]", " ", plano)
    return " ".join(plano.split())


def _nombres_territoriales_corpus(contenido):
    """Nombres territoriales declarados por el corpus (jurisdiccion/municipio de
    los doc.json con distribute true). Solo metadatos; sin texto de páginas."""
    nombres = set()
    for ruta_dj in sorted(contenido.glob("docs/*/*/doc.json")):
        try:
            meta = json.loads(ruta_dj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict) or meta.get("distribute") is not True:
            continue
        for clave in ("jurisdiccion", "municipio"):
            valor = meta.get(clave)
            if isinstance(valor, str) and valor.strip():
                nombres.add(valor.strip())
    return sorted(nombres)


def _cargar_fixture(ruta):
    """Valida el contrato regresion-recuperacion-sin-ubicacion-fixture/1: ids únicos,
    consultas no vacías, grupo territorial con campos permitidos dentro del vocabulario
    (lista no vacía, sin duplicados) y grupo nacional con gold doc/versión/páginas."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("esquema") != "regresion-recuperacion-sin-ubicacion-fixture/1":
        raise ValueError("esquema debe ser 'regresion-recuperacion-sin-ubicacion-fixture/1'")
    casos = datos.get("casos")
    if not isinstance(casos, list) or not casos:
        raise ValueError("fixture sin lista 'casos'")
    ids = set()
    for c in casos:
        cid = str(c.get("id") or "")
        if not cid or cid in ids:
            raise ValueError("id invalido o duplicado: %r" % cid)
        ids.add(cid)
        if not str(c.get("consulta") or "").strip():
            raise ValueError("consulta vacia en %r" % cid)
        grupo = c.get("grupo")
        if grupo == "territorial":
            if c.get("esperado_estado") != ESTADO_ACLARACION:
                raise ValueError("caso territorial %r exige esperado_estado %s" % (cid, ESTADO_ACLARACION))
            campos = c.get("campos_requeridos_permitidos")
            if (not isinstance(campos, list) or not campos
                    or len(set(campos)) != len(campos)
                    or any(x not in CAMPOS_TERRITORIO for x in campos)):
                raise ValueError("campos_requeridos_permitidos invalidos en %r" % cid)
        elif grupo == "nacional":
            if c.get("esperado_estado") != "ok":
                raise ValueError("caso nacional %r exige esperado_estado 'ok'" % cid)
            if not c.get("esperado_documento") or not c.get("esperada_version"):
                raise ValueError("gold doc/version ausente en %r" % cid)
            pags = c.get("esperadas_paginas")
            if (not isinstance(pags, list) or not pags
                    or any(not isinstance(p, int) or p < 1 for p in pags)):
                raise ValueError("esperadas_paginas invalidas en %r" % cid)
        else:
            raise ValueError("grupo invalido en %r: %r" % (cid, grupo))
    return datos


def _criterio(reg, cid, nombre, resultado, clase=None, evidencia=""):
    """Registra el resultado por criterio con evidencia concreta (rúbrica v1)."""
    reg["criterios"].append({"criterio": cid, "nombre": nombre, "resultado": resultado,
                             "clase": clase, "evidencia": evidencia})


def _registro(caso, res, contenido, nombres):
    """Registro por caso: traza TODO lo devuelto (páginas con integridad, aclaración
    observada, documentos), evalúa el criterio del grupo DESPUÉS de la respuesta y no
    filtra nunca páginas ni resultados. Sin pasar gold al motor: el gold solo aparece
    aquí, en 'esperado', para scoring."""
    grupo = caso["grupo"]
    doc_esp, ver_esp = caso.get("esperado_documento"), caso.get("esperada_version")
    gold = [int(g) for g in caso.get("esperadas_paginas") or []]
    ctx = res.get("texto_contexto") or ""
    reg = {"id": caso["id"], "grupo": grupo, "consulta": caso["consulta"],
           "esperado": {"estado": caso.get("esperado_estado"), "documento": doc_esp,
                        "version": ver_esp, "paginas": gold},
           "estado": res.get("estado"), "excedido": bool(res.get("excedido")),
           "tokens_contexto": res.get("tokens_contexto"),
           "tokens_nota": "recuento local (proxy de texto), no usage de API; "
                          "sin desglose entrada/salida/cache en este motor",
           "texto_contexto_sha256": hashlib.sha256(ctx.encode("utf-8")).hexdigest() if ctx else None,
           "texto_contexto_longitud": len(ctx),
           "resolucion_ambito": res.get("resolucion_ambito"),
           "error_preparar": res.get("error_preparar"),
           "aclaracion_observada": None,
           "primarias": [], "paginas": [], "documentos": [], "documentos_devueltos": [],
           "documentos_ajenos": [], "cobertura": {"contexto": [], "primaria": [],
                                                  "faltantes": list(gold)},
           "integridad_ok": True, "integridad_incidencias": [],
           "territorios_mencionados": [], "criterios": [], "acierto": False}
    for r in (res.get("recuperacion") or {}).get("resultados") or []:
        reg["primarias"].append({"documento": r.get("documento"), "id_tecnico": r.get("id_tecnico"),
                                 "ruta_oficial": r.get("ruta_oficial"), "titulo": r.get("titulo"),
                                 "puntuacion_bm25": r.get("puntuacion_bm25"),
                                 "paginas": list(r.get("paginas") or []),
                                 "paginas_entregadas": list(r.get("paginas_entregadas") or [])})
    acl = res.get("aclaracion") if isinstance(res.get("aclaracion"), dict) else None
    if acl is not None:
        reg["aclaracion_observada"] = {"pregunta": acl.get("pregunta"),
                                       "campos_requeridos": acl.get("campos_requeridos")}
    docs_meta, memo = {}, {}  # caché de edición y metadata por (doc, versión), por caso
    for p in res.get("paginas") or []:
        fila = {k: p.get(k) for k in EL.CLAVES_PAGINA}
        incs = reg["integridad_incidencias"]
        ruta_ok, texto, numero = EL._pagina_legible_libre(
            contenido, fila["archivo"], fila["doc"], fila["version"], memo)
        fila["ruta_ok"], fila["numero_archivo"] = ruta_ok, numero
        fila["pagina_coincide_archivo"] = bool(ruta_ok) and isinstance(fila["pagina"], int) \
            and numero == fila["pagina"]
        hay_texto = texto is not None and bool(texto.strip())
        literal = bool(hay_texto and ctx and texto in ctx)
        # Excepción documentada (la de ejecutar.py/ejecutar_libres.py): rstrip global
        # del adaptador, admitido SOLO si la página cerró el texto entregado.
        final_rstrip = bool(hay_texto and ctx and not literal
                            and ctx.endswith(texto.rstrip() + "\n"))
        fila["literal_en_contexto"], fila["ajuste_espacios_finales"] = literal, final_rstrip
        fila["texto_en_contexto"] = True if (literal or final_rstrip) \
            else (False if texto is not None else None)
        fila["sha256_local"] = hashlib.sha256(texto.encode("utf-8")).hexdigest() \
            if texto is not None else None
        fila["sha_coincide"] = bool(fila["sha256_local"]) \
            and fila["sha256_local"] == fila["texto_sha256"]
        fila["longitud_texto"] = len(texto) if texto is not None else None
        if grupo == "nacional":
            fila["coincide_documento_esperado"] = fila["doc"] == doc_esp
            fila["coincide_version_esperada"] = fila["version"] == ver_esp
            fila["coincide_esperado"] = fila["coincide_documento_esperado"] \
                and fila["coincide_version_esperada"]
        else:
            # sin gold declarado: no hay coincidencia esperada que evaluar
            fila["coincide_esperado"] = None
        reg["paginas"].append(fila)
        clave = (fila["doc"], fila["version"])
        if clave not in docs_meta:
            meta = EL._metadata_doc(contenido, fila["doc"], fila["version"], memo)
            docs_meta[clave] = {"documento": fila["doc"], "version": fila["version"],
                                "carpeta": meta["carpeta"], "metadata_ok": meta["metadata_ok"],
                                "error": meta["error"]}
            if not meta["metadata_ok"]:
                incs.append({"documento": fila["doc"], "tipo": "metadata_incoherente",
                             "detalle": meta["error"]})
        if not ruta_ok:
            incs.append({"pagina": fila["pagina"], "tipo": "ruta_fuera_documento_edicion",
                         "detalle": fila["archivo"]})
        elif texto is None:
            incs.append({"pagina": fila["pagina"], "tipo": "archivo_no_leible",
                         "detalle": fila["archivo"]})
        else:
            if not fila["pagina_coincide_archivo"]:
                incs.append({"pagina": fila["pagina"], "tipo": "pagina_no_coincide_archivo",
                             "detalle": "afirma %r, archivo %s" % (fila["pagina"],
                                                                   Path(fila["archivo"]).name)})
            if not hay_texto:
                incs.append({"pagina": fila["pagina"], "tipo": "sin_evidencia_textual",
                             "detalle": "página vacía o solo espacios"})
            else:
                if not fila["sha_coincide"]:
                    incs.append({"pagina": fila["pagina"], "tipo": "sha_texto_distinto"})
                if not fila["texto_en_contexto"]:
                    incs.append({"pagina": fila["pagina"], "tipo": "texto_no_en_contexto"})
    reg["documentos"] = sorted(docs_meta.values(),
                               key=lambda d: (str(d["documento"]), str(d["version"])))
    reg["documentos_devueltos"] = sorted({str(f["doc"]) for f in reg["paginas"] if f["doc"]})
    if grupo == "nacional":
        reg["documentos_ajenos"] = sorted(d for d in reg["documentos_devueltos"] if d != doc_esp)
        for g in gold:
            elegibles = [f for f in reg["paginas"] if f["pagina"] == g
                         and f["coincide_esperado"] and f["ruta_ok"]
                         and f["pagina_coincide_archivo"] is True
                         and f["sha_coincide"] is True and f["texto_en_contexto"] is True]
            if elegibles:
                reg["cobertura"]["contexto"].append(g)
                if any(f["motivo"] == "primaria" for f in elegibles):
                    reg["cobertura"]["primaria"].append(g)
                reg["cobertura"]["faltantes"].remove(g)
    reg["integridad_ok"] = not reg["integridad_incidencias"]
    if grupo == "territorial":
        _criterios_territorial(reg, caso, res, acl, nombres)
    else:
        _criterios_nacional(reg, res, acl)
    reg["acierto"] = all(c["resultado"] == "ok" for c in reg["criterios"])
    return reg


def _criterios_territorial(reg, caso, res, acl, nombres):
    """Rúbrica v2 territorial (c1..c6 del fixture): estado exacto, campos_igualdad
    (TODOS los campos requeridos del caso, sin extras; en v1 era subconjunto no
    vacío), pregunta no vacía, cero páginas, cero resultados, sin inventar territorio.
    El estado ok con páginas NO es acierto: falta la aclaración esperada (omisión) y se
    entregó lo que no tocaba (error)."""
    perm = set(caso.get("campos_requeridos_permitidos") or [])
    estado = reg["estado"]
    aclara = (estado == ESTADO_ACLARACION)
    # c1 estado_exacto
    if aclara:
        _criterio(reg, "c1", "estado_exacto", "ok",
                  evidencia="estado %s" % estado)
    else:
        _criterio(reg, "c1", "estado_exacto", "fallo",
                  "error" if estado is not None else "pendiente",
                  "estado observado %r; esperado %s" % (estado, ESTADO_ACLARACION))
    campos = (acl or {}).get("campos_requeridos") if acl else None
    # c2 campos_igualdad (rubrica v2): los campos pedidos deben ser EXACTAMENTE los
    # requeridos del caso (key 'campos_requeridos_permitidos' conservada por
    # compatibilidad): falta alguno = omision; extra fuera del conjunto = error;
    # vacio = omision; duplicados o tipos no cadena = error. v1 (subconjunto no
    # vacio) admitia pedir SOLO municipio cuando hacen falta CA+municipio:
    # falsoacierto logico corregido; la evaluacion v1 se conserva.
    if aclara and acl is None:
        _criterio(reg, "c2", "campos_igualdad", "fallo", "omision",
                  "estado %s sin clave aclaracion" % ESTADO_ACLARACION)
    elif aclara:
        if not isinstance(campos, list):
            _criterio(reg, "c2", "campos_igualdad", "fallo", "error",
                      "campos_requeridos malformado: %r" % (campos,))
        elif not campos:
            _criterio(reg, "c2", "campos_igualdad", "fallo", "omision",
                      "no pide ningun campo; requeridos %s" % sorted(perm))
        elif any(not isinstance(x, str) for x in campos):
            _criterio(reg, "c2", "campos_igualdad", "fallo", "error",
                      "campos_requeridos con tipos no cadena: %r" % (campos,))
        elif len(set(campos)) != len(campos):
            _criterio(reg, "c2", "campos_igualdad", "fallo", "error",
                      "campos_requeridos con duplicados: %r" % (campos,))
        else:
            faltan, sobran = perm - set(campos), set(campos) - perm
            if not faltan and not sobran:
                _criterio(reg, "c2", "campos_igualdad", "ok",
                          evidencia="campos %s == requeridos (igualdad v2)"
                                    % sorted(campos))
            elif faltan and not sobran:
                _criterio(reg, "c2", "campos_igualdad", "fallo", "omision",
                          "faltan campos requeridos %s (pedidos %s); la omision de un "
                          "campo requerido no es acierto"
                          % (sorted(faltan), sorted(campos)))
            else:
                _criterio(reg, "c2", "campos_igualdad", "fallo", "error",
                          "faltan %s y sobran %s frente a requeridos %s (pedidos %s)"
                          % (sorted(faltan), sorted(sobran), sorted(perm), sorted(campos)))
    else:
        _criterio(reg, "c2", "campos_igualdad", "pendiente", None,
                  "el motor no aclaro (estado %r); campos no evaluables" % estado)
    # c3 pregunta_no_vacia
    pregunta = (acl or {}).get("pregunta") if acl else None
    if aclara and acl is None:
        _criterio(reg, "c3", "pregunta_no_vacia", "fallo", "omision",
                  "estado %s sin clave aclaracion" % ESTADO_ACLARACION)
    elif aclara:
        if isinstance(pregunta, str) and pregunta.strip():
            _criterio(reg, "c3", "pregunta_no_vacia", "ok", evidencia="pregunta no vacia")
        else:
            _criterio(reg, "c3", "pregunta_no_vacia", "fallo", "omision",
                      "pregunta ausente o vacia: %r" % (pregunta,))
    else:
        _criterio(reg, "c3", "pregunta_no_vacia", "pendiente", None,
                  "el motor no aclaro (estado %r)" % estado)
    # c4 cero_paginas / c5 cero_resultados
    sin_respuesta = bool(reg.get("error_preparar"))
    paginas = res.get("paginas")
    if sin_respuesta:
        _criterio(reg, "c4", "cero_paginas", "pendiente", None,
                  "sin respuesta (error_preparar); paginas no evaluables")
    elif isinstance(paginas, list) and paginas == []:
        _criterio(reg, "c4", "cero_paginas", "ok", evidencia="0 paginas")
    elif isinstance(paginas, list):
        _criterio(reg, "c4", "cero_paginas", "fallo", "error",
                  "aclaracion (o respuesta) con %d paginas entregadas" % len(paginas))
    else:
        _criterio(reg, "c4", "cero_paginas", "error", "omision",
                  "res.paginas ausente o malformado: %r" % (paginas,))
    resultados = (res.get("recuperacion") or {}).get("resultados")
    if sin_respuesta:
        _criterio(reg, "c5", "cero_resultados", "pendiente", None,
                  "sin respuesta (error_preparar); resultados no evaluables")
    elif isinstance(resultados, list) and resultados == []:
        _criterio(reg, "c5", "cero_resultados", "ok", evidencia="0 resultados")
    elif isinstance(resultados, list):
        _criterio(reg, "c5", "cero_resultados", "fallo", "error",
                  "%d resultados entregados" % len(resultados))
    else:
        _criterio(reg, "c5", "cero_resultados", "error", "omision",
                  "recuperacion.resultados ausente o malformado")
    # c6 no_inventar_territorio (solo cuando emite aclaración)
    if acl is not None:
        ctx = res.get("texto_contexto") or ""
        texto = "%s\n%s" % (str(pregunta or ""), ctx)
        plano = _normalizar(texto)
        mencionados = sorted(n for n in nombres
                             if len(_normalizar(n)) >= 4 and _normalizar(n) in plano)
        reg["territorios_mencionados"] = mencionados
        if mencionados:
            _criterio(reg, "c6", "no_inventar_territorio", "fallo", "error",
                      "aclaracion menciona territorios del corpus: %s" % mencionados)
        else:
            _criterio(reg, "c6", "no_inventar_territorio", "ok",
                      evidencia="sin nombres territoriales del corpus en pregunta/contexto")
    else:
        _criterio(reg, "c6", "no_inventar_territorio", "no_aplica", None,
                  "sin aclaracion emitida; la heuristica solo aplica a respuestas de aclaracion")


def _criterios_nacional(reg, res, acl):
    """Rúbrica v1 nacional (n1..n4): estado ok sin pedir territorio, gold literal
    completo con integridad ok. Los documentos ajenos se trazan, no filtran."""
    estado = reg["estado"]
    if estado == "ok":
        _criterio(reg, "n1", "estado_exacto", "ok", evidencia="estado ok")
    else:
        _criterio(reg, "n1", "estado_exacto", "fallo", "error",
                  "estado observado %r; esperado 'ok'" % estado)
    if estado == ESTADO_ACLARACION or acl:
        _criterio(reg, "n2", "sin_peticion_territorio", "fallo", "error",
                  "el motor pide territorio para una consulta tecnica nacional "
                  "(estado %r, aclaracion=%r)" % (estado, bool(acl)))
    else:
        _criterio(reg, "n2", "sin_peticion_territorio", "ok",
                  evidencia="sin peticion de territorio")
    falt = reg["cobertura"]["faltantes"]
    if not falt:
        _criterio(reg, "n3", "gold_literal", "ok",
                  evidencia="paginas %s entregadas con doc/version literales"
                            % reg["esperado"]["paginas"])
    else:
        _criterio(reg, "n3", "gold_literal", "fallo", "omision",
                  "faltan paginas gold %s (deben entregarse con doc/version exactos "
                  "y texto en contexto)" % falt)
    if reg["integridad_ok"]:
        _criterio(reg, "n4", "integridad_ok", "ok", evidencia="sin incidencias")
    else:
        _criterio(reg, "n4", "integridad_ok", "fallo", "error",
                  "incidencias: %s" % reg["integridad_incidencias"])


def _resumen(registros, datos, n_nombres):
    """Resumen con aciertos/fallos por grupo, criterios con fallo, estados observados,
    documentos ajenos e inconsistencias fixture/registros. exit 1 si falla cualquier
    caso o hay inconsistencia; 0 si todo ok."""
    aciertos = [r["id"] for r in registros if r["acierto"]]
    fallos = [{"id": r["id"], "grupo": r["grupo"], "estado": r["estado"],
               "criterios_fallo": [c["criterio"] for c in r["criterios"]
                                   if c["resultado"] == "fallo"]}
              for r in registros if not r["acierto"]]
    estados = {e: sum(1 for r in registros if r["estado"] == e)
               for e in {str(r["estado"]) for r in registros}}
    por_grupo = {}
    for g in ("territorial", "nacional"):
        regs_g = [r for r in registros if r["grupo"] == g]
        por_grupo[g] = {"total": len(regs_g),
                        "aciertos": len([r for r in regs_g if r["acierto"]]),
                        "fallos": [r["id"] for r in regs_g if not r["acierto"]]}
    criterios_fallo = {}
    for r in registros:
        for c in r["criterios"]:
            if c["resultado"] == "fallo":
                criterios_fallo[c["criterio"]] = criterios_fallo.get(c["criterio"], 0) + 1
    esperado = dict(datos.get("esperado") or {})
    nacion = [r for r in registros if r["grupo"] == "nacional"]
    pag_gold = sum(len(r["esperado"]["paginas"]) for r in nacion)
    inconsistencias = []
    for clave, observado in (("casos", len(registros)),
                             ("territoriales", por_grupo["territorial"]["total"]),
                             ("nacionales", por_grupo["nacional"]["total"]),
                             ("paginas_gold_nacionales", pag_gold)):
        declarado = esperado.get(clave)
        if declarado is not None and int(declarado) != observado:
            inconsistencias.append({"campo": "esperado.%s" % clave,
                                    "declarado": declarado, "observado": observado})
    ids_fixture = [str(c.get("id") or "") for c in (datos.get("casos") or [])]
    if ids_fixture != [r["id"] for r in registros]:
        inconsistencias.append({"campo": "casos_ids", "declarado": ids_fixture,
                                "observado": [r["id"] for r in registros]})
    resumen = {
        "casos_total": len(registros), "estados": estados,
        "por_grupo": por_grupo,
        "aciertos": aciertos, "total_aciertos": len(aciertos),
        "fallos": fallos, "total_fallos": len(fallos),
        "criterios_con_fallos": criterios_fallo,
        "paginas_gold_nacionales": pag_gold,
        "cobertura_contexto_nacionales": sum(len(r["cobertura"]["contexto"]) for r in nacion),
        "documentos_ajenos": sorted({d for r in registros for d in r["documentos_ajenos"]}),
        "territorios_mencionados_en_aclaraciones": sorted(
            {m for r in registros for m in r["territorios_mencionados"]}),
        "territorios_corpus": n_nombres,
        "esperado": esperado, "inconsistencias": inconsistencias,
        "fallos_conocidos_admitidos": False,
        "limites": [
            "tokens_contexto es recuento local (proxy de texto), no usage de API; sin "
            "desglose entrada/salida/cache (no disponible en este motor); sin API ni red",
            "la deteccion de territorio inventado es heuristica por subcadena normalizada "
            "sobre nombres jurisdiccion/municipio de doc.json distribute=true; falsos "
            "positivos posibles con topónimos cortos homófonos de palabras comunes",
            "c2 (rubrica v2) exige IGUALDAD de conjuntos: campos_requeridos == TODOS los "
            "campos requeridos del caso (key 'campos_requeridos_permitidos' conservada "
            "por compatibilidad); faltan = omision, sobran = error, duplicados = error; "
            "v1 (subconjunto no vacio) se conserva como baseline",
            "una corrida por caso, sin reintentos; excepciones de preparar quedan como "
            "estado error_preparar con criterios pendientes",
            "la cobertura por presencia de página no acredita calidad global ni fidelidad "
            "sustantiva; sin cálculo de ahorro (no hay pares comparables aquí)",
        ],
    }
    codigo = 1 if (fallos or inconsistencias) else 0
    return resumen, codigo


def _imprimir(registros, resumen, salida_ruta, codigo):
    w = sys.stdout.write
    w("== Consultas sin ubicacion: %d casos ==\n" % resumen["casos_total"])
    for r in registros:
        fallos_c = [c["criterio"] for c in r["criterios"] if c["resultado"] == "fallo"]
        w("%-5s %-11s estado=%-21s aclaracion=%-5s pags=%-3s gold=%-6s faltan=%-5s "
          "integridad=%-9s acierto=%s%s\n"
          % (r["id"], r["grupo"], str(r["estado"]),
             "si" if r["aclaracion_observada"] else "-",
             len(r["paginas"]), "%s" % r["esperado"]["paginas"],
             "%s" % (r["cobertura"]["faltantes"] or "-"),
             "ok" if r["integridad_ok"] else "INTEGRIDAD",
             "si" if r["acierto"] else "no",
             (" criterios_fallo=%s" % fallos_c) if fallos_c else ""))
    w("-- Resumen --\n")
    pg = resumen["por_grupo"]
    w("Aciertos: %d/%d (territorial %d/%d, nacional %d/%d) | fallos: %s\n"
      % (resumen["total_aciertos"], resumen["casos_total"],
         pg["territorial"]["aciertos"], pg["territorial"]["total"],
         pg["nacional"]["aciertos"], pg["nacional"]["total"],
         [f["id"] for f in resumen["fallos"]] or "(ninguno)"))
    w("Estados observados: %s\n" % json.dumps(resumen["estados"], ensure_ascii=False))
    w("Criterios con fallos: %s\n" % json.dumps(resumen["criterios_con_fallos"],
                                                ensure_ascii=False))
    w("Cobertura gold nacional: %d/%d paginas | documentos ajenos (trazados, no filtrados): %s\n"
      % (resumen["cobertura_contexto_nacionales"], resumen["paginas_gold_nacionales"],
         resumen["documentos_ajenos"] or "(ninguno)"))
    w("Territorios mencionados en aclaraciones: %s | nombres territoriales del corpus: %d\n"
      % (resumen["territorios_mencionados_en_aclaraciones"] or "(ninguno)",
         resumen["territorios_corpus"]))
    w("Inconsistencias: %s\n" % (resumen["inconsistencias"] or "(ninguna)"))
    w("Salida: %s | exit %d\n" % (salida_ruta, codigo))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Regresion de consultas sin ubicacion (aclaracion + nacionales).")
    ap.add_argument("--contenido", default=str(CONTENIDO_DEFECTO))
    ap.add_argument("--fixture", default=str(FIXTURE_DEFECTO))
    ap.add_argument("--salida", default=str(SALIDA_DEFECTO))
    args = ap.parse_args(argv)
    try:
        datos = _cargar_fixture(Path(args.fixture))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("fixture invalida (%s): %s\n" % (args.fixture, exc))
        return 2
    rubrica_version = int((datos.get("rubrica") or {}).get("version") or 0)
    contenido = Path(args.contenido).resolve()
    if not (contenido / "indice" / "apartados.jsonl").exists():
        sys.stderr.write("sin indice de corpus en %s\n" % contenido)
        return 2
    salida_ruta = Path(args.salida) if Path(args.salida).is_absolute() \
        else RAIZ / args.salida
    sys.path.insert(0, str(HTTP_LOCAL))
    import adaptador_contexto  # import REAL; sin parches, sin oráculos
    ad = adaptador_contexto.AdaptadorContexto(str(contenido))
    cfg = datos.get("config") or {}
    presupuesto = int(cfg.get("presupuesto_tokens") or PRESUPUESTO)
    max_resultados = int(cfg.get("max_resultados") or MAX_RESULTADOS)
    nombres = _nombres_territoriales_corpus(contenido)
    registros = []
    for caso in datos["casos"]:  # orden del fixture, sin reordenar
        try:
            # API REAL: preparar(consulta, None, None, 20000, 2); ningún campo
            # esperado llega al motor; una llamada por caso, sin reintentos.
            res = ad.preparar(caso["consulta"], None, None, presupuesto, max_resultados)
        except Exception as exc:  # estado no-ok; la corrida continúa
            res = {"estado": "error_preparar", "texto_contexto": "", "excedido": False,
                   "tokens_contexto": None, "paginas": [],
                   "recuperacion": {"resultados": []},
                   "error_preparar": "%s: %s" % (type(exc).__name__, exc)}
        registros.append(_registro(caso, res, contenido, nombres))
    resumen, codigo = _resumen(registros, datos, len(nombres))
    hashes = {
        "runner": EL._sha_fichero(Path(__file__)),
        "motor_acceso": EL._sha_fichero(HTTP_LOCAL / "acceso.py"),
        "motor_adaptador_contexto": EL._sha_fichero(HTTP_LOCAL / "adaptador_contexto.py"),
        "helpers_integridad": EL._sha_fichero(CARPETA / "ejecutar_libres.py"),
        "fixture": {"archivo": Path(args.fixture).name,
                    "sha256": EL._sha_fichero(Path(args.fixture))},
    }
    for nombre, ruta in (("manifiesto_publico", contenido / "manifest_publico.json"),
                         ("indice_apartados", contenido / "indice" / "apartados.jsonl")):
        try:
            hashes[nombre] = {"archivo": ruta.name, "sha256": EL._sha_fichero(ruta)}
        except OSError:
            hashes[nombre] = {"archivo": ruta.name, "sha256": None, "nota": "ausente"}
    actual = {
        "esquema": ESQUEMA,
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "python": sys.version, "plataforma": sys.platform,
            "evaluacion": {"agente": "evaluacion-normativa", "modelo": "glm5.3-flash",
                           "proveedor": "nan", "encargo": "consultas-sin-ubicacion"},
            "orden": "orden del fixture, sin reordenar",
            "reintentos": 0,
            "hashes": hashes,
            "busqueda": {"presupuesto_tokens": presupuesto,
                         "max_resultados": max_resultados,
                         "modo_tokens": ad.modo_contadores, "encoders": sorted(ad.encs),
                         "filtro_documento": None, "sin_api_red": True,
                         "motor_recibio_gold": False},
        },
        "config": {"contenido": str(contenido), "salida": str(salida_ruta),
                   "rubrica_version": rubrica_version,
                   "criterio": "rubrica v%d del fixture; identico antes/despues DENTRO de "
                               "la misma version (c2 igualdad de campos desde v2; v1 "
                               "subconjunto se conserva como baseline); versiones "
                               "distintas NO se declaran criterio congelado identico; sin "
                               "adjudicaciones ni modos alternativos" % rubrica_version},
        "resumen": resumen, "casos": registros,
    }
    salida_ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(salida_ruta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(actual, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    _imprimir(registros, resumen, salida_ruta, codigo)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
