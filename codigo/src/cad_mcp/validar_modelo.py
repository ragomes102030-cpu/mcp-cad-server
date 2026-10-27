# -*- coding: utf-8 -*-
"""Validador do modelo ANTES de tocar no AutoCAD (~1 ms).

Por que existe: o AutoCAD aceita quase tudo calado. Porta desenhada sobre
parede fechada vira arco cortando alvenaria; texto de 70 caracteres a 0,22 m
vira 14 m de papel e o plot por *Extents* encolhe a planta inteira. Descobrir
isso depois custa um ciclo COM + DXF + PDF; descobrir aqui custa microssegundos.

Regra de ouro: cada verificacao tem uma `chave` -- a MESMA chave usada no
`historico.registrar`. Nada entra aqui sem ter acontecido de verdade (e, em
regra, sem ter acontecido 3 vezes). Ver `historico.promovidos()`.

Uso:
    from cad_mcp.validar_modelo import validar
    r = validar(modelo)
    if not r["ok"]: ...

    python -m cad_mcp.validar_modelo modelo.json [--json] [--estrito]
"""
from __future__ import annotations

import json
import math
import sys
from .areas import area_summary
from pathlib import Path

__all__ = ["validar", "AVANCO_TXT", "CHECKS"]

# Avanco medido do txt.shx maiusculo: ~0,9 x altura por caractere.
# (0,6 -- largura "de livro" -- foi o que estourou o selo na pratica.)
AVANCO_TXT = 0.9

CHECKS = [
    "modelo-sem-terreno", "ambiente-invertido", "ambiente-area-zero",
    "ambientes-sobrepostos", "area-total-diverge", "parede-comprimento-zero",
    "parede-diagonal", "parede-fora-terreno", "parede-duplicada",
    "porta-sem-parede", "porta-sem-vao", "porta-colide-parede",
    "porta-estreita", "porta-larga",
    "texto-transborda", "selo-transborda", "selo-linhas-colidem",
    "formato-ruim",
]

TOL = 0.01           # folga de comparacao (m)
EPS = 1e-6


# ------------------------------------------------------------------ geometria
def _eh_h(p) -> bool:
    return abs(p[3] - p[1]) < 1e-9


def _eh_v(p) -> bool:
    return abs(p[2] - p[0]) < 1e-9


def _comprimento(p) -> float:
    return math.hypot(p[2] - p[0], p[3] - p[1])


def _fundir(intervalos: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Une intervalos que se tocam (tolerancia 5 mm)."""
    out: list[list[float]] = []
    for a, b in sorted(intervalos):
        if out and a <= out[-1][1] + 0.005:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _vao_ao_lado(intervalos, p: float, w: float) -> bool:
    """Existe vao de largura >= w com o pivo `p` numa das pontas?

    Se `p` cai DENTRO de um trecho de parede (com 2 cm de folga), nao ha vao:
    o pivo tem de estar na ponta de um trecho, nao no meio dele. Sem essa
    guarda, uma porta colocada no meio da parede passava como "vao" porque
    nao havia parede antes do inicio dela.
    """
    for a, b in intervalos:
        if a + 0.02 < p < b - 0.02:
            return False
    prox = [a for a, _b in intervalos if a > p + EPS]
    ant = [b for _a, b in intervalos if b < p - EPS]
    d1 = (min(prox) - p) if prox else float("inf")
    d2 = (p - max(ant)) if ant else float("inf")
    return max(d1, d2) >= w - 0.02


def _lab(texto: str, h: float) -> float:
    """Largura estimada (superior) de um texto de altura h."""
    return AVANCO_TXT * float(h) * len(str(texto))


def _distancia_ponto_parede(x: float, y: float, parede) -> float:
    """Distância de um ponto ao eixo de uma parede ortogonal."""
    x1, y1, x2, y2 = parede
    if _eh_h(parede):
        if min(x1, x2) <= x <= max(x1, x2):
            return abs(y - y1)
        return min(math.hypot(x - x1, y - y1), math.hypot(x - x2, y - y2))
    if _eh_v(parede):
        if min(y1, y2) <= y <= max(y1, y2):
            return abs(x - x1)
        return min(math.hypot(x - x1, y - y1), math.hypot(x - x2, y - y2))
    return float("inf")


def _folha_colide_parede(porta, paredes, espessura: float) -> bool:
    """Testa pontos da folha aberta, excluindo o pivô da própria parede."""
    px, py, ang, largura = porta
    rad = math.radians(ang)
    # Os primeiros 12 cm pertencem à região do batente e não devem gerar um
    # falso positivo contra o eixo hospedeiro.
    for frac in (0.16, 0.28, 0.40, 0.52, 0.64, 0.76, 0.88, 1.0):
        x = px + largura * frac * math.cos(rad)
        y = py + largura * frac * math.sin(rad)
        if any(_distancia_ponto_parede(x, y, p) < espessura / 2.0 - 0.005 for p in paredes):
            return True
    return False


# ------------------------------------------------------------------ validacao
def validar(modelo: dict, estrito: bool = False) -> dict:
    """Devolve {"ok", "problemas", "avisos", "resumo", "extensao", "area_util"}.

    `estrito=True` transforma avisos em erro (para CI/regressao).
    """
    P: list[dict] = []

    def add(chave, onde, detalhe, severidade="erro"):
        P.append({"chave": chave, "onde": onde, "detalhe": detalhe,
                  "severidade": "aviso" if (severidade == "aviso" and not estrito) else "erro"})

    t = float(modelo.get("espessura_parede", 0.15) or 0.15)
    terreno = modelo.get("terreno")
    paredes = [tuple(float(v) for v in p) for p in modelo.get("paredes", [])]
    ambientes = modelo.get("ambientes", []) or []
    portas = [tuple(float(v) for v in d) for d in modelo.get("portas", []) or []]
    selo = modelo.get("selo", []) or []

    # ---------------------------------------------------------- terreno
    if not terreno or len(tuple(terreno)) != 4:
        add("modelo-sem-terreno", "modelo", "sem 'terreno' (x1,y1,x2,y2): o plot por Extents fica sem referencia")
        tx1 = ty1 = float("inf")
        tx2 = ty2 = float("-inf")
    else:
        tx1, ty1, tx2, ty2 = (float(v) for v in terreno)
        if tx2 <= tx1 or ty2 <= ty1:
            add("modelo-sem-terreno", "terreno", "terreno invertido/degenerado: %s" % (terreno,))

    # ---------------------------------------------------------- ambientes
    area_util = 0.0
    for amb in ambientes:
        nome = amb.get("nome", "?")
        x1, y1, x2, y2 = (float(amb[k]) for k in ("x1", "y1", "x2", "y2"))
        if x2 <= x1 + EPS or y2 <= y1 + EPS:
            add("ambiente-invertido", nome,
                "retangulo invertido/degenerado: x %.2f..%.2f, y %.2f..%.2f" % (x1, x2, y1, y2))
            continue
        area = (x2 - x1) * (y2 - y1)
        area_util += area
        if area < 1.0:
            add("ambiente-area-zero", nome, "area de %.2f m2 (digito trocado?)" % area)
        h = float(amb.get("h", 0.26))
        largura = _lab(nome, h)
        if largura > (x2 - x1) * 0.98:
            add("texto-transborda", nome,
                "rotulo ocupa %.2f m (0,9 x %.2f x %d chars) em %.2f m de largura"
                % (largura, h, len(nome), x2 - x1),
                "aviso" if largura < (x2 - x1) * 1.25 else "erro")

    for i in range(len(ambientes)):
        a = ambientes[i]
        for j in range(i + 1, len(ambientes)):
            b = ambientes[j]
            sx = min(float(a["x2"]), float(b["x2"])) - max(float(a["x1"]), float(b["x1"]))
            sy = min(float(a["y2"]), float(b["y2"])) - max(float(a["y1"]), float(b["y1"]))
            if sx > 0.02 and sy > 0.02:
                add("ambientes-sobrepostos", "%s x %s" % (a.get("nome"), b.get("nome")),
                    "sobreposicao de %.2f m2" % (sx * sy))

    pedida = modelo.get("area_pedida")
    if pedida:
        desvio = area_util - float(pedida)
        if abs(desvio) > max(2.0, 0.05 * float(pedida)):
            add("area-total-diverge", "modelo",
                "area util %.2f m2 para %.2f m2 pedidos (%.1f%%)"
                % (area_util, float(pedida), 100.0 * desvio / float(pedida)))

    # ---------------------------------------------------------- paredes
    vistas = set()
    for (x1, y1, x2, y2) in paredes:
        nome = "(%.2f,%.2f)-(%.2f,%.2f)" % (x1, y1, x2, y2)
        if _comprimento((x1, y1, x2, y2)) < 0.05:
            add("parede-comprimento-zero", nome, "comprimento < 0,05 m")
        if not (_eh_h((x1, y1, x2, y2)) or _eh_v((x1, y1, x2, y2))):
            add("parede-diagonal", nome,
                "parede nao ortogonal: `cons_faixa_parede` a desenha como CAIXA (bbox), nao como faixa",
                "aviso")
        chave = tuple(sorted([(round(x1, 3), round(y1, 3)), (round(x2, 3), round(y2, 3))]))
        if chave in vistas:
            add("parede-duplicada", nome, "eixo repetido")
        vistas.add(chave)
        if terreno:
            mt = t / 2.0
            if (min(x1, x2) - mt < tx1 - TOL or max(x1, x2) + mt > tx2 + TOL
                    or min(y1, y2) - mt < ty1 - TOL or max(y1, y2) + mt > ty2 + TOL):
                add("parede-fora-terreno", nome, "faixa da parede sai do terreno")

    # ---------------------------------------------------------- portas
    eixos_h: dict[float, list[tuple[float, float]]] = {}
    eixos_v: dict[float, list[tuple[float, float]]] = {}
    for (x1, y1, x2, y2) in paredes:
        if abs(y2 - y1) < 1e-9:
            eixos_h.setdefault(round(y1, 4), []).append((min(x1, x2), max(x1, x2)))
        elif abs(x2 - x1) < 1e-9:
            eixos_v.setdefault(round(x1, 4), []).append((min(y1, y2), max(y1, y2)))
    eixos_h = {y: _fundir(v) for y, v in eixos_h.items()}
    eixos_v = {x: _fundir(v) for x, v in eixos_v.items()}

    for (px, py, ang, w) in portas:
        onde = "porta (%.2f, %.2f) %.0f graus, %.2f m" % (px, py, ang, w)
        if w < 0.60:
            add("porta-estreita", onde, "vao de %.2f m nao passa (minimo usual 0,60)" % w, "aviso")
        if w > 1.20:
            add("porta-larga", onde, "vao de %.2f m acima do usual residencial (1,20)" % w, "aviso")

        tol = t / 2.0 + 0.03
        perto_h = [y for y in eixos_h if abs(py - y) <= tol]
        perto_v = [x for x in eixos_v if abs(px - x) <= tol]
        if not perto_h and not perto_v:
            add("porta-sem-parede", onde,
                "pivo a mais de %.2f m de qualquer eixo de parede" % tol)
            continue
        ok = False
        for y in perto_h:
            if _vao_ao_lado(eixos_h[y], px, w):
                ok = True
        for x in perto_v:
            if _vao_ao_lado(eixos_v[x], py, w):
                ok = True
        if not ok:
            add("porta-sem-vao", onde,
                "a parede esta FECHADA no pivo: falta abrir o vao de %.2f m no eixo" % w)
        if _folha_colide_parede((px, py, ang, w), paredes, t):
            add("porta-colide-parede", onde,
                "a folha aberta atravessa a faixa de outra parede; revisar dobradiça/sentido")

    # ---------------------------------------------------------- selo
    if selo:
        larg_ref = (tx2 - tx1) if terreno else 0.0
        for (x, y, txt, h) in selo:
            largura = _lab(txt, h)
            if larg_ref and x + largura > tx2 + TOL:
                add("selo-transborda", "selo y=%.2f" % float(y),
                    "'%s...' ocupa %.2f m e passa de x=%.2f (terreno termina em %.2f)"
                    % (str(txt)[:28], largura, x + largura, tx2))
        ordenado = sorted(selo, key=lambda s: -float(s[1]))
        for a, b in zip(ordenado, ordenado[1:]):
            dy = float(a[1]) - float(b[1])
            precisa = 1.2 * max(float(a[3]), float(b[3]))
            if dy < precisa - TOL:
                add("selo-linhas-colidem", "selo y=%.2f/%.2f" % (float(a[1]), float(b[1])),
                    "linhas a %.2f m; precisa >= %.2f m para h=%.2f" % (dy, precisa, max(float(a[3]), float(b[3]))))

    # ---------------------------------------------------------- formato
    extensao = None
    if terreno:
        xs, ys = [tx1, tx2], [ty1, ty2]
        for (x, y, _txt, h) in selo:
            xs.append(float(x))
            ys.append(float(y) - float(h))
            xs.append(float(x) + _lab(_txt, h))
        for p in paredes:
            xs += [p[0], p[2]]
            ys += [p[1], p[3]]
        ex1, ex2, ey1, ey2 = min(xs), max(xs), min(ys), max(ys)
        larg, alt = ex2 - ex1, ey2 - ey1
        extensao = {"x1": round(ex1, 3), "y1": round(ey1, 3),
                    "x2": round(ex2, 3), "y2": round(ey2, 3),
                    "largura": round(larg, 3), "altura": round(alt, 3)}
        if larg > 0 and alt > 0:
            razao = max(larg / alt, alt / larg)
            if razao > 1.9:
                add("formato-ruim", "extensao",
                    "%.2f x %.2f m (razao %.2f): numa folha A3/A4 sobra ~%.0f%% de papel"
                    % (larg, alt, razao, 100.0 * (1.0 - 1.0 / razao)), "aviso")

    # ---------------------------------------------------------- veredito
    erros = [p for p in P if p["severidade"] == "erro"]
    avisos = [p for p in P if p["severidade"] == "aviso"]
    return {
        "ok": not erros,
        "area_accounting": area_summary(ambientes) if not any(p['chave']=='ambiente-invertido' for p in P) else None,
        "problemas": P,
        "erros": erros,
        "avisos": avisos,
        "extensao": extensao,
        "area_util": round(area_util, 4),
        "resumo": {
            "ambientes": len(ambientes), "paredes": len(paredes),
            "portas": len(portas), "selo": len(selo),
            "erros": len(erros), "avisos": len(avisos),
        },
    }


# ------------------------------------------------------------------------- CLI
def relatar(r: dict) -> str:
    linhas = []
    for p in r["problemas"]:
        try:
            from .historico import vezes
            n = vezes(p["chave"])
        except Exception:
            n = 0
        hist = " (ja ocorreu %dx)" % n if n else ""
        linhas.append("  %-5s %-24s %-28s %s%s"
                      % (p["severidade"].upper(), p["chave"], p["onde"], p["detalhe"], hist))
    cab = "VALIDACAO: %d erro(s), %d aviso(s) | area util %.2f m2" % (
        len(r["erros"]), len(r["avisos"]), r["area_util"])
    if r["extensao"]:
        e = r["extensao"]
        cab += " | extensao %.2f x %.2f m" % (e["largura"], e["altura"])
    return "\n".join([cab] + linhas)


def _main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    alvo = Path(argv[0])
    modelo = json.loads(alvo.read_text(encoding="utf-8"))
    r = validar(modelo, estrito="--estrito" in argv)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(relatar(r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
