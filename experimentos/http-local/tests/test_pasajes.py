#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_pasajes.py — siete contratos semánticos de _operacion_consulta/_mejor_pasaje/_vista_puntuable.
Ejecutar con unittest desde la raíz del checkout; el motor se carga REAL con importlib bajo nombre
privado (como test_palabras_partidas.py), sin stubs compartidos, sin API ni corpus real. Los casos
son sintéticos, sin IDs, regiones, páginas ni pesos fijados: se comparan órdenes a cobertura de
raíces igual, sin alterar texto, citas ni hashes. Recuentos de texto aquí son proxy local, no
tokens de API.
"""
import hashlib, importlib.util, shutil, sys, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # experimentos/http-local


def _cargar_acceso_privado():
    """Carga acceso.py REAL con importlib sin dejar rastro en sys.modules."""
    spec = importlib.util.spec_from_file_location("_acc_priv_test_pasajes", RAIZ / "acceso.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.modules.pop(spec.name, None)
    return modulo


_ACC = _cargar_acceso_privado()

P_POS = "Ejemplo de prueba: el uso regulado queda conforme a esta regla sintética."


class PruebasPasajes(unittest.TestCase):
    """Contrato de operación de consulta y puntuación de pasajes."""

    def _cobertura_igual(self, palabras, pasajes):
        """Cobertura de raíces 1.0 en cada pasaje: aísla la señal del bonus."""
        roots = set(_ACC.tokenizar(palabras))
        for p in pasajes:
            self.assertEqual(_ACC.cobertura_roots(roots, p), 1.0)
        return roots

    def test_dicotomia_ambos_polos(self):
        """(1) a cobertura igual, el pasaje con ambos polos supera al solo positivo y al solo negativo (falla histórica resuelta)."""
        op = _ACC._operacion_consulta("Qué diferencia hay entre uso regulado y no regulado en el ejemplo")
        self.assertEqual(op["tipo"], "dicotomia")
        self.assertEqual(op["par"], _ACC.raiz(_ACC.norm("regulado")))
        self.assertGreaterEqual(len(op["par"]), 4)
        p_neg = "Ejemplo de prueba: el uso no regulado queda fuera de esta regla sintética."
        p_ambos = ("Ejemplo de prueba: el uso regulado queda conforme y el uso no regulado "
                   "queda fuera según esta regla sintética.")
        roots = self._cobertura_igual("uso regulado ejemplo", [P_POS, p_neg, p_ambos])
        s_pos, s_neg, s_ambos = (_ACC._mejor_pasaje(P_POS, roots, op),
                                 _ACC._mejor_pasaje(p_neg, roots, op),
                                 _ACC._mejor_pasaje(p_ambos, roots, op))
        self.assertGreater(s_pos, s_neg)
        self.assertGreater(s_ambos, s_pos)
        self.assertGreater(s_ambos, s_neg)

    def test_dicotomia_negacion_separada(self):
        """(1b) negación con salto o varios espacios no cuenta como polo positivo."""
        variantes = [
            ("Qué diferencia hay entre uso regulado y no\nregulado en el ejemplo",
             "Ejemplo de prueba: el uso\nno regulado queda fuera de esta regla."),
            ("Qué diferencia hay entre uso regulado y no   regulado en el ejemplo",
             "Ejemplo de prueba: el uso  no   regulado queda fuera de esta regla."),
        ]
        for cons, p_neg in variantes:
            with self.subTest(consulta=cons[:40]):
                op = _ACC._operacion_consulta(cons)
                self.assertEqual(op["tipo"], "dicotomia")
                roots = self._cobertura_igual("uso regulado ejemplo", [P_POS, p_neg])
                self.assertLess(_ACC._mejor_pasaje(p_neg, roots, op),
                                _ACC._mejor_pasaje(P_POS, roots, op))

    def test_maximo_minimo_polaridad(self):
        """(2) a igual cobertura gana el pasaje de la operación pedida; formas máximos/máximas/mínimos/mínimas."""
        p_max = "El ejemplo de prueba declara el máximo de reserva de suelo verde según esta regla sintética."
        p_min = "El ejemplo de prueba declara el mínimo de reserva de suelo verde según esta regla sintética."
        roots = self._cobertura_igual("reserva suelo verde", [p_max, p_min])
        casos = [("máximos", "maximo", "¿Cuáles son los máximos de reserva de suelo verde del ejemplo?"),
                 ("máximas", "maximo", "¿Cuáles son las máximas de reserva de suelo verde del ejemplo?"),
                 ("mínimos", "minimo", "¿Cuáles son los mínimos de reserva de suelo verde del ejemplo?"),
                 ("mínimas", "minimo", "¿Cuáles son las mínimas de reserva de suelo verde del ejemplo?")]
        for forma, tipo, cons in casos:
            with self.subTest(forma=forma):
                op = _ACC._operacion_consulta(cons)
                self.assertEqual(op["tipo"], tipo)
                bueno, malo = ((p_max, p_min) if tipo == "maximo" else (p_min, p_max))
                self.assertGreater(_ACC._mejor_pasaje(bueno, roots, op),
                                   _ACC._mejor_pasaje(malo, roots, op))

    def test_inicio_frente_a_transitoria(self):
        """(3) a igual cobertura la fórmula de inicio puntúa por encima del pasaje de transitoria."""
        op = _ACC._operacion_consulta("¿Cuándo se considera iniciado el procedimiento del ejemplo?")
        self.assertEqual(op["tipo"], "inicio")
        p_inicio = ("La fecha de inicio del procedimiento del ejemplo es la de la presentación "
                    "completa de la solicitud sintética.")
        p_trans = ("Los expedientes del procedimiento del ejemplo en trámite antes de la entrada "
                   "en vigor siguen su regla anterior.")
        roots = self._cobertura_igual("procedimiento ejemplo", [p_inicio, p_trans])
        self.assertGreater(_ACC._mejor_pasaje(p_inicio, roots, op),
                           _ACC._mejor_pasaje(p_trans, roots, op))

    def test_vista_puntuable_purga_y_conserva(self):
        """(4) purga líneas editoriales y el tramo que nombra al documento, conserva el
        contenido normativo y no altera el texto original ni su hash."""
        titulo = "Reglamento de ejemplo ficticio"
        texto = "\n".join([
            "Boletín Oficial del Estado número 99", titulo,
            "La reserva ficticia de suelo verde se regula en este ejemplo.",
            "El máximo de esta regla sintética es el declarado en el ejemplo.",
            "Legislación consolidada", "Texto consolidado",
            "Última modificación: 1 de enero de 2025", "Página 3", "3", "cve: ABC-123"])
        nv = _ACC.norm(_ACC._vista_puntuable(texto))
        self.assertIn("reserva ficticia de suelo verde", nv)
        for prohibido in ("boletín oficial", "legislación consolidada", "texto consolidado",
                          "última modificación", "página 3", "cve:"):
            self.assertNotIn(prohibido, nv)
        nv_t = _ACC.norm(_ACC._vista_puntuable(texto, titulo))
        self.assertNotIn(_ACC.norm(titulo), nv_t)
        self.assertIn("reserva ficticia de suelo verde", nv_t)
        copia = str(texto); _ACC._vista_puntuable(texto, titulo)
        self.assertEqual(texto, copia)
        tmp = Path(tempfile.mkdtemp(prefix="pasajes-vista-")) / "p0001.md"
        self.addCleanup(shutil.rmtree, str(tmp.parent), True)
        tmp.write_text(texto, encoding="utf-8", newline="\n")
        sha0 = hashlib.sha256(tmp.read_bytes()).hexdigest()
        _ACC._vista_puntuable(tmp.read_text(encoding="utf-8"), titulo)
        self.assertEqual(hashlib.sha256(tmp.read_bytes()).hexdigest(), sha0)

    def test_consulta_no_operativa_vacio(self):
        """(5) consulta sin operación o texto vacío: puntuación 0, sin error y determinista."""
        op_nula = _ACC._operacion_consulta("El ejemplo sintético describe plazos generales sin tope ni arranque.")
        self.assertIsNone(op_nula["tipo"])
        self.assertIsNone(_ACC._operacion_consulta("")["tipo"])
        op_max = _ACC._operacion_consulta("¿Cuál es el máximo del ejemplo?")
        roots = set(_ACC.tokenizar("ejemplo máximo"))
        pasaje = "El máximo del ejemplo sintético es el declarado aquí."
        self.assertEqual(_ACC._mejor_pasaje(pasaje, roots, op_nula), 0.0)
        self.assertEqual(_ACC._mejor_pasaje("", roots, op_max), 0.0)
        self.assertEqual(_ACC._mejor_pasaje(pasaje, set(), op_max), 0.0)
        self.assertEqual(_ACC._mejor_pasaje(pasaje, roots, op_max), _ACC._mejor_pasaje(pasaje, roots, op_max))

    def test_definicion_vinculada_supera_mencion(self):
        """(6) dicotomía con pedido de definición: el pasaje con predicado
        definitorio vinculado al X («integrado por») supera la mera
        coocurrencia en un preámbulo."""
        op = _ACC._operacion_consulta("Cuándo se considera un elemento aceptado y no aceptado")
        self.assertEqual(op["tipo"], "dicotomia")
        self.assertEqual(op["par"], _ACC.raiz(_ACC.norm("aceptado")))
        p_def = ("Aceptado, integrado por elementos verificados; no aceptado, "
                 "integrado por elementos pendientes.")
        p_mencion = "El preámbulo menciona aceptado y no aceptado en una explicación general."
        roots = self._cobertura_igual("aceptado", [p_def, p_mencion])
        self.assertGreater(_ACC._mejor_pasaje(p_def, roots, op),
                           _ACC._mejor_pasaje(p_mencion, roots, op))


if __name__ == "__main__":
    unittest.main()
