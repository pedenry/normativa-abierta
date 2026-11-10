# -*- coding: utf-8 -*-
"""Prueba unica de goteo (slowloris) sobre servicio_publico.Servidor.

Cliente 1 envia una cabecera incompleta a cuenta gotas; con TIMEOUT=0.25
el servidor debe cerrar la conexion y liberar el semaforo, de modo que un
segundo cliente completo reciba respuesta 200.
"""

import socket
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import servicio_publico as S

ERRORES_CORTE = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, formato, *args):
        pass


class TestGoteoPublico(unittest.TestCase):
    def test_goteo_cierra_y_libera_slot(self):
        sem = threading.BoundedSemaphore(1)
        with patch.object(S, 'TIMEOUT', 0.25):
            srv = S.Servidor(('127.0.0.1', 0), Handler, sem)
            hilo = threading.Thread(
                target=srv.serve_forever,
                kwargs={'poll_interval': 0.02},
                daemon=True,
            )
            hilo.start()
            cerrado = False
            try:
                with socket.create_connection(srv.server_address, timeout=1) as c1:
                    c1.sendall(b'GET / HTTP/1.0\r\nHost: x\r\nX:')
                    limite = time.monotonic() + 0.8
                    while time.monotonic() < limite:
                        try:
                            c1.sendall(b'x')
                        except ERRORES_CORTE:
                            cerrado = True
                            break
                        time.sleep(0.04)
                    if not cerrado:
                        try:
                            if c1.recv(1) == b'':
                                cerrado = True
                        except ERRORES_CORTE:
                            cerrado = True
                self.assertTrue(cerrado, 'el cliente goteante no fue cerrado')
                self.assertTrue(sem.acquire(timeout=1), 'slot del semaforo no liberado')
                sem.release()
                with socket.create_connection(srv.server_address, timeout=1) as c2:
                    c2.sendall(b'GET / HTTP/1.0\r\nHost: x\r\n\r\n')
                    respuesta = c2.recv(1024)
                self.assertIn(b'200', respuesta)
            finally:
                srv.shutdown()
                srv.server_close()
                hilo.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
