#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unittest del contrato HTTP de contexto (GET /contexto) y su
integración con /buscar, /leer y la puerta pública.

Encargo acotado (evaluación-normativa, 2026-11-16): SOLO este archivo; no se
toca producción, corpus, fixtures ni otros tests. El código se implementa en
paralelo: las aserciones expresan el CONTRATO OBJETIVO fijado en el encargo,
no el comportamiento actual (igual disciplina que test_aclaracion.py). Los
nombres de documentos son marcadores sintéticos de este test («doc-sint»,
«doc-sint-b», «doc-sin-municipio»); ninguno pertenece al corpus real.

Contrato fijado y verificado aquí:

 1. Ambos Handler (http_consulta.Handler y servicio_publico.Handler) aceptan
    GET /contexto con `q` requerido; `doc` y `version` opcionales; `version`
    requiere `doc`; `version_antes_de` es corte excluyente y estricto.
 2. ESTADO["adaptador"] es una instancia inyectada; el handler invoca
    preparar(q, documento, version, presupuesto_tokens=20000,
    max_resultados=2, propagar_errores=True). No se construye ningún
    adaptador por petición (inicialización singleton en main()).
 3. Respuesta raíz de /contexto (forma real cotejada, 2026-11-16): el estado
    del adaptador sin el campo `contenido` (ruta privada), con campos raíz
    estado/consulta/documento/version/texto_contexto/paginas/recuperacion/
    tokens_contexto/modo_tokens/limite_tokens/excedido/tiempo_ms/contenido y
    extras opcionales aclaracion/resolucion_ambito/versiones_disponibles;
    NO hay advertencias raíz ni presupuesto_tokens/max_resultados raíz.
    Cada página lleva doc/version/sha256/pagina/url_fuente/texto_sha256/
    etiqueta_impresa/archivo/motivo (sin «documento» ni «texto» en la
    página); cada resultado de recuperacion lleva documento/version/
    id_tecnico/apartado_id/ruta_oficial/titulo/puntuacion_bm25/paginas/
    etiquetas_impresas/hallada/cita (STRING)/paginas_entregadas/
    paginas_reutilizadas.
 4. Aclaración: HTTP 200, campos exactos y pregunta; cero páginas y cero
    resultados.
 5. Doc/version ausentes -> 404. Consultas/parámetros inválidos -> 400.
 6. Excepciones del adaptador, incluida SystemExit, -> 500 genérico sin
    rutas ni marcador privado.
 7. /buscar sin doc proyecta documentos/lecturas desde el adaptador,
    conserva consulta y advertencias (de recuperacion.advertencias), emite
    estado/aclaracion, con cero lecturas si falta lugar o si el municipio no
    está incorporado (el adaptador emite sin_resultados con páginas y
    resultados vacíos); la falta de municipio en la metadata NO elimina al
    documento nacional: con municipio=None SÍ genera lecturas; NO llama a
    construir_busqueda global.
 8. /buscar con doc+version sigue el flujo legado; /leer queda intacto.
 9. Público: /contexto en la allowlist; límites q<=400, target<=2048,
    duplicados y desconocidos -> 400, sólo GET, `prueba` 32 alfanumérico;
    enlaces con `prueba` y base externa; no modifica texto_contexto.

Interpretaciones registradas del contrato (para ajuste de rúbrica si la
implementación paralela decide otra cosa):
 (a) la validación de doc/version contra ESTADO["docs"] ocurre en el handler
     antes de llamar a preparar, como en las rutas legadas (/buscar, /leer);
 (b) el tercer argumento de preparar recibe la versión objetivo ya resuelta:
     el corte `version_antes_de` excluyente reduce a la única versión
     estrictamente anterior (una única versión disponible 2020-10-01 es
     alcanzable con antes_de=2020-10-02 y queda excluida con antes_de=2020-
     10-01, que responde 404 sin llamar al adaptador);
 (c) en la respuesta de /buscar sin doc se verifican los elementos con
     nombre fijado en el encargo (consulta, advertencias, estado,
     aclaración, cero lecturas en los casos indicados) y no una forma
     completa no fijada de «documentos»; las advertencias vienen de
     recuperacion.advertencias;
 (d) `resolucion_ambito` es el extra opcional que conserva el marcador del
     antiguo «ambito» ({"texto": "estatal"}): el cotejo fija su existencia,
     no su forma interna.

Infraestructura: servidores efímeros en 127.0.0.1:0 con ESTADO mockeado
(mock.Mock en "A" y "adaptador"), sin corpus real, sin OpenAI, sin red
externa y sin shell; sólo sockets efímeros dentro de unittest. No se
modifican límites (`MAX_CONSULTA`, `MAX_Q`, `MAX_TARGET`), tiempos ni
guardas; las constantes locales son espejos de sólo lectura.

Recuento y límites: no hay llamadas a API ni consumo de tokens (los
recuentos locales de texto serían proxies, y aquí ni siquiera se usan); no
existen pares comparables, así que no se calcula ahorro. Estos tests NO se
han ejecutado en este encargo (no se afirma ejecución). Previstos: 12
métodos de prueba; 19 casos van en subtest explícitos (3 en test_03, 6 en
test_05, 10 en test_10) y el resto son comprobaciones directas dentro de
cada método. El cotejo de la forma real (2026-11-16) no altera los
subtests; test_08 pasa de dos a tres bloques secuenciales por la guarda del
documento nacional. Pendiente de comprobación: rueda unittest con la
implementación paralela.
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
from types import SimpleNamespace
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
# Hermeticidad: http_consulta importa `acceso` a nivel de módulo; todos los
# usos del handler pasan por ESTADO["A"] y ESTADO["adaptador"], que aquí son
# mocks. El stub se instala sólo si `acceso` no está ya importado (misma
# disciplina que test_seguridad_http.py).
if "acceso" not in sys.modules:
    sys.modules["acceso"] = types.ModuleType("acceso")
import http_consulta as H  # noqa: E402
import servicio_publico as SP  # noqa: E402

SECRETO = "PRUEBA"  # dato ficticio de baja entropía; marcador de fuga
MAX_CONSULTA = 2000      # espejo del límite interno de /buscar (no se muta)
MAX_Q_PUBLICO = 400      # espejo del límite público declarado (no se muta)
DOC_A = "doc-sint"
DOC_B = "doc-sint-b"
DOC_SIN_MUNICIPIO = "doc-sin-municipio"


def _estado_ok(**extra):
    """Estado completo sintético con la forma real cotejada (2026-11-16).

    Campos raíz fijos del contrato; los extras opcionales (p. ej. aclaracion)
    se añaden por `extra`, y «resolucion_ambito» conserva el marcador del
    antiguo «ambito». No hay advertencias raíz ni presupuesto_tokens/
    max_resultados raíz: las advertencias viven en recuperacion.advertencias.
    Incluye «contenido» con un marcador de ruta privada: el contrato exige
    que esa clave desaparezca de la respuesta HTTP y que ninguna ruta o
    marcador privado se filtre en el cuerpo.
    """
    estado = {
        "estado": "ok",
        "consulta": "consulta sintetica de prueba",
        "documento": None,
        "version": "2020-10-01",
        "texto_contexto": "Texto literal sintetico de contexto áéíóú.",
        "paginas": [{
            "doc": DOC_A, "version": "2020-10-01",
            "sha256": "SHA-SINT-256", "pagina": 1,
            "url_fuente": "https://sint.ejemplo.test/fuente#p1",
            "texto_sha256": "SHA-TEXTO-SINT-256",
            "etiqueta_impresa": "pág. 1 sintética",
            "archivo": "doc-sint/p0001.md",
            "motivo": "consulta sintetica",
        }],
        "recuperacion": {
            "resultados": [{
                "documento": DOC_A, "version": "2020-10-01",
                "id_tecnico": "doc-sint#1.1", "apartado_id": "1.1",
                "ruta_oficial": "/doc-sint/1.1",
                "titulo": "Apartado 1.1 sintético",
                "puntuacion_bm25": 3.21, "paginas": [1],
                "etiquetas_impresas": ["pág. 1 sintética"],
                "hallada": True,
                "cita": "Cita literal sintetica 1.1.",
                "paginas_entregadas": 1, "paginas_reutilizadas": 0,
            }],
            "advertencias": ["aviso de recuperacion sintetico"],
        },
        "tokens_contexto": 42,
        "modo_tokens": "aproximado",
        "limite_tokens": 20000,
        "excedido": False,
        "tiempo_ms": 12,
        "resolucion_ambito": {"texto": "estatal"},
        "contenido": "RUTA-PRIVADA-MARCADOR\\doc-sint\\apartado\\p0001.md",
    }
    estado.update(extra)
    return estado


def _peticion(puerto, ruta, metodo="GET", host=None, timeout=5):
    """Petición HTTP/1.0 conservadora a 127.0.0.1; devuelve (status, cuerpo)."""
    host = host if host is not None else "127.0.0.1:%d" % puerto
    extra = "" if metodo == "GET" else "Content-Length: 0\r\n"
    peticion = "%s %s HTTP/1.0\r\nHost: %s\r\n%s\r\n" % (metodo, ruta, host,
                                                         extra)
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


class PruebasContextoHttp(unittest.TestCase):
    """Un servidor y un ESTADO sintético por prueba; nada persiste.

    El mock del adaptador captura cada llamada a preparar y devuelve el
    estado configurado; el mock de acceso (ESTADO["A"]) sirve para verificar
    que el flujo legado sigue intacto y que el flujo nuevo no lo invoca.
    """

    # ------------------------------------------------------------- fixtures

    def _estado(self, docs=None, estado_adaptador=None):
        """ESTADO sintético: adaptador mock en "adaptador", acceso mock en "A".

        Devuelve un SimpleNamespace con (a, ad, llamadas, raiz): el mock del
        adaptador consume los estados provisionados en orden y cae al estado
        por defecto si se agotan.
        """
        raiz = Path(tempfile.mkdtemp(prefix="ctx-http-")).resolve()
        self.addCleanup(shutil.rmtree, raiz, True)
        a = mock.Mock()
        a.construir_busqueda.return_value = {"resultados": [],
                                             "advertencias": []}
        a.construir_lectura.return_value = {}
        # Necesario sólo para la evidencia de `prueba` en el Handler público
        # (json.dumps): recuento local determinista, sin tiktoken ni API.
        a.contar = lambda *ar, **kw: 7
        ad = mock.Mock()
        llamadas = []
        estados = list(estado_adaptador or [])

        def capturar(consulta, *args, **kwargs):
            llamadas.append({"consulta": consulta, "args": args,
                             "kwargs": dict(kwargs)})
            if estados:
                return estados.pop(0)
            return _estado_ok()

        ad.preparar.side_effect = capturar
        docs = dict(docs or {
            DOC_A: ({"id": DOC_A, "version": "2020-10-01"}, None),
            DOC_B: ({"id": DOC_B, "version": "2019-05-05"}, None),
            DOC_SIN_MUNICIPIO: ({"id": DOC_SIN_MUNICIPIO, "municipio": None},
                                None),
        })
        estado = {"A": a, "adaptador": ad, "cont": raiz, "filas": [],
                  "docs": docs, "encs": {}, "P": raiz}
        parche = mock.patch.dict(H.ESTADO, estado, clear=True)
        parche.start()
        self.addCleanup(parche.stop)
        modulo_a = mock.patch.object(H, "A", a)
        modulo_a.start()
        self.addCleanup(modulo_a.stop)
        return SimpleNamespace(a=a, ad=ad, llamadas=llamadas, raiz=raiz)

    # ------------------------------------------------- helpers de contrato

    @staticmethod
    def _arg(llamada, indice, nombre, por_defecto=None):
        """Lee el argumento i-ésimo por posición o por nombre (firma flexible).

        El contrato fija preparar(q, documento, version, presupuesto_tokens,
        max_resultados, propagar_errores); el test acepta que el handler use
        posición o palabra clave, pero exige el valor fijado.
        """
        args = (llamada["consulta"], *llamada["args"])
        if len(args) > indice:
            return args[indice]
        return llamada["kwargs"].get(nombre, por_defecto)

    def _sin_privados(self, cuerpo, raiz):
        """Ninguna ruta privada ni marcador de fuga en el cuerpo.

        El marcador RUTA-PRIVADA-MARCADOR identifica el valor del campo
        privado `contenido`; «archivo» de las páginas es campo público
        cotejado y puede contener nombres de fichero legítimos.
        """
        self.assertNotIn(b"RUTA-PRIVADA-MARCADOR", cuerpo)
        self.assertNotIn(SECRETO.encode("utf-8"), cuerpo)
        self.assertNotIn(str(raiz).encode("utf-8"), cuerpo)

    # ------------------------------------------------------ /contexto raíz

    def test_01_contexto_raiz_preserva_estado_sin_contenido(self):
        """Contrato: /contexto 200 es el estado del adaptador sin «contenido»,
        con la forma raíz cotejada (sin advertencias ni límites raíz);
        cita STRING, campos de página y de resultado conservados; preparar
        recibe los límites fijados."""
        objetos = self._estado()
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/contexto?q=consulta%20prueba")
        self.assertEqual(cod, 200)
        self._sin_privados(cuerpo, objetos.raiz)
        resp = json.loads(cuerpo)
        # preservación exacta de los campos raíz fijados por el cotejo
        estado_ref = _estado_ok()
        self.assertEqual(resp["estado"], estado_ref["estado"])
        self.assertEqual(resp["consulta"], estado_ref["consulta"])
        self.assertEqual(resp["documento"], estado_ref["documento"])
        self.assertEqual(resp["version"], estado_ref["version"])
        self.assertEqual(resp["texto_contexto"], estado_ref["texto_contexto"])
        self.assertEqual(resp["paginas"], estado_ref["paginas"])
        self.assertEqual(resp["recuperacion"], estado_ref["recuperacion"])
        self.assertEqual(resp["tokens_contexto"], 42)
        self.assertEqual(resp["limite_tokens"], 20000)
        self.assertIsInstance(resp["modo_tokens"], str)
        self.assertIsInstance(resp["tiempo_ms"], int)
        self.assertIs(resp["excedido"], False)
        self.assertEqual(resp["resolucion_ambito"], {"texto": "estatal"})
        # tipos reales cotejados: página sin documento/texto; cita STRING
        pagina = resp["paginas"][0]
        self.assertEqual(pagina["doc"], DOC_A)
        self.assertEqual(pagina["sha256"], "SHA-SINT-256")
        self.assertEqual(pagina["pagina"], 1)
        for campo in ("version", "url_fuente", "texto_sha256",
                      "etiqueta_impresa", "archivo", "motivo"):
            self.assertIsInstance(pagina[campo], str, campo)
        self.assertNotIn("documento", pagina)
        self.assertNotIn("texto", pagina)
        resultado = resp["recuperacion"]["resultados"][0]
        self.assertEqual(resultado["documento"], DOC_A)
        self.assertEqual(resultado["apartado_id"], "1.1")
        self.assertIs(resultado["hallada"], True)
        self.assertIsInstance(resultado["cita"], str)
        self.assertEqual(resultado["cita"], "Cita literal sintetica 1.1.")
        # ausencias del cotejo: sin advertencias ni límites raíz
        self.assertNotIn("advertencias", resp)
        self.assertNotIn("presupuesto_tokens", resp)
        self.assertNotIn("max_resultados", resp)
        # ruta privada fuera de la respuesta y del cuerpo
        self.assertNotIn("contenido", resp)
        # llamada única al adaptador con los parámetros del contrato
        self.assertEqual(len(objetos.llamadas), 1)
        llamada = objetos.llamadas[0]
        self.assertEqual(llamada["consulta"], "consulta prueba")
        self.assertIsNone(self._arg(llamada, 1, "documento"))
        self.assertIsNone(self._arg(llamada, 2, "version"))
        self.assertEqual(self._arg(llamada, 3, "presupuesto_tokens"), 20000)
        self.assertEqual(self._arg(llamada, 4, "max_resultados"), 2)
        self.assertIs(self._arg(llamada, 5, "propagar_errores"), True)

    def test_02_contexto_aclaracion_200_campos_exactos(self):
        """Contrato: la aclaración del adaptador sale con HTTP 200, campos
        exactos y pregunta; cero páginas y cero resultados; sin «contenido»."""
        acl = {"pregunta": "¿En qué municipio se aplica?",
               "campos_requeridos": ["municipio"]}
        estado = _estado_ok(estado="aclaracion_necesaria", aclaracion=acl,
                            paginas=[],
                            recuperacion={"resultados": [],
                                          "advertencias": []})
        objetos = self._estado(estado_adaptador=[estado])
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/contexto?q=licencia%20obras")
        self.assertEqual(cod, 200)  # aclarar no es error HTTP
        self._sin_privados(cuerpo, objetos.raiz)
        resp = json.loads(cuerpo)
        self.assertEqual(resp["estado"], "aclaracion_necesaria")
        self.assertEqual(resp["aclaracion"], acl)  # campos exactos
        self.assertTrue(resp["aclaracion"]["pregunta"].strip())
        self.assertEqual(resp["aclaracion"]["campos_requeridos"],
                         ["municipio"])
        self.assertEqual(resp["paginas"], [])
        self.assertEqual(resp["recuperacion"]["resultados"], [])
        self.assertNotIn("contenido", resp)

    # -------------------------------------------- version / version_antes_de

    def test_03_contexto_version_y_corte_excluyente_estricto(self):
        """Contrato: `version` llega a preparar con la versión solicitada; el
        corte `version_antes_de` es EXCLUYENTE y estricto: con una única
        versión disponible 2020-10-01, antes_de=2020-10-02 resuelve esa
        versión, y antes_de=2020-10-01 la excluye (sin candidata -> 404; el
        adaptador no se invoca). Interpretación (b) del docstring."""
        objetos = self._estado()
        base = len(objetos.llamadas)
        with ServidorTemp(H.Handler) as s:
            casos = (
                ("/contexto?q=x&doc=%s&version=2020-10-01" % DOC_A,
                 200, "2020-10-01", "version exacta"),
                ("/contexto?q=x&doc=%s&version_antes_de=2020-10-02" % DOC_A,
                 200, "2020-10-01", "corte excluyente"),
                ("/contexto?q=x&doc=%s&version_antes_de=2020-10-01" % DOC_A,
                 404, None, "corte estricto sin candidata"),
            )
            for ruta, codigo, version_esp, rotulo in casos:
                with self.subTest(caso=rotulo):
                    cod, cuerpo = _peticion(s.puerto, ruta)
                    self.assertEqual(cod, codigo)
                    if version_esp is None:
                        self.assertIn("error", json.loads(cuerpo))
                        # el adaptador no fue invocado en el 404
                        self.assertEqual(len(objetos.llamadas), base)
                    else:
                        self.assertEqual(len(objetos.llamadas), base + 1)
                        base = len(objetos.llamadas)
                        self.assertEqual(
                            self._arg(objetos.llamadas[-1], 2, "version"),
                            version_esp)

    def test_04_contexto_404_doc_y_version_no_disponibles(self):
        """Contrato: doc ausente -> 404 sin llamar al adaptador; doc presente
        con version no disponible -> 404 sin llamar al adaptador."""
        objetos = self._estado()
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto,
                                    "/contexto?q=x&doc=doc-inexistente")
            self.assertEqual(cod, 404)
            self.assertIn("error", json.loads(cuerpo))
            cod, cuerpo = _peticion(
                s.puerto, "/contexto?q=x&doc=%s&version=1999-01-01" % DOC_A)
            self.assertEqual(cod, 404)
            self.assertIn("error", json.loads(cuerpo))
        objetos.ad.preparar.assert_not_called()

    def test_05_contexto_400_parametros_invalidos(self):
        """Contrato: consultas/parámetros inválidos -> 400 y cero llamadas al
        adaptador: q ausente, q vacía, q demasiado larga, version sin doc,
        version y version_antes_de combinados, fecha no ISO."""
        objetos = self._estado()
        casos = ("/contexto",
                 "/contexto?q=",
                 "/contexto?q=" + "x" * (MAX_CONSULTA + 1),
                 "/contexto?q=x&version=2020-10-01",
                 "/contexto?q=x&doc=%s&version=2020-10-01"
                 "&version_antes_de=2019-01-01" % DOC_A,
                 "/contexto?q=x&doc=%s&version=2020-13-99" % DOC_A)
        with ServidorTemp(H.Handler) as s:
            for ruta in casos:
                with self.subTest(ruta=ruta[:48]):
                    cod, cuerpo = _peticion(s.puerto, ruta)
                    self.assertEqual(cod, 400)
                    self.assertIn("error", json.loads(cuerpo))
        objetos.ad.preparar.assert_not_called()

    # --------------------------------------------------- errores genéricos

    def test_06_contexto_excepciones_500_genericas_sin_fuga(self):
        """Contrato: cualquier excepción del adaptador — incluida SystemExit —
        responde 500 genérico, sin rutas privadas ni detalles del fallo."""
        objetos = self._estado()
        fuga = "explotó en RUTA-PRIVADA-MARCADOR/%s" % SECRETO
        objetos.ad.preparar.side_effect = Exception(fuga)
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/contexto?q=x")
            self.assertEqual(cod, 500)
            self.assertIn("error", json.loads(cuerpo))
            self._sin_privados(cuerpo, objetos.raiz)
        objetos.ad.preparar.side_effect = SystemExit("SystemExit %s" % fuga)
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/contexto?q=x")
            self.assertEqual(cod, 500)
            self.assertIn("error", json.loads(cuerpo))
            self._sin_privados(cuerpo, objetos.raiz)

    # -------------------------------------------- /buscar sin doc (nuevo flujo)

    def test_07_buscar_sin_doc_proyecta_desde_adaptador(self):
        """Contrato: /buscar sin doc consulta el adaptador y proyecta
        documentos/lecturas; conserva la consulta y las advertencias (de
        recuperacion.advertencias); emite estado; no usa el buscador global
        (construir_busqueda)."""
        estado = _estado_ok(consulta="licencia de obras")
        objetos = self._estado(estado_adaptador=[estado])
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto,
                                    "/buscar?q=licencia%20de%20obras")
        self.assertEqual(cod, 200)
        resp = json.loads(cuerpo)
        self.assertEqual(resp["consulta"], "licencia de obras")
        self.assertEqual(resp["estado"], "ok")
        self.assertEqual(resp["advertencias"],
                         ["aviso de recuperacion sintetico"])
        self.assertIn("documentos", resp)
        self.assertIn(DOC_A, cuerpo.decode("utf-8"))
        objetos.a.construir_busqueda.assert_not_called()
        objetos.ad.preparar.assert_called_once()

    def test_08_buscar_sin_doc_cero_lecturas_aclaracion_y_sin_resultados(self):
        """Contrato: sin doc, con falta de lugar (aclaración) o con municipio
        no incorporado (el adaptador emite sin_resultados con páginas y
        resultados vacíos), /buscar responde 200 con cero lecturas; el
        buscador global no se invoca en ningún caso. Guarda: la falta de
        municipio en la metadata NO elimina al documento nacional — con
        municipio=None SÍ genera lecturas, coherentes con la página y el
        resultado."""
        # a) falta de lugar: el adaptador aclara; no hay lecturas ni resultados
        acl = {"pregunta": "¿En qué municipio?",
               "campos_requeridos": ["municipio"]}
        estado_a = _estado_ok(
            estado="aclaracion_necesaria", aclaracion=acl, paginas=[],
            recuperacion={"resultados": [], "advertencias": []})
        objetos_a = self._estado(
            docs={DOC_A: ({"id": DOC_A, "version": "2020-10-01"}, None)},
            estado_adaptador=[estado_a])
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/buscar?q=licencia%20obras")
        self.assertEqual(cod, 200)
        resp = json.loads(cuerpo)
        self.assertEqual(resp["estado"], "aclaracion_necesaria")
        self.assertEqual(resp["aclaracion"], acl)
        self.assertEqual(resp["lecturas"], [])
        objetos_a.a.construir_busqueda.assert_not_called()
        # b) municipio no incorporado: el ADAPTADOR (no la metadata) emite
        # sin_resultados con páginas y resultados vacíos; cero lecturas y
        # sin aclaración (no es un caso de falta de lugar)
        estado_b = _estado_ok(
            consulta="q", estado="sin_resultados", paginas=[],
            recuperacion={"resultados": [], "advertencias": []})
        objetos_b = self._estado(
            docs={DOC_SIN_MUNICIPIO: ({"id": DOC_SIN_MUNICIPIO,
                                       "municipio": None}, None)},
            estado_adaptador=[estado_b])
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/buscar?q=q")
        self.assertEqual(cod, 200)
        resp = json.loads(cuerpo)
        self.assertEqual(resp["estado"], "sin_resultados")
        self.assertNotIn("aclaracion", resp)
        self.assertEqual(resp["lecturas"], [])
        objetos_b.a.construir_busqueda.assert_not_called()
        # c) guarda: documento nacional (municipio=None en metadata) SÍ genera
        # lecturas; el doc de la página y del resultado es el mismo nacional
        estado_c = _estado_ok(consulta="q")
        estado_c["paginas"][0]["doc"] = DOC_SIN_MUNICIPIO
        estado_c["recuperacion"]["resultados"][0]["documento"] = \
            DOC_SIN_MUNICIPIO
        objetos_c = self._estado(
            docs={DOC_SIN_MUNICIPIO: ({"id": DOC_SIN_MUNICIPIO,
                                       "municipio": None}, None)},
            estado_adaptador=[estado_c])
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(s.puerto, "/buscar?q=q")
        self.assertEqual(cod, 200)
        resp = json.loads(cuerpo)
        self.assertEqual(resp["estado"], "ok")
        self.assertTrue(resp["lecturas"])
        self.assertIn("documentos", resp)
        self.assertIn(DOC_SIN_MUNICIPIO, cuerpo.decode("utf-8"))
        objetos_c.a.construir_busqueda.assert_not_called()

    # ------------------------------------------------------ legado intacto

    def test_09_buscar_doc_version_legado_y_leer_intactos(self):
        """Guarda: /buscar con doc+version sigue el flujo legado (construir_
        busqueda del módulo de acceso, filtro en la respuesta, el adaptador
        NO interviene); /leer responde igual que antes; el doc inexistente
        mantiene su 404 documentado."""
        resultado = {"documento": DOC_A, "version": "2020-10-01",
                     "sha256": "SHA-SINT-256", "pagina": 1, "paginas": [1],
                     "apartado_id": "1.1", "codigo": "SINT", "titulo": "D"}
        objetos = self._estado()
        objetos.a.construir_busqueda.return_value = {
            "resultados": [resultado], "advertencias": []}
        objetos.a.construir_lectura.return_value = {
            "pagina": {"pagina": 1, "texto": "Texto pagina sintetica",
                       "archivo": "doc-sint/pagina/p0001.md"},
            "documento": {"version": "2020-10-01", "sha256": "SHA-SINT-256",
                          "titulo": "D", "codigo": "SINT", "url":
                          "https://oficial.ejemplo/doc-sint"},
            "ambito": {"texto": "estatal"}}
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo = _peticion(
                s.puerto,
                "/buscar?q=x&doc=%s&version=2020-10-01" % DOC_A)
            self.assertEqual(cod, 200)
            resp = json.loads(cuerpo)
            self.assertEqual(resp["filtro"],
                             {"documento": DOC_A, "version": "2020-10-01"})
            self.assertEqual(resp["documentos"][0]["documento"], DOC_A)
            self.assertTrue(resp["lecturas"])
            objetos.a.construir_busqueda.assert_called_once()
            objetos.ad.preparar.assert_not_called()
            cod, cuerpo = _peticion(s.puerto,
                                    "/leer?doc=%s&page=1" % DOC_A)
            self.assertEqual(cod, 200)
            resp = json.loads(cuerpo)
            self.assertEqual(resp["documento"], DOC_A)
            self.assertEqual(resp["pagina"], 1)
            self.assertEqual(resp["texto"], "Texto pagina sintetica")
            objetos.ad.preparar.assert_not_called()
            # legado: doc inexistente sigue 404 con el error de siempre
            cod, cuerpo = _peticion(s.puerto,
                                    "/buscar?q=x&doc=doc-inexistente&version=2020-10-01")
            self.assertEqual(cod, 404)
            self.assertEqual(json.loads(cuerpo)["error"],
                             "documento_no_existe")

    # ------------------------------------------------------------ público

    def test_10_publico_contexto_allowlist_y_limites(self):
        """Público: /contexto en la allowlist con Host externo; límites fijados
        del encargo: q<=400, target<=2048 (414), duplicados y parámetros
        desconocidos -> 400, sólo GET, `prueba` alfanumérico de hasta 32."""
        self._estado()
        prueba32 = "a" * 32
        casos = (
            ("/contexto?q=x", 200, "ok"),
            ("/contexto?q=x&zz=1", 400, "solicitud_invalida"),
            ("/contexto?q=a&q=b", 400, "solicitud_invalida"),
            ("/contexto?q=" + "x" * (MAX_Q_PUBLICO + 1), 400,
             "solicitud_invalida"),
            ("/contexto?q=" + "x" * MAX_Q_PUBLICO, 200, "ok"),
            ("/contexto?q=" + "x" * 2049, 414, "uri_demasiado_larga"),
            ("/contexto?q=x&prueba=%s" % prueba32, 200, "ok"),
            ("/contexto?q=x&prueba=" + "a" * 33, 400, "solicitud_invalida"),
            ("/contexto?q=x&prueba=no-v%C3%A1lido!", 400,
             "solicitud_invalida"),
        )
        with ServidorTemp(SP.Handler) as s:
            for ruta, codigo, error in casos:
                with self.subTest(ruta=ruta[:40]):
                    cod, cuerpo = _peticion(s.puerto, ruta,
                                            host="externo.ejemplo.test")
                    self.assertEqual(cod, codigo)
                    if codigo != 200:
                        self.assertEqual(json.loads(cuerpo)["error"], error)
            cod, cuerpo = _peticion(s.puerto, "/contexto?q=x",
                                    metodo="POST",
                                    host="externo.ejemplo.test")
            self.assertEqual(cod, 405)
            self.assertEqual(json.loads(cuerpo)["error"],
                             "metodo_no_permitido")

    def test_11_publico_enlaces_prueba_base_externa_texto_intacto(self):
        """Público: con `prueba` y RENDER_EXTERNAL_URL, los href de lecturas
        del flujo legado llevan base externa y prueba; texto_contexto de
        /contexto pasa ÍNTEGRO (sin reescritura) con Host externo."""
        estado = _estado_ok()
        objetos = self._estado(estado_adaptador=[estado])
        resultado = {"documento": DOC_A, "version": "2020-10-01",
                     "sha256": "SHA-SINT-256", "pagina": 1, "paginas": [1],
                     "apartado_id": "1.1", "codigo": "SINT", "titulo": "D"}
        objetos.a.construir_busqueda.return_value = {
            "resultados": [resultado], "advertencias": []}
        con_env = mock.patch.dict(
            "os.environ", {"RENDER_EXTERNAL_URL":
                           "https://demo.onrender.com"})
        con_env.start()
        self.addCleanup(con_env.stop)
        with ServidorTemp(SP.Handler) as s:
            cod, cuerpo = _peticion(
                s.puerto, "/contexto?q=x&prueba=abc123",
                host="externo.ejemplo.test")
            self.assertEqual(cod, 200)
            resp = json.loads(cuerpo)
            self.assertEqual(resp["texto_contexto"],
                             estado["texto_contexto"])
            cod, cuerpo = _peticion(
                s.puerto,
                "/buscar?q=x&doc=%s&version=2020-10-01&prueba=abc123"
                % DOC_A, host="externo.ejemplo.test")
            self.assertEqual(cod, 200)
            lecs = json.loads(cuerpo)["lecturas"]
            self.assertTrue(lecs)
            self.assertEqual(
                lecs[0]["href"],
                "https://demo.onrender.com/leer?doc=%s&page=1&prueba=abc123"
                % DOC_A)

    # ------------------------------------------ sucesivas + singleton

    def test_12_dos_peticiones_sucesivas_sin_mezcla_y_singleton(self):
        """Dos /contexto sucesivas con filtros distintos: cada respuesta es
        exactamente el estado de SU llamada (sin mezcla de estado) y el
        adaptador es el mismo objeto inyectado (inicialización singleton en
        main; nada se reconstruye por petición)."""
        estado_a = _estado_ok(texto_contexto="TEXTO-A", consulta="primera",
                              documento=DOC_A,
                              contenido="PRIV-A-MARCADOR\\a.md")
        estado_b = _estado_ok(texto_contexto="TEXTO-B", consulta="segunda",
                              documento=DOC_B, version="2019-05-05",
                              contenido="PRIV-B-MARCADOR\\b.md")
        objetos = self._estado(estado_adaptador=[estado_a, estado_b])
        with ServidorTemp(H.Handler) as s:
            cod, cuerpo1 = _peticion(
                s.puerto,
                "/contexto?q=primera&doc=%s&version=2020-10-01" % DOC_A)
            self.assertEqual(cod, 200)
            cod, cuerpo2 = _peticion(
                s.puerto,
                "/contexto?q=segunda&doc=%s&version=2019-05-05" % DOC_B)
            self.assertEqual(cod, 200)
            resp1 = json.loads(cuerpo1)
            resp2 = json.loads(cuerpo2)
            self.assertEqual(resp1["texto_contexto"], "TEXTO-A")
            self.assertEqual(resp2["texto_contexto"], "TEXTO-B")
            self.assertNotIn("PRIV-A-MARCADOR".encode("utf-8"), cuerpo2)
            self.assertNotIn("PRIV-B-MARCADOR".encode("utf-8"), cuerpo1)
            # llamada 1: DOC_A + 2020-10-01; llamada 2: DOC_B + 2019-05-05
            l1, l2 = objetos.llamadas[0], objetos.llamadas[1]
            self.assertEqual(self._arg(l1, 1, "documento"), DOC_A)
            self.assertEqual(self._arg(l1, 2, "version"), "2020-10-01")
            self.assertEqual(self._arg(l2, 1, "documento"), DOC_B)
            self.assertEqual(self._arg(l2, 2, "version"), "2019-05-05")
            # singleton: el mismo objeto inyectado atiende ambas llamadas
            self.assertIs(objetos.ad, H.ESTADO["adaptador"])
            self.assertEqual(objetos.ad.preparar.call_count, 2)


if __name__ == "__main__":
    unittest.main()
