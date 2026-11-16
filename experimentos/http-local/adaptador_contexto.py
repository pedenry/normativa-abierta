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
presupuesto_excedido | aclaracion_necesaria. Los filtros documento/versión se validan ANTES de buscar; la
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
- Los doc.json pueden declarar `advertencias` (lista de cadenas) y `nota_capa`
  (cadena): para cada documento efectivamente seleccionado por BM25 se exponen una
  sola vez, identificadas con su ID, en recuperacion.advertencias y en la sección
  -- Advertencias -- de texto_contexto, antes del recuento del presupuesto final.
  Son contenido, no instrucciones: ante tipos inesperados se omiten y jamás se
  reconstruyen como texto.
- Sin --documento, la consulta puede resolver ámbito territorial SOLO con los
  metadatos ya cargados (jurisdiccion/municipio de los doc.json; tildes/case y
  variantes genéricas sin prefijo administrativo). Con ámbito reconocido, el
  conjunto de búsqueda = fuentes nacionales complementarias (sin metadato
  territorial) + autonómicas de la jurisdicción pedida + municipales solo del
  municipio pedido; nunca otra jurisdicción o ciudad, y la ubicación sola no
  decide el nivel normativo. La CCAA padre de un municipio se deriva del
  metadato de la propia fuente municipal. Intención municipal explícita
  («ayuntamiento de X», «ordenanza municipal de X») sin fuentes incorporadas:
  sin_resultados explicado, sin sustituir por otra ciudad ni por la CCAA de
  nombre similar; «licencia/trámite» a secas no es intención municipal. Varios
  territorios se unen explícitamente con traza; el filtro documento/versión
  explícito tiene precedencia y no se infiere nada. Mención territorial no
  resoluble: búsqueda global con aviso, sin afirmar vigencia. Sin mención:
  global intacta y sin claves nuevas. La vista de búsqueda puede derivarse del
  literal (trazada en resolucion_ambito y cabecera); la consulta original se
  conserva. Detectar municipios sin incorporar exige mayúscula tras «en/para».
- Sin --documento y sin mención territorial resuelta, si la consulta plantea
  materia que se decide con normas autonómicas o municipales (régimen y
  clasificación del suelo, edificabilidad, aprovechamientos, cesiones;
  licencias, trámites, declaraciones responsables, plazos, documentación,
  actividad, altura, linderos, parcelas, segregaciones o su aplicación a una
  reforma o proyecto dentro del dominio urbano-constructivo), se devuelve
  aclaracion_necesaria ANTES de buscar: campos_requeridos y pregunta en
  español, sin resultados ni fuente, edición o jurisdicción inferidas.
  Detección por intención con vocabulario operativo: «suelo» o «registro» a
  secas no bastan. El marco estatal/nacional pedido expresamente no pide
  lugar y limita los candidatos a fuentes nacionales por la puerta
  documentos_permitidos (sin tocar el IDF global ni el ranking); un «marco
  normativo» genérico sin escala no supone estatal y sí puede aclarar. Si
  junto a la escala estatal se pide también autonómica o municipal, la
  consulta es mixta: la exclusividad nacional no procede y vuelve al cauce
  general (aclaración o búsqueda global). Cabeza municipal sin operativa
  local («cesión … al ayuntamiento») no exige municipio si la materia ya es
  de régimen autonómico.
- Sin --documento y sin ámbito resuelto, una consulta de relación/conexión
  («qué conecta una entidad … de una X») puede derivar una vista de búsqueda
  que enfoca la entidad pedida y omite la cola final subordinada con artículo
  indeterminado (contexto, no objeto de la relación); la consulta original se
  conserva y la vista queda trazada en advertencias y `vista_busqueda`.
- Con marco estatal exclusivo (sin documento ni ámbito resuelto), una
  consulta conceptual de definición («cuáles son [entidad] que
  distingue/define/establece/regula …») puede acotar los candidatos
  nacionales a las fuentes cuyo texto en disco contiene literalmente la
  frase normalizada de la entidad, con vista enfocada para BM25 (mismas
  filas e IDF global) y traza en advertencias y `vista_busqueda`; sin
  coincidencia literal se conserva el conjunto nacional completo y la
  consulta original, sin sustitución autonómica.
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
           "documento_no_disponible", "presupuesto_excedido",
           "aclaracion_necesaria")
_RANGO_MOTIVO = {"primaria": 0, "fuente_apartado": 1, "continuada": 2, "auxiliar": 3}

__all__ = ["AdaptadorContexto", "CONTENIDO_DEFECTO", "ESTADOS"]


# --- ámbito territorial: resolución SOLO desde jurisdiccion/municipio de los
# doc.json ya cargados; vocabulario administrativo genérico, sin IDs ni casos.
_CABECERAS_TERRITORIO = (
    "comunidad autonoma de", "comunidad foral de", "comunidad de",
    "comunitat de", "region de", "principado de", "provincia de",
    "ciudad de", "diputacion de", "comunidad", "comunitat",
    "islas de", "illes de", "islas", "illes", "isla de", "isla")
_ARTICULOS = ("de", "del", "la", "el", "los", "las")
# «en/para + Nombre propio»: SOLO para detectar menciones no resolubles con el
# corpus; la resolución efectiva exige correspondencia en metadatos.
_PATRON_EN_NOMBRE = re.compile(
    r"\b(?i:en|para)\s+(?:el\s+|la\s+|los\s+|las\s+)?"
    r"([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{3,}(?:\s+(?:de\s+|del\s+|la\s+|el\s+)*"
    r"[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{3,})*)")
# Intención municipal explícita: cabeza municipal + «de» antes del nombre
# («ayuntamiento de X», «ordenanza municipal de X», «ciudad de X»), o léxico
# municipal en la consulta junto a mención libre. «Licencia» o «trámite» a
# secas NO es intención municipal: la ubicación sola no decide el nivel.
_CABEZAS_MUNICIPALES = ("ayuntamiento", "ajuntament", "municipio", "ciudad",
                        "ordenanza", "ordenanzas", "municipal", "municipales")
_LEXICO_MUNICIPAL = re.compile(
    r"\b(?:ayuntamiento|ajuntament|ordenanzas?|municipales?|municipios?)\b")


def _palabras_ambito(t):
    """Palabras normalizadas (tildes/case/puntuación fuera) de un texto."""
    return re.sub(r"[^0-9a-z ]+", " ", A.norm(t)).split()


def _variantes_alias(canon):
    """Claves de alias: forma completa y variantes sin prefijo administrativo
    genérico ni artículo inicial («Comunidad de Madrid» -> «...madrid», «madrid»)."""
    claves, base = [], _palabras_ambito(canon)
    if base:
        claves.append(" ".join(base))
        for pref in _CABECERAS_TERRITORIO:
            pp = pref.split()
            if len(base) > len(pp) and base[:len(pp)] == pp:
                resto = base[len(pp):]
                while resto and resto[0] in _ARTICULOS:
                    resto = resto[1:]
                if resto:
                    claves.append(" ".join(resto))
        if len(base) > 1 and base[0] in _ARTICULOS:
            claves.append(" ".join(base[1:]))
    out, vistos = [], set()
    for c in claves:
        if len(c) >= 4 and c not in vistos:
            vistos.add(c)
            out.append(c)
    return out


def _construir_alias_ambito(docs):
    """{clave normalizada: {canonico: {"niveles": set, "documentos": set}}} desde
    jurisdiccion/municipio reales de los doc.json; sin metadato, sin clave."""
    tabla = {}
    for doc, (dj, _base) in docs.items():
        dj = dj or {}
        for campo, nivel in (("jurisdiccion", "jurisdiccion"),
                             ("municipio", "municipio")):
            canon = str(dj.get(campo) or "").strip()
            if not canon:
                continue
            for clave in _variantes_alias(canon):
                ent = tabla.setdefault(clave, {})
                e2 = ent.setdefault(canon, {"niveles": set(), "documentos": set()})
                e2["niveles"].add(nivel)
                e2["documentos"].add(doc)
    return tabla


def _posicion_tupla(palabras, tupla):
    n = len(tupla)
    for i in range(len(palabras) - n + 1):
        if tuple(palabras[i:i + n]) == tupla:
            return i
    return None


def _intencion_municipal_adyacente(palabras, i):
    """Intención municipal explícita: cabeza municipal + «de/del» inmediatamente
    antes del nombre mencionado («ayuntamiento de X», «ordenanza municipal de X»)."""
    return i >= 2 and palabras[i - 1] in ("de", "del") and \
        palabras[i - 2] in _CABEZAS_MUNICIPALES


def _fragmento_literal(consulta, palabras, i, j):
    """Fragmento original de la consulta para el tramo [i, j) de palabras."""
    tokens = str(consulta).split()
    return " ".join(tokens[i:j] if len(tokens) == len(palabras) else palabras[i:j])


def _consulta_derivada(consulta, palabras, elegidos):
    """Vista de búsqueda sin los tramos territoriales auto resueltos (y su
    «en/para» adyacente), para no premiar portadas por identidad. Literal
    trazado; vacía o incoherente -> None (se conserva la consulta original)."""
    if not elegidos:
        return None
    borrar = set()
    for a, b, _clave in elegidos:
        ini = a
        if ini > 1 and palabras[ini - 1] in _ARTICULOS and \
                palabras[ini - 2] in ("en", "para"):
            ini -= 2
        elif ini > 0 and palabras[ini - 1] in ("en", "para"):
            ini -= 1
        borrar.update(range(ini, b))
    tokens = str(consulta).split()
    if len(tokens) != len(palabras):
        return None
    resto = re.sub(r"\s+", " ", " ".join(
        t for i, t in enumerate(tokens) if i not in borrar)).strip()
    return resto or None


# --- aclaración territorial: sin documento explícito ni mención territorial
# resuelta, si la consulta plantea materia que se decide con normas
# autonómicas o municipales se pide la ubicación faltante en vez de dejar que
# la búsqueda global adjudique una comunidad autónoma. Reglas por intención
# jurídico-urbanística con vocabulario operativo (tallos normalizados mediante
# _palabras_ambito), sin IDs, sin oro, sin ciudades y sin frases exactas.
_MARCO_NORMATIVO = ("norma", "normativ", "legal", "legislac", "regulator",
                     "reglam", "juridic", "ley")
# Escala estatal explícita: tallo de escala («estatal», «nacional») o sintagma
# «del Estado», junto a lexema normativo. Un «estado» aislado (estado de un
# expediente, estado de conservación) NO designa la escala nacional y
# «estatuto» no empieza por ninguno. Un «marco normativo» genérico sin escala
# NO supone estatal: si la materia es local, se pide aclaración.
_ESTATALES = ("estatal", "nacional")
# Modificadores que, junto a «edificable», marcan umbral o uso residencial.
_MOD_EDIFICAB = ("limit", "maxim", "residencial")
# «Abrir/apertura» junto a «local/local/es» (nunca «local» aislado).
_ABRE_LOCAL = ("abri", "apertur")
# Núcleo unívoco del dominio urbano-constructivo: los tallos genéricos de
# procedimiento y parámetro sólo cuentan junto a este núcleo («suelo»,
# «terreno» o «parcela» a secas NO bastan: «suelo eléctrico»,
# «impermeabilidad del suelo» o «parcela de cementerio» no son urbanismo).
_TRAMA_URBANA = ("urbanist", "urbanismo", "urbanizac", "planeamiento", "edific",
                 "construc", "obra", "vivienda", "terraza", "apertura",
                 "catastro", "finca", "rustic")
# Nivel CCAA: régimen del suelo y parámetros con umbral legal autonómico.
_CA_SOLOS = ("edificabilidad", "aprovechamiento")
# Nivel municipio: cabezas locales y tallos de procedimiento (no se vetan) y
# parámetros físicos del planeamiento local (se vetan ante vocabulario
# técnico: altura e instalaciones eléctricas no son planeamiento local).
_MUN_SOLOS = ("ordenanza", "ayuntamiento", "ajuntament")
_MUN_PROC = ("licencia", "tramite", "plazo", "documentac", "actividad",
             "reforma", "proyecto")
_PARAM_LOCAL = ("altura", "lindero", "parcela", "segrega")
_TECNICA = ("instalac", "contador", "electric", "enlace", "enchuf",
            "medidor", "acometida", "cablead", "fontaner", "saneam",
            "ventilac", "accesib", "pasillo", "ascensor", "cimentac",
            "estructur", "termic", "aislam")


def _adyacentes(palabras, a, b):
    """Par de tallos adyacentes o unidos por «de/del/no» («clasificación de
    suelo», «suelo no urbanizable»)."""
    n = len(palabras)
    for i in range(n - 1):
        if palabras[i].startswith(a):
            if palabras[i + 1].startswith(b):
                return True
            if palabras[i + 1] in ("de", "del", "no") and i + 2 < n and \
                    palabras[i + 2].startswith(b):
                return True
    return False


def _explicito_estatal(palabras):
    """True si la consulta pide expresamente el marco estatal/nacional: un
    tallo de escala («estatal», «nacional») o el sintagma «del Estado»,
    junto a un lexema normativo. Un «estado» aislado (estado de un
    expediente) no es la escala nacional; la escala a secas o el «marco
    normativo» genérico tampoco bastan: sin escala declarada no se supone
    que la consulta busca el marco estatal."""
    return (any(p.startswith(_ESTATALES) for p in palabras) or
            _adyacentes(palabras, "del", "estado")) and \
        any(p.startswith(_MARCO_NORMATIVO) for p in palabras)


# Otra escala pedida junto a la estatal: la consulta mixta («estatal y
# autonómica», «estatal o municipal») no es exclusiva del marco nacional.
_OTRAS_ESCALAS = ("autonom", "municipal")
# Verbos de relación/conexión cuya pregunta pide los elementos de una entidad.
_VERBOS_RELACION = ("conect", "conex", "enlaza", "compone", "une", "unir")
# Artículo indeterminado: marca de cola contextual, no de nombre técnico
# («línea general de alimentación» va sin artículo; «de una instalación …»
# enmarca el contexto).
_ART_INDET = ("un", "una", "unos", "unas")


def _escala_conjunta(palabras):
    """True si además de la escala estatal la consulta pide autonómica o
    municipal: la exclusividad nacional no procede y la consulta vuelve al
    cauce general, sin veto por la palabra «estatal» a secas."""
    return any(p.startswith(_OTRAS_ESCALAS) for p in palabras)


def _vista_relacion(consulta, palabras):
    """Vista derivada para consultas de relación/conexión: la entidad pedida es
    el objeto del verbo y la cola final «de (un|una) …» solo enmarca el contexto
    (una cola con «de» no es el objeto directo de la relación); la vista omite
    esa cola para no premiar la mención genérica del marco. Exige verbo de
    relación en la cabeza y contenido mínimo a ambos lados. Literal; el
    llamador lo traza y conserva la consulta original. None si no procede."""
    n = len(palabras)
    cola = None
    for i in range(1, n - 2):
        if palabras[i] == "de" and palabras[i + 1] in _ART_INDET:
            cola = i
    if cola is None or cola < 3 or n - cola < 3:
        return None
    if not any(p.startswith(_VERBOS_RELACION) for p in palabras[:cola]):
        return None
    tokens = str(consulta).split()
    if len(tokens) != len(palabras):
        return None
    vista = re.sub(r"\s+", " ", " ".join(tokens[:cola])).strip()
    return vista or None


# Consulta conceptual de definición/clasificación: cabeza «cuál/cuáles + ser»
# y verbo definitorio tras «que». Léxico general de consulta, sin frases,
# documentos ni casos concretos; la entidad es el sintagma entre la cabeza y
# el «que», y el resto enmarca el marco legal.
_CABEZAS_CONCEPTO = (("cuales", "son"), ("cual", "es"))
_VERBOS_CONCEPTO = ("distingu", "defin", "establec", "regula")


def _vista_conceptual(consulta, palabras):
    """Vista para consultas conceptuales («cuáles son [entidad] que
    distingue/define/establece/regula …»): la entidad es el sintagma entre la
    cabeza interrogativa y el «que» seguido de verbo definitorio; el resto
    enmarca el marco legal. Se omite el artículo inicial de la entidad y se
    exige un sintagma de >=2 palabras. Literal; el llamador lo traza y
    conserva la consulta original. None si no procede."""
    tokens = str(consulta).split()
    if len(tokens) != len(palabras):
        return None
    for h in range(len(palabras) - 5):
        if tuple(palabras[h:h + 2]) not in _CABEZAS_CONCEPTO:
            continue
        for i in range(h + 3, len(palabras) - 1):
            if palabras[i] != "que" or not any(
                    palabras[i + 1].startswith(v) for v in _VERBOS_CONCEPTO):
                continue
            ini = h + 2
            while ini < i and palabras[ini] in _ARTICULOS:
                ini += 1
            if i - ini >= 2:
                return re.sub(r"\s+", " ", " ".join(tokens[ini:i])).strip() or None
        return None
    return None


def _necesidad_ubicacion(consulta):
    """Campos de ubicación que exige la consulta según su intención
    jurídico-urbanística, o None si no hay evidencia de necesidad (la duda se
    resuelve a favor de la búsqueda previa). Nivel CCAA: régimen y
    clasificación del suelo, edificabilidad (tallo «edificabil-») y pares
    operativos «edificable» + límite/máximo/residencial, aprovechamientos y
    cesiones. Nivel CCAA + municipio: procedimientos locales (licencia de
    actividad, apertura de local, trámites, declaración responsable, plazos,
    documentación, actividad) y planeamiento local (altura, linderos,
    parcela, segregación; reforma o proyecto). Los parámetros físicos
    locales no disparan aclaración ante vocabulario técnico nacional
    (instalaciones, contadores, accesibilidad): la duda se resuelve a favor
    de la búsqueda. Un «marco normativo» genérico sin escala no suprime la
    aclaración: acompaña a la materia local (p. ej. «marco normativo de la
    licencia»), que sigue pidiendo lugar. Una cabeza municipal («ayuntamiento»)
    sin operativa local no eleva a municipio cuando la materia ya es de régimen
    autonómico (p. ej. el ayuntamiento como receptor de la cesión): se pide
    solo la comunidad autónoma."""
    palabras = _palabras_ambito(consulta)
    if not palabras:
        return None
    if _explicito_estatal(palabras) and not _escala_conjunta(palabras):
        return None  # marco estatal exclusivo: no pide lugar (mixta sí sigue)
    marco_gen = any(p.startswith(("marco",) + _MARCO_NORMATIVO)
                    for p in palabras)
    nucleo = [p for p in palabras if p.startswith(_TRAMA_URBANA)]
    impulso = bool(nucleo) or marco_gen
    ca = (any(p.startswith(_CA_SOLOS) for p in palabras) or
          (any(p.startswith("edificab") for p in palabras) and
           any(m.startswith(_MOD_EDIFICAB) for m in palabras)) or
          (impulso and any(p.startswith("cesion") for p in palabras)) or
          _adyacentes(palabras, "clasific", "suelo") or
          _adyacentes(palabras, "suelo", "urbano") or
          _adyacentes(palabras, "suelo", "urbanizable") or
          _adyacentes(palabras, "suelo", "rustic") or
          _adyacentes(palabras, "suelo", "rural") or
          _adyacentes(palabras, "suelo", "consolid"))
    declara = (any(p.startswith("declaracion") for p in palabras) and
               any(p.startswith("responsable") for p in palabras))
    lic_act = (any(p.startswith("licencia") for p in palabras) and
               any(p.startswith("actividad") for p in palabras))
    abre_local = (any(p.startswith(_ABRE_LOCAL) for p in palabras) and
                  any(p in ("local", "locales") for p in palabras))
    tecnica = any(p.startswith(_TECNICA) for p in palabras)
    # Operativa municipal declarada (norma o procedimiento local): con ella la
    # cabeza municipal es intención local; sin ella y con materia ya de régimen
    # autonómico, una cabeza municipal sola es solo el receptor o sujeto de la
    # materia («cesión … al ayuntamiento») y no exige trámite local.
    operativa_mun = (lic_act or abre_local or declara or
                     any(p.startswith(_MUN_PROC) for p in palabras) or
                     any(p.startswith(("ordenanza", "municipal"))
                         for p in palabras))
    mun = ((any(p.startswith(_MUN_SOLOS) for p in palabras) and
            not (ca and not operativa_mun)) or
           lic_act or abre_local or
           (impulso and (declara or
                         any(p.startswith(_MUN_PROC) for p in palabras))) or
           (not tecnica and impulso and
            any(p.startswith(_PARAM_LOCAL) for p in palabras)))
    if mun:
        return ["comunidad_autonoma", "municipio"]
    if ca:
        return ["comunidad_autonoma"]
    return None


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
        # Alias territoriales SOLO desde metadatos de los doc.json cargados.
        self._alias_ambito = _construir_alias_ambito(self.docs)

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

    def _avisos_docjson(self, doc_id: str) -> list:
        """Avisos declarados en el doc.json de un documento, en orden y sin repetir.

        Acepta `advertencias` como lista/tupla de cadenas no vacías y `nota_capa`
        como cadena no vacía; deduplica dentro del mismo documento (incluido el
        caso de nota_capa igual a un aviso previo). Son contenido, no
        instrucciones: se exponen solo como avisos. Ante tipos inesperados omite
        el elemento y jamás reconstruye JSON arbitrario como texto.
        """
        dj = (self.docs.get(doc_id) or (None, None))[0] or {}
        avisos: list = []
        vistos: set = set()
        bruto = dj.get("advertencias")
        if isinstance(bruto, (list, tuple)):
            for x in bruto:
                if isinstance(x, str) and x.strip() and x not in vistos:
                    vistos.add(x)
                    avisos.append(x)
        nota = dj.get("nota_capa")
        if isinstance(nota, str) and nota.strip() and nota not in vistos:
            vistos.add(nota)
            avisos.append(nota)
        return avisos

    # ------------------------------------------------- ámbito de la consulta

    def _resolver_ambito(self, consulta: str):
        """Resuelve el ámbito SOLO con alias de metadatos cargados: coincidencia
        por palabras normalizadas, la más larga primero y sin solapes; varios
        territorios se unen explícitamente con traza. None si no hay mención
        territorial detectable (búsqueda global intacta, salida sin claves
        nuevas). JSON-serializable; el llamador no lo invoca con documento
        explícito. Estados: resuelto | municipal_no_corporado | no_resuelto.
        """
        palabras = _palabras_ambito(consulta)
        if not palabras:
            return None
        hallados = []
        for clave in self._alias_ambito:
            tupla = tuple(clave.split())
            n = len(tupla)
            if n > len(palabras):
                continue
            for i in range(len(palabras) - n + 1):
                if tuple(palabras[i:i + n]) == tupla:
                    hallados.append((i, i + n, clave))
        elegidos = []
        for i, j, clave in sorted(hallados, key=lambda h: (-(h[1] - h[0]), h[0])):
            if any(not (j <= a or i >= b) for a, b, _c in elegidos):
                continue
            elegidos.append((i, j, clave))
        # Clasificación por nivel desde los metadatos de cada fuente. Regla
        # general: nacionales (fuente sin metadato territorial) siempre
        # complementarios; autonómicas solo de la jurisdicción pedida; municipales
        # solo del municipio pedido. La ubicación sola no decide el nivel: el
        # nivel municipal exige intención municipal explícita en la consulta.
        municipios, ccaas, padres = {}, set(), set()
        territorios, municipios_sin = [], []
        for i, j, clave in sorted(elegidos, key=lambda h: h[0]):
            info = self._alias_ambito[clave]
            mun_canon = next((c for c in sorted(info)
                              if "municipio" in info[c]["niveles"]), None)
            for canon in sorted(info):
                niv = sorted(info[canon]["niveles"])
                padre = None
                if canon == mun_canon:
                    municipios[canon] = {d for d, (_jur, _mun) in
                                         self._clasif_docs().items()
                                         if _mun == canon}
                    pj = sorted(self._padres_municipio(canon))
                    if pj:
                        padre = ", ".join(pj)
                        ccaas.update(pj)
                        padres.update(pj)
                elif "jurisdiccion" in info[canon]["niveles"]:
                    ccaas.add(canon)
                territorios.append({
                    "alias": clave, "canonico": canon, "niveles": niv,
                    "documentos": sorted(info[canon]["documentos"]),
                    "via": "doc.json:" + "+".join(niv), "padre_derivado": padre})
            if mun_canon is None and _intencion_municipal_adyacente(palabras, i):
                municipios_sin.append(_fragmento_literal(consulta, palabras, i, j))
        nombres_no = []
        for m in _PATRON_EN_NOMBRE.finditer(str(consulta)):
            pal_nombre = _palabras_ambito(m.group(1))
            if not pal_nombre:
                continue
            pos = _posicion_tupla(palabras, tuple(pal_nombre))
            if pos is not None and any(a <= pos and pos + len(pal_nombre) <= b
                                       for a, b, _c in elegidos):
                continue
            if m.group(1) in nombres_no or m.group(1) in municipios_sin:
                continue
            if _LEXICO_MUNICIPAL.search(A.norm(consulta)) or \
                    (pos is not None and _intencion_municipal_adyacente(palabras, pos)):
                municipios_sin.append(m.group(1))
            else:
                nombres_no.append(m.group(1))
        if municipios_sin:
            notas = ["intención municipal explícita para %s sin fuentes municipales "
                     "incorporadas: no se sustituye por otra ciudad, por fuentes "
                     "autonómicas de nombre similar ni por otra jurisdicción"
                     % ", ".join("'%s'" % n for n in municipios_sin)]
            if territorios:
                notas.append("la jurisdicción reconocida en la consulta no suple la "
                             "fuente municipal pedida; la ubicación sola no decide "
                             "el nivel normativo")
            return {"estado": "municipal_no_corporado", "consulta_original": consulta,
                    "consulta_derivada": None, "territorios": territorios,
                    "nombres_no_resueltos": nombres_no,
                    "municipios_sin_fuentes": municipios_sin,
                    "documentos_permitidos": None, "notas": notas}
        if not territorios and not nombres_no:
            return None
        notas = []
        if territorios:
            if len(territorios) > 1:
                notas.append("unión explícita de %d territorios reconocidos; no se "
                             "prioriza ninguno por orden de aparición"
                             % len(territorios))
            if municipios:
                notas.append("nivel municipal pedido: se permiten las fuentes "
                             "municipales del municipio pedido, las autonómicas de "
                             "su comunidad (derivada del metadato de la propia "
                             "fuente) y las nacionales complementarias")
            else:
                notas.append("nivel autonómico pedido: se permiten las autonómicas "
                             "de la jurisdicción y las nacionales complementarias; "
                             "las fuentes municipales quedan fuera salvo municipio "
                             "pedido expresamente")
            if padres:
                notas.append("comunidad autónoma padre derivada del metadato de las "
                             "fuentes municipales pedidas: %s"
                             % ", ".join(sorted(padres)))
            if len({n for t in territorios for n in t["niveles"]}) > 1:
                notas.append("ámbito mixto (municipio+jurisdicción): citar el nivel "
                             "solicitado, sin confundir fuentes")
            if nombres_no:
                notas.append("menciones territoriales sin correspondencia en el "
                             "corpus: " + ", ".join("'%s'" % n for n in nombres_no))
            notas.append("nunca se incluyen fuentes de otra jurisdicción ni de otro "
                         "municipio distinto al solicitado")
            notas.append("fuentes nacionales (sin metadato territorial en su fuente) "
                         "permitidas como complementarias; no sustituyen la "
                         "respuesta del ámbito solicitado")
            notas.append("edición = la incorporada por la fuente; sin afirmación de "
                         "vigencia ni régimen transitorio")
            permitidos = {d for d, (jur, mun) in self._clasif_docs().items()
                          if not jur and not mun}
            for docs_mun in municipios.values():
                permitidos |= docs_mun
            for c in ccaas:
                permitidos |= {d for d, (jur, mun) in self._clasif_docs().items()
                               if jur == c and not mun}
            derivada = _consulta_derivada(consulta, palabras, elegidos)
            return {"estado": "resuelto", "consulta_original": consulta,
                    "consulta_derivada": derivada if derivada and
                    derivada != consulta else None,
                    "territorios": territorios, "nombres_no_resueltos": nombres_no,
                    "municipios_pedidos": sorted(municipios),
                    "documentos_permitidos": sorted(permitidos), "notas": notas}
        notas.append("mención territorial sin correspondencia en los metadatos del "
                     "corpus: búsqueda global conservada, sin sustitución de ámbito "
                     "ni afirmación de vigencia")
        return {"estado": "no_resuelto", "consulta_original": consulta,
                "consulta_derivada": None, "territorios": [],
                "nombres_no_resueltos": nombres_no,
                "documentos_permitidos": None, "notas": notas}

    def _clasif_docs(self):
        """{doc: (jurisdiccion, municipio)} desde los doc.json cargados; en caché."""
        if getattr(self, "_clasif", None) is None:
            self._clasif = {}
            for d, (dj, _b) in self.docs.items():
                dj = dj or {}
                self._clasif[d] = (str(dj.get("jurisdiccion") or "").strip(),
                                   str(dj.get("municipio") or "").strip())
        return self._clasif

    def _padres_municipio(self, canon):
        """Jurisdicciones que declaran las propias fuentes municipales de `canon`."""
        return {jur for d, (jur, mun) in self._clasif_docs().items()
                if mun == canon and jur}

    def _lineas_ambito(self, res_amb):
        """Líneas de cabecera con la traza de ámbito; vacía si no hubo resolución."""
        if not res_amb:
            return []
        estado = res_amb.get("estado")
        nombres = ", ".join("'%s'" % n for n in
                            res_amb.get("municipios_sin_fuentes")
                            or res_amb.get("nombres_no_resueltos") or [])
        if estado == "resuelto":
            t = ["Ámbito reconocido desde metadatos (jurisdicción/municipio de las "
                 "fuentes; no es vigencia): " + "; ".join(
                     "%s [%s · docs: %s]" % (
                         x.get("canonico"), "/".join(x.get("niveles") or []),
                         ", ".join(x.get("documentos") or []))
                     for x in res_amb.get("territorios") or [])
                 + ". Se admiten además fuentes nacionales complementarias (sin "
                   "metadato territorial en su fuente); nunca de otra jurisdicción "
                   "ni de otro municipio."]
            if res_amb.get("consulta_derivada"):
                t.append("Vista de búsqueda derivada (literal trazado): «%s»; la "
                         "consulta original se conserva íntegra."
                         % res_amb["consulta_derivada"])
            return t
        if estado == "no_resuelto":
            return ["AVISO ámbito no resuelto: mención territorial (%s) sin "
                    "correspondencia en los metadatos del corpus; búsqueda global "
                    "sin sustitución de ámbito; no se afirma vigencia." % nombres]
        if estado == "municipal_no_corporado":
            return ["Intención municipal explícita sin incorporar: %s sin fuentes "
                    "municipales en el corpus; sin sustitución por otra ciudad ni "
                    "por fuentes autonómicas de nombre similar." % nombres]
        return []

    def _salida_municipal_no_corporado(self, consulta, res_amb, limite, t0):
        """sin_resultados explicado: municipio pedido sin incorporar; sin
        búsqueda ni fallback a otra ciudad, a su CCAA homónima ni a otra jurisdicción."""
        nombres = ", ".join("'%s'" % n for n in
                            res_amb.get("municipios_sin_fuentes")
                            or res_amb.get("nombres_no_resueltos") or [])
        partes = self._cabecera(consulta, None, None,
                                ["", *self._lineas_ambito(res_amb),
                                 "", "-- Advertencias --"])
        partes.extend("- %s" % a for a in res_amb.get("notas") or [])
        partes.append("")
        partes.append("ESTADO sin_resultados: la consulta pide fuente municipal de "
                      "un municipio sin incorporar (%s); no se sustituye por otra "
                      "ciudad, por fuentes autonómicas de nombre similar ni por "
                      "fuentes de otra jurisdicción." % nombres)
        texto = "\n".join(partes) + "\n"
        rec = {"busqueda": {"metodo": "bm25", "terminos": [], "ambito_capa": None},
               "resultados": [], "advertencias": list(res_amb.get("notas") or []),
               "omitidos": [], "relacionados_no_incluidos": []}
        return self._salida("sin_resultados", consulta, None, None, texto, [], rec,
                            limite, t0, resolucion_ambito=res_amb)

    def _salida_aclaracion(self, consulta, campos, limite, t0):
        """aclaracion_necesaria: sin documento explícito ni ubicación resuelta,
        la materia planteada exige división autonómica o municipal; se pide el
        dato faltante ANTES de buscar. Sin BM25, sin resultados retenidos, sin
        fuente/edición/jurisdicción inferidas y sin elegir región alguna."""
        municipio = len(campos) > 1
        aclaracion = {
            "campos_requeridos": list(campos),
            "pregunta": (
                "¿Sobre qué comunidad autónoma y qué municipio se plantea esta "
                "consulta? La materia planteada se decide con normas "
                "autonómicas o municipales y, sin la ubicación, no corresponde "
                "elegir una jurisdicción concreta por cuenta propia."
                if municipio else
                "¿Sobre qué comunidad autónoma se plantea esta consulta? La "
                "materia planteada se decide con normas autonómicas y, sin la "
                "ubicación, no corresponde elegir una jurisdicción concreta "
                "por cuenta propia.")}
        aviso = ("aclaracion_necesaria: la consulta plantea materia que se decide "
                 "con %s; sin documento explícito ni ubicación resuelta no se "
                 "ejecutó búsqueda" %
                 ("normas autonómicas o municipales" if municipio
                  else "normas autonómicas"))
        partes = self._cabecera(consulta, None, None,
                                ["", "-- Aclaración territorial necesaria --"])
        partes.append("- %s" % aviso)
        partes.append("Campos requeridos: %s." %
                      ", ".join(aclaracion["campos_requeridos"]))
        partes.append("Pregunta: %s" % aclaracion["pregunta"])
        partes.append("Se pide la ubicación en lugar de ejecutar la búsqueda: "
                      "sin ella, una búsqueda global invitaría a adjudicar una "
                      "comunidad autónoma; no se retienen resultados parciales "
                      "ni se entrega una región como elección automática.")
        partes.append("La consulta se conserva literal; no se infiere fuente, "
                      "edición ni jurisdicción.")
        texto = "\n".join(partes) + "\n"
        rec = {"busqueda": {"metodo": "no_ejecutada", "terminos": [],
                            "ambito_capa": None},
               "resultados": [], "advertencias": [aviso], "omitidos": [],
               "relacionados_no_incluidos": []}
        return self._salida("aclaracion_necesaria", consulta, None, None, texto,
                            [], rec, limite, t0, aclaracion=aclaracion)

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

        # ---------------------------------- resolución de ámbito (metadatos)
        # Solo búsqueda automática: el filtro documento/versión explícito y su
        # versión validada tienen precedencia y no se infiere territorio alguno.
        res_amb = None
        perm = None
        marco_nac = False
        motivo_vista = None
        vista_busq = None
        consulta_busq = consulta
        avisos_conc: list = []
        if doc_id is None:
            res_amb = self._resolver_ambito(consulta)
            if res_amb and res_amb.get("estado") == "resuelto":
                perm_set = set(res_amb.get("documentos_permitidos") or [])
                if perm_set:
                    perm = perm_set
                    consulta_busq = res_amb.get("consulta_derivada") or consulta
            elif res_amb and res_amb.get("estado") == "municipal_no_corporado":
                return self._salida_municipal_no_corporado(
                    consulta, res_amb, presupuesto_tokens, t0)
            if not res_amb:
                pal_amb = _palabras_ambito(consulta)
                if _explicito_estatal(pal_amb) and not _escala_conjunta(pal_amb):
                    # Marco estatal/nacional pedido expresamente: los
                    # candidatos se limitan a fuentes nacionales (sin metadato
                    # territorial en su fuente) por la puerta existente
                    # documentos_permitidos, conservando IDF global y
                    # precedencias. No es aclaración de lugar y no se elige
                    # ninguna fuente autonómica como respuesta estatal.
                    nac = {d for d, (jur, mun) in self._clasif_docs().items()
                           if not jur and not mun}
                    perm = nac
                    marco_nac = True
                    # Consulta conceptual de definición: la entidad pedida se
                    # contrasta como frase literal normalizada en el texto en
                    # disco de las fuentes nacionales ya permitidas. Con
                    # coincidencia dinámica, perm se acota a esas fuentes y la
                    # BM25 usa la vista enfocada (mismas filas e IDF global);
                    # sin coincidencias se conserva nac (incluido vacío) y la
                    # consulta original, sin fallback autonómico.
                    vista_c = _vista_conceptual(consulta, pal_amb)
                    if vista_c:
                        frase_c = A.norm(vista_c)
                        docs_c = {f["documento"] for f in self.filas
                                  if f["documento"] in nac and frase_c in
                                  A.norm(A.texto_fichero(
                                      self.contenido, f.get("archivo")))}
                        if docs_c:
                            perm = docs_c
                            vista_busq = vista_c
                            consulta_busq = vista_c
                            motivo_vista = "conceptual"
                            avisos_conc.append(
                                "vista de búsqueda derivada (consulta conceptual, "
                                "no relación/conexión): «%s» · frase normalizada "
                                "«%s» · criterio: coincidencia literal del texto en "
                                "disco · fuentes nacionales seleccionadas: %s; la "
                                "consulta original se conserva íntegra." % (
                                    vista_c, frase_c, ", ".join(sorted(docs_c))))
                        else:
                            avisos_conc.append(
                                "consulta conceptual (no relación/conexión): la frase "
                                "normalizada «%s» (vista candidata «%s») no aparece en "
                                "el texto en disco de las fuentes nacionales; se "
                                "conserva el conjunto nacional completo y la consulta "
                                "original, sin sustitución por fuentes autonómicas." % (
                                    frase_c, vista_c))
                else:
                    # Sin documento explícito ni territorio resuelto: si la
                    # consulta plantea materia autonómica/municipal se pide la
                    # ubicación en lugar de dejar que la búsqueda global
                    # adjudique una CCAA. Consulta mixta («estatal y
                    # autonómica») también entra aquí: la exclusividad
                    # nacional no procede.
                    campos = _necesidad_ubicacion(consulta)
                    if campos:
                        return self._salida_aclaracion(consulta, campos,
                                                       presupuesto_tokens, t0)
                    # Vista de relación/conexión: entidad pedida conservada,
                    # cola contextual subordinada «de + artículo indeterminado»
                    # omitida. Solo búsqueda automática sin documento y sin
                    # ámbito resuelto; literal trazado, consulta original
                    # conservada.
                    vista = _vista_relacion(consulta, pal_amb)
                    if vista and vista != consulta:
                        vista_busq = vista
                        consulta_busq = vista
                        motivo_vista = "relacion"

        # ------------------------------------------------------------- búsqueda
        terminos = [t for t in re.split(r"[\s,;]+", consulta_busq) if len(t) > 1]
        op = SimpleNamespace(max=max_resultados, presupuesto=presupuesto_tokens,
                             expandir=1, documento=doc_id, capa=None, materia=None,
                             documentos_permitidos=perm)
        advertencias: list = []
        omitidos: list = []
        if marco_nac:
            advertencias.append(
                "marco estatal/nacional pedido expresamente: candidatos "
                "limitados a fuentes nacionales (sin metadato territorial en "
                "su fuente) por la puerta documentos_permitidos; el IDF global "
                "y el ranking se conservan y no es una aclaración de lugar")
        advertencias.extend(avisos_conc)
        if vista_busq and motivo_vista == "relacion":
            advertencias.append(
                "vista de búsqueda derivada (relación/conexión: entidad pedida "
                "conservada, cola contextual subordinada con artículo "
                "indeterminado omitida): «%s»; la consulta original se conserva "
                "íntegra." % vista_busq)
        if res_amb and res_amb.get("estado") == "no_resuelto":
            advertencias.extend("ámbito: %s" % n for n in res_amb.get("notas") or [])
        try:
            busq = A.buscar_bm25(self.contenido, self.filas, self.docs, consulta_busq,
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
            extra_amb = self._lineas_ambito(res_amb)
            partes = self._cabecera(consulta, doc_id, objetivo,
                                    ["", *extra_amb, "-- Advertencias --"]
                                    if extra_amb else ["", "-- Advertencias --"])
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
            extra_sal = {"resolucion_ambito": res_amb} if res_amb else {}
            if vista_busq:
                extra_sal["vista_busqueda"] = vista_busq
            return self._salida(
                "sin_resultados", consulta, doc_id,
                objetivo or (str(version) if version is not None else None), texto, [],
                {"busqueda": {"metodo": "bm25", "terminos": busq.get("terminos") or terminos,
                              "ambito_capa": busq.get("ambito_capa")},
                 "resultados": [], "advertencias": advertencias, "omitidos": omitidos,
                 "relacionados_no_incluidos": []},
                presupuesto_tokens, t0, **extra_sal)

        # ------------------------------------------------ ensamblaje del contexto
        entregadas: dict = {}   # clave de página -> Resultado que la entregó
        meta_doc: dict = {}
        paginas_norm = ""       # texto normalizado de evidencia entregada (dedupe literal)
        bloques_vistos = set()  # claves de bloques de contexto ya impresos
        # Avisos de doc.json de cada documento efectivamente seleccionado por BM25
        # (tras el filtro de edición exacta): una sola vez por documento, con su ID,
        # añadidos a `advertencias` ANTES de construir texto_final y contar el
        # presupuesto, de modo que cuentan como cualquier parte del texto sin
        # recortes. No alteran la selección, los textos literales de páginas ni los
        # estados; no se añaden avisos de documentos cuyos resultados quedaron fuera.
        avisos_doc: dict = {}
        for r in resultados:
            d = r.get("documento")
            if d and d not in avisos_doc:
                avisos_doc[d] = self._avisos_docjson(d)
        for d, avisos in avisos_doc.items():
            advertencias.extend("documento %s: %s" % (d, a) for a in avisos)
        extra_amb = self._lineas_ambito(res_amb)
        partes = self._cabecera(consulta, doc_id, objetivo,
                                ["", *extra_amb, "-- Advertencias --"] if extra_amb
                                else ["", "-- Advertencias --"])
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
        extra_sal = {"resolucion_ambito": res_amb} if res_amb else {}
        if vista_busq:
            extra_sal["vista_busqueda"] = vista_busq
        return self._salida("ok", consulta, doc_id,
                            objetivo or (str(version) if version is not None else None),
                            texto_final, paginas_out, rec, presupuesto_tokens, t0,
                            versiones_disponibles=versiones_disp, **extra_sal)


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
