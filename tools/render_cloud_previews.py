"""Gerar pranchas de revisão a partir do modelo E do DXF real do MCP.

Uso: PYTHONPATH=cloud/ezdxf python tools/render_cloud_previews.py
As imagens são representações técnicas não normativas para inspeção visual.
"""
from __future__ import annotations

import base64
import io
import json
import math
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Rectangle

from mcp_cad_cloud.planta_assistida import wall_boundary_segments
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.validar_modelo import validar

OUTPUT = Path("out/preview-cad")
OUTPUT.mkdir(parents=True, exist_ok=True)

BASE = {
    "template": "programa_sob_medida",
    "largura": 9.0,
    "terreno_largura": 10.0,
    "terreno_profundidade": 20.0,
    "recuo_lateral": 0.50,
    "recuo_frente": 3.0,
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
AMPLIADA = {
    **BASE,
    "ambientes": [
        {"nome": "Sala de estar", "area": 20.0},
        {"nome": "Cozinha", "area": 10.0},
        {"nome": "Área de serviço", "area": 5.0},
        {"nome": "Quarto 1", "area": 13.0},
        {"nome": "Quarto 2", "area": 11.0},
        {"nome": "Banheiro social", "area": 5.0},
    ],
}


def render(model, programa, etiqueta, destino):
    largura = model["resumo_geometria"]["largura"]
    profundidade = model["resumo_geometria"]["profundidade"]
    fig = plt.figure(figsize=(15, 11.2), dpi=155, facecolor="white")
    ax = fig.add_axes([0.045, 0.095, 0.68, 0.78])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("white")

    # Limites externos reais do estudo; os recuos são fornecidos pelo usuário,
    # não verificados urbanisticamente.
    minx, miny, maxx, maxy = model["terreno"]
    ax.add_patch(Rectangle((minx, miny), maxx-minx, maxy-miny,
                           fill=False, linewidth=1.2, linestyle="--",
                           edgecolor="#8b99a9"))
    ax.text((minx+maxx)/2, maxy-.45, "TERRENO 10,00 × 20,00 m",
            ha="center", fontsize=9, color="#566674")

    for x1, y1, x2, y2 in wall_boundary_segments(model["paredes"]):
        ax.plot([x1,x2], [y1,y2], lw=2.0, c="#243446", solid_capstyle="round")
    for x, y, angle, width in model["portas"]:
        angle_rad = math.radians(angle)
        ax.plot([x,x+width*math.cos(angle_rad)], [y,y+width*math.sin(angle_rad)],
                lw=1.2, c="#206c6a")
        ax.add_patch(Arc((x,y), 2*width, 2*width, theta1=angle,
                         theta2=angle+90, linewidth=0.9, edgecolor="#206c6a"))
        ax.plot(x, y, ".", ms=2.5, color="#206c6a")
    for x1,y1,x2,y2 in model["janelas"]:
        if abs(y2-y1) < 1e-7:
            for delta in (-0.038, 0.038):
                ax.plot([x1,x2], [y1+delta,y2+delta], c="#3685ae", lw=2.1)
        else:
            for delta in (-0.038, 0.038):
                ax.plot([x1+delta,x2+delta], [y1,y2], c="#3685ae", lw=2.1)
    for x1,y1,x2,y2 in model["moveis"]:
        ax.add_patch(Rectangle((x1,y1),x2-x1,y2-y1,
                               fill=False,linewidth=1.0,edgecolor="#96a4ae"))
    for item in model["ambientes"]:
        x1,y1,x2,y2=(item[k] for k in ("x1","y1","x2","y2"))
        cx,cy=(item.get("texto_x",(x1+x2)/2),
               item.get("texto_y",(y1+y2)/2))
        area=(x2-x1)*(y2-y1)
        name=item["nome"]
        fontsize=8.0 if min(x2-x1,y2-y1)>=1.8 else 6.8
        ax.text(cx,cy+.13,name,ha="center",va="center",fontsize=fontsize,
                color="#1e2f3f",fontweight="medium")
        ax.text(cx,cy-.18,f"{area:.2f} m²",ha="center",va="center",fontsize=7.0,
                color="#3e6577")
    # Dimensões da projeção externa
    ax.annotate("", xy=(0,-1.1), xytext=(largura,-1.1),
                arrowprops={"arrowstyle":"|-|","lw":0.8,"color":"#334155"})
    ax.text(largura/2,-1.35,f"{largura:.2f} m",ha="center",va="top",fontsize=9)
    ax.annotate("", xy=(largura+0.85,0), xytext=(largura+0.85,profundidade),
                arrowprops={"arrowstyle":"|-|","lw":0.8,"color":"#334155"})
    ax.text(largura+1.02,profundidade/2,f"{profundidade:.2f} m",
            rotation=90,va="center",fontsize=9)

    ax.set_xlim(minx-1.3,maxx+3.1)
    ax.set_ylim(miny-1.0,maxy+1.25)

    # Informações de auditoria à direita, sem sobrepor o desenho.
    right=fig.add_axes([0.75,0.12,0.225,0.74])
    right.axis("off")
    right.text(0.0,1.0,"QUADRO DE ÁREAS",fontsize=12,weight="bold",
               color="#192b3e",va="top",transform=right.transAxes)
    for i,a in enumerate(programa["ambientes"]):
        y=.935-i*.069
        right.text(0,y,a["nome"],fontsize=8.3,va="top",transform=right.transAxes)
        right.text(1,y,f'{a["area"]:.2f} m²',ha="right",fontsize=8.3,va="top",
                   transform=right.transAxes)
    g=model["resumo_geometria"]
    yy=.47
    for label,number in (
        ("Ambientes", f'{g["area_ambientes"]:.2f} m²'),
        ("Útil total", f'{g["area_util_total"]:.2f} m²'),
        ("Projeção", f'{g["area_construida"]:.2f} m²'),
        ("Circulação livre", f'{g.get("hall_livre", g.get("corredor_livre", 0)):.2f} m'),
        ("Espessura parede", "0.15 m"),
    ):
        right.text(0,yy,label,fontsize=9,va="top",transform=right.transAxes)
        right.text(1,yy,number,fontsize=9,ha="right",va="top",weight="medium",
                   transform=right.transAxes)
        yy-=.06
    right.text(0,.075,"PAREDES     PORTAS     JANELAS",fontsize=7.8,
               va="top",transform=right.transAxes)
    right.text(0,.03,"mobiliário esquemático para conferência",fontsize=8.0,
               color="#6d7885",va="top",transform=right.transAxes)

    fig.text(.05,.945,f"PRÉVIA {etiqueta}  |  RESIDÊNCIA TÉRREA",
             fontsize=18,weight="bold",color="#142a3d")
    fig.text(.05,.91,"Gerada pelo MCP CAD Cloud — modelo paramétrico real da PR #1",
             fontsize=11,color="#476275")
    fig.text(.05,.032,
             "ESTUDO PRELIMINAR  •  Sem validação urbanística, acessibilidade, ventilação ou aprovação técnica",
             fontsize=9,color="#954b2b")
    fig.savefig(destino, bbox_inches="tight", pad_inches=.20)
    plt.close(fig)


def executar(programa, etiqueta, slug):
    preview = cad.planta_criar_validada(programa=programa, modo="preview",
                                        template="programa_sob_medida")
    assert preview["ok"], preview
    model=preview["modelo"]
    audit=validar(model)
    assert audit["ok"], audit
    drawn=cad.planta_criar_validada(programa=programa, modo="desenhar",
                                   preview_token=preview["preview_token"],
                                   template="programa_sob_medida",nome=slug)
    assert drawn["ok"], drawn
    exported=cad.export_dxf()
    assert exported["ok"], exported
    # ZIP com o DXF real produzido pelo MCP, para conferência cruzada.
    (OUTPUT / f"{slug}.zip").write_bytes(base64.b64decode(exported["data_base64"]))
    (OUTPUT / f"{slug}.json").write_text(
        json.dumps({"programa": programa, "modelo": model,
                    "validacao": audit, "desenho": drawn},ensure_ascii=False,indent=2),
        encoding="utf-8")
    render(model,programa,etiqueta, OUTPUT / f"{slug}.png")
    print("PREVIEW_OK",slug, "area_util",model["resumo_geometria"]["area_util_total"],
          "dimensoes_externas",model["resumo_geometria"]["largura"],
          model["resumo_geometria"]["profundidade"],
          "paredes",len(model["paredes"]),"portas",len(model["portas"]),
          "janelas",len(model["janelas"]))
    print("PREVIEW_MODEL_JSON_"+slug.upper()+"="+json.dumps(model,ensure_ascii=False,separators=(",",":")))


if __name__=="__main__":
    executar({**BASE,"estrategia":"duas_faixas"},"A — duas faixas (legado)","planta_a")
    executar({**AMPLIADA,"estrategia":"duas_faixas"},"B — duas faixas ampliadas (legado)","planta_b")
    executar(BASE,"C — layout compacto 2D","planta_c_compacta")
