#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exportador de resultados del piloto SUA (solo stdlib, sin API).

Diseñado SOLO para este piloto (casos y fixtures sintéticos): el saneo no
es universal y exige revisión manual antes de publicar.
Solo lectura del origen; los crudos nunca se modifican. CLI:
  python exportar_publico.py --origen resultados --destino <nuevo/vacio>

Exporta por cada subdirectorio con consumo.jsonl: manifest.json,
consumo.jsonl, revision_codex.json, resumen_consumo.json, *.response.json,
*.recuperacion.json y cierre_publico.json (conteos, estados de recursos
sin IDs y costes observados). Ignora *.request.json, api_llamadas.jsonl,
recursos.json, error_http_*.json y cleanup.json. Las respuestas crudas
nunca se publican tal cual: solo versiones reducidas y saneadas.
"""
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

CLAVES_BORRAR = {"encrypted_content", "file_data", "vector_store_id", "file_id",
                 "request_id", "access_programs", "billing", "image", "ruta", "python"}
RE_ID = re.compile(
    r"\b(?:resp|req|msg|rs|fs|vs|ses)_[A-Za-z0-9_-]{8,}|\bfile-[A-Za-z0-9_-]{8,}")
RE_RUTA = re.compile(
    r"[A-Za-z]:[\\/]Users[\\/][^\s\"'|<>]*|/Users/[^\s\"'|<>]*|/home/[^\s\"'|<>]*",
    re.IGNORECASE)
OMITIDOS = ["*.request.json", "api_llamadas.jsonl", "recursos.json (solo leido para estados)",
            "error_http_*.json", "cleanup.json", "encrypted_content, file_data, vector_store_id, "
            "file_id, request_id, access_programs, billing, image, ruta, python",
            "razonamiento y metadatos de responses fuera de la lista permitida",
            "IDs resp_/req_/vs_/msg_/rs_/fs_/file-/ses_ -> [identificador omitido]",
            "rutas absolutas locales -> [ruta local omitida]"]


def sanear(nodo):
    """Recursivo: borra claves sensibles, oculta rutas locales e IDs de API."""
    if isinstance(nodo, dict):
        limpio = {}
        for k, v in nodo.items():
            if isinstance(k, str) and k in CLAVES_BORRAR:
                continue
            kk = k
            if isinstance(k, str) and RE_ID.search(k):  # claves que son IDs (p. ej. dict cleanup dev)
                kk = "[identificador omitido]"
                while kk in limpio:
                    kk += "#2"
            limpio[kk] = sanear(v)
        return limpio
    if isinstance(nodo, list):
        return [sanear(x) for x in nodo]
    if isinstance(nodo, str):
        m = RE_RUTA.search(nodo)
        if m and (m.start() == 0 or m.group(0) == nodo):
            return "[ruta local omitida]"  # empieza por ruta de usuario: solo marcador
        return RE_RUTA.sub("[ruta local omitida]",
                           RE_ID.sub("[identificador omitido]", nodo))
    return nodo


def cargar_json(ruta):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"JSON ilegible, no se exporta ni se inventa: {ruta.name} ({type(e).__name__})")


def _hashes_a_lista(m, clave):
    """dict archivo->SHA -> lista {archivo, sha256}: evita falsos positivos
    gitleaks (generic-api-key) cuando la clave es nombre de archivo; conserva
    cada SHA y no borra datos."""
    m[clave] = [{"archivo": k, "sha256": v} for k, v in m[clave].items()]


def exportar_manifest(archivo):
    m = cargar_json(archivo)
    if isinstance(m.get("hashes"), dict):
        # hashes se publica renombrado a hashes_codigo: dict archivo->SHA ->
        # lista {archivo, sha256}; si ya existia hashes_codigo se fusiona al
        # final para no perder SHAs (contrato original del exportador).
        lista = [{"archivo": k, "sha256": v} for k, v in m.pop("hashes").items()]
        m["hashes_codigo"] = m["hashes_codigo"] + lista \
            if isinstance(m.get("hashes_codigo"), list) else lista
    for clave in ("codigo_sha256", "archivos_sha256"):  # aliases dev: mismo dict, mismo nombre
        if isinstance(m.get(clave), dict):
            _hashes_a_lista(m, clave)
    return sanear(m)


def _texto_output(texto):
    """output_text: si el texto es JSON valido, sanea el objeto y re-serializa
    (valores normativos y usage no se alteran; el saneo no toca numeros ni
    claves de ese tipo); si no es JSON, sanea como cadena."""
    try:
        dato = json.loads(texto)
    except ValueError:
        return sanear(str(texto))
    if isinstance(dato, (dict, list)):
        return json.dumps(sanear(dato), ensure_ascii=False)
    return sanear(dato) if isinstance(dato, str) else texto


def reducir_respuesta(archivo):
    """Conserva model/status/usage/incomplete_details/error y output util; sin IDs."""
    resp = cargar_json(archivo)
    r = {c: sanear(resp[c]) for c in ("model", "status", "usage", "incomplete_details", "error") if c in resp}
    salida = []
    for item in resp.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            cont = [{"type": "output_text", "text": _texto_output(c.get("text", ""))}
                    for c in item.get("content", []) or []
                    if isinstance(c, dict) and c.get("type") == "output_text"]
            if cont:
                salida.append({"type": "message", "role": item.get("role"), "content": cont})
        elif item.get("type") == "file_search_call":
            ficha = {"type": "file_search_call"}
            ficha.update({k: sanear(item[k]) for k in ("status", "queries") if k in item})
            res = [{k: sanear(x.get(k)) for k in ("filename", "score", "text") if k in x}
                   for x in item.get("results", []) or [] if isinstance(x, dict)]
            if res:
                ficha["results"] = res
            salida.append(ficha)
    r["output"] = salida
    return r


def cerrar_run(origen, conteos, filas):
    """Metadata publica: conteos, estados de recursos sin IDs y costes observados."""
    recursos = {}
    if (origen / "recursos.json").is_file():
        for tipo, d in cargar_json(origen / "recursos.json").items():
            if isinstance(d, dict):
                estados = {}
                for meta in d.values():
                    e = meta.get("estado", "desconocido") if isinstance(meta, dict) else str(meta)
                    estados[e] = estados.get(e, 0) + 1
                recursos[tipo] = estados
    costes = {}
    if filas:
        ultimo = filas[-1]
        for k, n in (("gastado_sesion", "coste_run_usd"), ("gastado_total", "coste_acumulado_observado_usd")):
            if k in ultimo:
                costes[n] = ultimo[k]
        costes["respuestas_con_coste"] = sum(1 for f in filas if "coste_usd" in f)
    return {"run": origen.name, "conteo": conteos, "recursos_estados": recursos,
            "costes_observados": costes,
            "nota": "estimacion de coste; cache subset de entrada, reasoning de salida"}


def exportar_run(origen, destino):
    if not (origen / "consumo.jsonl").is_file():
        return None
    destino.mkdir(parents=True, exist_ok=True)
    filas = []
    for linea in (origen / "consumo.jsonl").read_text(encoding="utf-8").splitlines():
        if linea.strip():
            filas.append(sanear(json.loads(linea)))
    with (destino / "consumo.jsonl").open("w", encoding="utf-8") as f:
        for fila in filas:  # JSON una fila por linea; sumas intactas
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    (destino / "manifest.json").write_text(
        json.dumps(exportar_manifest(origen / "manifest.json"), ensure_ascii=False, indent=2), encoding="utf-8")
    conteos = {"manifest": 1, "consumo_filas": len(filas)}
    for patron, nombre, fabrica in (("*.response.json", "respuestas", reducir_respuesta),
                                    ("*.recuperacion.json", "recuperaciones", lambda p: sanear(cargar_json(p)))):
        piezas = []
        for archivo in sorted(origen.glob(patron)):
            piezas.append((destino / archivo.name, fabrica(archivo)))
        for ruta, dato in piezas:
            ruta.write_text(json.dumps(dato, ensure_ascii=False, indent=2), encoding="utf-8")
        conteos[nombre] = len(piezas)
    extras = {}
    for nombre in ("revision_codex.json", "resumen_consumo.json"):
        if (origen / nombre).is_file():
            (destino / nombre).write_text(
                json.dumps(sanear(cargar_json(origen / nombre)), ensure_ascii=False, indent=2), encoding="utf-8")
            extras[nombre] = 1
    cierre = cerrar_run(origen, {**conteos, **extras}, filas)
    (destino / "cierre_publico.json").write_text(
        json.dumps(cierre, ensure_ascii=False, indent=2), encoding="utf-8")
    return cierre


def main():
    p = argparse.ArgumentParser(description="Exportacion publica depurada del piloto SUA.")
    p.add_argument("--origen", required=True, help="Directorio resultados del piloto.")
    p.add_argument("--destino", required=True, help="Directorio de exportacion, nuevo o vacio.")
    a = p.parse_args()
    origen, destino = Path(a.origen), Path(a.destino)
    if destino.is_file():  # antes de iterdir: mensaje claro si destino es archivo
        sys.exit("--destino existe y es un archivo: se requiere un directorio nuevo o vacio.")
    if destino.exists() and any(destino.iterdir()):
        sys.exit("--destino debe ser un directorio nuevo o vacio.")
    if not origen.is_dir():
        sys.exit(f"--origen no existe: carpeta que termina en '{origen.name}'")
    d, o = destino.resolve(), origen.resolve()
    if d == o or d.is_relative_to(o):
        sys.exit("--destino no puede ser el origen ni residir dentro del origen.")
    destino.mkdir(parents=True, exist_ok=True)
    runs = {}
    for sub in sorted(car for car in origen.iterdir() if car.is_dir()):
        try:
            cierre = exportar_run(sub, destino / sub.name)
        except (OSError, ValueError) as e:
            sys.exit(f"Fallo exportando {sub.name}: {type(e).__name__}: {e}")
        if cierre:
            runs[sub.name] = cierre["conteo"]
            print(f"{sub.name}: {cierre['conteo']}")
    (destino / "manifest_export.json").write_text(json.dumps(
        {"version": "1", "generado_utc": datetime.now(timezone.utc).isoformat(),
         "origen": origen.name, "originales_preservados": True, "omitidos": OMITIDOS, "runs": runs},
        ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(sum(c.values()) for c in runs.values())
    print(f"Runs exportados: {len(runs)} | piezas totales: {total}")


if __name__ == "__main__":
    main()
