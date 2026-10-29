"""Single-call residential CAD pipeline for a narrowly supported typology.

Claude interprets the human request; this deterministic server accepts either
a short Portuguese description or a full structured program. Unsupported
requirements are rejected, never silently dropped.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from urllib.parse import urlparse


_TWO_ROOMS = re.compile(r"\b(?:2|dois|duas)\s+(?:quartos?|dormit[oó]rios?)\b", re.I)
_LOT = re.compile(
    r"\b(?:terreno|lote)\s*(?:de|com)?\s*"
    r"(\d+(?:[.,]\d+)?)\s*(?:m(?:etros)?)?\s*(?:x|×|por)\s*"
    r"(\d+(?:[.,]\d+)?)\s*(?:m(?:etros)?)?",
    re.I,
)
_UNSUPPORTED = re.compile(
    r"\b(?:su[ií]tes?|garagens?|vagas?\s+de\s+carro|piscinas?|"
    r"varandas?|sobrados?|pavimento\s+superior|"
    r"(?:1|um|uma|3|tr[eê]s|4|quatro|5|cinco)\s+(?:quartos?|dormit[oó]rios?))\b",
    re.I,
)

_PADRAO = {
    "estrategia": "compacto_2quartos",
    "largura": 9.0,
    "espessura_parede": .15,
    "pe_direito": 2.8,
    "terreno_largura": 10.0,
    "terreno_profundidade": 20.0,
    "recuo_frente": 3.0,
    "recuo_lateral": .5,
    "recuo_fundo": 2.0,
    "ambientes": [
        {"nome": "Sala de estar", "area": 18.0},
        {"nome": "Cozinha", "area": 9.0},
        {"nome": "Área de serviço", "area": 5.0},
        {"nome": "Quarto 1", "area": 12.0},
        {"nome": "Quarto 2", "area": 10.0},
        {"nome": "Banheiro social", "area": 5.0},
    ],
}


def interpretar_pedido(pedido: str, programa: dict | None) -> tuple[dict, list[str]]:
    if not isinstance(pedido, str) or not 8 <= len(pedido.strip()) <= 2000:
        raise ValueError("pedido deve ser texto de 8 a 2000 caracteres")
    trecho = pedido.casefold()
    inadequado = _UNSUPPORTED.search(trecho)
    if inadequado:
        raise ValueError(
            f"tipologia ainda nao suportada: {inadequado.group(0)}; "
            "esta fase suporta somente casa terrea de 2 quartos sem suite ou garagem")
    if programa is not None:
        if not isinstance(programa, dict):
            raise ValueError("programa deve ser um objeto com ambientes e medidas")
        if programa.get("estrategia", "compacto_2quartos") != "compacto_2quartos":
            raise ValueError("esta operacao suporta apenas estrategia compacto_2quartos")
        p = deepcopy(programa)
        p["estrategia"] = "compacto_2quartos"
        # The generator itself checks exact room counts and dimensions.
        return p, []
    if not _TWO_ROOMS.search(trecho):
        raise ValueError(
            "texto nao indica claramente dois quartos; "
            "informe 2 quartos ou envie um programa estruturado")
    p = deepcopy(_PADRAO)
    premissas = [
        "Areas assumidas por modelo piloto: sala 18, cozinha 9, servico 5, "
        "quartos 12/10 e banheiro 5 m2.",
        "Largura da casa adotada: 9,00 m; paredes de 0,15 m e pe-direito de 2,80 m.",
        "Recuos 3,00 m frontal, 0,50 m laterais e 2,00 m de fundo sao "
        "hipoteses, nao exigencias urbanisticas verificadas.",
    ]
    lote = _LOT.search(trecho)
    if lote:
        p["terreno_largura"] = float(lote.group(1).replace(",", "."))
        p["terreno_profundidade"] = float(lote.group(2).replace(",", "."))
    else:
        premissas.append("Terreno assumido: 10,00 x 20,00 m.")
    # An explicit requested room area must not be ignored in the fixed pilot.
    if re.search(r"\d+(?:[.,]\d+)?\s*(?:m²|m2|metros\s+quadrados)", trecho):
        raise ValueError(
            "areas explicitas exigem programa estruturado para nao ignorar valores")
    return p, premissas


def projetar_uma_vez(pedido: str, programa: dict | None = None,
                     nome: str = "Residencia_2_quartos") -> dict:
    """Preview -> real DXF -> audit -> PDF/PNG -> short-lived download URLs."""
    from mcp_cad_cloud import tools_verified as cad
    from mcp_cad_cloud.backend import _ensure
    from mcp_cad_cloud.downloads import attach_visuals
    from mcp_cad_cloud.prancha_dxf import renderizar_prancha

    if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 80:
        raise ValueError("nome de desenho invalido")
    p, premissas = interpretar_pedido(pedido, programa)
    preview = cad.planta_criar_validada(
        programa=p, template="programa_sob_medida", modo="preview")
    if not preview.get("ok"):
        return {"ok": False, "etapa": "preview", **preview}
    if not preview.get("validacao", {}).get("ok"):
        return {"ok": False, "etapa": "validacao", "validacao": preview["validacao"]}

    desenho = cad.planta_criar_validada(
        programa=p, template="programa_sob_medida", modo="desenhar",
        preview_token=preview["preview_token"], nome=nome)
    if not desenho.get("ok"):
        return {"ok": False, "etapa": "desenhar", "detalhes": desenho}
    auditoria = cad.drawing_audit()
    if not auditoria.get("ok") or auditoria.get("errors", 0):
        return {"ok": False, "etapa": "auditoria", "auditoria": auditoria}
    quant = cad.quantitativo()
    if not quant.get("ok"):
        return {"ok": False, "etapa": "quantitativo", "detalhes": quant}

    pdf, png = renderizar_prancha(_ensure(), nome, preview["resumo_geometria"])
    if len(pdf) > 3_000_000 or len(png) > 3_000_000:
        return {"ok": False, "etapa": "prancha", "error": "PDF ou PNG acima do limite de 3MB"}
    export = cad.export_dxf()
    if not export.get("ok"):
        return {"ok": False, "etapa": "export", "detalhes": export}
    extra = attach_visuals(export["dxf_url"], pdf=pdf, png=png)
    return {
        "ok": True,
        "etapa": "concluido",
        "modo": "uma_chamada",
        "tipologia": "residencia_terrea_compacta_2_quartos",
        "escopo": "estudo_preliminar_sem_validacao_normativa",
        "premissas": premissas,
        "resumo_geometria": preview["resumo_geometria"],
        "quantitativo": quant,
        "auditoria": auditoria,
        "arquivos": {
            "dxf_url": export["dxf_url"],
            "zip_url": export["download_url"],
            "pdf_url": extra["pdf_url"],
            "png_url": extra["png_url"],
            "expires_in_seconds": export["expires_in_seconds"],
            "sha256_dxf": export["sha256_dxf"],
            "sha256_pdf": hashlib.sha256(pdf).hexdigest(),
            "sha256_png": hashlib.sha256(png).hexdigest(),
        },
        "avisos": [
            "Estudo conceitual; nao substitui revisao arquitetonica ou legal.",
            "Links temporarios e publicos; nao usar para desenhos sigilosos.",
            *preview.get("avisos", []),
        ],
    }
