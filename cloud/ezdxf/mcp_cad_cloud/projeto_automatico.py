"""Single-call residential CAD pipeline for a narrowly supported typology.

Claude interprets the human request; this deterministic server accepts either
a short Portuguese description or a full structured program. Unsupported
requirements are rejected, never silently dropped.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import io
import json
import re
import unicodedata
import zipfile


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
        "quadro_areas_m2": preview["resumo_geometria"].get("quadro_areas_m2"),
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


def evaluate_package(package, requirements, applicability_rules, evaluators) -> dict:
    """Evaluate only requirements backed by current metadata and registered checks."""
    from mcp_cad_cloud.arquitetura_requisitos import (
        RequirementStatus, evaluate_applicability,
    )

    records = tuple(requirements or ())
    if not records:
        return {
            "licensing_readiness": "review_required",
            "reason": "Nenhum requisito normativo/local foi cadastrado e verificado.",
            "results": (),
        }
    results = tuple(
        evaluate_applicability(
            package.project_context, requirement,
            applicability_rules=applicability_rules or {},
            evaluators=evaluators or {},
        )
        for requirement in records
    )
    statuses = {item.status for item in results}
    if RequirementStatus.FAILED in statuses:
        readiness = "blocked"
        reason = "Ao menos um requisito aplicável falhou; revisar antes de emitir."
    elif RequirementStatus.NOT_TESTABLE in statuses:
        readiness = "review_required"
        reason = "Há requisitos sem verificação suficiente ou com fonte/contexto pendente."
    elif not statuses or statuses <= {RequirementStatus.NOT_APPLICABLE}:
        readiness = "review_required"
        reason = "Não há requisito aplicável efetivamente verificado."
    else:
        readiness = "ready_for_professional_review"
        reason = "Verificações cadastradas passaram; revisão profissional continua obrigatória."
    return {"licensing_readiness": readiness, "reason": reason, "results": results}


def _sheet_spec_from_dict(value):
    from mcp_cad_cloud.prancha_dxf import SheetSpec, ViewportSpec
    if not isinstance(value, dict):
        raise ValueError("cada folha deve ser um objeto")
    viewports = value.get("viewports")
    if not isinstance(viewports, list):
        raise ValueError("viewports deve ser uma lista")
    return SheetSpec(
        paper_format=value.get("paper_format", "A3"),
        orientation=value.get("orientation", "landscape"),
        scale=value.get("scale", 50), margin_mm=value.get("margin_mm", 10),
        sheet_id=value.get("sheet_id", ""),
        viewports=tuple(ViewportSpec(**item) for item in viewports),
    )


def _requirement_report_item(result) -> dict:
    return {
        "requirement_id": result.requirement_id,
        "status": result.status.value,
        "reason": result.reason,
        "evidence": list(result.evidence),
        "standard": result.standard,
        "edition": result.edition,
    }


def export_licensing_package(programa: dict, contexto: dict, envelope: dict,
                             folhas: list[dict], carimbo: dict,
                             requirements=(), applicability_rules=None,
                             evaluators=None) -> dict:
    """Build, reopen, audit, render and publish an in-memory architecture set."""
    from mcp_cad_cloud.arquitetura_requisitos import ProjectContext
    from mcp_cad_cloud.auditoria_prancha import audit_sheet_document
    from mcp_cad_cloud.projeto_arquitetonico import (
        BuildingEnvelope, generate_architecture_package,
    )
    from mcp_cad_cloud.planta_gerador import gerar_modelo
    from mcp_cad_cloud.prancha_dxf import (
        TitleBlockData, compose_licensing_sheets, renderizar_folha,
    )
    import ezdxf

    if not isinstance(contexto, dict) or not isinstance(envelope, dict):
        raise ValueError("contexto e envelope devem ser objetos JSON")
    if not isinstance(folhas, list) or not 1 <= len(folhas) <= 12:
        raise ValueError("informe de 1 a 12 folhas arquitetônicas")
    project_context = ProjectContext(
        project_name=str(contexto.get("project_name", "")),
        use=str(contexto.get("use", "residencial_unifamiliar")),
        typology=str(contexto.get("typology", "compacto_2quartos")),
        municipality=contexto.get("municipality"), state=contexto.get("state"),
        storeys=int(contexto.get("storeys", 1)),
        lot_width_m=contexto.get("lot_width_m"),
        lot_depth_m=contexto.get("lot_depth_m"),
        requested_rooms=tuple(contexto.get("requested_rooms", ())),
        stage=str(contexto.get("stage", "licenciamento")),
        municipal_profile_revision=contexto.get("municipal_profile_revision"),
    )
    building_envelope = BuildingEnvelope(**envelope)
    plan_model = gerar_modelo(deepcopy(programa))
    package = generate_architecture_package(plan_model, project_context, building_envelope)
    if not isinstance(carimbo, dict):
        raise ValueError("carimbo deve ser um objeto JSON")
    title_block = TitleBlockData(**{
        key: carimbo.get(key) for key in (
            "project_name", "municipality", "state", "owner", "designer",
            "professional_registration", "issue_date", "revision",
        )
    })
    specs = [_sheet_spec_from_dict(item) for item in folhas]
    sheets = compose_licensing_sheets(package, specs, title_block)
    evaluation = evaluate_package(package, requirements, applicability_rules, evaluators)

    serialized, audits, visuals = [], [], []
    for sheet in sheets:
        stream = io.StringIO()
        sheet.document.write(stream)
        raw = stream.getvalue().encode("utf-8")
        reopened = ezdxf.read(io.StringIO(raw.decode("utf-8")))
        audit = audit_sheet_document(reopened, sheet.spec, package)
        audits.append(audit)
        if not audit["ok"]:
            return {
                "ok": False, "etapa": "auditoria_prancha",
                "licensing_readiness": "blocked",
                "auditorias_folhas": audits,
                "arquivos": {},
                "avisos": ["Exportação bloqueada: auditoria do DXF serializado falhou."],
            }
        reopened_sheet = type(sheet)(sheet.sheet_id, sheet.spec,
                                    sheet.title_block_rows, reopened)
        pdf, png = renderizar_folha(reopened_sheet)
        if len(raw) > 3_000_000 or len(pdf) > 3_000_000 or len(png) > 3_000_000:
            raise ValueError(f"folha {sheet.sheet_id} excede o limite individual de 3 MB")
        serialized.append((sheet.sheet_id, raw, pdf, png))
        visuals.append((pdf, png))

    results = [_requirement_report_item(item) for item in evaluation["results"]]
    report = {
        "schema_version": 1,
        "project": {
            "name": project_context.project_name,
            "use": project_context.use,
            "typology": project_context.typology,
            "municipality": project_context.municipality,
            "state": project_context.state,
            "stage": project_context.stage,
        },
        "licensing_readiness": evaluation["licensing_readiness"],
        "readiness_reason": evaluation["reason"],
        "requirements": results,
        "sheet_audits": audits,
        "limitations": list(package.limitations),
        "artifacts": [f"{sheet_id}.{ext}" for sheet_id, *_ in serialized
                      for ext in ("dxf", "pdf", "png")],
        "generated_at": date.today().isoformat(),
    }
    report_json = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    report_md = [
        f"# Pacote arquitetônico — {project_context.project_name}", "",
        f"- Etapa: {project_context.stage}",
        f"- Situação: {evaluation['licensing_readiness']}",
        f"- Motivo: {evaluation['reason']}",
        "- Revisão profissional obrigatória; sem afirmação de aprovação ou conformidade total.",
        "", "## Requisitos", "",
    ]
    report_md.extend(
        f"- {item['requirement_id']}: {item['status']} — {item['reason']}"
        for item in results
    )
    if not results:
        report_md.append("- Nenhum requisito cadastrado/verificado; situação mantida em revisão.")
    report_md.extend(["", "## Pranchas", ""])
    report_md.extend(f"- {sheet_id}: auditoria independente passou."
                     for sheet_id, *_ in serialized)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for sheet_id, raw, pdf, png in serialized:
            archive.writestr(f"{sheet_id}.dxf", raw)
            archive.writestr(f"{sheet_id}.pdf", pdf)
            archive.writestr(f"{sheet_id}.png", png)
        archive.writestr("report.json", report_json)
        archive.writestr("report.md", "\n".join(report_md).encode("utf-8"))
    archive_bytes = zip_buffer.getvalue()
    if len(archive_bytes) > 20_000_000:
        raise ValueError("ZIP do projeto excede o limite seguro de 20 MB")
    from mcp_cad_cloud.downloads import attach_visuals, publish
    links = publish(serialized[0][1], archive_bytes)
    visual_links = attach_visuals(links["dxf_url"], pdf=visuals[0][0], png=visuals[0][1])
    return {
        "ok": True,
        "etapa": "concluido",
        "modo": "pacote_arquitetonico_licenciamento",
        "licensing_readiness": evaluation["licensing_readiness"],
        "motivo_prontidao": evaluation["reason"],
        "resultados_requisitos": results,
        "auditorias_folhas": audits,
        "arquivos": {
            "dxf_url": links["dxf_url"], "zip_url": links["download_url"],
            "pdf_url": visual_links["pdf_url"], "png_url": visual_links["png_url"],
            "expires_in_seconds": links["expires_in_seconds"],
            "folhas": [sheet_id for sheet_id, *_ in serialized],
        },
        "avisos": [
            "Revisão de profissional habilitado obrigatória; este pacote não é aprovação de licenciamento.",
            "Normas NBR e regras municipais não verificadas permanecem pendentes.",
            "Links temporários públicos; não enviar projetos sigilosos.",
        ],
    }
