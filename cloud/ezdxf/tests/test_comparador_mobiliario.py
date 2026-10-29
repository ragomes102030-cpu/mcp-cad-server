"""Regression for non-destructive, independent furniture proposal."""
import pytest

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure

BRIEF = ("Desenhe residência térrea com dois quartos, banheiro social, "
         "sala e cozinha integradas e lavanderia, em terreno de 10 x 20 m.")


def test_comparison_preserves_original_and_requires_verified_gain():
    result=cad.propor_melhoria_circulacao(BRIEF)
    assert result["ok"],result
    assert result["modo"]=="comparacao_sem_aplicacao"
    assert result["alteracoes_aplicadas_ao_original"] is False
    assert result["original"]["auditoria_circulacao"]["ok"]
    assert result["original"]["auditoria_geometrica"]["ok"]
    assert result["candidatas_avaliadas"] > 0

    original_urls=result["original"]["arquivos"]
    assert all(original_urls.get(k) for k in ("dxf_url","pdf_url","png_url","zip_url"))
    # The in-session drawing must retain the original furniture footprint.
    furniture=list(_ensure().modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]'))
    assert len(furniture)==12
    original_m03=[tuple(p[:2]) for p in furniture[2].get_points("xy")]
    assert [coord for point in original_m03 for coord in point] == pytest.approx([5.92,.30,6.65,.30,6.65,2.43,5.92,2.43])

    assert result["alternativa_disponivel"],result
    p=result["proposta"]
    assert p["status"]=="para_revisao_humana_nao_aplicada"
    assert p["ganho_estimado_m"] >= .10
    assert p["largura_depois_estimativa_m"] > p["largura_antes_estimativa_m"]
    assert p["movel"] == "MOVEL-03"
    assert p["rotacionado_90_graus"] is True
    original=p["posicao_original_m"]
    alternate=p["posicao_proposta_m"]
    original_area=(original[2]-original[0])*(original[3]-original[1])
    alternate_area=(alternate[2]-alternate[0])*(alternate[3]-alternate[1])
    assert alternate_area == pytest.approx(original_area,abs=1e-6)
    assert p["posicao_original_m"] != p["posicao_proposta_m"]
    assert p["auditoria_geometrica"]["ok"]
    assert p["auditoria_geometrica"]["arquivo_reaberto"]
    assert p["auditoria_circulacao"]["ok"]
    assert p["arquivos"]["sha256_dxf"] != original_urls["sha256_dxf"]
    assert all(p["arquivos"].get(k) for k in
               ("dxf_url","pdf_url","png_url","zip_url","sha256_zip"))
    assert p["arquivos"]["dxf_url"] != original_urls["dxf_url"]
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
