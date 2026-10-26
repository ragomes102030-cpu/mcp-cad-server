# -*- coding: utf-8 -*-
"""FastMCP HTTP server — mcp-cad-cloud (ezdxf headless, sem AutoCAD).

Rodar:
    python -m mcp_cad_cloud.server

Saída:
    INFO:     Uvicorn running on http://127.0.0.1:8000/mcp
    INFO:     MCP server "mcp-cad-cloud" pronto (transport=http)

O cliente MCP (Claude Code, etc.) se conecta via HTTP para o endpoint /mcp.

Nota: este é o 'cloud' isolado (cloud/ezdxf). O mcp-cad-server original
(contém COM/pywin32) fica intacto em master.
"""

from __future__ import annotations

import logging
import os
import sys

# garante que o package local (mcp_cad_cloud) seja importável
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fastmcp import FastMCP

from mcp_cad_cloud import __version__, CONTRATO
from mcp_cad_cloud.tools import TOOLS

# caminho e porta
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))


# ---------- inicialização do backend (ezdxf headless) ----------
def _init_backend() -> None:
    try:
        from mcp_cad_cloud.backend import initialize
    except Exception:
        return
    initialize()


def _on_connect() -> dict:
    """Chamado quando o cliente se conecta (informação de setup)."""
    from mcp_cad_cloud.backend import ezx_version

    try:
        from mcp_cad_cloud.backend import _ensure, state_summary
    except Exception:
        return {"backend": "not_ready", "ezdxf": ezx_version()}
    try:
        st = state_summary()
        return {"backend": "ezdxf", "ok": st.get("ok", False), "ezdxf": ezx_version()}
    except Exception:
        return {"backend": "ezdxf", "ok": False, "ezdxf": ezx_version()}


# ---------- montagem do MCP ----------
mcp = FastMCP(
    name="mcp-cad-cloud",
    instructions=(
        "MCP cloud-ready para mapeamento de plantas. "
        "Backend: ezdxf headless (Linux, sem AutoCAD). "
        "Use as ferramentas do CONTRATO (draw_*, layer_*, block_*, export_dxf, "
        "plot_pdf, render_png, quantitativo, state_summary, etc.). "
        "Todas as ferramentas atuam sobre um desenho em memória (drawing_atual). "
        "Comece com new_drawing(), desenhe, exporte (export_dxf/plot_pdf/render_png) "
        "e finalize com state_summary(). Invariável de nome de desenho: _drawing_name."
    ),
)

# registrar todas as ferramentas do mapa
for _nome, _fn in TOOLS.items():
    mcp.tool(_nome)(_fn)

# relatório de estado + healthz (endpoint HTTP)
@mcp.tool()
def status() -> dict:
    """Status do backend (ezdxf level, versão)."""
    return _on_connect()


@mcp.tool()
def healthz() -> dict:
    """Endpoint de healthcheck para o Render deploy."""
    return {
        "servico": "mcp-cad-cloud",
        "versão": __version__,
        "backend": "ezdxf",
        "status": "ok",
        "endpoint": "/mcp",
        "transport": "http",
    }


# ---------- entry point ----------
def main() -> None:
    _init_backend()
    print(f"[mcp-cad-cloud] FastMCP pronto (HTTP; backend ezdxf; v{__version__})", flush=True)
    # fastmcp.run(transport="http", host=HOST, port=PORT)
    mcp.run(transport="http", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
