"""Regressão do programa paramétrico cloud. Não requer AutoCAD COM."""
from copy import deepcopy

import pytest

from mcp_cad_cloud.planta_gerador import ErroPrograma, gerar_modelo
from mcp_cad_cloud import tools_verified
from mcp_cad_cloud.validar_modelo import validar


PROGRAMA = {
    "largura": 10.0,
    "terreno_largura": 12.0,
    "terreno_profundidade": 20.0,
    "recuo_lateral": 1.0,
    "recuo_frente": 3.0,
    "recuo_fundo": 2.0,
    "ambientes": [
        {"nome": "Sala de estar", "area": 18.0},
        {"nome": "Cozinha", "area": 9.0},
        {"nome": "Área de serviço", "area": 4.0},
        {"nome": "Quarto 1", "area": 12.0},
        {"nome": "Quarto 2", "area": 10.0},
        {"nome": "Banheiro social", "area": 4.0},
    ],
}


def test_modelo_preserva_areas_liquidas_e_validador():
    model = gerar_modelo(PROGRAMA)
    audit = validar(model)
    assert audit["ok"], audit["problemas"]
    assert model["resumo_geometria"]["area_ambientes"] == 57.0
    for requisitado in PROGRAMA["ambientes"]:
        a = next(a for a in model["ambientes"] if a["nome"] == requisitado["nome"])
        real = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
        assert real == pytest.approx(requisitado["area"], abs=1e-6)
        assert 0.05 <= a["h"] <= 0.22
    assert model["resumo_geometria"]["corredor_livre"] >= 1.0
    assert len(model["portas"]) == len(PROGRAMA["ambientes"]) + 1


def test_entrada_e_janelas_nao_sobrepostas():
    model = gerar_modelo(PROGRAMA)
    entradas = [(x, y, largura) for x, y, _, largura in model["portas"] if y == 0]
    assert len(entradas) == 1
    for x, y, w in entradas:
        for x1, y1, x2, y2 in model["janelas"]:
            if y1 == y2 == y:
                assert min(x + w, x2) - max(x, x1) <= 0.0


def test_terreno_usa_recuos_informados_sem_afirmar_conformidade():
    model = gerar_modelo(PROGRAMA)
    assert model["terreno"] == (-1.0, -3.0, 11.0, 17.0)
    assert any("NÃO É PROJETO EXECUTIVO" in linha[2] for linha in model["selo"])
    assert any("normas locais" in aviso for aviso in model["avisos"])


def test_suite_without_explicitly_supported_private_bath_is_rejected():
    program = deepcopy(PROGRAMA)
    bedroom = next(room for room in program["ambientes"]
                   if "quarto" in room["nome"].casefold())
    bedroom["nome"] = "Suíte"

    with pytest.raises(ErroPrograma, match="suíte.*não suportada"):
        gerar_modelo(program)


@pytest.mark.parametrize("alteracao", [
    {"largura": float("nan")},
    {"largura": float("inf")},
    {"largura": -1},
    {"terreno_profundidade": 4},
    {"recuo_frente": -2},
    {"terreno_largura": 9},
])
def test_medidas_invalidas_sao_rejeitadas(alteracao):
    program = deepcopy(PROGRAMA)
    program.update(alteracao)
    with pytest.raises(ErroPrograma):
        gerar_modelo(program)


def test_rejeita_banheiro_impraticavel_ao_inves_de_publicar_planta():
    program = deepcopy(PROGRAMA)
    program["ambientes"].extend([
        {"nome": "Suíte", "area": 12},
        {"nome": "Banheiro da suíte", "area": 4},
    ])
    with pytest.raises(ErroPrograma, match="suíte.*não suportada"):
        gerar_modelo(program)


@pytest.mark.parametrize("ambientes", [
    [{"nome": "Sala", "area": float("nan")}, {"nome": "Quarto", "area": 12}],
    [{"nome": "Sala", "area": 10}, {"nome": "Sala", "area": 12}],
    [{"nome": "Cozinha", "area": 10}, {"nome": "Quarto", "area": 12}],
    [{"nome": "Sala", "area": 10, "setor": "indefinido"}, {"nome": "Quarto", "area": 12}],
])
def test_nao_aceita_programa_ambiguo(ambientes):
    with pytest.raises(ErroPrograma):
        gerar_modelo({"largura": 10, "ambientes": ambientes})


def test_fluxo_mcp_publico_preview_desenhar_exportar():
    catalogo = tools_verified.planta_templates()
    assert any(x["id"] == "programa_sob_medida" for x in catalogo["templates"])
    preview = tools_verified.planta_criar_validada(
        programa=PROGRAMA, modo="preview", template="programa_sob_medida")
    assert preview["ok"], preview
    assert preview["backend"] == "ezdxf"
    assert preview["resumo"]["ambientes"] == 7
    assert preview["preview_token"]
    assert preview["avisos"]
    modelo = preview["modelo"]
    assert validar(modelo)["ok"]
    sem_token = tools_verified.planta_criar_validada(
        programa=PROGRAMA, modo="desenhar", template="programa_sob_medida")
    assert sem_token["ok"] is False
    assert sem_token["code"] == "WORKFLOW_REQUIRED"
    desenho = tools_verified.planta_criar_validada(
        programa=PROGRAMA, modo="desenhar", template="programa_sob_medida",
        nome="teste_programa_custom", preview_token=preview["preview_token"])
    assert desenho["ok"], desenho
    assert desenho["entities"] > 30
    from mcp_cad_cloud.backend import _ensure
    desenho_dxf = _ensure()
    rotulos = list(desenho_dxf.modelspace().query("TEXT"))
    # Os textos de ambiente precisam estar realmente centrados no DXF.
    nomes = {a["nome"] for a in preview["modelo"]["ambientes"]}
    assert any(e.dxf.get("halign", 0) == 1 and e.dxf.get("valign", 0) == 2
               for e in rotulos if e.dxf.text in nomes)
    cotas = list(desenho_dxf.modelspace().query("DIMENSION"))
    textos_cotas = [ent.text for dim in cotas for ent in dim.virtual_entities()
                    if ent.dxftype() == "MTEXT"]
    assert any(f"{PROGRAMA['largura']:.2f} m" in valor.replace(",", ".") for valor in textos_cotas), textos_cotas
    assert tools_verified.export_dxf()["ok"]


def test_regressao_templates_fixos():
    assert tools_verified.planta_criar_validada(modo="preview")["ok"]
    assert tools_verified.planta_criar_validada(
        programa={"template": "tiny_house_10m2"}, modo="preview")["ok"]
