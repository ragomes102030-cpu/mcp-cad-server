"""Validação geométrica headless do contrato de plantas.

O cloud não importa o pacote local: estas regras ficam aqui para manter a
mesma barreira de segurança antes de criar entidades ezdxf.
"""
from __future__ import annotations

import math

TOL = 0.01


def _h(p):
    return abs(p[3] - p[1]) < 1e-9


def _v(p):
    return abs(p[2] - p[0]) < 1e-9


def _len(p):
    return math.hypot(p[2] - p[0], p[3] - p[1])


def _merge(items):
    out = []
    for a, b in sorted(items):
        if out and a <= out[-1][1] + 0.005:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _gap(intervals, start, width):
    end = start + width
    for a, b in intervals:
        if min(end, b) - max(start, a) > 0.01:
            return False
    return end > start + 0.01


def _overlap(a, b, gap=0.01):
    return min(a[2], b[2]) - max(a[0], b[0]) > gap and min(a[3], b[3]) - max(a[1], b[1]) > gap


def validar(modelo: dict, estrito: bool = False) -> dict:
    problemas = []

    def add(chave, onde, detalhe, severidade="erro"):
        if severidade == "aviso" and not estrito:
            sev = "aviso"
        else:
            sev = "erro"
        problemas.append({"chave": chave, "onde": onde, "detalhe": detalhe, "severidade": sev})

    try:
        t = float(modelo.get("espessura_parede", 0.15))
        paredes = [tuple(map(float, p)) for p in modelo.get("paredes", []) or []]
        ambientes = modelo.get("ambientes", []) or []
        portas = [tuple(map(float, p)) for p in modelo.get("portas", []) or []]
        janelas = [tuple(map(float, p)) for p in modelo.get("janelas", []) or []]
        moveis = [tuple(map(float, p)) for p in modelo.get("moveis", []) or []]
    except (TypeError, ValueError) as exc:
        return {"ok": False, "problemas": [{"chave": "modelo-invalido", "onde": "modelo", "detalhe": str(exc), "severidade": "erro"}], "erros": [], "avisos": []}

    eixos_h = {}
    eixos_v = {}
    vistos = set()
    for i, p in enumerate(paredes, 1):
        if len(p) != 4 or _len(p) < 0.05:
            add("parede-comprimento-zero", f"parede {i}", "parede degenerada")
            continue
        if not (_h(p) or _v(p)):
            add("parede-diagonal", f"parede {i}", "somente paredes ortogonais sao suportadas")
            continue
        key = tuple(sorted(((round(p[0], 3), round(p[1], 3)), (round(p[2], 3), round(p[3], 3)))))
        if key in vistos:
            add("parede-duplicada", f"parede {i}", "eixo repetido")
        vistos.add(key)
        if _h(p):
            eixos_h.setdefault(round(p[1], 4), []).append((min(p[0], p[2]), max(p[0], p[2])))
        else:
            eixos_v.setdefault(round(p[0], 4), []).append((min(p[1], p[3]), max(p[1], p[3])))
    eixos_h = {k: _merge(v) for k, v in eixos_h.items()}
    eixos_v = {k: _merge(v) for k, v in eixos_v.items()}

    for i, a in enumerate(paredes):
        if not (_h(a) or _v(a)):
            continue
        for j, b in enumerate(paredes[i + 1:], i + 1):
            if _h(a) and _h(b) and abs(a[1] - b[1]) < 1e-9:
                ov = min(max(a[0], a[2]), max(b[0], b[2])) - max(min(a[0], a[2]), min(b[0], b[2]))
            elif _v(a) and _v(b) and abs(a[0] - b[0]) < 1e-9:
                ov = min(max(a[1], a[3]), max(b[1], b[3])) - max(min(a[1], a[3]), min(b[1], b[3]))
            else:
                continue
            if ov > 0.01:
                add("paredes-sobrepostas", f"parede {i + 1} x parede {j + 1}", f"trechos colineares se sobrepoem em {ov:.2f} m")

    def openings_axis(x1, y1, x2, y2):
        if abs(y2 - y1) < 1e-9:
            return [("h", y, min(x1, x2), max(x1, x2)) for y in eixos_h if abs(y1 - y) <= t / 2 + 0.03]
        if abs(x2 - x1) < 1e-9:
            return [("v", x, min(y1, y2), max(y1, y2)) for x in eixos_v if abs(x1 - x) <= t / 2 + 0.03]
        return []

    porta_intervals = []
    for i, p in enumerate(portas, 1):
        if len(p) != 4 or p[3] <= 0:
            add("porta-invalida", f"porta {i}", "largura invalida")
            continue
        px, py, _ang, width = p
        perto_h = [y for y in eixos_h if abs(py - y) <= t / 2 + 0.03]
        perto_v = [x for x in eixos_v if abs(px - x) <= t / 2 + 0.03]
        if not perto_h and not perto_v:
            add("porta-sem-parede", f"porta {i}", "pivo nao esta em parede")
        ok = False
        for y in perto_h:
            ok |= any(_gap(eixos_h[y], px, width) for _ in [0])
            porta_intervals.append(("h", y, px, px + width, i))
        for x in perto_v:
            ok |= any(_gap(eixos_v[x], py, width) for _ in [0])
            porta_intervals.append(("v", x, py, py + width, i))
        if not ok:
            add("porta-sem-vao", f"porta {i}", "parede fechada no trecho da porta")
    for i, a in enumerate(porta_intervals):
        for b in porta_intervals[i + 1:]:
            if a[:2] == b[:2] and a[4] != b[4] and min(a[3], b[3]) - max(a[2], b[2]) > 0.01:
                add("portas-sobrepostas", f"porta {a[4]} x porta {b[4]}", "vãos se sobrepoem")

    for i, w in enumerate(janelas, 1):
        if len(w) != 4 or _len(w) < 0.05:
            add("janela-sem-parede", f"janela {i}", "vao degenerado")
            continue
        eixos = openings_axis(*w)
        if not eixos or not any(_gap(eixos_h[e] if o == "h" else eixos_v[e], a, b - a) for o, e, a, b in eixos):
            add("janela-sem-parede", f"janela {i}", "janela sem vao correspondente na parede")

    area_util = 0.0
    for i, a in enumerate(ambientes):
        try:
            x1, y1, x2, y2 = (float(a[k]) for k in ("x1", "y1", "x2", "y2"))
        except (KeyError, TypeError, ValueError):
            add("ambiente-invertido", a.get("nome", f"ambiente {i + 1}"), "retangulo invalido")
            continue
        area_util += max(0.0, x2 - x1) * max(0.0, y2 - y1)
        if x2 <= x1 or y2 <= y1:
            add("ambiente-invertido", a.get("nome", f"ambiente {i + 1}"), "retangulo invertido")
        for b in ambientes[i + 1:]:
            if _overlap((x1, y1, x2, y2), tuple(float(b[k]) for k in ("x1", "y1", "x2", "y2"))):
                add("ambientes-sobrepostos", f"{a.get('nome')} x {b.get('nome')}", "ambientes se sobrepoem")

    for i, m in enumerate(moveis, 1):
        if len(m) != 4 or m[2] <= m[0] or m[3] <= m[1]:
            add("moveis-invalidos", f"movel {i}", "retangulo invalido")
        if not any(m[0] >= float(a["x1"]) - TOL and m[1] >= float(a["y1"]) - TOL and m[2] <= float(a["x2"]) + TOL and m[3] <= float(a["y2"]) + TOL for a in ambientes):
            add("movel-fora-ambiente", f"movel {i}", "movel nao contido em ambiente")
        for j, n in enumerate(moveis[i:], i + 1):
            if _overlap(m, n):
                add("moveis-sobrepostos", f"movel {i} x movel {j}", "mobiliarios se sobrepoem")

    erros = [p for p in problemas if p["severidade"] == "erro"]
    avisos = [p for p in problemas if p["severidade"] == "aviso"]
    return {"ok": not erros, "problemas": problemas, "erros": erros, "avisos": avisos,
            "area_util": round(area_util, 4), "resumo": {"ambientes": len(ambientes), "paredes": len(paredes), "portas": len(portas), "janelas": len(janelas), "moveis": len(moveis), "erros": len(erros), "avisos": len(avisos)}}
