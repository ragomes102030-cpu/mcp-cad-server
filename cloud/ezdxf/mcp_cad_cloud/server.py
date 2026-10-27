"""Authenticated, single-user headless CAD MCP for Render. Desktop COM stays on Windows."""
from __future__ import annotations

import os
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp_cad_cloud import __version__
from mcp_cad_cloud.backend import initialize
from mcp_cad_cloud import tools_verified as verified

_token = os.environ.get("CAD_MCP_AUTH_TOKEN", "")
if len(_token) < 24:
    raise RuntimeError("CAD_MCP_AUTH_TOKEN must be set to a secret of at least 24 characters")

mcp = FastMCP(
    name="mcp-cad-cloud",
    auth=StaticTokenVerifier(tokens={_token: {"sub": "cad-owner", "client_id": "cad-private"}}),
    instructions=("Private headless ezdxf workspace in metres. This does NOT edit desktop AutoCAD or DWG. "
                  "Changes are in volatile single-user memory. Export before reset. "
                  "Only tools listed here are supported; check ok and entity handles."),
)
for name in verified.TOOLS:
    mcp.tool(name=name)(getattr(verified, name))

@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "service": "mcp-cad-cloud", "version": __version__})

def main() -> None:
    initialize()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)

if __name__ == "__main__":
    main()
