"""Public headless CAD MCP for Render. Desktop COM stays on Windows."""
from __future__ import annotations

import os
from functools import wraps
from inspect import signature, Parameter
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, PlainTextResponse
from mcp_cad_cloud import __version__
from mcp_cad_cloud.build_identity import info
from mcp_cad_cloud.backend import initialize, session_lock, auth_mode, tool_workspace
from mcp_cad_cloud import tools_verified as verified
from mcp_cad_cloud import tools as headless

mcp = FastMCP(
    name="mcp-cad-cloud",
    instructions=(
        "MCP CAD Cloud generates, audits and exports architectural drawings. "
        "For ordinary requests to create, review or export a plant, go straight "
        "to the result, verified findings and DXF/PDF/PNG links; do not volunteer "
        "limitations about the user's computer or make cloud operation sound broken. "
        "Mention the desktop boundary ONLY when the user explicitly asks to "
        "control their local AutoCAD session, open a file on their Windows PC "
        "or edit a native DWG in place. In that case, explain briefly that this "
        "cloud connection creates editable DXF files, and direct desktop "
        "automation requires a separately connected local CAD MCP. "
        "Never invoke desktop COM, system_status, abrir_autocad, drawing_open "
        "for a local file, or request a desktop restart on this cloud server. "
        "For one user prompt describing a supported two-bedroom house, call "
        "projetar_residencia(pedido=...) once, with ONLY pedido; do NOT "
        "add programa unless the user explicitly supplied room areas. "
        "It draws, audits and exports "
        "real DXF plus A3 PDF and PNG URLs. Do not request preview tokens. "
        "If the user asks for a furniture improvement, compare original and "
        "suggested layouts with propor_melhoria_circulacao(pedido=...) once. "
        "This returns separate files; it NEVER applies or overwrites the original. "
        "For unsupported typologies, honestly report unsupported scope; do "
        "not drop requirements. For advanced/manual CAD: start with cad_status, "
        "then planta_templates and "
        "planta_criar_validada(preview); draw with preview_token. "
        "On stateless HTTP clients, always pass workspace_token returned by "
        "the previous tool call when drawing, auditing or exporting DXF. "
        "export_dxf now returns temporary direct HTTPS DXF and ZIP download links. "
        "Use new_drawing for a volatile in-memory DXF and export_dxf before reset. "
        "Raw primitives are available in full profile only for explicit advanced "
        "CAD or unsupported typologies; validate the model first, interrupt walls "
        "at openings, audit, then export."
    ),
)
_EXISTING_DRAWING_TOOLS = {
    "inspect_drawing", "query_entities", "drawing_audit", "quantitativo",
    "export_dxf", "layer_list",
}


def _serialize_session(fn, tool_name: str):
    """Expose workspace_token for newer stateless HTTP MCP clients.

    Legacy session-based clients keep working without the argument.
    No anonymous request can select another user's drawing without the
    randomly generated token returned by the MCP on a previous call.
    """
    @wraps(fn)
    def invoke(*args, workspace_token: str | None = None, **kwargs):
        try:
            with tool_workspace(workspace_token) as minted_token:
                if minted_token and not workspace_token and (
                    tool_name in _EXISTING_DRAWING_TOOLS or (
                        tool_name in {"planta_assistida", "planta_criar_validada"}
                        and kwargs.get("modo", "preview") == "desenhar"
                    )
                ):
                    return {
                        "ok": False,
                        "code": "WORKSPACE_TOKEN_REQUIRED",
                        "error": "passe workspace_token da prévia ou do desenho anterior",
                    }
                with session_lock():
                    result = fn(*args, **kwargs)
                if minted_token and isinstance(result, dict):
                    return {**result, "workspace_token": minted_token}
                return result
        except (ValueError, RuntimeError, PermissionError) as exc:
            return {"ok": False, "code": "WORKSPACE_ERROR", "error": str(exc)}

    # The explicit parameter is in the published MCP schema so agents
    # discover how to preserve a drawing between independent HTTP calls.
    params = list(signature(fn).parameters.values())
    params.append(Parameter("workspace_token", kind=Parameter.KEYWORD_ONLY,
                            default=None, annotation=str | None))
    invoke.__signature__ = signature(fn).replace(parameters=params)
    invoke.__annotations__ = {**getattr(fn, "__annotations__", {}),
                              "workspace_token": str | None}
    return invoke

for name in verified.PUBLIC_TOOLS:
    # High-level verified implementations win on name collisions.
    fn = getattr(verified, name, None) or getattr(headless, name, None)
    if fn is not None:
        mcp.tool(name=name)(_serialize_session(fn, name))


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

@mcp.custom_route("/downloads/{token}/{fmt}", methods=["GET"])
async def download_dxf(request: Request) -> Response:
    """Serve the actual DXF/ZIP bytes; no JSON/base64 or fake file path."""
    from mcp_cad_cloud.downloads import retrieve
    token = request.path_params.get("token", "")
    fmt = request.path_params.get("fmt", "")
    record = retrieve(token, fmt)
    if record is None:
        return PlainTextResponse("Arquivo expirado ou nao encontrado", status_code=404,
                                 headers={"Cache-Control": "no-store"})
    content, mime, filename = record
    return Response(
        content, media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def main() -> None:
    # Test mode is intentionally public. Set MCP_CAD_AUTH_MODE=required to
    # restore Bearer authentication; the API key is not needed while off.
    mode = auth_mode()
    if mode == "required" and len(os.environ.get("MCP_CAD_API_KEY", "")) < 32:
        raise RuntimeError(
            "MCP_CAD_API_KEY de 32+ caracteres é obrigatória com autenticação requerida.")
    initialize()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)

if __name__ == "__main__":
    main()
