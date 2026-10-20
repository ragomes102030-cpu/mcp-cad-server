# -*- coding: utf-8 -*-
"""Valida um modelo JSON ANTES de abrir o AutoCAD (~1 ms, sem COM).

    python scripts/validar.py modelo.json
    python scripts/validar.py modelo.json --json
    python scripts/validar.py modelo.json --estrito   # aviso tambem reprova

Exit code 0 = pode desenhar; 1 = corrija antes.

O que ele pega (aprendido na pratica, ver references/falhas.md):
  * porta sem vao -- a parede esta fechada no pivo e o arco vai cortar alvenaria;
  * rotulo/selo maior que o espaco -- o plot por Extents encolhe a planta toda;
  * ambiente invertido ou sobreposto; soma das areas longe do m2 pedido;
  * parede fora do terreno, parede duplicada, selo com linhas colidindo;
  * formato (razao > 1,9) que desperdica a folha.

Cada achado traz a chave do sintoma no historico do projeto:
    python -m cad_mcp.historico --chave texto-transborda
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJETO = Path(os.environ.get("MCP_CAD_SERVER", r"C:\Users\Correta Engenharia\mcp-cad-server"))
SRC = PROJETO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from cad_mcp.validar_modelo import _main
except ImportError as exc:                      # pragma: no cover
    sys.stderr.write("nao achei cad_mcp em %s (%s)\n"
                     "defina MCP_CAD_SERVER para a pasta do mcp-cad-server\n" % (SRC, exc))
    raise SystemExit(2)

if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
