# -*- coding: utf-8 -*-
"""Porte de `autocad-mcp-pro/engineering/arch` -- testes sem AutoCAD.

O que se prova aqui:
  1. o vao nao e desenhado: e o que sobra quando a parede e cortada;
  2. abertura fora da parede, sobreposta ou atravessando vertice e recusada;
  3. a porta sai com folha perpendicular e arco de 90 graus, no pivo certo;
  4. a janela sai com 4 linhas e a caixa cobre o vao;
  5. `expandir()` gera um modelo que o renderer desenha e o validador aprova.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.arch import (Abertura, Parede, comprimento, expandir,  # noqa: E402
                          escada_reta, primitivas, trechos, validar)
from cad_mcp.validar_modelo import validar as validar_modelo  # noqa: E402

falhas = []


def checar(nome: str, cond: bool, extra: str = "") -> None:
    print("  %s  %s%s" % ("ok  " if cond else "FALHA", nome,
                          (" -- " + str(extra)) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)


def recusa(nome: str, fn) -> None:
    try:
        fn()
    except ValueError as exc:
        checar("%s -> recusado (%s)" % (nome, str(exc)[:52]), True)
        return
    checar("%s -> DEVERIA RECUSAR" % nome, False)


def perto(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def main() -> int:
    print("1) corte da parede")
    p = Parede("P1", ((0.0, 0.0), (6.0, 0.0)))
    ab = Abertura("A1", "P1", "porta", offset=2.0, largura=0.8)
    validar([p], [ab])
    segs = trechos(p, [ab])
    checar("2 trechos", len(segs) == 2, segs)
    checar("primeiro 0..2", perto(segs[0][0][0], 0) and perto(segs[0][1][0], 2.0), segs[0])
    checar("segundo 2,8..6", perto(segs[1][0][0], 2.8) and perto(segs[1][1][0], 6.0), segs[1])
    soma = sum(math.dist(a, b) for a, b in segs)
    checar("material = 6,00 - 0,80", perto(soma, 5.2), soma)

    print("\n2) o que a parede nao aceita")
    recusa("fora do fim", lambda: validar([p], [Abertura("X", "P1", "porta", 5.6, 0.8)]))
    recusa("sobreposta", lambda: validar([p], [
        Abertura("A", "P1", "porta", 1.0, 0.9),
        Abertura("B", "P1", "porta", 1.5, 0.9)]))
    recusa("parede inexistente", lambda: validar([p], [Abertura("Y", "P9", "porta", 1.0, 0.8)]))
    recusa("id repetido", lambda: validar([p], [
        Abertura("A", "P1", "porta", 1.0, 0.8),
        Abertura("A", "P1", "porta", 3.0, 0.8)]))

    L = Parede("L", ((0.0, 0.0), (4.0, 0.0), (4.0, 3.0)))
    recusa("atravessa o vertice",
           lambda: validar([L], [Abertura("V", "L", "porta", 3.6, 0.8)]))
    checar("comprimento de L = 7", perto(comprimento(L), 7.0), comprimento(L))

    print("\n3) porta: folha perpendicular, arco de 90 graus")
    pr = primitivas(p, ab)
    x, y, ang, larg = pr["porta"]
    checar("pivo em (2,0)", perto(x, 2.0) and perto(y, 0.0), (x, y))
    checar("folha a 90 (para dentro)", perto(ang, 90.0), ang)
    checar("largura = 0,80", perto(larg, 0.8), larg)
    cx, cy, r, a1, a2 = pr["arco"]
    checar("arco 0 -> 90", perto(a1, 0.0) and perto(a2, 90.0), (a1, a2))
    checar("raio = largura", perto(r, 0.8), r)
    fx, fy = pr["folha_fim"]
    checar("ponta da folha em (2; 0,8)", perto(fx, 2.0) and perto(fy, 0.8), (fx, fy))

    ab_dir = Abertura("A2", "P1", "porta", 2.0, 0.8, gira="direita")
    pr2 = primitivas(p, ab_dir)
    checar("gira= direita desce", perto(pr2["porta"][2], 270.0), pr2["porta"][2])
    checar("arco -90 -> 0", perto(pr2["arco"][3], 270.0) and perto(pr2["arco"][4], 0.0),
           pr2["arco"][3:])

    ab_fim = Abertura("A3", "P1", "porta", 2.0, 0.8, dobradica="fim")
    pr3 = primitivas(p, ab_fim)
    checar("pivo no batente final (2,8)", perto(pr3["porta"][0], 2.8), pr3["porta"][:2])

    print("\n4) janela: 4 linhas, caixa do tamanho do vao")
    j = Abertura("J1", "P1", "janela", offset=1.0, largura=1.2, peitoril=0.9)
    pj = primitivas(p, j)
    checar("4 linhas", len(pj["linhas"]) == 4, len(pj["linhas"]))
    xs = [q[0] for par in pj["linhas"] for q in par]
    ys = [q[1] for par in pj["linhas"] for q in par]
    checar("comprimento 1,20", perto(max(xs) - min(xs), 1.2), max(xs) - min(xs))
    checar("espessura 0,15", perto(max(ys) - min(ys), 0.15), max(ys) - min(ys))

    print("\n5) expandir(): modelo de casa -> schema do planta.py")
    modelo = {
        "unidade": "m",
        "espessura_parede": 0.15,
        "terreno": (-1.0, -1.0, 7.0, 5.0),
        "paredes_arquitetonicas": [
            {"id": "N", "eixo": [(0, 4), (6, 4)]},
            {"id": "S", "eixo": [(0, 0), (6, 0)]},
            {"id": "O", "eixo": [(0, 0), (0, 4)]},
            {"id": "L", "eixo": [(6, 0), (6, 4)]},
        ],
        "aberturas": [
            {"id": "D1", "parede": "S", "tipo": "porta", "offset": 1.0, "largura": 0.9},
            {"id": "D2", "parede": "N", "tipo": "porta", "offset": 4.5, "largura": 0.8,
             "dobradica": "fim", "gira": "direita"},
            {"id": "J1", "parede": "L", "tipo": "janela", "offset": 1.2, "largura": 1.4},
        ],
        "ambientes": [{"nome": "SALA", "x1": 0.075, "y1": 0.075,
                       "x2": 5.925, "y2": 3.925, "h": 0.22}],
    }
    exp = expandir(modelo)
    checar("paredes cortadas: 3 paredes com vao viram 6 + 1 inteira = 7",
           len(exp["paredes"]) == 7, len(exp["paredes"]))
    checar("2 portas", len(exp["portas"]) == 2, exp["portas"])
    checar("1 janela", len(exp["janelas"]) == 1, exp["janelas"])
    r = validar_modelo(exp)
    checar("validador aprova o resultado", r["ok"], [p["chave"] for p in r["erros"]])

    class _R:
        def __init__(self, payload=None):
            self.payload, self.ok, self.error = payload, True, None

    class Fake:
        def __init__(self):
            self.entes = 0

        async def entmakex(self, corpo):
            self.entes += 1
            return _R("H%d" % self.entes)

        def __getattr__(self, nome):
            async def _q(*a, **k):
                return _R("X")
            return _q

    import asyncio
    from cad_mcp.planta import desenhar_modelo

    fb = Fake()
    rv = asyncio.run(desenhar_modelo(fb, modelo))
    checar("renderer desenha a casa", rv.get("valido") and rv["entidades_criadas"] > 10,
           rv.get("entidades_criadas"))
    checar("paredes + portas + janela desenhados",
           rv["entidades_criadas"] >= 7 + 2 + 1, rv["entidades_criadas"])

    print("\n6) parede fechada (anel) tambem aceita abertura")
    anel = Parede("R", ((0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (0.0, 3.0)), fechada=True)
    checar("perimetro 12", perto(comprimento(anel), 12.0), comprimento(anel))
    ab_anel = Abertura("AR", "R", "porta", offset=11.0, largura=0.8)
    validar([anel], [ab_anel])
    segs = trechos(anel, [ab_anel])
    checar("anel cortado em 5 (4 lados, um deles partido)", len(segs) == 5, len(segs))
    checar("material 11,20", perto(sum(math.dist(a, b) for a, b in segs), 11.2),
           sum(math.dist(a, b) for a, b in segs))

    print("\n7) escada reta: tramo, talaias, pisadas, seta, Blondel")
    es = escada_reta(x=0.0, y=0.0, largura=1.0, degraus=10, piso=0.28,
                     altura_total=1.80, angulo=0.0)
    checar("comprimento = 10 x 0,28 = 2,80", perto(es["comprimento"], 2.8), es["comprimento"])
    checar("2 talaias + 9 pisadas = 11 linhas", len(es["linhas"]) == 11, len(es["linhas"]))
    checar("riser = 1,80/10 = 0,18", perto(es["riser"], 0.18), es["riser"])
    checar("blondel = 2*0,18 + 0,28 = 0,64", perto(es["blondel"], 0.64), es["blondel"])
    checar("blondel conforme (0,62..0,66)", es["blondel_conforme"] is True, es["blondel_conforme"])
    checar("seta desenhada (ponta de 3 pts)",
           es["seta"] is not None and len(es["seta"]["ponta"]) == 3, es["seta"])
    checar("rotulo SUBA no inicio", es["rotulo"] and es["rotulo"]["texto"] == "SUBA", es["rotulo"])

    es90 = escada_reta(x=0.0, y=0.0, largura=1.0, degraus=4, piso=0.3, angulo=90.0)
    checar("talaias giradas 90 ficam verticais",
           perto(es90["linhas"][0][1][0], 0.0) and perto(es90["linhas"][0][1][1], 1.2),
           es90["linhas"][0])

    es1 = escada_reta(largura=1.0, degraus=1, piso=0.3)
    checar("1 degrau: so' 2 talaias, sem pisada", len(es1["linhas"]) == 2, len(es1["linhas"]))
    checar("sem altura_total: sem Blondel", es1["blondel"] is None, es1["blondel"])
    checar("seta=False omite a seta",
           escada_reta(largura=1.0, degraus=4, piso=0.3, seta=False)["seta"] is None)
    checar("rotulo=None omite o rotulo",
           escada_reta(largura=1.0, degraus=4, piso=0.3, rotulo=None)["rotulo"] is None)

    recusa("escada: largura zero", lambda: escada_reta(largura=0, degraus=4, piso=0.3))
    recusa("escada: piso zero", lambda: escada_reta(largura=1.0, degraus=4, piso=0))
    recusa("escada: degraus < 1", lambda: escada_reta(largura=1.0, degraus=0, piso=0.3))
    recusa("escada: altura_total negativa",
           lambda: escada_reta(largura=1.0, degraus=4, piso=0.3, altura_total=-1.0))

    print()
    if falhas:
        print("FALHOU: %d caso(s): %s" % (len(falhas), ", ".join(falhas)))
        return 1
    print("TUDO OK -- abertura hospedada: o vao agora e consequencia, nao tarefa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
