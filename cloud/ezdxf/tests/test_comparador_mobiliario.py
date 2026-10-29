"""Regression for non-destructive, independent furniture proposal."""
import pytest

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure

BRIEF = ("Desenhe residência térrea com dois quartos, banheiro social, "
         "sala e cozinha integradas e lavanderia, em terreno de 10 x 20 m.")


def test_comparison_keeps_clear_baseline_and_does_not_propose_unneeded_change():
    result=cad.propor_melhoria_circulacao(BRIEF)
    assert result["ok"],result
    assert result["modo"]=="comparacao_sem_aplicacao"
    assert result["alteracoes_aplicadas_ao_original"] is False
    assert result["original"]["auditoria_circulacao"]["ok"]
    assert result["original"]["auditoria_geometrica"]["ok"]
    assert result["candidatas_avaliadas"] == 0
    assert not result["alternativa_disponivel"]
    assert "mobiliario identificavel proximo ao gargalo" in result["motivo"]

    original_urls=result["original"]["arquivos"]
    assert all(original_urls.get(k) for k in ("dxf_url","pdf_url","png_url","zip_url"))
    # The in-session drawing must retain the original furniture footprint.
    furniture=list(_ensure().modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]'))
    assert len(furniture)==12
    original_m03=[tuple(p[:2]) for p in furniture[2].get_points("xy")]
    assert [coord for point in original_m03 for coord in point] == pytest.approx([5.52,.30,6.25,.30,6.25,2.43,5.52,2.43])
    assert [tuple(v[:2]) for v in furniture[2].get_points("xy")] == original_m03


def test_no_improvement_does_not_publish_unjustified_proposal(monkeypatch):
    from mcp_cad_cloud import comparador_mobiliario as lib
    monkeypatch.setattr(lib, "_candidate_safe",lambda before,after:False)
    response=cad.propor_melhoria_circulacao(BRIEF)
    assert response["ok"],response
    assert response["alternativa_disponivel"] is False
    assert response["alteracoes_aplicadas_ao_original"] is False
    assert "proposta" not in response
    assert "arquivos" in response["original"]


def test_unsupported_brief_does_not_propose_plan():
    response=cad.propor_melhoria_circulacao("Desenhe um sobrado com cinco quartos.")
    assert not response["ok"]
    assert response.get("alternativa_disponivel",False) is False
    assert response["code"] == "INVALID_INPUT"
    assert "sobrado" in response["error"]
