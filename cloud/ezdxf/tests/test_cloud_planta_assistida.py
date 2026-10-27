from mcp_cad_cloud.planta_assistida import build_assisted_model, planta_assistida
from mcp_cad_cloud import tools_verified
from mcp_cad_cloud.validar_modelo import validar


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


def test_cloud_template_catalog_is_read_only_and_parity_ready():
    result = tools_verified.planta_templates()

    assert result["ok"] is True
    assert result["template_padrao"] == "residencia_unifamiliar_12x11"
    assert {item["id"] for item in result["templates"]} >= {
        "residencia_unifamiliar_12x11", "tiny_house_10m2"
    }


def test_cloud_rejects_unsupported_dimensions_before_drawing():
    result = planta_assistida(programa={
        "largura_externa": 2.5,
        "profundidade_externa": 4.0,
        "area_util_minima": 10,
    }, modo="preview")

    assert result["ok"] is False
    assert result["code"] == "TEMPLATE_NOT_SUPPORTED"
    assert result["templates"]
    assert result["proxima_acao"] == "escolher um template suportado"


def test_cloud_assisted_tool_draws_real_entities_in_expected_layers():
    result = tools_verified.planta_assistida(modo="desenhar", nome="planta_corrigida_cloud")

    assert result["ok"] is True
    assert result["backend"] == "ezdxf"
    assert result["entities"] > 100
    assert tools_verified.cad_status()["drawing"] == "planta_corrigida_cloud"


def test_cloud_validator_is_blocking_for_overlapping_walls():
    model = build_assisted_model()
    model["paredes"].append(tuple(model["paredes"][0]))

    result = tools_verified.validar_planta(modelo=model)

    assert result["ok"] is False
    assert any(p["chave"] == "parede-duplicada" for p in result["validacao"]["erros"])

