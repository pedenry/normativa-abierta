#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de regresión de seguridad del HTTP local, con casos sintéticos.

Sin corpus real, sin API y sin Internet: servidores efímeros en 127.0.0.1:0,
ESTADO mockeado y fixtures en un directorio temporal.
Ejecutar: python tests/test_seguridad_http.py (desde experimentos/http-local).
"""
import json
import shutil
import socket
import sys
import tempfile
import threading
import types
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
# Hermeticidad: http_consulta importa `acceso` a nivel de módulo; el handler
# sólo lo alcanza vía ESTADO["A"], que aquí siempre es un mock. El stub se
# instala sólo si `acceso` no está ya importado.
if "acceso" not in sys.modules:
    sys.modules["acceso"] = types.ModuleType("acceso")
import http_consulta as H  # noqa: E402
import servicio_publico as SP  # noqa: E402

SECRETO = "PRUEBA"  # dato ficticio de baja entropía; marcador de fuga


def _get(puerto, ruta, host=None, timeout=5):
    """GET HTTP/1.0 conservador a 127.0.0.1; devuelve (status, cuerpo)."""
    host = host if host is not None else "127.0.0.1:%d" % puerto
    peticion = "GET %s HTTP/1.0\r\nHost: %s\r\n\r\n" % (ruta, host)
    with socket.create_connection(("127.0.0.1", puerto), timeout=timeout) as s:
        s.sendall(peticion.encode("ascii"))
        bruto = b""
        while True:
            trozo = s.recv(65536)
            if not trozo:
                break
            bruto += trozo
    linea, _, resto = bruto.partition(b"\r\n")
    return int(linea.split()[1]), resto.partition(b"\r\n\r\n")[2]


class ServidorTemp:
    """Servidor efímero; shutdown + server_close garantizados al salir."""

    def __init__(self, handler):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.hilo = threading.Thread(target=self.srv.serve_forever,
                                     kwargs={"poll_interval": 0.05},
                                     daemon=True)

    def __enter__(self):
        self.hilo.start()
        return self

    def __exit__(self, *exc):
        try:
            self.srv.shutdown()
            self.srv.server_close()
        finally:
            self.hilo.join(timeout=5)

    @property
    def puerto(self):
        return self.srv.server_port


class PruebasSeguridadHttp(unittest.TestCase):
    """Un servidor y un ESTADO sintético por prueba; nada persiste."""

    def _estado(self, **extra):
        raiz = Path(tempfile.mkdtemp(prefix="seg-http-")).resolve()
        self.addCleanup(shutil.rmtree, raiz, True)
        a = mock.Mock()
        a.construir_busqueda.return_value = {}
        estado = {"A": a, "cont": raiz, "filas": [], "docs": {},
                  "encs": {}, "P": raiz}
        estado.update(extra)
        parche = mock.patch.dict(H.ESTADO, estado, clear=True)
        parche.start()
        self.addCleanup(parche.stop)
        return raiz, a

    def test_host_ajeno_403_y_host_local_ok(self):
        self._estado()
        with ServidorTemp(H.Handler) as s:
            self.assertEqual(
                _get(s.puerto, "/", host="ajeno.ejemplo.test")[0], 403)
            cod, cuerpo = _get(s.puerto, "/", host="127.0.0.1:%d" % s.puerto)
            self.assertEqual(cod, 200)
            self.assertIn(b"Normativa Abierta", cuerpo)

    def test_q_excesivo_400_sin_llamar_buscador(self):
        _, a = self._estado()
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _get(s.puerto, "/buscar?q=" + "x" * 2001)
            self.assertEqual(cod, 400)
            self.assertEqual(json.loads(cuerpo),
                             {"error": "consulta_demasiado_larga"})
            a.construir_busqueda.assert_not_called()
            cod, _ = _get(s.puerto, "/buscar?q=" + "x" * 2000)
            self.assertEqual(cod, 200)
            a.construir_busqueda.assert_called_once()

    def test_estatico_ocultos_traversal_y_publico(self):
        raiz, _ = self._estado()
        contenido = (raiz / "contenido").resolve()
        site = (raiz / "site").resolve()
        contenido.mkdir()
        site.mkdir()
        (contenido / "nota.md").write_text("texto publico", encoding="utf-8")
        for nombre, valor in (("CONT", contenido), ("SITE", site)):
            p = mock.patch.object(H, nombre, valor)
            p.start()
            self.addCleanup(p.stop)
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _get(s.puerto, "/estatico?path=contenido/nota.md")
            self.assertEqual(cod, 200)
            self.assertEqual(cuerpo, b"texto publico")
            for denegada in ("../secreto.txt", ".git/config", ".oculto.md",
                             "nota.xyz", "nota%5Cmd"):
                with self.subTest(ruta=denegada):
                    self.assertEqual(
                        _get(s.puerto, "/estatico?path=" + denegada)[0], 403)

    def test_docs_publicos_excluye_false_y_string_true(self):
        _, a = self._estado()
        docs = {"d-ok": ({"distribute": True}, None),
                "d-false": ({"distribute": False}, None),
                "d-texto": ({"distribute": "true"}, None)}
        a.cargar_indice.return_value = [{"documento": d} for d in docs]
        a.cargar_docs.return_value = docs
        filas, salida = H.docs_publicos("cont-ficticio")
        self.assertEqual(set(salida), {"d-ok"})
        self.assertEqual([f["documento"] for f in filas], ["d-ok"])

    def test_errores_genericos_sin_ruta_ni_secreto(self):
        raiz, a = self._estado(docs={"doc-demo": ({}, None)})
        fuga = "fallo en %s/%s.txt" % (raiz, SECRETO)
        a.construir_busqueda.side_effect = Exception(fuga)
        a.construir_lectura.side_effect = Exception(fuga)
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo_b = _get(s.puerto, "/buscar?q=prueba")
            self.assertEqual(cod, 500)
            self.assertEqual(json.loads(cuerpo_b), {"error": "fallo_busqueda"})
            cod, cuerpo_l = _get(s.puerto, "/leer?doc=doc-demo&page=1")
            self.assertEqual(cod, 500)
            self.assertEqual(json.loads(cuerpo_l), {"error": "fallo_lectura"})
            for cuerpo in (cuerpo_b, cuerpo_l):
                self.assertNotIn(SECRETO.encode("utf-8"), cuerpo)
                self.assertNotIn(str(raiz).encode("utf-8"), cuerpo)

    def test_handler_publico_host_externo_y_validaciones(self):
        self._estado()
        externo = "normativa.ejemplo.org"
        with ServidorTemp(SP.Handler) as s:
            cod, cuerpo = _get(s.puerto, "/", host=externo)
            self.assertEqual(cod, 200)
            self.assertIn(b"Normativa Abierta", cuerpo)
            cod, cuerpo = _get(s.puerto, "/buscar?q=prueba", host=externo)
            self.assertEqual(cod, 200)
            self.assertEqual(json.loads(cuerpo)["consulta"], "prueba")
            cod, cuerpo = _get(s.puerto, "/buscar?q=" + "x" * 401, host=externo)
            self.assertEqual(cod, 400)
            self.assertEqual(json.loads(cuerpo), {"error": "solicitud_invalida"})
            cod, cuerpo = _get(s.puerto, "/estatico?path=nota.md", host=externo)
            self.assertEqual(cod, 404)
            self.assertEqual(json.loads(cuerpo), {"error": "no_encontrado"})


if __name__ == "__main__":
    unittest.main()
