"""Proposta REVERSIVEL para o gargalo de uma casa compacta.

Gera DUAS versoes independentes: original auditado + variante de mobiliario.
Nunca altera a planta original nem aplica automaticamente uma proposta.
Usa apenas a malha de circulacao como criterio preliminar; nenhuma norma
de ergonomia, acessibilidade ou habitabilidade foi certificada.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import zipfile

import ezdxf

from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao
from mcp_cad_cloud.auditoria_geometrica import auditar_dxf_serializado
from mcp_cad_cloud.validar_modelo import validar

MIN_GAIN_M = 0.10
TOLERATED_OTHER_LOSS_M = 0.10
OFFSETS_M = ((-.20, 0), (-.35, 0), (-.50, 0),
             (-.65, 0), (-.80, 0), (-.95, 0),
             (-.35, .15), (-.50, .15), (-.65, .15))
MAX_PUBLIC_DXF = 3_000_000


def _service_width(audit: dict) -> float | None:
    rows=audit.get("metricas",{}).get("diagnostico_passagens",{}).get("larguras",[])
    return next((row["largura_estimativa_m"] for row in rows
                 if "servico" in row["ambiente"].casefold()
                 or "serviço" in row["ambiente"].casefold()
                 or "lavanderia" in row["ambiente"].casefold()),None)


def _widths(audit):
    return {r["ambiente"]:r["largura_estimativa_m"]
            for r in audit.get("metricas",{}).get("diagnostico_passagens",{}).get("larguras",[])}


def _candidate_safe(reference, proposed):
    before=_widths(reference)
    after=_widths(proposed)
    for room,old in before.items():
        if room not in after or (old is not None and after[room] is None):
            return False
        if old is not None and after[room]+TOLERATED_OTHER_LOSS_M < old:
            return False
    if len(proposed["avisos"]) > len(reference["avisos"]):
        return False
    return True


def _nearby_furniture_ids(audit):
    items=audit.get("metricas",{}).get("gargalos_estimados",[])
    ids=[]
    for row in items:
        for obj in row.get("obstaculos_proximos",[]):
            name=obj.get("id","")
            if name.startswith("MOVEL-") and name[6:].isdigit():
                number=int(name[6:])
                if number not in ids:
                    ids.append(number)
    return ids[:2]


def _new_rect(doc,index,rect):
    entities=list(doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]'))
    if index>=len(entities):
        return False
    x1,y1,x2,y2=rect
    entities[index].set_points(
        ((x1,y1),(x2,y1),(x2,y2),(x1,y2)),format="xy")
    return True


def _export_candidate(doc,model):
    from mcp_cad_cloud.downloads import publish, attach_visuals
    from mcp_cad_cloud.prancha_dxf import renderizar_prancha
    with tempfile.TemporaryDirectory(prefix="cad_alternativa_") as tmp:
        path=Path(tmp)/"proposta_mobiliario.dxf"
        doc.saveas(path)
        payload=path.read_bytes()
    if len(payload)>MAX_PUBLIC_DXF:
        raise ValueError("DXF alternativo acima de 3 MB")
    pdf,png=renderizar_prancha(doc,"PROPOSTA NAO APLICADA - REVISAO NECESSARIA",model["resumo_geometria"])
    if len(pdf)>MAX_PUBLIC_DXF or len(png)>MAX_PUBLIC_DXF:
        raise ValueError("PDF/PNG alternativo acima de 3 MB")
    stream=BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("proposta_mobiliario.dxf",payload)
    archive=stream.getvalue()
    urls=publish(payload,archive)
    views=attach_visuals(urls["dxf_url"],pdf=pdf,png=png)
    return {
        "dxf_url":urls["dxf_url"],"pdf_url":views["pdf_url"],
        "png_url":views["png_url"],"zip_url":urls["download_url"],
        "expires_in_seconds":urls["expires_in_seconds"],
        "sha256_dxf":hashlib.sha256(payload).hexdigest(),
        "sha256_pdf":hashlib.sha256(pdf).hexdigest(),
        "sha256_png":hashlib.sha256(png).hexdigest(),
        "sha256_zip":hashlib.sha256(archive).hexdigest(),
    }


def propor_alternativa(pedido: str) -> dict:
    """Returns original and one audited improvement, without applying it.

    Unsupported prompts are rejected by the original, proven one-call flow.
    """
    from mcp_cad_cloud.projeto_automatico import interpretar_pedido, projetar_uma_vez
    from mcp_cad_cloud.backend import _ensure
    from mcp_cad_cloud.planta_gerador import gerar_modelo

    original=projetar_uma_vez(pedido=pedido,nome="Residencia_ORIGINAL")
    if not original.get("ok"):
        return {"ok":False,"etapa":"original","original":original,
                "alternativa_disponivel":False}
    base_audit=original["auditoria_circulacao"]
    base_width=_service_width(base_audit)
    result={
        "ok":True,
        "modo":"comparacao_sem_aplicacao",
        "versao_original":"residencia_original_intacta",
        "alteracoes_aplicadas_ao_original":False,
        "original":{
            "arquivos":original["arquivos"],
            "auditoria_circulacao":base_audit,
            "auditoria_geometrica":original["auditoria_geometrica"],
            "quadro_areas_m2":original["quadro_areas_m2"],
        },
        "alternativa_disponivel":False,
        "candidatas_avaliadas":0,
        "criterio":"ganho minimo 0,10 m estimado na rota da lavanderia; "
                   "sem erros criticos, sem novos avisos e sem perdas "
                   "superiores a 0,10 m nas demais rotas",
        "limites":[
            "Proposta de mobiliario esquematico, nunca troca automaticamente o desenho original.",
            "Larguras derivadas de malha 0,10 m com incerteza aproximada de 0,20 m; "
            "nao demonstram largura livre legal.",
            "A alternativa exige conferência de dimensões e uso real dos equipamentos.",
        ],
    }
    if base_width is None:
        result["motivo"]="Nao ha largura estimada no acesso a lavanderia"
        return result
    ids=_nearby_furniture_ids(base_audit)
    if not ids:
        result["motivo"]="Nao existe mobiliario identificavel proximo ao gargalo; rever paredes/portas"
        return result

    program,_=interpretar_pedido(pedido,None)
    model=gerar_modelo(program)
    doc=_ensure()
    # Snapshot once, then reopen isolated DXF for each candidate.
    with tempfile.TemporaryDirectory(prefix="cad_comparador_") as directory:
        source=Path(directory)/"original.dxf"
        doc.saveas(source)
        original_bytes=source.read_bytes()
        best=None
        rejected=[]
        for furniture_number in ids:
            furniture_index=furniture_number-1
            if furniture_index>=len(model["moveis"]):
                continue
            old=model["moveis"][furniture_index]
            for dx,dy in OFFSETS_M:
                result["candidatas_avaliadas"]+=1
                candidate=deepcopy(model)
                moved=[round(old[0]+dx,6),round(old[1]+dy,6),
                       round(old[2]+dx,6),round(old[3]+dy,6)]
                candidate["moveis"][furniture_index]=moved
                validation=validar(candidate)
                if not validation["ok"]:
                    rejected.append("modelo-invalido")
                    continue
                alternate=ezdxf.readfile(source)
                if not _new_rect(alternate,furniture_index,moved):
                    rejected.append("entidade-nao-localizada")
                    continue
                geometric=auditar_dxf_serializado(candidate,alternate)
                if not geometric["ok"]:
                    rejected.append("dxf-divergente")
                    continue
                audit=auditar_circulacao(candidate,alternate)
                if not audit["ok"] or not _candidate_safe(base_audit,audit):
                    rejected.append("circulacao-erro-ou-regressao")
                    continue
                width=_service_width(audit)
                if width is None:
                    rejected.append("largura-sem-estimativa")
                    continue
                gain=round(width-base_width,3)
                if gain < MIN_GAIN_M:
                    rejected.append("ganho-insuficiente")
                    continue
                # Choose greater improvement, then smaller furniture displacement.
                score=(gain,-round(abs(dx)+abs(dy),3))
                if best is None or score>best["score"]:
                    best={
                        "score":score,"model":candidate,"doc":alternate,
                        "audit":audit,"geom":geometric,"before":old,
                        "after":moved,"furniture":furniture_number,
                        "dx":dx,"dy":dy,"gain":gain,"width":width,
                    }
        if original_bytes!=source.read_bytes():
            raise RuntimeError("Snapshot original alterado durante a busca")
        if best is None:
            result["motivo"]="Nenhuma proposta passou a validacao e o ganho minimo"
            result["candidatas_rejeitadas"]=len(rejected)
            return result
        # Publish a separate, audited candidate, never touch session's doc.
        proposal_files=_export_candidate(best["doc"],best["model"])
        result["alternativa_disponivel"]=True
        result["proposta"]={
            "status":"para_revisao_humana_nao_aplicada",
            "movel":f"MOVEL-{best['furniture']:02d}",
            "posicao_original_m":list(best["before"]),
            "posicao_proposta_m":list(best["after"]),
            "deslocamento_m":[best["dx"],best["dy"]],
            "largura_antes_estimativa_m":base_width,
            "largura_depois_estimativa_m":best["width"],
            "ganho_estimado_m":best["gain"],
            "auditoria_geometrica":best["geom"],
            "auditoria_circulacao":best["audit"],
            "arquivos":proposal_files,
        }
        return result
