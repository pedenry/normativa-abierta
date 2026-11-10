"""Prueba de servicio_publico.Servidor.process_request_thread (plazo anti-slowloris).

Camino: threading.Timer.start lanza RuntimeError -> _interrumpir(request) y return,
sin invocar ThreadingHTTPServer.process_request_thread y con sem.release() una vez.
Evidencia: servicio_publico.py líneas 312-337. Sin sockets reales: solo mocks.
"""
import http.server
import socket
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import servicio_publico


class PlazoPublicoTest(unittest.TestCase):
    """Un único caso: fallo de arranque del Timer en process_request_thread."""

    def test_timer_start_runtime_error_interrumpe_y_libera_slot(self):
        timer = mock.Mock(name="Timer")
        timer.start.side_effect = RuntimeError("arranque simulado fallido")
        with mock.patch.object(
            http.server.ThreadingHTTPServer, "process_request_thread"
        ) as padre, mock.patch.object(
            threading, "Timer", return_value=timer
        ):
            servidor = servicio_publico.Servidor.__new__(servicio_publico.Servidor)
            servidor.sem = mock.Mock(name="sem")
            request = mock.Mock(name="request")
            cliente = ("127.0.0.1", 1)

            servicio_publico.Servidor.process_request_thread(
                servidor, request, cliente
            )

        padre.assert_not_called()
        timer.start.assert_called_once_with()
        timer.cancel.assert_not_called()
        request.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        request.close.assert_called_once_with()
        servidor.sem.release.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
