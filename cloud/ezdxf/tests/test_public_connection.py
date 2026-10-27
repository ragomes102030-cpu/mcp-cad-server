from pathlib import Path


def test_cloud_server_is_public_without_token_verifier():
    server = (Path(__file__).parents[1] / "mcp_cad_cloud" / "server.py").read_text(encoding="utf-8")

    assert "StaticTokenVerifier" not in server
    assert "CAD_MCP_AUTH_TOKEN" not in server
