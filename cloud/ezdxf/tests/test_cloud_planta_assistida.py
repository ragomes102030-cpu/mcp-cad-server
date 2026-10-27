from mcp_cad_cloud.planta_assistida import build_assisted_model, planta_assistida
from mcp_cad_cloud import tools_verified


def test_cloud_template_has_real_window_gaps_and_back_dimensions():
    model = build_assisted_model()

    assert model["parede_sem_sobreposicao"] is True
    assert {(a, b) for a, b, y, _ in model["cotas_h"] if y > 11} >= {
        (0, 4.6), (4.6, 8.6), (8.6, 12), (0, 12)
    }


def test_cloud_assisted_tool_preview_is_headless():
    result = planta_assistida(modo="preview")

    assert result["ok"] is True
    assert result["backend"] == "ezdxf"
    assert result["resumo"]["portas"] == 11
    assert result["resumo"]["janelas"] == 10


def test_cloud_assisted_tool_draws_real_entities_in_expected_layers():
    result = tools_verified.planta_assistida(modo="desenhar", nome="planta_corrigida_cloud")

    assert result["ok"] is True
    assert result["backend"] == "ezdxf"
    assert result["entities"] > 100
    assert tools_verified.cad_status()["drawing"] == "planta_corrigida_cloud"

