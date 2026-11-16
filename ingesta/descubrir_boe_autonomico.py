#!/usr/bin/env python3
"""Descubrimiento simple de Códigos de Urbanismo autonómicos en el índice BOE
(tipo=C). SOLO descubre: recorre «Código de Urbanismo de [región]», sigue «Ver
contenido» o agrega ``&tab=2`` (codigo.php por defecto muestra la descarga, no
las normas) y extrae TODOS los enlaces act.php/doc.php por su parámetro id
(BOE-A-... y autonómicos: BOA-d-, BOJA-b-, BORM-s-, DOCM-q-, DOGV-r-...) con su
título. Sin selección de leyes ni heurísticas: revisión humana posterior.
Salida: 0 ok; 1 errores de captura; 2 configuración; HTML+SHA-256 en .local/."""

from __future__ import annotations

import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recopilar_territorial import (AnalizadorPagina, CHECKOUT_RAIZ, FalloConfig,
                                   FalloPermanente, Rastreador, normalizar_texto)

INDICE = "https://www.boe.es/biblioteca_juridica/index.php?tipo=C"
HOSTS = {"www.boe.es"}
SALIDA_DEFECTO = CHECKOUT_RAIZ / ".local" / "autonomicas-boe"
RE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
PENDIENTES = {"seleccion_leyes_principales": "PENDIENTE: revision humana por region",
              "ambito_y_vigencia": "PENDIENTE: requiere regimen transitorio",
              "licencia": "PENDIENTE por fuente: aviso legal del portal BOE"}

def con_tab2(url):
    consulta = urlparse(url).query
    if "tab=" in consulta: return url
    return url + ("&" if consulta else "?") + "tab=2"

def analizar(bytes_html):
    analizador = AnalizadorPagina()
    analizador.feed(bytes_html.decode("utf-8", "replace"))
    return analizador

def guardar_html(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return {"sha256": hashlib.sha256(datos).hexdigest(), "bytes": len(datos)}

def extraer_candidatos(bytes_html, url_base):
    """Primer enlace act.php/doc.php por valor del parámetro id de la query
    (BOE-A-... u autonómico: BOA-d-, BOJA-b-, BORM-s-, DOCM-q-, DOGV-r-...),
    validado con regex segura; sin filtrar solo BOE-A."""
    candidatos, vistos = [], set()
    for href, texto in analizar(bytes_html).enlaces:
        if "act.php" not in href and "doc.php" not in href: continue
        valor = (parse_qs(urlparse(urljoin(url_base, href)).query).get("id") or [""])[0].strip()
        if not valor or not RE_ID.fullmatch(valor) or valor in vistos: continue
        vistos.add(valor)
        candidatos.append({"id": valor, "titulo": (texto or "").strip(),
                           "url": urljoin(url_base, href)})
    return candidatos

def principal():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", default=str(SALIDA_DEFECTO))
    parser.add_argument("--limite", type=int, default=None)
    args = parser.parse_args()
    salida = Path(args.salida).resolve()
    if salida != SALIDA_DEFECTO.resolve():
        raise FalloConfig(f"--salida solo puede ser {SALIDA_DEFECTO}")
    rastreador = Rastreador(1.0, 30)
    errores, codigos, vistos = [], [], set()

    datos, estado, url_final, *_ = rastreador.descargar(INDICE, HOSTS)
    ev_indice = {"url": url_final, "estado_http": estado, **guardar_html(salida / "html" / "indice.html", datos)}
    for href, texto in analizar(datos).enlaces:
        if "codigo.php" not in href or "urbanismo" not in normalizar_texto(texto or ""):
            continue
        base = urljoin(INDICE, href)
        cid = (parse_qs(urlparse(base).query).get("id") or ["?"])[0]
        if cid in vistos: continue
        vistos.add(cid)
        codigos.append({"codigo": cid, "titulo": (texto or "").strip(), "url": base})
    if args.limite is not None: codigos = codigos[:max(0, args.limite)]

    resultado = {"generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "indice": ev_indice, "pendientes": PENDIENTES, "codigos": [], "errores": errores}
    for cod in codigos:
        try:
            datos_c, estado_c, final, *_ = rastreador.descargar(cod["url"], HOSTS)
            destino = next((urljoin(cod["url"], h) for h, t in analizar(datos_c).enlaces
                            if "ver contenido" in normalizar_texto(t or "")), con_tab2(cod["url"]))
            if destino != cod["url"]:
                datos_c, estado_c, final, *_ = rastreador.descargar(destino, HOSTS)
            cod["url_contenido"] = destino
            cod["candidatos"] = extraer_candidatos(datos_c, destino)
            cod["evidencia"] = {"url": final, "estado_http": estado_c,
                                "html": f"html/codigo-{cod['codigo']}.html",
                                **guardar_html(salida / "html" / f"codigo-{cod['codigo']}.html", datos_c)}
            resultado["codigos"].append(cod)
        except FalloPermanente as exc:
            errores.append({"codigo": cod["codigo"], "url": cod["url"], "error": str(exc)})

    (salida / "candidatos.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"codigos={len(resultado['codigos'])} candidatos={sum(len(c['candidatos']) for c in resultado['codigos'])} errores={len(errores)} salida={salida / 'candidatos.json'}")
    return 1 if errores else 0

if __name__ == "__main__":
    try: sys.exit(principal())
    except FalloConfig as exc: print(f"ERROR de configuracion: {exc}", file=sys.stderr); sys.exit(2)
