"""Cliente OpenAI API (solo stdlib) para el piloto SUA.

Clave unicamente por OPENAI_API_KEY (nunca se registra ni persiste). Sin
reintentos: un reintento automatico podria duplicar coste en /responses.
"""
from __future__ import annotations

import hashlib, json, os, time, urllib.error, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.openai.com/v1"
TIMEOUT_S, POLL_MAX_S, POLL_SLEEP_S, RESERVA_USD = 180, 120, 2, 0.50
PRECIOS = {"input": 0.75, "cache": 0.075, "output": 4.50}  # USD por millon de tokens
COSTE_FILE_SEARCH = 0.0025  # USD por llamada file_search


class ClienteAPI:
    def __init__(self, carpeta_salida: Path, presupuesto_usd: float = 4.0, gastado_previo: float = 0.0):
        self.carpeta = Path(carpeta_salida)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.presupuesto, self.gastado_previo = float(presupuesto_usd), float(gastado_previo)
        self.gastado_sesion = 0.0
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY ausente en el entorno; no se acepta ni persiste por archivo.")
        self.ruta_recursos = self.carpeta / "recursos.json"
        self.ruta_log = self.carpeta / "api_llamadas.jsonl"
        self.ruta_consumo = self.carpeta / "consumo.jsonl"
        self.recursos: dict = self._leer_recursos()

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        """Peticion JSON; errores HTTP se guardan depurados y se elevan; sin reintentos."""
        datos = json.dumps(body).encode("utf-8") if body is not None else None
        extra = {"Content-Type": "application/json"} if datos is not None else {}
        req = urllib.request.Request(
            BASE + path, data=datos, method=method,
            headers={"Authorization": f"Bearer {self.key}", **extra})  # cabeceras jamas en logs
        return self._enviar(req, f"{method} {path}")

    def _upload_multipart(self, campo: str, nombre: str, datos: bytes, campos: dict[str, str]) -> dict:
        """Helper multipart de bytes; devuelve el JSON de /files."""
        limite = "----pilotosua" + uuid.uuid4().hex
        partes: list[bytes] = [
            f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
            for k, v in campos.items()]
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{campo}"; filename="{nombre}"\r\n'
                      'Content-Type: application/octet-stream\r\n\r\n'.encode("utf-8") + datos + b"\r\n")
        partes.append(f"--{limite}--\r\n".encode("utf-8"))
        req = urllib.request.Request(
            BASE + "/files", data=b"".join(partes), method="POST",
            headers={"Authorization": f"Bearer {self.key}",
                     "Content-Type": f"multipart/form-data; boundary={limite}"})
        return self._enviar(req, "POST /files (multipart)")

    def _enviar(self, req: urllib.request.Request, endpoint: str) -> dict:
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                crudo, estado, rid = r.read(), r.status, r.headers.get("x-request-id", "")
        except urllib.error.HTTPError as e:
            self._guardar_error(endpoint, e.code, (e.headers or {}).get("x-request-id", ""), e.read())
            raise
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            self._log(endpoint, None, None, "", fallo=type(e).__name__)  # timeout/red: sin reintento
            raise
        self._log(endpoint, estado, time.monotonic() - t0, rid)
        return json.loads(crudo) if crudo else {}

    def _guardar_error(self, endpoint: str, status: int, rid: str, cuerpo: bytes) -> None:
        texto = cuerpo.decode("utf-8", "replace").replace(self.key, "[REDACTADO]")
        (self.carpeta / f"error_http_{status}_{int(time.time())}.json").write_text(json.dumps(
            {"endpoint": endpoint, "status": status, "request_id": rid, "cuerpo": texto},
            ensure_ascii=False, indent=2), encoding="utf-8")
        self._log(endpoint, status, None, rid, fallo="http_error")

    def _log(self, endpoint: str, status: int | None, dur: float | None, rid: str, **extra) -> None:
        fila = {"ts": datetime.now(timezone.utc).isoformat(), "endpoint": endpoint, "status": status,
                "s": round(dur, 3) if dur is not None else None, "request_id": rid} | extra
        with self.ruta_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")  # solo metadata, sin cuerpos ni base64

    def _leer_recursos(self) -> dict:
        return json.loads(self.ruta_recursos.read_text(encoding="utf-8")) \
            if self.ruta_recursos.exists() else {"vector_stores": {}, "files": {}}

    def _guardar_recursos(self) -> None:
        self.ruta_recursos.write_text(json.dumps(self.recursos, ensure_ascii=False, indent=2), encoding="utf-8")

    def _registrar_recurso(self, tipo: str, rid: str, meta: dict) -> None:
        self.recursos.setdefault(tipo, {})[rid] = {
            **meta, "estado": "creado", "ts": datetime.now(timezone.utc).isoformat()}
        self._guardar_recursos()  # inmediato, antes de pasos dependientes

    def crear_indice(self, pdf: Path, atributos: dict) -> str:
        """Sube el PDF (purpose assistants), crea el vector store e indexa; devuelve su id."""
        datos = Path(pdf).read_bytes()
        sub = self._upload_multipart("file", Path(pdf).name, datos, {"purpose": "assistants"})
        self._registrar_recurso("files", sub["id"], {"origen": Path(pdf).name, "purpose": "assistants"})
        vs = self.request("POST", "/vector_stores", {
            "name": "normativa-sua-piloto",
            "expires_after": {"anchor": "last_active_at", "days": 1}})
        self._registrar_recurso("vector_stores", vs["id"], {"nombre": "normativa-sua-piloto"})
        self.request("POST", f"/vector_stores/{vs['id']}/files", {
            "file_id": sub["id"], "attributes": atributos,
            "chunking_strategy": {"type": "static",
                                  "static": {"max_chunk_size_tokens": 800, "chunk_overlap_tokens": 400}}})
        t0 = time.monotonic()
        while time.monotonic() - t0 < POLL_MAX_S:
            vf = self.request("GET", f"/vector_stores/{vs['id']}/files/{sub['id']}")
            if vf.get("status") == "completed":
                return vs["id"]
            if vf.get("status") in ("failed", "errored", "cancelled", "expired"):
                raise RuntimeError(f"Indexado termino en {vf.get('status')} ({vs['id']}): {vf.get('last_error')}")
            time.sleep(POLL_SLEEP_S)
        raise TimeoutError(f"Indexado sin completar en {POLL_MAX_S}s: {vs['id']}")

    def respuesta(self, body: dict, run_id: str) -> dict:
        """POST /responses en un intento; guarda peticion saneada, respuesta y consumo."""
        run_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(run_id))
        (self.carpeta / f"{run_id}.request.json").write_text(
            json.dumps(self._sanear(body), ensure_ascii=False, indent=2), encoding="utf-8")
        pendiente = RESERVA_USD + self.gastado_previo + self.gastado_sesion
        if pendiente > self.presupuesto:
            raise RuntimeError(f"Presupuesto: reserva+gastado {pendiente:.2f} USD > {self.presupuesto:.2f} USD")
        self._log("POST /responses", None, None, run_id, fase="antes",
                  gastado_total=round(self.gastado_previo + self.gastado_sesion, 6))
        t0 = time.monotonic()
        resp = self.request("POST", "/responses", body)  # incomplete/failed no se reintenta
        (self.carpeta / f"{run_id}.response.json").write_text(
            json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        if not resp.get("usage"):
            self._log("POST /responses", resp.get("status"), time.monotonic() - t0, run_id,
                      fase="despues", fallo="usage_ausente")
            raise RuntimeError(f"Respuesta sin usage (uso desconocido); respuesta guardada: {run_id}")
        coste = self._contabilizar(run_id, resp, time.monotonic() - t0)
        self._log("POST /responses", resp.get("status"), time.monotonic() - t0, run_id, fase="despues",
                  coste_usd=round(coste, 6), gastado_total=round(self.gastado_previo + self.gastado_sesion, 6))
        return resp

    def _sanear(self, nodo):
        """Copia profunda: input_file.file_data -> sha256/longitud (sin base64 en disco)."""
        if isinstance(nodo, dict):
            if "file_data" in nodo:
                d = str(nodo["file_data"])
                return {**nodo, "file_data": {"sha256": hashlib.sha256(d.encode()).hexdigest(), "longitud": len(d)}}
            return {k: self._sanear(v) for k, v in nodo.items()}
        if isinstance(nodo, list):
            return [self._sanear(v) for v in nodo]
        return nodo

    def _contabilizar(self, run_id: str, resp: dict, elapsed: float) -> float:
        u = resp["usage"]
        ent, sal = int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0))
        cache = int((u.get("input_tokens_details") or {}).get("cached_tokens", 0))
        razon = int((u.get("output_tokens_details") or {}).get("reasoning_tokens", 0))
        llamadas = sum(1 for o in resp.get("output", [])
                       if isinstance(o, dict) and o.get("type") == "file_search_call")
        coste = ((ent - cache) * PRECIOS["input"] + cache * PRECIOS["cache"] + sal * PRECIOS["output"]) / 1e6 \
            + llamadas * COSTE_FILE_SEARCH
        self.gastado_sesion += coste
        fila = {"ts": datetime.now(timezone.utc).isoformat(), "run_id": run_id, "status": resp.get("status"),
                "usage": {"input": ent, "output": sal, "total_observado": u.get("total_tokens"),
                          "total_input_mas_output": ent + sal, "cache": cache, "reasoning": razon,
                          "nota": "cache subset de input y reasoning de output; no se cobran dos veces"},
                "file_search_calls": llamadas, "coste_usd": round(coste, 6),
                "gastado_sesion": round(self.gastado_sesion, 6),
                "gastado_total": round(self.gastado_previo + self.gastado_sesion, 6),
                "elapsed_s": round(elapsed, 3),
                "ambito": "solo /responses; tokens de upload/indexado desconocidos (no se anotan como 0)"}
        with self.ruta_consumo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
        return coste

    def limpiar(self) -> dict:
        """DELETE solo IDs de recursos.json; estado por ID; sigue si uno falla; logs intactos."""
        resultado: dict[str, str] = {}
        for tipo in ("vector_stores", "files"):
            for rid, meta in list(self.recursos.get(tipo, {}).items()):
                if meta.get("estado") == "borrado":
                    resultado[rid] = "ya_borrado"
                    continue
                try:
                    self.request("DELETE", f"/{tipo}/{rid}")
                    self.recursos[tipo][rid]["estado"] = "borrado"
                    resultado[rid] = "borrado"
                except Exception as e:
                    self.recursos[tipo][rid]["estado"] = f"error_borrado:{type(e).__name__}"
                    resultado[rid] = f"error:{type(e).__name__}"
                finally:
                    self._guardar_recursos()
        return resultado

    def __enter__(self) -> "ClienteAPI":
        return self

    def __exit__(self, *exc) -> bool:
        return False  # limpieza explicita: el runner raiz llama limpiar() en finally
