"""Security + built-dimension acceptance tests, no deployment or real secrets."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from mcp_cad_cloud.backend import _ensure, reset_drawing, test_session as session_scope, state_summary
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.planta_assistida import wall_boundary_segments
from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA


def test_exterior_dimensions_area_and_recuos_are_real_not_axis_based():
    m = gerar_modelo(CASA)
    walls = wall_boundary_segments(m["paredes"], m["espessura_parede"])
    x_values = [v for x1, _, x2, _ in walls for v in (x1, x2)]
    y_values = [v for _, y1, _, y2 in walls for v in (y1, y2)]
    eps = 1e-8
    assert min(x_values) == pytest.approx(0.0, abs=eps)
    assert max(x_values) == pytest.approx(9.0, abs=eps)
    assert min(y_values) == pytest.approx(0.0, abs=eps)
    assert max(y_values) == pytest.approx(8.60, abs=eps)
    assert m["resumo_geometria"]["area_construida"] == pytest.approx(77.40)
    x0, y0, x1, y1 = m["terreno"]
    assert (x0, y0, x1, y1) == pytest.approx((-0.5, -3, 9.5, 17))
    assert min(x_values)-x0 == pytest.approx(.5)
    assert x1-max(x_values) == pytest.approx(.5)
    assert min(y_values)-y0 == pytest.approx(3.)
    assert y1-max(y_values) == pytest.approx(8.4)


def test_narrow_lot_rejected_using_exterior_faces():
    params=deepcopy(CASA)
    params["terreno_largura"]=9.5
    params["recuo_lateral"]=0.5
    with pytest.raises(ValueError, match="largura do terreno"):
        gerar_modelo(params)


def test_two_sessions_own_distinct_docs_names_and_tokens():
    with session_scope("alice-session"):
        reset_drawing()
        cad.new_drawing("ALICE")
        cad.layer_create("PAREDES", 1)
        cad.draw_line([0,0],[2,0],"PAREDES")
        assert cad.inspect_drawing()["entities"] == 1
        alice_preview=cad.planta_criar_validada(
            programa=CASA, template="programa_sob_medida", modo="preview")
        assert alice_preview["ok"]
    with session_scope("bob-session"):
        reset_drawing()
        cad.new_drawing("BOB")
        assert cad.inspect_drawing()["entities"] == 0
        assert cad.inspect_drawing()["drawing"] == "BOB"
        unauthorized=cad.planta_criar_validada(
            programa=CASA, template="programa_sob_medida", modo="desenhar",
            preview_token=alice_preview["preview_token"])
        assert not unauthorized["ok"]
        assert cad.inspect_drawing()["entities"] == 0
    with session_scope("alice-session"):
        assert cad.inspect_drawing()["entities"] == 1
        assert cad.inspect_drawing()["drawing"] == "ALICE"
        preview=cad.planta_criar_validada(
            programa=CASA, template="programa_sob_medida", modo="preview")
        assert preview["ok"]
        drew=cad.planta_criar_validada(
            programa=CASA, template="programa_sob_medida", modo="desenhar",
            preview_token=preview["preview_token"])
        assert drew["ok"]
    with session_scope("bob-session"):
        assert cad.inspect_drawing()["entities"] == 0
        assert cad.inspect_drawing()["drawing"] == "BOB"


def test_remote_http_requires_long_api_key_and_session(monkeypatch):
    from fastmcp.server import dependencies
    from mcp_cad_cloud.backend import session_key
    monkeypatch.setattr(dependencies, "get_http_request", lambda: SimpleNamespace(
        headers={"mcp-session-id": "session-123"}))
    monkeypatch.delenv("MCP_CAD_API_KEY", raising=False)
    with pytest.raises(PermissionError,match="MCP_CAD_API_KEY"):
        session_key()
    monkeypatch.setenv("MCP_CAD_API_KEY","A"*40)
    with pytest.raises(PermissionError,match="credenciais"):
        session_key()
    monkeypatch.setattr(dependencies, "get_http_request", lambda: SimpleNamespace(
        headers={"mcp-session-id": "session-123", "authorization": "Bearer "+"A"*40}))
    assert session_key() == "mcp:session-123"
    monkeypatch.setattr(dependencies, "get_http_request", lambda: SimpleNamespace(
        headers={"authorization": "Bearer "+"A"*40}))
    with pytest.raises(RuntimeError,match="sessão MCP ausente"):
        session_key()


def test_mcp_does_not_expose_unimplemented_noop_headless_commands():
    from mcp_cad_cloud import tools_verified as verified
    advertised=set(verified.PUBLIC_TOOLS)
    assert "planta_criar_validada" in advertised
    assert "draw_line" in advertised
    assert "command_line" not in advertised
    assert "move_entity" not in advertised
    assert "plot_pdf" not in advertised
    assert "arch_wall" not in advertised
