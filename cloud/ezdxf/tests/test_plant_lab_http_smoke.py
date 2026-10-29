"""Exercise initialize -> tools/list -> real MCP tool call -> HTTP file downloads."""
import json
from pathlib import Path
from urllib.parse import urlparse

import ezdxf
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0, str(ROOT / "cloud" / "ezdxf"))

from mcp_cad_cloud.server import mcp


def _result(response):
    for line in response.text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            if "result" in payload:
                return payload["result"]
    raise AssertionError(f"MCP response has no result payload: {response.text[:500]}")


def test_mcp_http_call_and_downloaded_files_are_real_and_reopenable(tmp_path):
    headers = {"Accept": "application/json, text/event-stream"}
    with TestClient(mcp.http_app()) as client:
        initialized = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "plant-lab", "version": "1"}},
        })
        assert initialized.status_code == 200
        session_id = initialized.headers["mcp-session-id"]
        session_headers = {**headers, "mcp-session-id": session_id}
        initialized_body = _result(initialized)
        assert initialized_body["serverInfo"]["name"] == "mcp-cad-cloud"

        listed = client.post("/mcp", headers=session_headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
        })
        assert listed.status_code == 200
        tools = _result(listed)["tools"]
        assert any(tool["name"] == "projetar_residencia" for tool in tools)

        call = client.post("/mcp", headers=session_headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "projetar_residencia", "arguments": {
                "pedido": "Residência térrea de dois quartos, sala, cozinha, lavanderia e banheiro em lote de 10 x 20 m."
            }},
        })
        assert call.status_code == 200
        payload = _result(call)
        assert not payload.get("isError"), payload
        text = next(item["text"] for item in payload["content"] if item.get("type") == "text")
        result = json.loads(text)
        assert result["ok"] is True, result

        for kind, signature in (("dxf", None), ("pdf", b"%PDF-"),
                                ("png", b"\x89PNG\r\n\x1a\n")):
            path = urlparse(result["arquivos"][f"{kind}_url"]).path
            downloaded = client.get(path)
            assert downloaded.status_code == 200
            content = downloaded.content
            assert content
            if signature:
                assert content.startswith(signature)
            if kind == "dxf":
                disk = tmp_path / "mcp-output.dxf"
                disk.write_bytes(content)
                reopened = ezdxf.readfile(disk)
                assert not reopened.audit().has_errors
                assert len(list(reopened.modelspace().query('ARC[layer=="PORTAS"]'))) == 5
