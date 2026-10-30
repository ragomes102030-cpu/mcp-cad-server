"""The cloud MCP must not present its desktop boundary as a routine failure.

Exercise the public MCP initialize response rather than checking source text
alone: agents consume serverInfo.instructions during connection.
"""
import json

from starlette.testclient import TestClient

from mcp_cad_cloud.server import mcp
from mcp_cad_cloud.tools_verified import cad_status, planta_templates


def _mcp_result(response):
    for line in response.text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            if "result" in payload:
                return payload["result"]
    raise AssertionError(f"Resposta MCP sem result: {response.text[:400]}")


def test_initialize_leads_with_generation_and_only_contextual_desktop_warning():
    with TestClient(mcp.http_app()) as client:
        response = client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "cloud-guidance-contract", "version": "1"},
                },
            },
        )
    assert response.status_code == 200
    result = _mcp_result(response)
    instructions = result["instructions"]
    assert instructions.startswith("MCP CAD Cloud generates")
    assert "projetar_residencia(pedido=...)" in instructions
    assert "do not volunteer" in instructions
    assert "ONLY when the user explicitly asks" in instructions
    assert "requires a separately connected local CAD MCP" in instructions
    assert "Never invoke desktop COM" in instructions
    # Old startup statement caused the assistant to report an irrelevant failure.
    assert "It cannot see, open, control or save" not in instructions


def test_cad_status_suggests_generation_without_unsolicited_desktop_failure():
    status = cad_status()
    assert status["ok"] is True
    assert status["backend"] == "ezdxf"
    assert status["autocad_available"] is False  # truthful capability boundary remains
    assert "projetar_residencia" in status["next_step"]
    assert "nao tente abrir" not in status["next_step"].lower()
    templates = planta_templates()
    assert templates["autocad"]["disponivel"] is False
    assert "dxF".casefold() in templates["autocad"]["acao"].casefold()
    assert "nao tentar abrir" not in templates["autocad"]["acao"].lower()
