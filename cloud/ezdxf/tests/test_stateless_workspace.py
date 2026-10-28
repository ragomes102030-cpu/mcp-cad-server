"""End-to-end stateless MCP HTTP workspace-token compatibility tests.

MCP 2026-07-28 clients do not send Mcp-Session-Id on tool calls.
"""
from types import SimpleNamespace

import pytest

from mcp_cad_cloud import server, tools_verified as cad
from mcp_cad_cloud.backend import tool_workspace, session_key
from test_layout_compacto import CASA


@pytest.fixture
def anonymous_request(monkeypatch):
    from fastmcp.server import dependencies
    monkeypatch.setenv("MCP_CAD_AUTH_MODE", "off")
    monkeypatch.setattr(
        dependencies, "get_http_request",
        lambda: SimpleNamespace(headers={"user-agent": "stateless-test"}))


def test_anonymous_status_mints_workspace_without_shared_global_fallback(anonymous_request):
    run=server._serialize_session(cad.cad_status,"cad_status")
    a,b=run(),run()
    assert a["ok"] and b["ok"], (a,b)
    assert len(a["workspace_token"])==43
    assert a["workspace_token"] != b["workspace_token"]
    assert a["isolation"] == "mcp_session_or_workspace_token"


def test_stateless_preview_draw_audit_export_isolated(anonymous_request):
    status=server._serialize_session(cad.cad_status,"cad_status")
    first=status()["workspace_token"]
    second=status()["workspace_token"]
    setup=server._serialize_session(cad.new_drawing,"new_drawing")
    preview=server._serialize_session(cad.planta_criar_validada,"planta_criar_validada")
    audit=server._serialize_session(cad.drawing_audit,"drawing_audit")
    export=server._serialize_session(cad.export_dxf,"export_dxf")
    inspect=server._serialize_session(cad.inspect_drawing,"inspect_drawing")
    assert setup("TEST A",workspace_token=first)["ok"]
    assert setup("TEST B",workspace_token=second)["ok"]
    p=preview(programa=CASA,template="programa_sob_medida",
              modo="preview",workspace_token=first)
    assert p["ok"],p
    assert p["workspace_token"] == first
    unauthorized=preview(programa=CASA,template="programa_sob_medida",
                         modo="desenhar",preview_token=p["preview_token"],
                         workspace_token=second)
    assert not unauthorized["ok"]
    assert inspect(workspace_token=second)["entities"]==0
    # A token consumed in B is intentionally one-use. Re-preview in A.
    p=preview(programa=CASA,template="programa_sob_medida",
              modo="preview",workspace_token=first)
    drawn=preview(programa=CASA,template="programa_sob_medida",modo="desenhar",
                  preview_token=p["preview_token"],workspace_token=first)
    assert drawn["ok"],drawn
    assert drawn["workspace_token"]==first
    assert audit(workspace_token=first)["errors"]==0
    assert export(workspace_token=first)["ok"]
    assert inspect(workspace_token=first)["entities"]>30
    assert inspect(workspace_token=second)["entities"]==0
    assert not audit()["ok"]
    assert audit()["code"]=="WORKSPACE_TOKEN_REQUIRED"
    assert not export(workspace_token="not-a-real-token")["ok"]


def test_mcp_schema_advertises_workspace_token():
    from inspect import signature
    wrapped=server._serialize_session(cad.planta_criar_validada,"planta_criar_validada")
    sig=signature(wrapped)
    assert "workspace_token" in sig.parameters
    assert sig.parameters["workspace_token"].default is None
    assert "programa" in sig.parameters
    assert "preview_token" in sig.parameters
