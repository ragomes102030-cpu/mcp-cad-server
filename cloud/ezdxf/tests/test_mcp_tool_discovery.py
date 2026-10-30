"""Contrato de descoberta MCP: os tools de planta precisam existir na lista
real do servidor FastMCP, em ambos os perfis. Não testa apenas importação
de funções Python, pois isso não assegura exposição ao ChatGPT/Claude.
"""
import os
import subprocess
import sys
import json

import pytest


CHAVES = {"cad_status", "planta_templates", "planta_assistida",
          "planta_criar_validada", "validar_planta", "drawing_audit",
          "export_dxf", "projetar_pacote_licenciamento"}


def _catalogo(profile: str):
    script = r'''
import asyncio, json
from mcp_cad_cloud.server import mcp, build_info
from mcp_cad_cloud import tools_verified as verified

async def main():
    # FastMCP 2 usa get_tools(dict); 3 usa list_tools(lista).
    if hasattr(mcp, "list_tools"):
        published = await mcp.list_tools()
    else:
        published = await mcp.get_tools()
    names = list(published.keys()) if isinstance(published, dict) else [
        entry.name for entry in published
    ]
    print("CATALOG_JSON=" + json.dumps({
        "names": names, "public": list(verified.PUBLIC_TOOLS),
        "profile": verified.PROFILE, "info": build_info()
    }))

asyncio.run(main())
'''
    env = dict(os.environ)
    env["MCP_CAD_PROFILE"] = profile
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=env, text=True, capture_output=True, timeout=35)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    data = [line.partition("CATALOG_JSON=")[2]
            for line in proc.stdout.splitlines()
            if line.startswith("CATALOG_JSON=")]
    assert len(data) == 1, proc.stdout
    return json.loads(data[0])


@pytest.mark.parametrize("profile", ["full", "planta_segura"])
def test_mcp_tools_list_publica_o_fluxo_de_plantas(profile):
    catalogo = _catalogo(profile)
    actual = set(catalogo["names"])
    expected = set(catalogo["public"])
    assert CHAVES <= actual
    assert actual == expected, (sorted(actual - expected), sorted(expected - actual))
    assert catalogo["info"]["tool_count"] == str(len(actual))
    assert catalogo["profile"] == profile
    if profile == "planta_segura":
        assert "command_line" not in actual
        assert "draw_line" not in actual
    else:
        assert "draw_line" in actual


def test_versao_da_pr_tem_template_personalizado_e_compacto():
    from mcp_cad_cloud import tools_verified
    from mcp_cad_cloud.planta_gerador import gerar_modelo
    from test_layout_compacto import CASA
    assert "planta_criar_validada" in tools_verified.PUBLIC_TOOLS
    ids = {t["id"] for t in tools_verified.planta_templates()["templates"]}
    assert "programa_sob_medida" in ids
    result = tools_verified.planta_criar_validada(
        programa=CASA, modo="preview", template="programa_sob_medida")
    assert result["ok"], result
    assert result["modelo"]["estrategia"] == "compacto_2quartos"
