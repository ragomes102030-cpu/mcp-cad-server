from pathlib import Path
import sys

from starlette.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "cloud" / "ezdxf")]

from mcp_cad_cloud import __version__
from mcp_cad_cloud.server import mcp


def test_healthz_reports_common_build_identity():
    with TestClient(mcp.http_app()) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["version"] == __version__
    assert body["transport"] == "http"
    assert body["backend"] == "ezdxf"
    assert body["revision"]


def test_initialize_is_public_without_bearer_token():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "contract-test", "version": "1"},
        },
    }
    with TestClient(mcp.http_app()) as client:
        response = client.post(
            "/mcp", json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert response.status_code != 401
    assert response.status_code == 200
    assert '"jsonrpc":"2.0"' in response.text


def test_render_builds_the_cloud_subpackage_from_repository_root():
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "pip install -e ./cloud/ezdxf" in render
    assert "HOST" in render
