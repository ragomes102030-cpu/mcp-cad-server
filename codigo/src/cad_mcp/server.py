# -*- coding: utf-8 -*-
r"""mcp-cad-server — servidor MCP (stdio) com as ferramentas de CAD/planta/quantitativo.

Registrar no cliente MCP (transport stdio):
    command: python  (ou o caminho absoluto do python do seu ambiente)
    args   : -m cad_mcp.server   (se instalado)  ou  <caminho>\src\cad_mcp\server.py

Exemplo de bloco pronto: `instalacao\mcp-config.json`.

Variaveis de ambiente:
    MCP_CAD_BACKEND = auto | com | autocad | file_ipc | ezdxf   (default: auto)
        auto    -> COM se houver AutoCAD aberto; senao ezdxf headless
        com     -> obriga COM (exige AutoCAD aberto)
        autocad -> COM ou, na falta dele, ponte LISP por arquivo
        ezdxf   -> sempre headless
    MCP_CAD_TEMP    = pasta de trabalho do LISP (default C:/temp/mcp_cad_com,
                      SEM espacos: `SendCommand` corta o texto no espaco)
    MCP_CAD_ACCORE  = caminho explicito do accoreconsole.exe
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastmcp import FastMCP  # noqa: E402

from cad_mcp import __version__, tools  # noqa: E402
from cad_mcp.build_identity import revision  # noqa: E402
from cad_mcp.tool_contract import guarded

mcp = FastMCP(
    name="mcp-cad-server",
    instructions=(
        "Motor CAD próprio: desenha plantas, lê desenhos e calcula quantitativos. "
        "Com o AutoCAD aberto opera no desenho vivo pelo canal COM (sem roubar foco); "
        "sem AutoCAD, opera headless (ezdxf) e usa o accoreconsole para DXF/PDF. "
        "Para plantas, use planta_criar_validada: preview primeiro e depois desenho "
        "com o preview_token; o perfil planta_segura oculta primitivas de desenho. "
        "Use MCP_CAD_PROFILE=full somente para CAD avancado explicito. "
        f"versão {__version__}"
    ),
)


def build_info() -> dict[str, str]:
    """Return stable identity and capability boundary for this transport."""
    return {
        "version": __version__,
        "revision": revision(),
        "transport": "stdio",
        "backend": "autocad-or-headless",
    }

for _fn in tools.PUBLIC_TOOLS:
    # nome publico no padrao do autocad-mcp-pro (entity_create_line, drawing_save...)
    mcp.tool(name=tools.nome_publico(_fn))(guarded(_fn))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
