"""Public headless CAD MCP for Render. Desktop COM stays on Windows."""
from __future__ import annotations

import os
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp_cad_cloud import __version__
from mcp_cad_cloud.build_identity import info
from mcp_cad_cloud.backend import initialize
from mcp_cad_cloud import tools_verified as verified

mcp = FastMCP(
    name="mcp-cad-cloud",
    instructions=("Public headless ezdxf workspace in metres. This does NOT edit desktop AutoCAD or DWG. "
                  "Changes are in volatile single-user memory. Export before reset. "
                   "Only tools listed here are supported; check ok and entity handles. "
                   "For floor plans use planta_criar_validada: preview first, then draw "
                   "with the returned preview_token. Raw drawing primitives are hidden "
                   "in the default planta_segura profile; set MCP_CAD_PROFILE=full only "
                   "for explicit advanced CAD work."),
)
for name in verified.PUBLIC_TOOLS:
    mcp.tool(name=name)(getattr(verified, name))


def build_info() -> dict[str, str]:
    """Return stable identity and capability boundary for this transport."""
    return info(__version__, "http", "ezdxf")

@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "service": "mcp-cad-cloud", **build_info()})

def main() -> None:
    initialize()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)

if __name__ == "__main__":
    main()
