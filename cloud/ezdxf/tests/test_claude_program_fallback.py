"""Regression of Claude's incomplete/over-parameterized CAD tool calls.

The user should be able to request a 10x20 m two-bedroom house using one
sentence, without knowing internal hall dimensions or room area ratios.
"""
from copy import deepcopy

import pytest

from mcp_cad_cloud.projeto_automatico import interpretar_pedido
from mcp_cad_cloud.planta_gerador import gerar_modelo, ErroPrograma
from mcp_cad_cloud import tools_verified as cad


PEDIDO = ("Desenhe uma residencia terrea com dois quartos, sala e cozinha "
          "integradas, banheiro social e lavanderia no terreno de 10 x 20 m.")


def test_default_one_call_matches_actual_10x20_lot_and_validated_plan():
    p, premissas = interpretar_pedido(PEDIDO, None)
    assert p["largura"] == 9.0
    assert p["terreno_largura"] == 10.0
    assert p["terreno_profundidade"] == 20.0
    assert len(p["ambientes"]) == 6
    assert any("Areas" in x for x in premissas)
    model = gerar_modelo(p)
    x0, y0, x1, y1 = model["terreno"]
    assert (x1-x0, y1-y0) == pytest.approx((10, 20))
    assert model["resumo_geometria"]["area_construida"] == pytest.approx(77.40)
    assert len(model["moveis"]) == 12
    assert len(model["cotas_h_2d"]) == len(model["cotas_v_2d"]) == 4


def test_partial_program_does_not_erase_safe_room_defaults():
    p, premissas = interpretar_pedido(PEDIDO, {
        "largura": 9.0, "terreno_largura": 10.0, "terreno_profundidade": 20.0})
    assert len(p["ambientes"]) == 6
    assert p["ambientes"][-1]["area"] == 5.0
    assert any("lista ambientes foi omitida" in item for item in premissas)
    assert gerar_modelo(p)["resumo_geometria"]["area_construida"] == pytest.approx(77.40)


def test_six_names_without_areas_are_filled_and_disclosed():
    rows = [
        {"nome":"Sala"}, {"nome":"Cozinha"}, {"nome":"Lavanderia"},
        {"nome":"Quarto 1"}, {"nome":"Quarto 2"}, {"nome":"Banheiro social"},
    ]
    p, premissas = interpretar_pedido(PEDIDO, {"ambientes": rows})
    assert [a["area"] for a in p["ambientes"]] == [18,9,5,12,10,5]
    assert len([x for x in premissas if "Area de " in x]) == 6
    assert gerar_modelo(p)["resumo_geometria"]["largura"] == 9.


def test_explicit_bathroom_areas_are_preserved_and_infeasibility_explained():
    rows = deepcopy(interpretar_pedido(PEDIDO, None)[0]["ambientes"])
    for bad in (4.5, 6.0):
        rows[-1]["area"] = bad
        p, _ = interpretar_pedido(PEDIDO, {"ambientes":rows})
        assert p["ambientes"][-1]["area"] == bad
        with pytest.raises(ErroPrograma, match="intervalo geometrico"):
            gerar_modelo(p)
    rows[-1]["area"] = 5.0
    p, _ = interpretar_pedido(PEDIDO, {"ambientes": rows})
    assert gerar_modelo(p)["resumo_geometria"]["largura"] == 9.


def test_combined_living_kitchen_label_gives_guidance_not_fake_success():
    rows = [
        {"nome":"Sala e Cozinha integradas", "area":27},
        {"nome":"Lavanderia", "area":5},
        {"nome":"Quarto 1", "area":12},
        {"nome":"Quarto 2", "area":10},
        {"nome":"Banheiro social", "area":5},
        {"nome":"Hall", "area":3},
    ]
    with pytest.raises(ValueError, match="separados"):
        interpretar_pedido(PEDIDO, {"ambientes":rows})


def test_conflicting_lot_is_rejected_instead_of_silently_replaced():
    with pytest.raises(ValueError, match="contradiz"):
        interpretar_pedido(PEDIDO, {"terreno_largura":12.0})


def test_real_mcp_one_call_still_exports_when_no_program():
    r = cad.projetar_residencia(PEDIDO)
    assert r["ok"], r
    assert r["quantitativo"]["entities"] == 175
    assert r["quantitativo"]["by_layer"]["EIXOS-PAREDES"] == 22
    assert r["quantitativo"]["by_layer"]["PISOS"] == 7
    assert r["quantitativo"]["quantitativos_construtivos"]["resumo"]["pisos"] == 7
    assert r["auditoria"]["errors"] == 0
    assert all(r["arquivos"].get(name) for name in ("dxf_url","pdf_url","png_url","zip_url"))
