"""Ejecutor delgado del piloto SUA: planifica, prepara contextos y llama a ClienteAPI.
Sin gold en la entrada del modelo y sin reintentos; recuperacion sin modelo y tiempo prep aparte (no entrada API).
"""
import argparse, hashlib, json, sys, time
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
FUENTE = REPO / "contenido" / "docs" / "DB-SUA-oficial" / "2022-06-14__3cfb5bbb135e" / "fuente.pdf"

for _p in (str(CARPETA), str(REPO / "experimentos" / "http-local")):
    sys.path.insert(0, _p)
from cliente_api import ClienteAPI
import solicitudes

def ahora(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def escribe_json(ruta, dato): ruta.write_text(json.dumps(dato, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def sanear(nodo):  # copia sin file_data en claro (igual que _sanear), para dry-run sin cliente ni clave
    if isinstance(nodo, dict):
        if "file_data" in nodo:
            d = str(nodo["file_data"])
            return {**nodo, "file_data": {"sha256": hashlib.sha256(d.encode()).hexdigest(), "longitud": len(d)}}
        return {k: sanear(v) for k, v in nodo.items()}
    if isinstance(nodo, list):
        return [sanear(v) for v in nodo]
    return nodo

def parsear():
    p = argparse.ArgumentParser(description="Ejecutor del piloto SUA.")
    p.add_argument("--salida", required=True, help="Directorio del run, nuevo o vacio.")
    p.add_argument("--split", required=True, choices=["desarrollo", "evaluacion"])
    p.add_argument("--ids", help="IDs de caso separados por coma.")
    p.add_argument("--repeticiones", type=int, help="Defecto: 1 desarrollo / 3 evaluacion.")
    p.add_argument("--max-resultados", type=int, default=3)
    p.add_argument("--max-context-tokens", type=int, default=20000)
    p.add_argument("--budget-usd", type=float, default=4.0)
    p.add_argument("--spent-before-usd", type=float, default=0.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--cleanup", action="store_true")
    a = p.parse_args()
    if a.repeticiones is not None and a.repeticiones < 1: sys.exit("--repeticiones debe ser >= 1")
    a.repeticiones = a.repeticiones or (1 if a.split == "desarrollo" else 3)
    a.ids = [s.strip() for s in a.ids.split(",") if s.strip()] if a.ids else None
    return a

def filtrar_casos(args):  # errores: IDs desconocidos, conjunto vacio, PDF de caso faltante
    casos = json.loads((CARPETA / "casos.json").read_text(encoding="utf-8"))["casos"]
    if args.ids and (d := sorted(set(args.ids) - {c.get("id") for c in casos})):
        sys.exit(f"IDs desconocidos en casos.json: {d}")
    sel = [c for c in casos if c.get("split") == args.split and (not args.ids or c.get("id") in args.ids)]
    if not sel: sys.exit("Conjunto de casos vacio tras filtrar por split/ids.")
    if not all((CARPETA / c["archivo_pdf"]).is_file() for c in sel): sys.exit("PDF de caso inexistente.")
    return sel

def preparar_contextos(args, casos, salida):  # instancia unica del adaptador; sin modelo; JSON por caso
    from adaptador_contexto import AdaptadorContexto
    ad, ctx, tiempos = AdaptadorContexto(), {}, {}
    for c in casos:
        t0 = time.perf_counter()
        ctx[c["id"]] = ad.preparar(c["consulta"], c["documento"], c["version"],
                                   args.max_context_tokens, args.max_resultados)
        tiempos[c["id"]] = round(time.perf_counter() - t0, 3)
        escribe_json(salida / f"{c['id']}.recuperacion.json", ctx[c["id"]])  # reutilizable por repeticion
    return ctx, tiempos

def crear_manifest(args, slots, casos, fuente_sha, salida):  # previo a llamadas; casos: solo ID+hash
    pdfs = {c["id"]: hashlib.sha256((CARPETA / c["archivo_pdf"]).read_bytes()).hexdigest() for c in casos}
    man = {
        "creado_utc": ahora(), "python": sys.version,
        "modelo": solicitudes.MODELO, "estado": "dry_run" if args.dry_run else "iniciado",
        "config": {"split": args.split, "ids": args.ids, "repeticiones": args.repeticiones,
                   "max_resultados": args.max_resultados, "max_context_tokens": args.max_context_tokens,
                   "budget_usd": args.budget_usd, "spent_before_usd": args.spent_before_usd, "dry_run": args.dry_run},
        "fuente": {"ruta": str(FUENTE), "url": solicitudes.FUENTE_URL, "sha256": fuente_sha,
                   "sha256_esperado": solicitudes.FUENTE_SHA},
        "hashes": {n: hashlib.sha256(Path(p).read_bytes()).hexdigest() for n, p in {
            "casos.json": CARPETA / "casos.json", "solicitudes.py": CARPETA / "solicitudes.py",
            "esquema_respuesta.json": CARPETA / "esquema_respuesta.json",
            "cliente_api.py": CARPETA / "cliente_api.py", "ejecutar.py": Path(__file__).resolve(),
            "adaptador_contexto.py": REPO / "experimentos" / "http-local" / "adaptador_contexto.py"}.items()},
        "casos": [{"id": c["id"], "pdf_sha256": pdfs[c["id"]]} for c in casos],  # sin gold; solo hashes/IDs
        "pdfs": pdfs,
        "slots": [{"id": s["id"], "brazo": s["brazo"], "caso_id": s["caso"]["id"],
                   "repeticion": s["repeticion"]} for s in slots],
        "preparacion": {},
    }
    escribe_json(salida / "manifest.json", man)
    return man

def main():
    args = parsear()
    salida = Path(args.salida)
    if not FUENTE.is_file() or hashlib.sha256(FUENTE.read_bytes()).hexdigest() != solicitudes.FUENTE_SHA:
        sys.exit(f"Fuente ausente o SHA-256 distinto de FUENTE_SHA: {FUENTE}")
    if args.cleanup:  # salta la validacion de carpeta nueva/vacia; la limpieza no toca archivos locales
        if not (salida / "manifest.json").is_file(): sys.exit("--cleanup requiere manifest.json de run previo.")
        cliente = ClienteAPI(salida)  # recarga recursos.json de ese run: borra solo IDs creados alli
        consumo = salida / "consumo.jsonl"
        filas = consumo.read_text(encoding="utf-8").strip().splitlines() if consumo.is_file() else []
        fila = json.loads(filas[-1]) if filas else {}
        escribe_json(salida / "cleanup.json", {"fecha_utc": ahora(), "limpieza": cliente.limpiar(), "coste_usd_run": fila.get("gastado_sesion"), "coste_usd_total": fila.get("gastado_total")})
        return
    if salida.exists() and any(salida.iterdir()): sys.exit("--salida debe ser un directorio nuevo o vacio.")
    salida.mkdir(parents=True, exist_ok=True)
    casos = filtrar_casos(args)
    slots = solicitudes.planificar(casos, args.repeticiones)
    pdfs = {c["id"]: (CARPETA / c["archivo_pdf"]).read_bytes() for c in casos}  # mismos PDF bytes por brazo
    man = crear_manifest(args, slots, casos, hashlib.sha256(FUENTE.read_bytes()).hexdigest(), salida)
    ctx, tiempos = preparar_contextos(args, casos, salida)  # mismo contexto para todas las repeticiones
    man["preparacion"] = {"segundos_total": round(sum(tiempos.values()), 3), "por_caso": tiempos,
                          "nota": "preparacion local sin modelo; no es entrada API observada"}
    escribe_json(salida / "manifest.json", man)
    if args.dry_run:  # sin red y sin cliente/clave; vector_id DRY_RUN; sin resultados inventados
        for s in slots:
            cuerpo = solicitudes.construir_solicitud(s["caso"], pdfs[s["caso"]["id"]], s["brazo"],
                                                     contexto=ctx[s["caso"]["id"]], vector_id="DRY_RUN")
            escribe_json(salida / f"{s['id']}.request.json", sanear(cuerpo))
        return
    cliente = ClienteAPI(salida, presupuesto_usd=args.budget_usd, gastado_previo=args.spent_before_usd)
    try:  # sin reintentos; el cliente guarda request saneada, response y consumo; errores sin clave
        vsid = cliente.crear_indice(FUENTE, {"documento": "DB-SUA-oficial", "version": "2022-06-14"})
        man["creados"] = {"vector_store_id": vsid}; escribe_json(salida / "manifest.json", man)
        for s in slots:
            cuerpo = solicitudes.construir_solicitud(s["caso"], pdfs[s["caso"]["id"]], s["brazo"],
                                                     contexto=ctx[s["caso"]["id"]], vector_id=vsid)
            print(f"{s['id']}: {cliente.respuesta(cuerpo, s['id']).get('status')}")  # solo ID/status
        man["estado"] = "completado"
    except Exception as e:  # tipo/mensaje sin secretos; estado parcial; re-eleva
        man["estado"], man["error"] = "parcial", {"tipo": type(e).__name__, "mensaje": str(e)}
        escribe_json(salida / "manifest.json", man)
        raise
    finally:
        escribe_json(salida / "cleanup.json", {"fecha_utc": ahora(), "limpieza": cliente.limpiar(),
                     "coste_usd_run": round(cliente.gastado_sesion, 6),
                     "coste_usd_total": round(cliente.gastado_previo + cliente.gastado_sesion, 6)})
    escribe_json(salida / "manifest.json", man)

if __name__ == "__main__": main()
