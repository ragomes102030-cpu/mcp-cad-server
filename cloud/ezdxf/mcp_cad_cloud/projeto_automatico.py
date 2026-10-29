"""Single-call residential CAD pipeline for a narrowly supported typology.

Claude interprets the human request; this deterministic server accepts either
a short Portuguese description or a full structured program. Unsupported
requirements are rejected, never silently dropped.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import unicodedata


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


def _chave(nome: str) -> str:
    return unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().casefold()


def _completar_ambientes(itens: list, premissas: list[str]) -> list[dict]:
    """Complete only missing areas for the six supported distinct rooms.

    Never change or guess an area explicitly supplied by the agent/user.
    """
    if not isinstance(itens, list) or len(itens) != 6:
        raise ValueError(
            "modelo compacto requer seis ambientes separados: Sala, Cozinha, "
            "Lavanderia, Quarto 1, Quarto 2 e Banheiro. "
            "Se nao conhece as areas, omita 'ambientes' ou todo o 'programa'.")
    defaults = {
        "sala": 18.0, "cozinha": 9.0, "servico": 5.0,
        "quarto1": 12.0, "quarto2": 10.0, "banheiro": 5.0,
    }
    result, seen, quarto_num = [], set(), 0
    for item in itens:
        if not isinstance(item, dict):
            raise ValueError("cada ambiente deve ser objeto com nome e area opcional")
        nome = item.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("cada ambiente precisa de um nome")
        n = _chave(nome)
        if "sala" in n and "cozinha" in n:
            raise ValueError(
                "'Sala e Cozinha integradas' deve ser informada como dois "
                "ambientes separados ('Sala' e 'Cozinha'); o desenho gerado "
                "os integra fisicamente sem parede divisoria.")
        if "quarto" in n or "dormitorio" in n:
            quarto_num += 1
            categoria = "quarto1" if quarto_num == 1 else "quarto2"
            # The geometric engine expects the literal 'quarto' in the name.
            if "quarto" not in n:
                nome = "Quarto " + str(quarto_num)
        elif "banheiro" in n:
            categoria = "banheiro"
        elif "sala" in n or "estar" in n:
            categoria = "sala"
        elif "cozinha" in n:
            categoria = "cozinha"
        elif "servico" in n or "lavanderia" in n:
            categoria = "servico"
        else:
            raise ValueError(
                f"ambiente {nome!r} nao suportado no piloto de dois quartos")
        if categoria in seen or categoria not in defaults:
            raise ValueError("programa contem ambientes repetidos ou quartos adicionais")
        seen.add(categoria)
        sala = dict(item)
        sala["nome"] = nome
        if sala.get("area") is None:
            sala["area"] = defaults[categoria]
            premissas.append(f"Area de {nome} assumida: {sala['area']:.2f} m2")
        result.append(sala)
    if seen != set(defaults):
        raise ValueError(
            "programa incompleto: sao obrigatorios sala, cozinha, "
            "lavanderia, dois quartos e banheiro em itens distintos")
    return result


def interpretar_pedido(pedido: str, programa: dict | None) -> tuple[dict, list[str]]:
    if not isinstance(pedido, str) or not 8 <= len(pedido.strip()) <= 2000:
        raise ValueError("pedido deve ser texto de 8 a 2000 caracteres")
    trecho = pedido.casefold()
    inadequado = _UNSUPPORTED.search(trecho)
    if inadequado:
        raise ValueError(
            f"tipologia ainda nao suportada: {inadequado.group(0)}; "
            "esta fase suporta somente casa terrea de 2 quartos sem suite ou garagem")
    if not _TWO_ROOMS.search(trecho) and programa is None:
        raise ValueError(
            "texto nao indica claramente dois quartos; "
            "informe 2 quartos ou envie um programa estruturado")

    p = deepcopy(_PADRAO)
    premissas: list[str] = []
    lote = _LOT.search(trecho)
    if lote:
        p["terreno_largura"] = float(lote.group(1).replace(",", "."))
        p["terreno_profundidade"] = float(lote.group(2).replace(",", "."))
    else:
        premissas.append("Terreno assumido: 10,00 x 20,00 m.")

    if programa is None:
        if re.search(r"\d+(?:[.,]\d+)?\s*(?:m²|m2|metros\s+quadrados)", trecho):
            raise ValueError(
                "areas explicitas exigem programa estruturado para nao ignorar valores")
        premissas.extend([
            "Areas do modelo piloto assumidas: sala 18, cozinha 9, servico 5, "
            "quartos 12/10 e banheiro 5 m2.",
            "Largura da casa adotada: 9,00 m; paredes de 0,15 m e pe-direito de 2,80 m.",
            "Recuos 3,00 m frontal, 0,50 m laterais e 2,00 m de fundo sao "
            "hipoteses, nao exigencias urbanisticas verificadas.",
        ])
        return p, premissas

    if not isinstance(programa, dict):
        raise ValueError("programa deve ser objeto JSON; omita se nao conhece areas")
    if programa.get("estrategia", "compacto_2quartos") != "compacto_2quartos":
        raise ValueError("esta operacao suporta apenas estrategia compacto_2quartos")
    aceitos = set(_PADRAO) | {"titulo", "integracao_sala_cozinha"}
    desconhecidos = set(programa) - aceitos
    if desconhecidos:
        raise ValueError(
            f"campos ainda nao suportados: {sorted(desconhecidos)}. "
            "Se nao sao requisitos explicitos, omita 'programa' para usar o modelo seguro.")
    if programa.get("integracao_sala_cozinha") is False:
        raise ValueError("esta ferramenta somente produz sala e cozinha integradas")
    for field in ("terreno_largura", "terreno_profundidade"):
        if field in programa and lote and abs(float(programa[field]) - p[field]) > 1e-8:
            raise ValueError(
                f"{field} no programa contradiz o terreno descrito no pedido")
    p.update({key: deepcopy(value) for key, value in programa.items()
              if key in aceitos and key != "integracao_sala_cozinha"})
    if "ambientes" in programa:
        p["ambientes"] = _completar_ambientes(programa["ambientes"], premissas)
    else:
        premissas.append(
            "Areas internas assumidas conforme modelo validado porque "
            "a lista ambientes foi omitida: 18/9/5/12/10/5 m2.")
    for field, message in (
        ("largura", "Largura da edificacao assumida: 9,00 m."),
        ("recuo_frente", "Recuo frontal assumido: 3,00 m."),
        ("recuo_lateral", "Recuo lateral assumido: 0,50 m."),
        ("recuo_fundo", "Recuo de fundo assumido: 2,00 m."),
    ):
        if field not in programa:
            premissas.append(message)
    if premissas:
        premissas.append(
            "Recuos sao hipoteses de implantacao e nao regras urbanisticas verificadas.")
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

    # Independent audit of the actual serialized DXF, not only model metadata.
    # Fail closed: no PDF/PNG or external download URL for inconsistent output.
    from mcp_cad_cloud.auditoria_geometrica import auditar_dxf_serializado
    geometria = auditar_dxf_serializado(preview["modelo"], _ensure())
    if not geometria["ok"]:
        return {
            "ok": False, "etapa": "auditoria_geometrica",
            "code": "CONTRATO_GEOMETRICO_VIOLADO",
            "auditoria_geometrica": geometria,
            "avisos": ["Arquivo DXF bloqueado por divergencia com o programa."],
        }

    # A DXF geometric equality check ran above: circulation analysis may
    # now combine real DXF furniture/door arcs with validated model wall axes.
    from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao
    circulacao = auditar_circulacao(preview["modelo"], _ensure())
    if not circulacao["ok"]:
        return {
            "ok": False, "etapa": "auditoria_circulacao",
            "code": "CIRCULACAO_INTERFERENCIA_CRITICA",
            "auditoria_circulacao": circulacao,
            "avisos": ["Entrega bloqueada por obstrucao ou conflito geométrico comprovado."],
        }

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
        "auditoria_geometrica": geometria,
        "auditoria_circulacao": circulacao,
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
