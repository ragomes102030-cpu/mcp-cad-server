"""Real one-call acceptance: natural-language -> DXF -> A3 PDF/PNG and audit."""
import asyncio
import hashlib
import io
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import ezdxf
from starlette.requests import Request

from mcp_cad_cloud import server, tools_verified as cad
from mcp_cad_cloud.projeto_automatico import interpretar_pedido
from test_layout_compacto import CASA


PEDIDO = (
    "Desenhe uma residencia terrea em terreno de 10 x 20 metros, "
    "com dois quartos, sala e cozinha integradas, banheiro e lavanderia."
)


def _get(url: str):
    parsed = urlparse(url)
    parts = parsed.path.split("/")
    req = Request({
        "type": "http", "method": "GET", "path": parsed.path,
        "path_params": {"token": parts[-2], "fmt": parts[-1]},
        "query_string": b"", "headers": [],
    })
    return asyncio.run(server.download_dxf(req))


def test_one_prompt_produces_downloadable_real_dxfs_png_and_a3_pdf():
    result = cad.projetar_residencia(PEDIDO)
    assert result["ok"], result
    assert result["etapa"] == "concluido"
    assert result["modo"] == "uma_chamada"
    assert result["premissas"]
    assert result["quantitativo"]["entities"] == 146
    assert result["quantitativo"]["by_type"]["DIMENSION"] == 8
    assert result["auditoria"]["ok"]
    assert result["auditoria"]["errors"] == 0
    assert result["resumo_geometria"]["largura"] == 9
    assert result["resumo_geometria"]["profundidade"] == 8.6
    files = result["arquivos"]
    assert files["expires_in_seconds"] == 900

    by_kind = {}
    for kind in ("dxf", "pdf", "png"):
        response = _get(files[f"{kind}_url"])
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        by_kind[kind] = response.body
        assert hashlib.sha256(response.body).hexdigest() == files[f"sha256_{kind}"]
    assert by_kind["pdf"].startswith(b"%PDF-")
    assert by_kind["png"].startswith(bytes.fromhex("89504e470d0a1a0a"))
    assert len(by_kind["pdf"]) > 10000
    assert len(by_kind["png"]) > 10000
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audited.dxf"
        path.write_bytes(by_kind["dxf"])
        reopened = ezdxf.readfile(path)
    assert len(reopened.modelspace()) == 146
    assert reopened.audit().has_errors is False
    assert len(list(reopened.modelspace().query("DIMENSION"))) == 8


def test_explicit_supported_program_and_error_on_unsupported_requirements():
    import copy
    p, premissas = interpretar_pedido(PEDIDO, copy.deepcopy(CASA))
    assert p["ambientes"] == CASA["ambientes"]
    assert not premissas
    cad.new_drawing("nao_alterar")
    before = cad.inspect_drawing()["entities"]
    for pedido in (
        "Quero uma casa de tres quartos, sala e cozinha",
        "Quero uma casa com dois quartos, uma suite e garagem",
        "Quero uma casa com piscina e dois quartos",
        "Desenhe uma casa com dois quartos de 18 m2 num terreno 10 x 20",
    ):
        r = cad.projetar_residencia(pedido)
        assert r["ok"] is False, (pedido, r)
        assert cad.inspect_drawing()["entities"] == before
    result = cad.projetar_residencia(PEDIDO, programa=copy.deepcopy(CASA),
                                   nome="CASA_TESTE_AUTOMATICO")
    assert result["ok"], result


def test_tool_is_published_in_both_profiles():
    assert "projetar_residencia" in cad.PUBLIC_TOOLS
