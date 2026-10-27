# -*- coding: utf-8 -*-
"""Renderizador genérico de planta baixa para um AutoCAD vivo (backend COM).

A geometria é DADO: um dicionário "modelo" com terreno, paredes, ambientes,
portas, janelas, móveis, cotas e selo. Trocar de planta não exige mexer no
motor — só descrever outro modelo.

Convenções (as mesmas do resto do pacote):
  - unidades em METROS, `INSUNITS=6`;
  - paredes descritas pelo EIXO e transformadas em faixa de espessura `t`;
  - portas: (x, y, ângulo_graus, largura) -> arco de 90° + folha;
  - cotas via `DIMLINEAR` (horizontal quando y1==y2, vertical quando x1==x2);
  - a entidade é sempre identificada pelo HANDLE do AutoCAD.

Formato do modelo:
    {
      "titulo": str, "espessura_parede": 0.15,
      "terreno": (x1, y1, x2, y2),
      "paredes": [(x1, y1, x2, y2), ...],                      # eixos
      "ambientes": [{"nome", "x1", "y1", "x2", "y2", "h": 0.26}, ...],
      "portas":   [(x, y, ang, largura), ...],
      "janelas":  [(x1, y1, x2, y2), ...],
      "moveis":   [(x1, y1, x2, y2), ...],
      "cotas_h":  [(x1, x2, y, y_texto), ...],
      "cotas_v":  [(x, y1, y2, x_texto), ...],
      "selo":     [(x, y, texto, altura), ...],
      "camadas_ativas": {"paredes": "PAREDES", ...}            # opcional
    }
"""
from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP
from .areas import decimal_area
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from .layers import LAYER_STANDARD  # noqa: E402

__all__ = [
    "cons_poligono", "cons_linha", "cons_arco", "cons_texto", "cons_faixa_parede",
    "wall_boundary_segments", "Desenho", "desenhar_modelo", "areas_do_modelo", "num_br",
]


# ----------------------------------------------------------------- primitivas
def _fprec(v, casas: int = 4) -> str:
    """Numero -> literal LISP (sem notacao cientifica, sem zeros a toa)."""
    return ("%.*f" % (casas, float(v))).rstrip("0").rstrip(".") or "0"


def _f(v) -> str:
    """Numero -> literal LISP (sem notacao cientifica, sem zeros a toa)."""
    return _fprec(v, 4)


def _rad(graus: float) -> str:
    """Graus -> literal LISP em RADIANOS.

    ATENCAO: no AutoLISP os grupos de angulo (50/51) de `entmake`/`entget` estao
    em RADIANOS, nao em graus. Passar graus gira o arco (90 -> 116,62).
    Ver `tests/probe_arco4.py`.
    """
    return _fprec(math.radians(graus), 9)


def num_br(v: float, casas: int = 2) -> str:
    """Formata numero no padrao brasileiro (virgula decimal)."""
    value=Decimal(str(v)).quantize(Decimal(1).scaleb(-casas),rounding=ROUND_HALF_UP)
    return format(value,'.%df' % casas).replace('.',',')


def cons_poligono(x1, y1, x2, y2, camada: str = "0", fechado: bool = True) -> str:
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    c10 = "".join(" (cons 10 (list %s %s))" % (_f(p[0]), _f(p[1])) for p in pts)
    return (
        '(list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
        ' (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 %d)%s)'
        % (camada, 1 if fechado else 0, c10)
    )


def cons_linha(x1, y1, x2, y2, camada: str = "0") -> str:
    return (
        '(list (cons 0 "LINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
        ' (cons 100 "AcDbLine") (cons 10 (list %s %s 0.0)) (cons 11 (list %s %s 0.0)))'
        % (camada, _f(x1), _f(y1), _f(x2), _f(y2))
    )


def cons_arco(cx, cy, r, a1, a2, camada: str = "0") -> str:
    return (
        '(list (cons 0 "ARC") (cons 100 "AcDbEntity") (cons 8 "%s")'
        ' (cons 100 "AcDbCircle") (cons 10 (list %s %s 0.0)) (cons 40 %s)'
        ' (cons 100 "AcDbArc") (cons 50 %s) (cons 51 %s))'
        % (camada, _f(cx), _f(cy), _f(r), _rad(a1), _rad(a2))
    )


def cons_texto(x, y, txt, h, camada: str = "TEXTOS", centro: bool = False, angulo: float = 0.0) -> str:
    extra = (
        ' (cons 72 1) (cons 11 (list %s %s 0.0)) (cons 73 2)' % (_f(x), _f(y)) if centro else ""
    )
    return (
        '(list (cons 0 "TEXT") (cons 100 "AcDbEntity") (cons 8 "%s")'
        ' (cons 100 "AcDbText") (cons 10 (list %s %s 0.0)) (cons 40 %s)'
        ' (cons 1 "%s") (cons 50 %s)%s)'
        % (camada, _f(x), _f(y), _f(h), txt, _rad(angulo), extra)
    )


def cons_faixa_parede(x1, y1, x2, y2, t: float = 0.15, camada: str = "PAREDES") -> str:
    """Eixo da parede -> faixa retangular de espessura t."""
    mt = t / 2.0
    if abs(y2 - y1) < 1e-9:  # horizontal
        return cons_poligono(min(x1, x2), y1 - mt, max(x1, x2), y1 + mt, camada)
    if abs(x2 - x1) < 1e-9:  # vertical
        return cons_poligono(x1 - mt, min(y1, y2), x1 + mt, max(y1, y2), camada)
    return cons_poligono(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), camada)


def wall_boundary_segments(walls, t: float = 0.15) -> list[tuple[float, float, float, float]]:
    """Converte eixos cortados em faces/cabeceiras sem sobrepor retângulos.

    Os trechos de eixo já vêm separados nos vãos. Cada trecho vira duas linhas
    paralelas e só recebe cabeceira quando a ponta não encontra outra parede.
    Assim, portas e janelas continuam sendo vãos reais, e os encontros L/T não
    acumulam polilinhas retangulares umas sobre as outras.
    """
    segs = [tuple(float(v) for v in p) for p in walls]
    half = float(t) / 2.0
    eps = 1e-7

    def on_segment(x, y, s):
        x1, y1, x2, y2 = s
        if abs(y2 - y1) < eps:
            return abs(y - y1) < eps and min(x1, x2) - eps <= x <= max(x1, x2) + eps
        if abs(x2 - x1) < eps:
            return abs(x - x1) < eps and min(y1, y2) - eps <= y <= max(y1, y2) + eps
        return False

    def connected(x, y, current):
        for other in segs:
            if other == current:
                continue
            if on_segment(x, y, other):
                return True
        return False

    out = []

    def add(a, b):
        key = tuple(round(v, 8) for v in (*a, *b))
        rev = tuple(round(v, 8) for v in (*b, *a))
        keys = {tuple(round(v, 8) for v in (*p, *q)) for p, q in out}
        if key not in keys and rev not in keys:
            out.append((a, b))

    for s in segs:
        x1, y1, x2, y2 = s
        if abs(y2 - y1) < eps:
            lo, hi = sorted((x1, x2))
            add((lo, y1 - half), (hi, y1 - half))
            add((lo, y1 + half), (hi, y1 + half))
            if not connected(lo, y1, s):
                add((lo, y1 - half), (lo, y1 + half))
            if not connected(hi, y1, s):
                add((hi, y1 - half), (hi, y1 + half))
        elif abs(x2 - x1) < eps:
            lo, hi = sorted((y1, y2))
            add((x1 - half, lo), (x1 - half, hi))
            add((x1 + half, lo), (x1 + half, hi))
            if not connected(x1, lo, s):
                add((x1 - half, lo), (x1 + half, lo))
            if not connected(x1, hi, s):
                add((x1 - half, hi), (x1 + half, hi))
        else:
            raise ValueError("parede diagonal não suportada: %r" % (s,))
    return out


# ------------------------------------------------------------------ desenhista
class Desenho:
    def __init__(self, backend, log=None):
        self.b = backend
        self.log = log or (lambda *_a, **_k: None)
        self.handles: list[str] = []
        self.erros: list[str] = []

    async def _ent(self, corpo: str):
        r = await self.b.entmakex(corpo)
        if not r.ok:
            self.erros.append(str(r.error)[:140])
            return None
        h = r.payload
        if isinstance(h, str):
            self.handles.append(h)
        elif isinstance(h, list) and h:
            self.handles.append(str(h[0]))
        return h

    async def poligono(self, x1, y1, x2, y2, camada="0"):
        return await self._ent(cons_poligono(x1, y1, x2, y2, camada))

    async def linha(self, x1, y1, x2, y2, camada="0"):
        return await self._ent(cons_linha(x1, y1, x2, y2, camada))

    async def arco(self, cx, cy, r, a1, a2, camada="0"):
        return await self._ent(cons_arco(cx, cy, r, a1, a2, camada))

    async def texto(self, x, y, txt, h=0.24, camada="TEXTOS", centro=False):
        return await self._ent(cons_texto(x, y, txt, h, camada, centro))

    async def cota_h(self, x1, x2, y, y_texto=None):
        dy = y_texto if y_texto is not None else y - 0.85
        r = await self.b.create_dimension_linear(x1, y, x2, y, (x1 + x2) / 2.0, dy)
        if not r.ok:
            self.erros.append("cota_h(%s-%s): %s" % (x1, x2, str(r.error)[:90]))
        elif isinstance(r.payload, str):
            self.handles.append(r.payload)
        return r

    async def cota_v(self, x, y1, y2, x_texto=None):
        dx = x_texto if x_texto is not None else x - 0.85
        r = await self.b.create_dimension_linear(x, y1, x, y2, dx, (y1 + y2) / 2.0)
        if not r.ok:
            self.erros.append("cota_v(%s-%s): %s" % (y1, y2, str(r.error)[:90]))
        elif isinstance(r.payload, str):
            self.handles.append(r.payload)
        return r


# -------------------------------------------------------------------- modelo
def areas_do_modelo(modelo: dict) -> dict:
    out = {}
    for a in modelo.get("ambientes", []):
        out[a["nome"]] = float(decimal_area(a))
    return out


async def desenhar_modelo(b, modelo: dict, log=None,
                          validar: bool = True,
                          seguir_com_erros: bool = False) -> dict:
    """Desenha o modelo inteiro no desenho ativo do AutoCAD. Devolve um resumo.

    Antes de qualquer chamada COM, o modelo passa por `validar_modelo.validar`
    (~1 ms). Com erro e sem `seguir_com_erros`, NADA e desenhado: devolve
    {"valido": False, "erros_validacao": [...]}. Isso evita gastar um ciclo
    AutoCAD -> DXF -> PDF para descobrir um vao de porta que falta.
    """
    diga = log or (lambda *_a, **_k: None)
    if modelo.get("paredes_arquitetonicas"):
        # paredes com aberturas hospedadas: o vao e o que sobra do corte
        from .arch import expandir
        modelo = expandir(modelo)
        diga("arquitetura: %s" % modelo.get("_arquitetura"))
    v = None
    if validar:
        from .validar_modelo import validar as _validar
        v = _validar(modelo)
        if v["erros"]:
            diga("validacao: %d erro(s), %d aviso(s)" % (len(v["erros"]), len(v["avisos"])))
            for p in v["erros"]:
                diga("  ERRO %s -- %s: %s" % (p["chave"], p["onde"], p["detalhe"]))
            if not seguir_com_erros:
                diga("nada foi desenhado (use seguir_com_erros=True para forcar)")
                return {"valido": False, "validacao": v,
                        "erros_validacao": v["erros"], "entidades_criadas": 0,
                        "erros": [], "areas": {}, "area_util": 0.0, "handles": []}
        for p in v["avisos"]:
            diga("  aviso %s -- %s: %s" % (p["chave"], p["onde"], p["detalhe"]))

    d = Desenho(b, log=diga)
    t = float(modelo.get("espessura_parede", 0.15))

    diga("linetypes...")
    # O LTYPE tem de existir ANTES de criar a camada: `layer_create` recusa a
    # camada se o tipo de linha nao esta na tabela, e o desenho sai sem linha
    # de centro/tracejada (medido em 21/10/2026: EIXOS e PROJECAO falharam por
    # CENTER e DASHED nao estarem carregados).
    for _nome, (_cor, lt) in LAYER_STANDARD.items():
        if lt and lt.upper() != "CONTINUOUS":
            rl = await b.layer_linetype_load(lt)
            if not rl.ok:
                diga("  linetype %s: %s" % (lt, rl.error))

    diga("camadas padrao...")
    for nome, (cor, lt) in LAYER_STANDARD.items():
        r = await b.layer_create(nome, cor, lt)
        if not r.ok:
            diga("  camada %s: %s" % (nome, r.error))

    diga("parametros de desenho/cota...")
    await b.drawing_setup(unidades=6, escala_cota=1.0)
    await b.execute_lisp(
        '(progn (setvar "DIMSCALE" 1.0) (setvar "DIMTXT" %s) (setvar "DIMASZ" %s)'
        ' (setvar "DIMEXO" %s) (setvar "DIMEXE" %s) (setvar "DIMGAP" %s)'
        ' (setvar "DIMTIH" 0) (setvar "DIMTOH" 0) (setvar "DIMDEC" 2)'
        ' (setvar "DIMSE1" 0) (setvar "DIMSE2" 0) T)'
        % (_f(modelo.get("dim_txt", 0.22)), _f(modelo.get("dim_asz", 0.18)),
           _f(0.06), _f(0.12), _f(0.06))
    )

    if modelo.get("terreno"):
        await b.layer_set_current("TERRENO")
        await d.poligono(*modelo["terreno"], camada="TERRENO")

    diga("paredes (%d eixos)..." % len(modelo.get("paredes", [])))
    await b.layer_set_current("PAREDES")
    if modelo.get("parede_sem_sobreposicao"):
        for x1, y1, x2, y2 in wall_boundary_segments(modelo.get("paredes", []), t):
            await d.linha(x1, y1, x2, y2, "PAREDES")
    else:
        for (x1, y1, x2, y2) in modelo.get("paredes", []):
            await d._ent(cons_faixa_parede(x1, y1, x2, y2, t))

    diga("ambientes (%d)..." % len(modelo.get("ambientes", [])))
    await b.layer_set_current("TEXTOS")
    for amb in modelo.get("ambientes", []):
        x1, y1, x2, y2 = amb["x1"], amb["y1"], amb["x2"], amb["y2"]
        area = (x2 - x1) * (y2 - y1)
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        h = float(amb.get("h", 0.26))
        await d.texto(cx, cy + 0.16, amb["nome"], h, "TEXTOS", centro=True)
        await d.texto(cx, cy - 0.26, "%s m2" % num_br(area), h * 0.72, "TEXTOS", centro=True)

    diga("portas (%d)..." % len(modelo.get("portas", [])))
    await b.layer_set_current("PORTAS")
    for (px, py, ang, larg) in modelo.get("portas", []):
        await d.arco(px, py, larg, ang, ang + 90.0, "PORTAS")
        rad = math.radians(ang)
        await d.linha(px, py, px + larg * math.cos(rad), py + larg * math.sin(rad), "PORTAS")

    diga("janelas (%d)..." % len(modelo.get("janelas", [])))
    await b.layer_set_current("JANELAS")
    mt = t / 2.0
    for (x1, y1, x2, y2) in modelo.get("janelas", []):
        if abs(y2 - y1) < 1e-9:
            await d.linha(x1, y1 - mt / 2, x2, y2 - mt / 2, "JANELAS")
            await d.linha(x1, y1 + mt / 2, x2, y2 + mt / 2, "JANELAS")
        else:
            await d.linha(x1 - mt / 2, y1, x2 - mt / 2, y2, "JANELAS")
            await d.linha(x1 + mt / 2, y1, x2 + mt / 2, y2, "JANELAS")

    if modelo.get("moveis"):
        diga("moveis (%d)..." % len(modelo["moveis"]))
        await b.layer_set_current("MOBILIARIO")
        for (x1, y1, x2, y2) in modelo["moveis"]:
            await d.poligono(x1, y1, x2, y2, "MOBILIARIO")

    diga("cotas...")
    await b.layer_set_current("COTAS")
    for c in modelo.get("cotas_h", []):
        await d.cota_h(*c)
    for c in modelo.get("cotas_v", []):
        await d.cota_v(*c)

    if modelo.get("selo"):
        diga("selo (%d linhas)..." % len(modelo["selo"]))
        await b.layer_set_current("TEXTOS")
        for (x, y, txt, h) in modelo["selo"]:
            await d.texto(x, y, txt, h, "TEXTOS")

    diga("zoom extents / regen...")
    await b.zoom_extents()
    await b.execute_lisp('(progn (command "_.REGENALL") T)')

    return {
        "valido": True,
        "validacao": v,
        "entidades_criadas": len(d.handles),
        "erros": d.erros,
        "areas": areas_do_modelo(modelo),
        "area_util": round(sum(areas_do_modelo(modelo).values()), 4),
        "handles": d.handles,
    }
