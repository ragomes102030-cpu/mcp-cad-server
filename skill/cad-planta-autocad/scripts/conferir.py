# -*- coding: utf-8 -*-
"""Inspeciona um DXF gerado pelo mcp-cad-server (ou por qualquer CAD).

    python conferir.py planta.dxf
    python conferir.py planta.dxf --mapa          # desenha a planta em ASCII
    python conferir.py planta.dxf --mapa --passo 0.15

Checa o que realmente importa:
  * unidades (INSUNITS=6 = metros);
  * contagem por tipo e por camada;
  * extensão em metros (extents do plot);
  * **abertura de cada arco** — a porta tem que abrir 90°,00. Se aparecer 116,62°,
    alguém passou GRAUS onde o `entmake` do AutoLISP espera RADIANOS;
  * áreas das polilinhas fechadas (terreno, paredes);
  * textos (nomes de ambiente, selo).
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VERMELHO, VERDE, FIM = "\033[91m", "\033[92m", "\033[0m"


def area_poligono(pontos) -> float:
    soma = 0.0
    n = len(pontos)
    for i in range(n):
        x1, y1 = pontos[i]
        x2, y2 = pontos[(i + 1) % n]
        soma += x1 * y2 - x2 * y1
    return abs(soma) / 2.0


def conferir(arq: Path) -> int:
    import ezdxf
    from ezdxf import bbox

    doc = ezdxf.readfile(arq)
    msp = doc.modelspace()

    print("arquivo  : %s (%.1f KB)" % (arq, arq.stat().st_size / 1024.0))
    print("versao   : %s" % doc.dxfversion)
    unid = doc.header.get("$INSUNITS")
    ok_unid = unid == 6
    print("INSUNITS : %s (6 = metros) %s" % (unid, VERDE + "OK" + FIM if ok_unid else VERMELHO + "CONFERIR" + FIM))
    print("entidades: %d" % len(msp))
    print("tipos    : %s" % dict(collections.Counter(e.dxftype() for e in msp)))

    camadas = collections.Counter(e.dxf.layer for e in msp)
    print("camadas  : %s" % dict(sorted(camadas.items())))

    ext = bbox.extents(msp)
    print("extensao : x %.2f..%.2f (%.2f m) | y %.2f..%.2f (%.2f m)"
          % (ext.extmin.x, ext.extmax.x, ext.size.x, ext.extmin.y, ext.extmax.y, ext.size.y))

    # ---- arcos: a checagem que pega o bug de radianos
    arcos = [e for e in msp if e.dxftype() == "ARC"]
    ruins = []
    if arcos:
        aberturas = [round((e.dxf.end_angle - e.dxf.start_angle) % 360.0, 3) for e in arcos]
        ruins = [a for a in aberturas if abs(a - 90.0) >= 0.01]
        print("arcos    : %d | aberturas: %s" % (len(arcos), aberturas))
        if ruins:
            print(VERMELHO + "!! %d arco(s) fora de 90 graus: %s" % (len(ruins), ruins[:8]) + FIM)
            print("!! sintoma classico: graus passados onde entmake espera RADIANOS "
                  "(use (angtof \"90\") ou math.radians)")
        else:
            print("           todas as aberturas em 90 graus " + VERDE + "OK" + FIM)

    # ---- areas
    areas = collections.defaultdict(float)
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.closed:
            areas[e.dxf.layer] += area_poligono([(p[0], p[1]) for p in e.get_points("xy")])
    if areas:
        print("areas    : %s m2" % {k: round(float(v), 2) for k, v in sorted(areas.items())})

    # ---- textos
    textos = []
    for e in msp:
        if e.dxftype() == "MTEXT":
            textos.append(e.plain_text())
        elif e.dxftype() == "TEXT":
            textos.append(e.dxf.text)
    print("textos   : %d" % len(textos))
    for t in textos:
        print("    %s" % t)

    # ---- soma de comprimentos por camada (quantitativo rapido)
    comp = collections.defaultdict(float)
    for e in msp:
        if e.dxftype() == "LINE":
            comp[e.dxf.layer] += e.dxf.start.distance(e.dxf.end)
        elif e.dxftype() == "CIRCLE":
            comp[e.dxf.layer] += 2 * 3.141592653589793 * e.dxf.radius
    if comp:
        print("comprimento por camada (m): %s" % {k: round(v, 2) for k, v in sorted(comp.items())})

    return 0 if (ok_unid and not ruins) else 1


def mapa(arq: Path, passo: float = 0.2) -> None:
    """Rasteriza PAREDES/PORTAS/TEXTOS em ASCII, para 'olhar' sem ver imagem.

    Usa sub-amostragem 5x5 por celula: parede de 0,15 m some se voce amostrar
    so o centro de celulas de 0,2 m (aliasing).
    """
    import ezdxf

    doc = ezdxf.readfile(arq)
    msp = doc.modelspace()

    caixas = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "PAREDES":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            caixas.append((min(xs), min(ys), max(xs), max(ys)))
    portas = [(e.dxf.center.x, e.dxf.center.y) for e in msp if e.dxftype() == "ARC"]
    textos = [(e.dxf.insert.x, e.dxf.insert.y) for e in msp
              if e.dxftype() == "TEXT" and e.dxf.layer == "TEXTOS"]

    if not caixas and not portas:
        print("nada para desenhar (sem PAREDES/ARC)")
        return

    xs = [c[0] for c in caixas] + [p[0] for p in portas]
    ys = [c[1] for c in caixas] + [p[1] for p in portas]
    x0, x1 = min(xs) - passo, max(xs) + passo
    y0, y1 = min(ys) - passo, max(ys) + passo
    sub = 5

    def dentro(px, py):
        for (a, b, c, d) in caixas:
            for i in range(sub):
                for j in range(sub):
                    qx = px + (i + 0.5) / sub * passo - passo / 2
                    qy = py + (j + 0.5) / sub * passo - passo / 2
                    if a <= qx <= c and b <= qy <= d:
                        return True
        return False

    ny = int(round((y1 - y0) / passo))
    nx = int(round((x1 - x0) / passo))
    print("mapa: %s  (%.2f m por caracter)  # parede  o porta  * texto" % (arq.name, passo))
    for j in range(ny, -1, -1):
        py = y0 + j * passo
        linha = []
        for i in range(nx):
            px = x0 + i * passo
            ch = "#" if dentro(px, py) else "."
            if any(abs(px - p[0]) <= passo and abs(py - p[1]) <= passo for p in portas):
                ch = "o"
            if any(abs(px - t[0]) <= passo and abs(py - t[1]) <= passo * 1.5 for t in textos):
                ch = "*"
            linha.append(ch)
        print("%6.1f %s" % (py, "".join(linha)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Confere um DXF e, opcionalmente, desenha a planta em ASCII.")
    ap.add_argument("dxf")
    ap.add_argument("--mapa", action="store_true", help="desenha a planta em ASCII")
    ap.add_argument("--passo", type=float, default=0.2, help="metros por caracter do mapa")
    args = ap.parse_args()

    arq = Path(args.dxf)
    if not arq.exists():
        raise SystemExit("nao encontrado: %s" % arq)
    codigo = conferir(arq)
    if args.mapa:
        print()
        mapa(arq, args.passo)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
