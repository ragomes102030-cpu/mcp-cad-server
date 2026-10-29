"""Exercise initialize -> tools/list -> real MCP tool call -> HTTP file downloads."""
import json
from pathlib import Path
import io
import zipfile
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


def test_mcp_http_exposes_and_executes_licensing_package(tmp_path):
    from test_layout_compacto import CASA

    headers = {"Accept": "application/json, text/event-stream"}
    context = {
        "project_name": "Casa compacta MCP", "use": "residencial_unifamiliar",
        "typology": "compacto_2quartos", "municipality": None, "state": None,
        "storeys": 1, "lot_width_m": 10, "lot_depth_m": 20,
        "requested_rooms": ["Sala de estar", "Cozinha", "Área de serviço",
                            "Quarto 1", "Quarto 2", "Banheiro social"],
        "stage": "licenciamento",
    }
    envelope = {
        "floor_level_m": 0, "wall_height_m": 2.8, "door_head_m": 2.1,
        "window_sill_m": .9, "window_head_m": 2.2, "roof_type": "gable",
        "roof_pitch_degrees": 25, "roof_overhang_m": .45, "ridge_axis": "x",
    }
    sheets = [{
        "paper_format": "A3", "orientation": "landscape", "scale": 50,
        "margin_mm": 10, "sheet_id": "ARQ-01",
        "viewports": [{"view_id": "ARQ-PLANTA", "x_mm": 20, "y_mm": 70,
                       "width_mm": 220, "height_mm": 200}],
    }]
    title_block = {
        "project_name": context["project_name"], "municipality": None,
        "state": None, "owner": "", "designer": "",
        "professional_registration": "", "issue_date": "2026-10-29",
        "revision": "R00",
    }
    with TestClient(mcp.http_app()) as client:
        initialized = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 11, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "licensing-smoke", "version": "1"}},
        })
        assert initialized.status_code == 200
        session_headers = {**headers, "mcp-session-id": initialized.headers["mcp-session-id"]}
        listed = client.post("/mcp", headers=session_headers, json={
            "jsonrpc": "2.0", "id": 12, "method": "tools/list", "params": {},
        })
        assert "projetar_pacote_licenciamento" in {
            item["name"] for item in _result(listed)["tools"]
        }
        call = client.post("/mcp", headers=session_headers, json={
            "jsonrpc": "2.0", "id": 13, "method": "tools/call",
            "params": {"name": "projetar_pacote_licenciamento", "arguments": {
                "programa": CASA, "contexto": context, "envelope": envelope,
                "folhas": sheets, "carimbo": title_block,
            }},
        })
        assert call.status_code == 200
        payload = _result(call)
        assert not payload.get("isError"), payload
        result = json.loads(next(item["text"] for item in payload["content"]
                                 if item.get("type") == "text"))
        assert result["ok"] is True, result
        assert result["licensing_readiness"] == "review_required"
        zip_path = urlparse(result["arquivos"]["zip_url"]).path
        response = client.get(zip_path)
        assert response.status_code == 200
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        assert {"ARQ-01.dxf", "ARQ-01.pdf", "ARQ-01.png", "report.json"} <= set(archive.namelist())
        dxf_path = tmp_path / "ARQ-01.dxf"
        dxf_path.write_bytes(archive.read("ARQ-01.dxf"))
        reopened = ezdxf.readfile(dxf_path)
        assert reopened.header["$INSUNITS"] == ezdxf.units.MM
        assert not reopened.audit().has_errors
