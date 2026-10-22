# -*- coding: utf-8 -*-
"""Desenha uma planta no CADCraft 'ao vivo', comando a comando.

Executa, no motor do CADCraft, as primitivas de desenho (rectang/line/arc/text
etc.) e entrega DWG + preview PNG, do mesmo modelo que a skill
cad-planta-autocad usa (modelo-3-quartos.json).

Uso:
    python draw_cadcraft_live.py skill/cad-planta-autocad/assets/modelo-3-quartos.json
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
_SRC = str(BASE / "codigo" / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
import cad_mcp.validar_modelo as vm  # projeto (valida, nao desenha)

CADCRAFT = "C:/Program Files/CADCraft/cadcraft-cli.exe"
OUT = BASE / "saida" / "residencia_cadcraft"


def _run(cmds):
    """Envia comandos ao CADCraft e devolve a lista de resultados."""
    args = [CADCRAFT, "run"]
    for _cmd, _arg in cmds:
        args.append("--cmd")
        if _arg is None:
            args.append(_cmd)
        else:
            args.append(_cmd + " " + _arg)
    res = subprocess.run(args, capture_output=True, text=True, timeout=180)
    return res.stdout



def build_cmds(modelo: dict):
    """Gera a sequencia de comandos CADCraft a partir do modelo (json.dumps)."""
    cmds = [("new", None)]
    t = float(modelo.get("espessura_parede", 0.15))
    D = lambda **kw: json.dumps(kw, ensure_ascii=True)

    def L(nome, cor):
        return ("layer.new", D(name=nome, color=cor, linetype="CONTINUOUS", current=True))

    # terreno
    tx1, ty1, tx2, ty2 = modelo["terreno"]
    cmds.append(L("TERRENO", 6))
    cmds.append(("rectang", D(p1=[tx1, ty1], p2=[tx2, ty2])))

    # paredes (face com espessura t)
    cmds.append(L("PAREDES", 4))
    for (x1, y1, x2, y2) in modelo["paredes"]:
        cmds.append(("rectang", D(p1=[x1 - t / 2, y1 - t / 2], p2=[x2 + t / 2, y2 + t / 2])))

    # portas (arco 90 + folha)
    cmds.append(L("PORTAS", 3))
    for (px, py, ang, larg) in modelo["portas"]:
        cmds.append(("arc", D(center=[px, py], radius=larg, start=ang, end=ang + 90)))
        cr = math.radians(ang)
        cmds.append(("line", D(points=[[px, py], [px + larg * math.cos(cr), py + larg * math.sin(cr)]])))

    # janelas (duas linhas)
    cmds.append(L("JANELAS", 5))
    mt = t / 2
    for (x1, y1, x2, y2) in modelo["janelas"]:
        if abs(y2 - y1) < 1e-9:
            cmds.append(("line", D(points=[[x1, y1 - mt / 2], [x2, y2 - mt / 2]])))
            cmds.append(("line", D(points=[[x1, y1 + mt / 2], [x2, y2 + mt / 2]])))
        else:
            cmds.append(("line", D(points=[[x1 - mt / 2, y1], [x2 - mt / 2, y2]])))
            cmds.append(("line", D(points=[[x1 + mt / 2, y1], [x2 + mt / 2, y2]])))

    # moveis
    cmds.append(L("MOBILIARIO", 9))
    for (x1, y1, x2, y2) in modelo["moveis"]:
        cmds.append(("rectang", D(p1=[x1, y1], p2=[x2, y2])))

    # cotas
    cmds.append(L("COTAS", 1))
    for (x1, x2, y, ytxt) in modelo.get("cotas_h", []):
        cmds.append(("dimlinear", D(p1=[x1, y], p2=[x2, y], at=[(x1 + x2) / 2.0, ytxt])))
    for (x, y1, y2, xtxt) in modelo.get("cotas_v", []):
        cmds.append(("dimaligned", D(p1=[x, y1], p2=[x, y2], at=[xtxt, (y1 + y2) / 2.0])))

    # ambientes (nome + area) e selo
    cmds.append(L("TEXTOS", 7))
    for amb in modelo.get("ambientes", []):
        x1, y1, x2, y2 = amb["x1"], amb["y1"], amb["x2"], amb["y2"]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        h = float(amb.get("h", 0.26))
        area = (x2 - x1) * (y2 - y1)
        cmds.append(("text", D(at=[cx, cy + 0.16], text=amb["nome"], height=h)))
        cmds.append(("text", D(at=[cx, cy - 0.26], text="%s m2" % round(area, 2), height=h * 0.72)))
    for (x, y, txt, h) in modelo.get("selo", []):
        cmds.append(("text", D(at=[x, y], text=txt, height=h)))

    # visualizacao final
    cmds.append(("zoom", D(mode="extents")))
    cmds.append(("regen", "{}"))
    return cmds



def main():
    if len(sys.argv) < 2:
        print("uso: draw_cadcraft_live.py modelo.json")
        return 2
    modelo = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    valid = vm.validar(modelo)
    if not valid["ok"]:
        print("VALIDACAO FALHOU:", valid["area_util"])
        for p in valid["problemas"]:
            print("  ERRO", p["chave"], "|", p["onde"], "|", p["detalhe"])
        return 1
    print("VALIDO: %d erros, %d avisos | area util %.2f m2" %
          (len(valid["erros"]), len(valid["avisos"]), valid["area_util"]))

    cmds = build_cmds(modelo)
    (OUT.parent).mkdir(parents=True, exist_ok=True)
    scr = OUT.parent / "residencia_cadcraft.scr"
    scr.write_text(chr(10).join(_cmd + " " + _arg if _arg else _cmd for _cmd, _arg in cmds), encoding="utf-8")

    # TUDO na MESMA sessao do CADCraft: desenha -> salva DWG -> exporta PNG
    print("executando %d comandos no CADCraft (ao vivo)..." % len(cmds))
    args = [CADCRAFT, "run"]
    for _cmd, _arg in cmds:
        args.append("--cmd")
        if _arg is None:
            args.append(_cmd)
        else:
            args.append(_cmd + " " + _arg)
    args.append("--cmd")
    args.append("qsave " + json.dumps({"path": str(OUT) + ".dwg", "format": "dwg"}))
    args.append("--export")
    args.append(str(OUT) + ".png")
    res = subprocess.run(args, capture_output=True, text=True, timeout=180)
    print("rc:", res.returncode)
    for line in res.stdout.strip().splitlines():
        print(" ", line)
    if res.stderr.strip():
        print("STDERR:", res.stderr.strip()[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
