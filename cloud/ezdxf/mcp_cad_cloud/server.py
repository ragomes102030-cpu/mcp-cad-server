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
from mcp_cad_cloud import tools as headless

mcp = FastMCP(
    name="mcp-cad-cloud",
    instructions=(
        "CLOUD HEADLESS: this server runs on Render/Linux with ezdxf only. "
        "It cannot see, open, control or save the user's AutoCAD, Windows desktop "
        "or DWG files. Never call or request AutoCAD COM, system_status, "
        "abrir_autocad, drawing_open for a desktop file, or an AutoCAD restart. "
        "Start with cad_status, then planta_templates and "
        "planta_criar_validada(preview); draw with the returned preview_token. "
        "Use new_drawing for a volatile in-memory DXF and export_dxf before reset. "
        "Raw primitives are available in full profile only for explicit advanced "
        "CAD or unsupported typologies; validate the model first, interrupt walls "
        "at openings, audit, then export."
    ),
)
for name in verified.PUBLIC_TOOLS:
    # High-level verified implementations win on name collisions.  The
    # remaining tools come from the ezdxf headless primitive registry.
    fn = getattr(verified, name, None) or getattr(headless, name, None)
    if fn is not None:
        mcp.tool(name=name)(fn)


def build_info() -> dict[str, str]:
    """Return stable identity and capability boundary for this transport."""
    return {
        **info(__version__, "http", "ezdxf"),
        "profile": verified.PROFILE,
        "tool_count": str(len(verified.PUBLIC_TOOLS)),
    }

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
