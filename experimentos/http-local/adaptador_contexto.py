#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adaptador_contexto.py — adaptador de contexto recuperable para el piloto Normativa Abierta.

Biblioteca + CLI sobre acceso.py (reutilizado, no copiado): recupera solo del corpus
distribuible `contenido/` con buscar_bm25 (IDF global sobre el índice público, sin
oráculos ni páginas fijas) y abre páginas literales completas con construir_lectura,
siguiendo el mismo principio de plan_lecturas (http_consulta.py). No abre sockets,
no escribe salvo --salida, no conoce rúbricas, respuestas esperadas, PDFs del proyecto
ni credenciales. Compatible Python >= 3.12; solo biblioteca estándar y tiktoken
opcional (vía acceso.py).

Uso:
    from adaptador_contexto import AdaptadorContexto
    ad = AdaptadorContexto()            # contenido = raíz_repo/contenido
    res = ad.preparar(consulta, documento, version=None,
                      presupuesto_tokens=12000, max_resultados=5)
    # res es JSON-serializable

    python adaptador_contexto.py --consulta "..." [--documento ID] [--version AAAA-MM-DD]
        [--contenido RUTA] [--presupuesto 12000] [--max 5] [--salida ruta.json]

Estados: ok | sin_resultados | version_no_disponible | documento_no_disponible |
presupuesto_excedido. Los filtros documento/versión se validan ANTES de buscar; la
versión solicitada se contrasta por igualdad exacta con la del doc.json y jamás se
sustituye por otra. El presupuesto se aplica al texto_contexto FINAL serializado
(incluidos metadatos): si excede, el texto se conserva íntegro con excedido=true —
jamás se recorta ni se presenta como completo. Lo que el buscador omitió (presupuesto
o error) queda listado y visible en texto_contexto y recuperacion.

Limitaciones declaradas (reales, no silenciadas):
- tokens_contexto NO es usage real de un modelo: es recuento local con tiktoken
  cl100k_base, o aproximación len/4 si tiktoken no está disponible. No hay CLI para
  elegir o200k_base (el motor contabiliza en cl100k_base; se mantiene por coherencia).
- El presupuesto interno del buscador (vista) y el del adaptador (texto final) difieren:
  puede haber omitidos del motor aunque el texto final quepa, y viceversa; ambos quedan
  reflejados.
- Si el buscador no puede abrir una página, se conserva el texto que él mismo devolvió
  en su plan y se advierte; si nada pudo abrirse, se entrega texto_integro del apartado
  con advertencia. Nada se pierde en silencio.
- versiones_disponibles refleja el campo `version` del doc.json del corpus distribuible
  (una por documento). Sin --documento, la búsqueda es global con el filtro de capas por
  defecto del motor (oficial+asociada). El adaptador no afirma vigencia ni régimen
  transitorio: conserva la edición del corpus.
- El índice se filtra a doc.json con distribute===True antes del IDF global; con
  --contenido personalizado, los documentos no distribuibles quedan fuera del corpus
  y no se abren jamás (si se piden, estado documento_no_disponible).
- Ámbitos/definiciones/excepciones/tablas/notas cuyo literal ya fue entregado (bloque
  idéntico o contenido en páginas completas entregadas, por substring normalizado) se
  sustituyen por un aviso de no duplicación conservando el metadato; sin resumen ni
  cambio de texto.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

CARPETA = Path(__file__).resolve().parent
if str(CARPETA) not in sys.path:
    sys.path.insert(0, str(CARPETA))
try:
    import acceso as A
except Exception as e:  # pragma: no cover
    raise SystemExit("Falta acceso.py junto a adaptador_contexto.py: %s" % e)

CONTENIDO_DEFECTO = Path(__file__).resolve().parents[2] / "contenido"
ESTADOS = ("ok", "sin_resultados", "version_no_disponible",
           "documento_no_disponible", "presupuesto_excedido")
_RANGO_MOTIVO = {"primaria": 0, "fuente_apartado": 1, "continuada": 2, "auxiliar": 3}

__all__ = ["AdaptadorContexto", "CONTENIDO_DEFECTO", "ESTADOS"]


class AdaptadorContexto:
    """Carga índice/docs/contadores una vez y prepara contexto JSON-serializable."""

    def __init__(self, contenido: Path | str | None = None):
        cont = Path(contenido).resolve() if contenido else CONTENIDO_DEFECTO
        self.contenido = cont
        A.cont_global = cont  # requerido por ficha_doc() dentro de construir_lectura
        self.filas = A.cargar_indice(cont)
        docs_brutos = A.cargar_docs(cont, self.filas)
        # Solo corpus distribuible: doc.json con distribute===True, filtrado ANTES del
        # IDF global de buscar_bm25. Sin lecturas nuevas: usa los doc.json ya cargados.
        permitidos = {d for d, (dj, _base) in docs_brutos.items()
                      if (dj or {}).get("distribute") is True}
        self.filas = [f for f in self.filas if f["documento"] in permitidos]
        self.docs = {d: v for d, v in docs_brutos.items() if d in permitidos}
        self.encs, self.modo_contadores = A.crear_contadores()

    # ------------------------------------------------------------------ salida

    def _salida(self, estado, consulta, documento, version, texto_contexto,
                paginas, recuperacion, limite, t0, **extra):
        if "cl100k_base" in self.encs:
            tokens = A.contar(texto_contexto, self.encs, "cl100k_base")
            modo = "tiktoken:cl100k_base"
        else:
            tokens = max(1, math.ceil(len(texto_contexto) / 4.0))
            modo = "aproximacion_caracteres_4"
        excedido = bool(limite and tokens > limite)
        if excedido and estado == "ok":
            estado = "presupuesto_excedido"
        res = {
            "estado": estado,
            "consulta": consulta,
            "documento": documento,
            "version": version,
            "texto_contexto": texto_contexto,
            "paginas": paginas,
            "recuperacion": recuperacion,
            "tokens_contexto": tokens,
            "modo_tokens": modo,
            "limite_tokens": limite,
            "excedido": excedido,
            "tiempo_ms": round((time.perf_counter() - t0) * 1000.0, 1),
            "contenido": str(self.contenido),
        }
        res.update(extra)
        return res

    # ------------------------------------------------- validación de filtros

    def _cabecera(self, consulta, doc_id, objetivo, extra_lineas=()):
        partes = ["== Contexto recuperado (Normativa Abierta · corpus distribuible) ==",
                  "Consulta literal: %s" % consulta]
        if doc_id:
            partes.append("Filtro validado antes de buscar: documento=%s · version=%s" % (
                doc_id, objetivo if objetivo else "sin filtro"))
        partes.extend(extra_lineas)
        return partes

    def preparar(self, consulta: str, documento: str | None = None,
                 version: str | None = None, presupuesto_tokens: int = 12000,
                 max_resultados: int = 5) -> dict:
        t0 = time.perf_counter()
        if not isinstance(consulta, str) or not consulta.strip():
            raise ValueError("consulta vacía: indique texto natural de búsqueda")
        if documento is not None and not str(documento).strip():
            documento = None
        if version is not None and not str(version).strip():
            version = None
        if version is not None and documento is None:
            raise ValueError("--version requiere --documento: no hay edición que validar")
        try:
            max_resultados = int(max_resultados)
        except (TypeError, ValueError):
            raise ValueError("max_resultados inválido: se requiere entero >= 1")
        if max_resultados < 1:
            raise ValueError("max_resultados inválido: se requiere entero >= 1")
        try:
            presupuesto_tokens = int(presupuesto_tokens)
        except (TypeError, ValueError):
            raise ValueError("presupuesto_tokens inválido: se requiere entero >= 1")
        if presupuesto_tokens < 1:
            raise ValueError("presupuesto_tokens inválido: se requiere entero >= 1")

        doc_id = objetivo = None
        versiones_disp: list = []
        if documento is not None:
            doc_id = str(documento)
            if doc_id not in self.docs:
                docs_disp = sorted(self.docs)
                partes = self._cabecera(consulta, doc_id, None, [
                    "", "ESTADO documento_no_disponible: el documento '%s' no existe en el "
                        "corpus distribuible. No se sustituye por otro." % doc_id,
                    "Documentos disponibles: %s" % ", ".join(docs_disp)])
                texto = "\n".join(partes) + "\n"
                return self._salida(
                    "documento_no_disponible", consulta, doc_id,
                    str(version) if version is not None else None, texto, [],
                    {"advertencias": ["documento no disponible: %s" % doc_id],
                     "omitidos": [], "resultados": [], "relacionados_no_incluidos": []},
                    presupuesto_tokens, t0, documentos_disponibles=docs_disp)
            docj = self.docs[doc_id][0] or {}
            v_doc = str(docj.get("version") or "")
            versiones_disp = [v_doc] if v_doc else []
            if version is not None:
                if str(version) not in versiones_disp:
                    partes = self._cabecera(consulta, doc_id, None, [
                        "", "ESTADO version_no_disponible: el documento '%s' no tiene la "
                            "edición '%s'. No se sustituye por otra versión." % (
                                doc_id, version),
                        "Versiones disponibles: %s" % (", ".join(versiones_disp) or "(ninguna)")])
                    texto = "\n".join(partes) + "\n"
                    return self._salida(
                        "version_no_disponible", consulta, doc_id, str(version), texto,
                        [], {"advertencias": ["versión no disponible: %s" % version],
                             "omitidos": [], "resultados": [],
                             "relacionados_no_incluidos": []},
                        presupuesto_tokens, t0, versiones_disponibles=versiones_disp)
                objetivo = str(version)

        # ------------------------------------------------------------- búsqueda
        terminos = [t for t in re.split(r"[\s,;]+", consulta) if len(t) > 1]
        op = SimpleNamespace(max=max_resultados, presupuesto=presupuesto_tokens,
                             expandir=1, documento=doc_id, capa=None, materia=None)
        advertencias: list = []
        omitidos: list = []
        try:
            busq = A.buscar_bm25(self.contenido, self.filas, self.docs, consulta,
                                 terminos, op, self.encs)
        except (SystemExit, Exception) as e:
            busq = {"resultados": [], "omitidos": [], "advertencias": [],
                    "terminos": terminos, "ambito_capa": "oficial+asociada"}
            advertencias.append("fallo del buscador (%s): %s" % (type(e).__name__, e))
        resultados = list(busq.get("resultados") or [])[:max_resultados]
        if objetivo:
            conservados = []
            for r in resultados:
                if str(r.get("version") or "") != objetivo:
                    advertencias.append(
                        "resultado descartado por versión distinta a la solicitada (%s): %s"
                        % (objetivo, r.get("documento")))
                    omitidos.append({"documento": r.get("documento"),
                                     "apartado_id": r.get("apartado_id"),
                                     "motivo": "version_distinta"})
                else:
                    conservados.append(r)
            resultados = conservados
        advertencias.extend(busq.get("advertencias") or [])
        omitidos.extend(busq.get("omitidos") or [])

        aviso_tarde: list = []
        relacionados_no: list = []
        resumen: list = []
        paginas_out: list = []

        if not resultados:
            partes = self._cabecera(consulta, doc_id, objetivo, [
                "", "-- Advertencias --"])
            partes.extend("- %s" % a for a in advertencias)
            if omitidos:
                partes.append("")
                partes.append("-- Omitidos por el buscador --")
                partes.extend("- %s" % json.dumps(o, ensure_ascii=False, sort_keys=True)
                              for o in omitidos)
            partes.append("")
            partes.append("ESTADO sin_resultados: el motor BM25 no devolvió resultados "
                          "para esta consulta en el corpus distribuible; nada se "
                          "sustituye ni se amplía por fuera del motor.")
            texto = "\n".join(partes) + "\n"
            return self._salida(
                "sin_resultados", consulta, doc_id,
                objetivo or (str(version) if version is not None else None), texto, [],
                {"busqueda": {"metodo": "bm25", "terminos": busq.get("terminos") or terminos,
                              "ambito_capa": busq.get("ambito_capa")},
                 "resultados": [], "advertencias": advertencias, "omitidos": omitidos,
                 "relacionados_no_incluidos": []},
                presupuesto_tokens, t0)

        # ------------------------------------------------ ensamblaje del contexto
        entregadas: dict = {}   # clave de página -> Resultado que la entregó
        meta_doc: dict = {}
        paginas_norm = ""       # texto normalizado de evidencia entregada (dedupe literal)
        bloques_vistos = set()  # claves de bloques de contexto ya impresos
        partes = self._cabecera(consulta, doc_id, objetivo, ["", "-- Advertencias --"])
        partes.extend("- %s" % a for a in advertencias)
        if omitidos:
            partes.append("")
            partes.append("-- Omitidos por el buscador (íntegros en disco, no recortados) --")
            partes.extend("- %s" % json.dumps(o, ensure_ascii=False, sort_keys=True)
                          for o in omitidos)
        partes.append("")

        def meta(d):
            if d not in meta_doc:
                meta_doc[d] = (self.docs.get(d) or (None, None))[0] or {}
            return meta_doc[d]

        for idx, r in enumerate(resultados, 1):
            d = r["documento"]
            dj = meta(d)
            ver = str(dj.get("version") or "")
            sha = dj.get("sha256")
            url = dj.get("url")
            ctxr = r.get("contexto") or {}
            partes.append("== Resultado %d: %s ==" % (
                idx, r.get("ruta_oficial") or r.get("id_tecnico") or d))
            partes.append("Documento: %s · código %s · versión %s · capa %s · sha256 %s" % (
                d, r.get("codigo") or dj.get("code") or "-", ver or "-",
                r.get("capa") or "-", sha or "-"))
            partes.append("Título: %s" % r.get("titulo"))
            partes.append("Ruta oficial: %s · id técnico: %s · impresas: %s" % (
                r.get("ruta_oficial") or "-", r.get("id_tecnico"),
                r.get("etiquetas_impresas") or "-"))
            partes.append("Fuente oficial: %s" % (url or "(sin url en doc.json)"))
            partes.append("Archivo del apartado: %s · páginas físicas: %s" % (
                r.get("archivo"), r.get("paginas") or []))
            if r.get("tablas"):
                partes.append("Tablas en estas páginas (rutas): %s"
                              % ", ".join(str(t) for t in r["tablas"]))
            amb = ctxr.get("ambito")
            if amb and amb.get("texto"):
                ruta_amb = amb.get("ruta_oficial") or amb.get("id_tecnico") or "doc.json"
                t_amb = amb["texto"]
                if A.norm(t_amb) in paginas_norm:
                    partes.append("Ámbito literal (%s): [literal ya incluido arriba; "
                                  "sin duplicación]" % ruta_amb)
                else:
                    partes.append("Ámbito literal (%s): %s" % (ruta_amb, t_amb))
            for tipo, titulo in (("definiciones", "Definiciones relacionadas"),
                                 ("excepciones", "Excepciones relacionadas")):
                for x in ctxr.get(tipo) or []:
                    t_b = x.get("texto") or ""
                    clave_b = (tipo, x.get("archivo") or x.get("id_tecnico"))
                    if t_b and (clave_b in bloques_vistos or
                                A.norm(t_b) in paginas_norm):
                        partes.append("%s — %s (%s): [literal ya incluido arriba; "
                                      "sin duplicación]" % (
                                          titulo,
                                          x.get("ruta_oficial") or x.get("id_tecnico"),
                                          x.get("archivo")))
                        continue
                    partes.append("%s — %s (%s): %s" % (
                        titulo, x.get("ruta_oficial") or x.get("id_tecnico"),
                        x.get("archivo"), t_b))
                    if t_b:
                        bloques_vistos.add(clave_b)
            if r.get("referencias"):
                partes.append("Referencias detectadas: %s"
                              % ", ".join(str(x) for x in r["referencias"]))
            for a in ctxr.get("ancestros") or []:
                partes.append("Ancestro en la ruta (texto íntegro en disco): %s · %s [%s]" % (
                    a.get("ruta_oficial") or a.get("id_tecnico"), a.get("titulo"),
                    a.get("archivo")))
            for x in ctxr.get("relacionados_enlazados") or []:
                relacionados_no.append({"documento": d,
                                        "ruta_oficial": x.get("ruta_oficial"),
                                        "titulo": x.get("titulo"),
                                        "archivo": x.get("archivo")})

            # plan de lecturas: mismo principio que plan_lecturas (http_consulta.py)
            if r.get("pagina"):
                opt = SimpleNamespace(documento=d, apartado=None,
                                      pagina=int(r["pagina"]), expandir=0)
            else:
                opt = SimpleNamespace(documento=d, apartado=r.get("apartado_id"),
                                      pagina=None, expandir=1)
            lec = None
            try:
                lec = A.construir_lectura(self.contenido, self.filas, self.docs,
                                          opt, self.encs)
            except (SystemExit, Exception) as e:
                aviso_tarde.append("lectura_no_disponible %s/%s: %s" % (
                    d, r.get("apartado_id") or r.get("pagina"), e))
            plan: dict = {}

            def plan_add(p, motivo, texto=None, tablas=None, notas=None):
                p = int(p)
                ent = plan.get(p)
                if ent is None:
                    plan[p] = {"motivo": motivo, "texto": texto,
                               "tablas": list(tablas or []), "notas": list(notas or [])}
                    return
                if _RANGO_MOTIVO.get(motivo, 9) < _RANGO_MOTIVO.get(ent["motivo"], 9):
                    ent["motivo"] = motivo
                if texto and not ent["texto"]:
                    ent["texto"] = texto
                vistos_t = {t.get("archivo") for t in ent["tablas"]}
                ent["tablas"].extend(t for t in (tablas or [])
                                     if t.get("archivo") not in vistos_t)
                nums = {n.get("numero") for n in ent["notas"]}
                ent["notas"].extend(n for n in (notas or [])
                                    if n.get("numero") not in nums)

            for p in r.get("paginas") or []:
                plan_add(p, "primaria")
            if lec:
                c = lec.get("contexto") or {}
                for pf in c.get("paginas_fuente") or []:
                    plan_add(pf["pagina"], "fuente_apartado", pf.get("texto"),
                             pf.get("tablas"))
                for pc in c.get("paginas_continuadas") or []:
                    plan_add(pc["pagina"], "continuada", pc.get("texto"))
                pg = lec.get("pagina") or {}
                if pg.get("pagina"):
                    plan_add(pg["pagina"], "primaria", pg.get("texto"))
            for a in ctxr.get("auxiliares") or []:
                notas = list(a.get("notas") or [])
                if a.get("nota") and all(n.get("numero") != a["nota"].get("numero")
                                         for n in notas):
                    notas.insert(0, a["nota"])
                plan_add(a["pagina"], "auxiliar", a.get("texto"), notas=notas)

            # apertura literal de páginas completas con construir_lectura
            paginas_abiertas = []
            paginas_reutilizadas = []
            for p in sorted(plan):
                info = plan[p]
                clave = (d, ver, str(sha or ""), p)
                if clave in entregadas:
                    paginas_reutilizadas.append(p)
                    partes.append("- Página %d ya entregada en el Resultado %d "
                                  "(misma edición): no se repite el texto." % (
                                      p, entregadas[clave]))
                    continue
                texto_pg = etiqueta = archivo_pg = None
                try:
                    lec_p = A.construir_lectura(
                        self.contenido, self.filas, self.docs,
                        SimpleNamespace(documento=d, apartado=None, pagina=p,
                                        expandir=0), self.encs)
                    pg = lec_p.get("pagina") or {}
                    texto_pg = pg.get("texto")
                    etiqueta = pg.get("etiqueta_impresa")
                    archivo_pg = pg.get("archivo")
                except (SystemExit, Exception) as e:
                    aviso_tarde.append("página_no_abierta %s p.%d: %s" % (d, p, e))
                if not texto_pg and info.get("texto"):
                    texto_pg = info["texto"]
                    aviso_tarde.append("página %d de %s entregada con el texto del plan "
                                       "del motor (construir_lectura no pudo abrirla)" % (p, d))
                if not texto_pg:
                    omitidos.append({"documento": d, "pagina": p,
                                     "motivo": "pagina_no_abierta"})
                    partes.append("- Página %d NO disponible: omitida, no recortada." % p)
                    continue
                entregadas[clave] = idx
                paginas_out.append({
                    "doc": d, "version": ver or None, "sha256": sha,
                    "pagina": p, "url_fuente": url,
                    "texto_sha256": hashlib.sha256(
                        texto_pg.encode("utf-8")).hexdigest(),
                    "etiqueta_impresa": etiqueta, "archivo": archivo_pg,
                    "motivo": info["motivo"],
                })
                partes.append("--- Página %d (motivo: %s%s) [%s] ---" % (
                    p, info["motivo"],
                    (" · impresa: %s" % etiqueta) if etiqueta else "",
                    archivo_pg or "(archivo no determinado)"))
                partes.append(texto_pg)
                paginas_norm += A.norm(texto_pg) + "\n"
                for t in info.get("tablas") or []:
                    partes.append("[Tabla %s — requiere contraste visual con el PDF "
                                  "oficial; el texto extraído no acredita formato]" % (
                                      t.get("archivo")))
                    t_txt = t.get("texto") or ""
                    clave_t = ("tabla", t.get("archivo"))
                    if t_txt and (clave_t in bloques_vistos or
                                  A.norm(t_txt) in paginas_norm):
                        partes.append("[Texto de tabla ya incluido arriba; sin duplicación]")
                    elif t_txt:
                        partes.append(t_txt)
                        bloques_vistos.add(clave_t)
                for n in info.get("notas") or []:
                    n_txt = n.get("texto") or ""
                    clave_n = ("nota", n.get("archivo"), n.get("numero"))
                    if n_txt and (clave_n in bloques_vistos or
                                  A.norm(n_txt) in paginas_norm):
                        partes.append("[Nota (%s) %s]: [literal ya incluido arriba; "
                                      "sin duplicación]" % (
                                          n.get("numero", "?"), n.get("archivo") or ""))
                        continue
                    partes.append("[Nota (%s) %s]: %s" % (
                        n.get("numero", "?"), n.get("archivo") or "", n_txt))
                    if n_txt:
                        bloques_vistos.add(clave_n)
                paginas_abiertas.append(p)
            if not paginas_abiertas and not paginas_reutilizadas and r.get("texto_integro"):
                partes.append("[Ninguna página pudo abrirse para este resultado; "
                              "texto íntegro del apartado, sin recortar:]")
                partes.append(r["texto_integro"])
                paginas_norm += A.norm(r["texto_integro"]) + "\n"
                aviso_tarde.append("resultado %s sin páginas abiertas ni reutilizadas: "
                                   "se incluyó texto_integro del apartado"
                                   % r.get("id_tecnico"))
            resumen.append({
                "documento": d, "version": ver or None,
                "id_tecnico": r.get("id_tecnico"), "apartado_id": r.get("apartado_id"),
                "ruta_oficial": r.get("ruta_oficial"), "titulo": r.get("titulo"),
                "puntuacion_bm25": r.get("puntuacion_bm25"),
                "paginas": r.get("paginas") or [],
                "etiquetas_impresas": r.get("etiquetas_impresas"),
                "hallada": r.get("hallada"),
                "cita": (r.get("cita") or {}).get("texto"),
                "paginas_entregadas": paginas_abiertas,
                "paginas_reutilizadas": paginas_reutilizadas,
            })
            partes.append("")

        if relacionados_no:
            partes.append("-- Relacionados enlazados NO incluidos por el motor "
                          "(solo rutas, texto íntegro en disco) --")
            for x in relacionados_no:
                partes.append("- %s · %s [%s]" % (
                    x.get("ruta_oficial") or "-", x.get("titulo") or "-",
                    x.get("archivo") or "-"))
            partes.append("")
        if aviso_tarde:
            partes.append("-- Advertencias de ensamblaje --")
            partes.extend("- %s" % a for a in aviso_tarde)
            partes.append("")
        texto_final = "\n".join(partes).rstrip() + "\n"

        rec = {"busqueda": {"metodo": "bm25",
                            "terminos": busq.get("terminos") or terminos,
                            "ambito_capa": busq.get("ambito_capa")},
               "resultados": resumen, "advertencias": advertencias + aviso_tarde,
               "omitidos": omitidos, "relacionados_no_incluidos": relacionados_no}
        return self._salida("ok", consulta, doc_id,
                            objetivo or (str(version) if version is not None else None),
                            texto_final, paginas_out, rec, presupuesto_tokens, t0,
                            versiones_disponibles=versiones_disp)


# ----------------------------------------------------------------------------- CLI


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="Adaptador de contexto recuperable (corpus distribuible, solo lectura).")
    ap.add_argument("--consulta", required=True,
                    help="consulta natural; no se transforma en IDs de apartados")
    ap.add_argument("--documento", default=None, help="ID de documento (filtro exacto)")
    ap.add_argument("--version", default=None, help="edición exacta AAAA-MM-DD (con --documento)")
    ap.add_argument("--contenido", default=None, help="ruta del corpus (por defecto repo/contenido)")
    ap.add_argument("--presupuesto", type=int, default=12000,
                    help="tokens máximos del texto_contexto FINAL (>= 1)")
    ap.add_argument("--max", type=int, default=5, help="resultados máximos (>= 1)")
    ap.add_argument("--salida", default=None, help="ruta de escritura opcional del JSON")
    args = ap.parse_args()
    try:
        ad = AdaptadorContexto(args.contenido)
        res = ad.preparar(args.consulta, args.documento, args.version,
                          args.presupuesto, args.max)
    except ValueError as e:
        sys.stderr.write(json.dumps({"error": "parametro_invalido", "detalle": str(e)},
                                    ensure_ascii=False) + "\n")
        return 2
    texto = json.dumps(res, ensure_ascii=False, indent=1)
    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
    else:
        sys.stdout.write(texto + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
