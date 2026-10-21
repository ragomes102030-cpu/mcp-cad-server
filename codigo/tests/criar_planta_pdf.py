# -*- coding: utf-8 -*-
"""Cria uma planta baixa DENTRO do AutoCAD (via COM) e plota o PDF.

Fluxo: novo desenho -> camadas padrao -> paredes/aberturas/cotas/textos ->
zoom extents -> PlotToFile -> PDF. Nada de `load`, nada de dialogo modal.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.com_backend import ComBackend  # noqa: E402
from cad_mcp.layers import LAYER_STANDARD  # noqa: E402

TMP = Path(r"C:/temp/mcp_cad_com")
ENTREGA = Path(r"C:\Users\Correta Engenharia\mcp-cad-server\saida")
ENTREGA.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------- geometria (m)
T = 0.15          # espessura da parede
MT = T / 2.0

# eixos das paredes: (x1, y1, x2, y2)
PAREDES_EIXOS = [
    (0.0, 0.0, 8.0, 0.0),      # frente
    (8.0, 0.0, 8.0, 6.0),      # direita
    (8.0, 6.0, 0.0, 6.0),      # fundo
    (0.0, 6.0, 0.0, 0.0),      # esquerda
    (4.10, 0.0, 4.10, 6.0),    # divisoria vertical principal
    (4.10, 3.30, 8.0, 3.30),   # divisoria horizontal (quarto/cozinha+banho)
    (6.05, 0.0, 6.05, 3.30),   # divisoria vertical (cozinha/banheiro)
]

# ambientes: (nome, x1, y1, x2, y2)  -> medidas LIVRES (entre faces internas)
AMBIENTES = [
    ("SALA",     0.075, 0.075, 4.025, 5.925),
    ("QUARTO",   4.175, 3.375, 7.925, 5.925),
    ("COZINHA",  4.175, 0.075, 5.975, 3.225),
    ("BANHEIRO", 6.125, 0.075, 7.925, 3.225),
]

# portas: (x, y, angulo_graus, largura)  -> arco de 90 graus + folha
PORTAS = [
    (4.10, 1.20, 0.0, 0.80),    # cozinha/banheiro -> sala
    (4.10, 4.60, 180.0, 0.80),  # quarto -> sala
    (0.0, 2.00, 0.0, 0.90),     # entrada
]

# janelas: (x1, y1, x2, y2)
JANELAS = [
    (1.20, 0.0, 2.20, 0.0),
    (5.20, 6.0, 6.40, 6.0),
    (8.0, 4.40, 8.0, 5.40),
]

TERRENO = (-1.50, -1.50, 9.50, 7.50)


def f(v) -> str:
    """Formata numero para LISP (sem notacao cientifica)."""
    return ("%.4f" % float(v)).rstrip("0").rstrip(".")


def retangulo(x1, y1, x2, y2, camada) -> str:
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    cons = "".join(" (cons 10 (list %s %s))" % (f(p[0]), f(p[1])) for p in pts)
    return (
        '(list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
        ' (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1)%s)' % (camada, cons)
    )


def faixa_parede(x1, y1, x2, y2, camada="PAREDES") -> str:
    """Transforma o eixo da parede na faixa retangular (espessura T)."""
    if abs(y2 - y1) < 1e-9:  # horizontal
        return retangulo(min(x1, x2), y1 - MT, max(x1, x2), y1 + MT, camada)
    if abs(x2 - x1) < 1e-9:  # vertical
        return retangulo(x1 - MT, min(y1, y2), x1 + MT, max(y1, y2), camada)
    return retangulo(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), camada)


class Planta:
    def __init__(self, b: ComBackend):
        self.b = b
        self.handles: list[str] = []
        self.erros: list[str] = []

    def expr(self, corpo: str) -> str:
        h = self.b._eval('(progn (entmakex %s) (cdr (assoc 5 (entget (entlast)))))' % corpo)
        if isinstance(h, str):
            self.handles.append(h)
        else:
            self.erros.append("entmakex sem handle: %s" % str(corpo)[:60])
        return h

    def poly(self, x1, y1, x2, y2, camada):
        return self.expr(retangulo(x1, y1, x2, y2, camada))

    def linha(self, x1, y1, x2, y2, camada):
        return self.expr(
            '(list (cons 0 "LINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbLine") (cons 10 (list %s %s 0.0)) (cons 11 (list %s %s 0.0)))'
            % (camada, f(x1), f(y1), f(x2), f(y2))
        )

    def arco(self, cx, cy, r, a1, a2, camada):
        return self.expr(
            '(list (cons 0 "ARC") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbCircle") (cons 10 (list %s %s 0.0)) (cons 40 %s)'
            ' (cons 100 "AcDbArc") (cons 50 %s) (cons 51 %s))'
            % (camada, f(cx), f(cy), f(r), f(a1), f(a2))
        )

    def texto(self, x, y, txt, h, camada="TEXTOS", centro=False):
        extra = " (cons 72 1) (cons 11 (list %s %s 0.0)) (cons 73 2)" % (f(x), f(y)) if centro else ""
        return self.expr(
            '(list (cons 0 "TEXT") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbText") (cons 10 (list %s %s 0.0)) (cons 40 %s) (cons 1 "%s")%s)'
            % (camada, f(x), f(y), f(h), txt, extra)
        )

    def cota_h(self, x1, x2, y, ytexto=None):
        return self.b._eval(
            '(progn (setvar "CMDECHO" 0) (setvar "OSMODE" 0)'
            ' (command "_.DIMLINEAR" "_non" (list %s %s 0.0) "_non" (list %s %s 0.0)'
            ' "_non" (list %s %s 0.0)) (cdr (assoc 5 (entget (entlast)))))'
            % (f(x1), f(y), f(x2), f(y), f((x1 + x2) / 2.0), f(ytexto if ytexto is not None else y - 0.80))
        )

    def cota_v(self, x, y1, y2, xtexto=None):
        return self.b._eval(
            '(progn (setvar "CMDECHO" 0) (setvar "OSMODE" 0)'
            ' (command "_.DIMLINEAR" "_non" (list %s %s 0.0) "_non" (list %s %s 0.0)'
            ' "_non" (list %s %s 0.0)) (cdr (assoc 5 (entget (entlast)))))'
            % (f(x), f(y1), f(x), f(y2), f(xtexto if xtexto is not None else x - 0.80), f((y1 + y2) / 2.0))
        )


async def main() -> int:
    b = ComBackend()
    print("1) conectando no AutoCAD...")
    r = await b.initialize()
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    if not r.ok:
        return 1

    print("2) novo desenho...")
    r = await b.drawing_create()
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    if not r.ok:
        return 1

    print("3) configurando desenho novo (unidades = metros)...")
    r = await b.drawing_setup(unidades=6, escala_cota=1.0)
    print("   ok=%s erro=%s" % (r.ok, r.error))
    print("   camadas padrao...")
    for nome, (cor, lt) in LAYER_STANDARD.items():
        rr = await b.layer_create(nome, cor, lt)
        if not rr.ok:
            print("   camada %s: %s" % (nome, rr.error))
    await b.layer_set_current("PAREDES")

    p = Planta(b)
    print("4) desenhando...")

    # terreno
    p.poly(TERRENO[0], TERRENO[1], TERRENO[2], TERRENO[3], "TERRENO")

    # paredes
    for (x1, y1, x2, y2) in PAREDES_EIXOS:
        p.expr(faixa_parede(x1, y1, x2, y2))

    # ambientes: nome + area
    areas = {}
    for (nome, x1, y1, x2, y2) in AMBIENTES:
        a = (x2 - x1) * (y2 - y1)
        areas[nome] = a
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        p.texto(cx, cy + 0.12, nome, 0.22, "TEXTOS", centro=True)
        p.texto(cx, cy - 0.22, "%.2f m2" % a, 0.16, "TEXTOS", centro=True)

    # portas: folha + arco de 90 graus
    for (px, py, ang, larg) in PORTAS:
        p.arco(px, py, larg, ang, ang + 90.0, "PORTAS")
        import math

        rad = math.radians(ang)
        p.linha(px, py, px + larg * math.cos(rad), py + larg * math.sin(rad), "PORTAS")

    # janelas: duas linhas paralelas ao longo da parede
    for (x1, y1, x2, y2) in JANELAS:
        if abs(y2 - y1) < 1e-9:
            p.linha(x1, y1 - MT / 2, x2, y2 - MT / 2, "JANELAS")
            p.linha(x1, y1 + MT / 2, x2, y2 + MT / 2, "JANELAS")
        else:
            p.linha(x1 - MT / 2, y1, x2 - MT / 2, y2, "JANELAS")
            p.linha(x1 + MT / 2, y1, x2 + MT / 2, y2, "JANELAS")

    # cotas gerais
    await b.layer_set_current("COTAS")
    await b.execute_lisp(
        '(progn (setvar "DIMSCALE" 1.0) (setvar "DIMTXT" 0.18) (setvar "DIMASZ" 0.15)'
        ' (setvar "DIMEXO" 0.05) (setvar "DIMEXE" 0.10) (setvar "DIMGAP" 0.05)'
        ' (setvar "DIMTIH" 0) (setvar "DIMTOH" 0) T)'
    )
    p.cota_h(0.0, 8.0, 0.0, -1.00)          # largura total
    p.cota_v(0.0, 0.0, 6.0, -1.00)          # altura total
    p.cota_h(0.0, 4.10, 6.0, 6.85)          # sala x quarto
    p.cota_v(8.0, 0.0, 3.30, 9.10)          # cozinha/banheiro x quarto

    # selo / resumo
    await b.layer_set_current("TEXTOS")
    tot = sum(areas.values())
    y0 = -2.80
    p.texto(0.0, y0, "PLANTA BAIXA - RESIDENCIA UNIFAMILIAR", 0.30)
    p.texto(0.0, y0 - 0.45, "Escala 1:50  |  Cotas em metros  |  Area util total: %.2f m2" % tot, 0.18)
    p.texto(0.0, y0 - 0.80, "SALA %.2f  |  QUARTO %.2f  |  COZINHA %.2f  |  BANHEIRO %.2f m2"
            % (areas["SALA"], areas["QUARTO"], areas["COZINHA"], areas["BANHEIRO"]), 0.18)
    p.texto(0.0, y0 - 1.15, "Terreno: 11.00 x 9.00 m = 99.00 m2  |  Paredes: %.2f m (eixo)"
            % sum(abs(((x2 - x1) + (y2 - y1))) for (x1, y1, x2, y2) in PAREDES_EIXOS), 0.18)
    p.texto(0.0, y0 - 1.50, "Gerado por mcp-cad-server + AutoCAD 2025 (COM) em %s" % time.strftime("%d/%m/%Y %H:%M"), 0.15)

    print("   entidades criadas: %d  erros: %d" % (len(p.handles), len(p.erros)))
    for e in p.erros[:5]:
        print("     ! %s" % e)

    print("5) zoom extents / regen...")
    await b.zoom_extents()
    await b.execute_lisp('(progn (command "_.REGENALL") T)')

    print("6) contagem de entidades e camadas...")
    r = await b.entity_count()
    print("   entidades no ModelSpace: %s" % r.payload)
    r = await b.layer_list()
    print("   camadas: %s" % ", ".join(c["nome"] for c in (r.payload or [])))

    print("7) salvando DWG...")
    dwg = TMP / "planta_mcp.dwg"
    r = await b.drawing_save(str(dwg))
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    if dwg.exists():
        shutil.copy2(dwg, ENTREGA / dwg.name)
        print("   copiado -> %s (%.1f KB)" % (ENTREGA / dwg.name, dwg.stat().st_size / 1024.0))

    print("7b) exportando DXF (accoreconsole headless)...")
    dxf = ENTREGA / "planta_mcp.dxf"
    r = await b.drawing_save_as_dxf(str(dxf))
    info = dict(r.payload) if r.ok else {"erro": r.error}
    info.pop("saida", None)
    print("   %s" % json.dumps(info, ensure_ascii=False))

    print("8) plotando PDF...")
    pdf = ENTREGA / "planta_mcp.pdf"
    r = await b.drawing_plot_pdf(str(pdf))
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    if r.ok and pdf.exists():
        print("   PDF OK: %s (%.1f KB)" % (pdf, pdf.stat().st_size / 1024.0))
    else:
        print("   PDF NAO gerado")

    print("9) screenshot da tela do AutoCAD...")
    r = await b.get_screenshot()
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))

    print("\nresumo: %s" % json.dumps(areas, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
