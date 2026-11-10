#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generador de fixtures PDF sintéticos del piloto SUA (evaluacion/piloto_sua).

Lee casos.json y genera, por caso, un PDF A4 de DOS páginas en archivo_pdf
(ruta relativa a esta carpeta). p1: memoria sintética (proyecto ficticio, uso,
ediciones solo como metadatos, alcance = consulta exacta ajustada a línea,
elemento de itinerario accesible y notas memoria_extra; sin cotas, umbrales ni
veredictos). p2: plano esquemático acotado (dibujo geométrico grande, cotas
identificadas >= 11 pt y mensaje de sin-escala: medir solo las cotas).

Determinismo: Canvas(invariant=1, pageCompression=1), fuentes base Helvetica
(acentos españoles compatibles), sin reloj ni aleatoriedad; metadatos
sintéticos sin valores de cota ni respuestas. No ejecutar aquí: Codex hará el
hook y la ejecución. Uso: python generar_fixtures.py [--casos RUTA] [--ids D01,E05]
"""
import argparse
import json
from pathlib import Path

from reportlab.lib.colors import Color, black
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

CARPETA = Path(__file__).resolve().parent
ANCHO, ALTO = A4
MARGEN = 40.0
X0, X1 = MARGEN, ANCHO - MARGEN
Y0, Y1 = MARGEN, ALTO - MARGEN
NEGRO = black
GRIS = Color(0.25, 0.32, 0.45)  # gris azulado
F, FB = "Helvetica", "Helvetica-Bold"
TAM_COTA = 11.0
EDICION_MEMORIA = "2026-05-20, revisión A (edición hipotética fijada)"

def _m(v):
    return f"{v:.2f}".replace(".", ",") + " m"

def _pct(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") + " %"

def _wrap(can, texto, fuente, tam, ancho):
    lineas, linea = [], ""
    for p in texto.split():
        t = (linea + " " + p).strip()
        if can.stringWidth(t, fuente, tam) <= ancho:
            linea = t
        else:
            if linea:
                lineas.append(linea)
            linea = p
    if linea:
        lineas.append(linea)
    return lineas

def _parrafo(can, texto, y, tam=10.5, fuente=F, x=None, color=NEGRO):
    x = X0 + 6 if x is None else x
    can.setFont(fuente, tam)
    can.setFillColor(color)
    for l in _wrap(can, texto, fuente, tam, X1 - X0 - 12):
        can.drawString(x, y, l)
        y -= tam * 1.45
    can.setFillColor(NEGRO)
    return y

def _etiqueta(can, texto, x, y, tam=9.5, color=GRIS):
    can.setFont(F, tam)
    can.setFillColor(color)
    can.drawString(x, y, texto)
    can.setFillColor(NEGRO)

def _marco(can, caso, pagina):
    can.setLineWidth(0.8)
    can.rect(X0, Y0, X1 - X0, Y1 - Y0)
    can.setFont(FB, 9.5)
    can.drawString(X0 + 6, Y1 - 16, "DOCUMENTO SINTÉTICO DE PRUEBA · NO CORRESPONDE A OBRA REAL · SIN VALIDEZ TÉCNICA")
    can.setFont(F, 9.5)
    can.setFillColor(GRIS)
    can.drawString(X0 + 6, Y0 + 8, "caso " + caso["id"] + " · página " + str(pagina) + " de 2")
    can.drawRightString(X1 - 6, Y0 + 8, "fixture sintético · piloto SUA")
    can.setFillColor(NEGRO)

def _tick(can, x, y):
    can.line(x - 4, y - 4, x + 4, y + 4)

def _cota_h(can, x1, x2, y, texto=None, y_txt=None):
    """Cota horizontal con trazos a 45°; texto centrado encima o en y_txt."""
    can.setLineWidth(0.7)
    can.line(x1, y, x2, y)
    _tick(can, x1, y)
    _tick(can, x2, y)
    if texto:
        can.setFont(F, TAM_COTA)
        w = can.stringWidth(texto, F, TAM_COTA)
        can.drawString((x1 + x2) / 2 - w / 2, (y_txt if y_txt is not None else y) + 5, texto)

def _cota_v(can, y1, y2, x, texto, lado=1):
    """Cota vertical con trazos a 45°; texto a la derecha (lado=1) o izquierda."""
    can.setLineWidth(0.7)
    can.line(x, y1, x, y2)
    _tick(can, x, y1)
    _tick(can, x, y2)
    can.setFont(F, TAM_COTA)
    w = can.stringWidth(texto, F, TAM_COTA)
    can.drawString(x + 5 if lado > 0 else x - 5 - w, (y1 + y2) / 2 - TAM_COTA / 2, texto)

def _muro(can, tramos, grosor=2.4):
    can.setLineWidth(grosor)
    for (x1, y1), (x2, y2) in tramos:
        can.line(x1, y1, x2, y2)
    can.setLineWidth(0.7)

def _plano_pasillo(can, d):
    cy, a, b, h = 430.0, 150.0, 470.0, 70.0
    yb, yt = cy - h, cy + h
    _muro(can, [((a, yt), (b, yt)), ((a, yb), (b, yb))])
    _cota_v(can, yb, yt, a + 60, "anchura libre de paso: " + _m(d["anchura_libre_m"]))
    _cota_h(can, a, b, yb - 26, "longitud: " + _m(d["longitud_m"]))
    _etiqueta(can, "planta del pasillo (esquema)", a, yt + 14)

def _plano_puerta(can, d):
    cy, a, b = 420.0, 130.0, 470.0
    xj1, xj2 = 260.0, 350.0
    _muro(can, [((a, cy), (xj1, cy)), ((xj2, cy), (b, cy))])
    _tick(can, xj1, cy)
    _tick(can, xj2, cy)
    can.setLineWidth(1.8)
    can.line(xj1, cy, xj1, cy + 90)  # hoja única abierta 90 grados hacia arriba
    can.setLineWidth(0.7)
    can.arc(xj1 - 90, cy - 90, xj1 + 90, cy + 90, 0, 90)  # giro de la hoja
    _etiqueta(can, "1 hoja", xj1 - 70, cy + 66)
    _cota_h(can, xj1, xj2, cy - 28, "hueco en marco: " + _m(d["ancho_marco_m"]))
    _cota_h(can, xj1, xj2, cy - 58, "anchura libre de paso a máxima apertura: " + _m(d["ancho_libre_efectivo_m"]))

def _plano_estrechamiento(can, d):
    cy, a, b, h, hn = 430.0, 120.0, 510.0, 70.0, 44.0
    xe1, xe2, xp1, xp2 = 290.0, 330.0, 430.0, 495.0
    yb, yt, ybn, ytn = cy - h, cy + h, cy - hn, cy + hn
    _muro(can, [
        ((a, yt), (xe1, yt)), ((xe1, yt), (xe1, ytn)), ((xe1, ytn), (xe2, ytn)),
        ((xe2, ytn), (xe2, yt)), ((xe2, yt), (b, yt)),
        ((a, yb), (xp1, yb)), ((xp2, yb), (b, yb)),
    ])
    _tick(can, xp1, yb)
    _tick(can, xp2, yb)
    can.setLineWidth(1.8)
    can.line(xp1, yb, xp1, yb - 65)  # hoja de la puerta abierta hacia abajo
    can.setLineWidth(0.7)
    can.arc(xp1 - 65, yb - 65, xp1 + 65, yb + 65, 270, 90)
    can.line(xe1, yt, xe1, yt + 30)
    can.line(xe2, yt, xe2, yt + 30)
    can.line(xe2, yb, xe2, yb - 30)
    _cota_v(can, yb, yt, 160.0, "anchura general: " + _m(d["anchura_general_m"]))
    _cota_v(can, yb, ytn, (xe1 + xe2) / 2, "ancho estrechamiento: " + _m(d["estrechamiento"]["anchura_m"]))
    _cota_h(can, xe1, xe2, yt + 26, "longitud estrechamiento: " + _m(d["estrechamiento"]["longitud_m"]))
    _etiqueta(can, "estrechamiento puntual", xe1 - 10, yt + 8)
    _etiqueta(can, "hueco de paso", xp1 + 4, yb + 10)
    if d.get("separacion_cota_ilegible") or d.get("separacion_al_hueco_m") is None:
        _cota_h(can, xe2, xp1, yb - 24)  # cota sin valor; mancha de tinta en el original
        cx = (xe2 + xp1) / 2
        can.setFillColor(NEGRO)
        can.ellipse(cx - 95, yb - 40, cx + 95, yb - 26, stroke=0, fill=1)
        can.ellipse(cx - 55, yb - 42, cx + 45, yb - 28, stroke=0, fill=1)
        can.setFillColor(NEGRO)
    else:
        _cota_h(can, xe2, xp1, yb - 24, "separación al hueco de paso: " + _m(d["separacion_al_hueco_m"]), y_txt=yb - 44)

def _plano_rampa(can, d):
    ax, bx, yb = 110.0, 340.0, 400.0
    can.setLineWidth(2.4)
    can.line(ax, yb, bx, yb)
    can.line(ax, yb, bx, yb + 48)  # alzado esquemático, sin escala
    can.setLineWidth(0.7)
    _cota_h(can, ax, bx, yb - 26, "longitud en planta: " + _m(d["longitud_m"]))
    pl = d.get("pendiente_longitudinal_pct")
    if pl is None:
        _etiqueta(can, "sin cota en el original", ax + 8, yb + 58)
    else:
        can.setFont(F, TAM_COTA)
        can.drawString(ax + 8, yb + 58, "pendiente longitudinal: " + _pct(pl))
    _etiqueta(can, "alzado (esquema)", ax, yb + 92)
    sx1, sx2, sy = 370.0, 500.0, 470.0
    _etiqueta(can, "sección transversal (esquema)", sx1, sy + 40)
    can.setLineWidth(2.4)
    can.line(sx1, sy, sx2, sy + 10)
    can.setLineWidth(0.7)
    pt = d.get("pendiente_transversal_pct")
    if pt is None:
        _etiqueta(can, "sin cota en el original", sx1, sy - 18)
    else:
        can.setFont(F, TAM_COTA)
        can.drawString(sx1, sy - 18, "pendiente transversal: " + _pct(pt))

def _pie_plano(can, caso):
    d = caso["datos_plano"]
    can.setLineWidth(0.5)
    can.line(X0 + 6, Y0 + 124, X1 - 6, Y0 + 124)
    y = Y0 + 110
    for nota in d.get("notas_plano", []):
        y = _parrafo(can, "Nota: " + nota, y, tam=9.5)
    if caso["tipo"] == "pasillo_con_estrechamiento":
        y = _parrafo(can, "Nota: trazado recto, sin cambios de dirección; el hueco dibujado es la única abertura cercana del pasillo.", y, tam=9.5)
    y = _parrafo(can, "Unidades: cotas en metros (m); pendientes en porcentaje (%).", y, tam=9.5)
    y = _parrafo(can, "Plano esquemático sin escala: no medir sobre el dibujo; solo valen las cotas anotadas.", y, tam=9.5)
    _parrafo(can, "Documento sintético de prueba; no corresponde a obra real ni certifica conformidad alguna.", y, tam=9.5)

def pagina_plano(can, caso):
    d = caso["datos_plano"]
    _marco(can, caso, 2)
    _parrafo(can, "PLANO ESQUEMÁTICO ACOTADO · SIN ESCALA", Y1 - 44, tam=12.5, fuente=FB)
    _parrafo(can, d["elemento"] + " · uso del edificio: " + caso["uso"], Y1 - 62, tam=9.5, color=GRIS)
    tipo = caso["tipo"]
    if tipo == "pasillo_recto":
        _plano_pasillo(can, d)
    elif tipo == "puerta_una_hoja":
        _plano_puerta(can, d)
    elif tipo == "rampa_recta":
        _plano_rampa(can, d)
    elif tipo == "pasillo_con_estrechamiento":
        _plano_estrechamiento(can, d)
    _pie_plano(can, caso)

def pagina_memoria(can, caso):
    d = caso["datos_plano"]
    _marco(can, caso, 1)
    y = Y1 - 46
    y = _parrafo(can, caso["titulo"], y, tam=13, fuente=FB) - 8
    y = _parrafo(can, "Proyecto ficticio para pruebas; no corresponde a obra real.", y, tam=10) - 6
    y = _parrafo(can, "Uso del edificio: " + caso["uso"] + ".", y)
    y = _parrafo(can, "Edición normativa solicitada para la consulta: " + caso["version"] + ".", y)
    y = _parrafo(can, "Edición de esta memoria: " + EDICION_MEMORIA + ".", y) - 6
    y = _parrafo(can, "Elemento consultado (itinerario accesible): " + d["elemento"] + ".", y)
    for extra in d.get("memoria_extra", []):
        y = _parrafo(can, extra, y)
    y -= 8
    y = _parrafo(can, "Alcance de la consulta (texto íntegro):", y, fuente=FB) - 2
    y = _parrafo(can, caso["consulta"], y) - 10
    y = _parrafo(can, "Esta memoria no contiene medidas ni valores de cumplimiento: las cotas del proyecto constan solo en el plano esquemático de la página 2, que no está a escala; las medidas no deben inferirse del dibujo, solo de las cotas anotadas.", y, tam=9.5)
    _parrafo(can, "No se certifica el conjunto del edificio ni la conformidad reglamentaria global, y no se afirma la vigencia de ninguna edición normativa.", y, tam=9.5)

def _generar(caso):
    ruta = CARPETA / caso["archivo_pdf"]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    can = Canvas(str(ruta), pagesize=A4, invariant=1, pageCompression=1)
    can.setTitle("Fixture sintético " + caso["id"] + " - piloto SUA")
    can.setAuthor("normativa-abierta · fixtures sintéticos")
    can.setSubject("Documento sintético de prueba; no corresponde a obra real")
    can.setCreator("generar_fixtures.py (reportlab, invariant=1)")
    pagina_memoria(can, caso)
    can.showPage()
    pagina_plano(can, caso)
    can.showPage()
    can.save()
    return ruta

def main():
    ap = argparse.ArgumentParser(description="Genera los fixtures PDF sintéticos del piloto SUA.")
    ap.add_argument("--casos", default=str(CARPETA / "casos.json"), help="ruta alternativa a casos.json")
    ap.add_argument("--ids", default="", help="ids separados por comas; por defecto, todos")
    args = ap.parse_args()
    datos = json.loads(Path(args.casos).read_text(encoding="utf-8"))
    todos = {c["id"] for c in datos["casos"]}
    pedidos = [s.strip() for s in args.ids.split(",") if s.strip()] or sorted(todos)
    faltan = [s for s in pedidos if s not in todos]
    if faltan:
        raise SystemExit("ids no presentes en casos.json: " + ", ".join(faltan))
    for caso in datos["casos"]:
        if caso["id"] in pedidos:
            print("generado", _generar(caso).relative_to(CARPETA))

if __name__ == "__main__":
    main()
