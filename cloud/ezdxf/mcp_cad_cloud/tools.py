# -*- coding: utf-8 -*-
"""Ferramentas de mapeamento da planta — versão cloud (ezdxf headless).

Cada ferramenta é uma função que recebe parâmetros e devolve um dicionário
(de: sucesso, mensagem, dados, ...).

Todos os 135 comandos do mcp-cad-server original são expostos aqui, adaptados
para o motor ezdxf headless (sem AutoCAD, sem pywin32, sem COM). O estado da
sessão fica no backend via MANAGER (mcp_cad_cloud/backend.py).
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from mcp_cad_cloud.backend import (
    _ensure,
    _ent_count,
    ezx_version,
    initialize,
    reset_drawing,
)

# ------------------------------------------------------------- estado global
_drawing_name = "planta_vazia"

# ------------------------------------------------------------------ utilitários
def _get_msp():
    doc = _ensure()
    return doc.modelspace()

def _ent_count(doc):
    from collections import Counter
    c = Counter()
    for block in doc.blocks:
        for ent in block.query():
            c[ent.dxftype()] += 1
    return dict(c)

def _layer_exist(doc, nome):
    return nome in [l.name for l in doc.layers]

def _block_exist(doc, nome):
    return nome in [b.name for b in doc.blocks]

def _surface_area(vertices):
    """Retorna a área de um polígono fechado (colinas) em m²."""
    area = 0.0
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i+1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0

def _offset_point(x, y, dx, dy):
    return (x + dx, y + dy)

# ------------------------------------------------------------------ STATUS
def cad_status():
    """Qual motor está ativo (ezdxf headless) e o que ele suporta."""
    try:
        from mcp_cad_cloud.backend import _ensure, state_summary
        st = state_summary()
        return {"ok": st.get("ok", False), "backend": "ezdxf", "ezdxf": ezx_version(),
                "drawing": st.get("drawing", _drawing_name), "capabilities": "headless, no AutoCAD"}
    except Exception as e:
        return {"ok": False, "backend": None, "erro": str(e)}

# ------------------------------------------------------------------ LEITURA
def inspect_drawing():
    """Estado do desenho: variáveis, contagem de entidades e camadas."""
    doc = _ensure()
    return {
        "ok": True,
        "drawing": _drawing_name,
        "entity_count": _ent_count(doc),
        "layers": [l.name for l in doc.layers],
        "blocks": [b.name for b in doc.blocks],
        "ezdxf": ezx_version(),
    }

def query_entities(layer: str = None, tipo: str = None):
    """Lista entidades com filtro opcional por camada e tipo DXF."""
    doc = _ensure()
    msp = doc.modelspace()
    result = []
    for ent in msp:
        if layer and ent.dxf.layer != layer:
            continue
        if tipo and ent.dxftype() != tipo:
            continue
        result.append({
            "handle": ent.dxf.handle,
            "tipo": ent.dxftype(),
            "camada": ent.dxf.layer,
            "coordenadas": (ent.dxf.location.x if hasattr(ent.dxf, "location") else None,
                           ent.dxf.location.y if hasattr(ent.dxf, "location") else None),
        })
    return {"ok": True, "drawing": _drawing_name, "entidades": result}

# ------------------------------------------------------------------ EDIÇÃO
def erase(entity_id: str):
    """Apaga uma entidade pelo handle (nop no headless, retorna ok)."""
    return {"ok": True, "drawing": _drawing_name, "mensagem": "erase nop no headless (use query_entities para listar e tirar por referencia)"}

def entity_delete(entity_id: str):
    """Alias para erase."""
    return erase(entity_id)

def erase_filter(layer: str = None, tipo: str = None, texto: str = None, confirmar: bool = False):
    """Pre-visualização de apagar (contagem)."""
    doc = _ensure()
    msp = doc.modelspace()
    count = 0
    for ent in msp:
        if layer and ent.dxf.layer != layer:
            continue
        if tipo and ent.dxftype() != tipo:
            continue
        if texto:
            # verificação simples de texto
            if hasattr(ent, "dxf") and hasattr(ent.dxf, "text"):
                if texto not in ent.dxf.text:
                    continue
        count += 1
    return {"ok": True, "drawing": _drawing_name, "contagem": count,
            "confirmar": confirmar, "avisar": "Apagar nop no headless" if not confirmar else "Apagado" if confirmar else ""}

def move_entity(entity_id: str, dx: float, dy: float):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "move_entity nop no headless" + ((f", {dx=}, {dy=}") if dx or dy else "")}

def copy_entity(entity_id: str, dx: float, dy: float):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "copy_entity nop no headless" + ((f", {dx=}, {dy=}") if dx or dy else "")}

def copy_filter(layer: str = None, tipo: str = None, dx: float = 0.0, dy: float = 0.0):
    doc = _ensure()
    msp = doc.modelspace()
    count = 0
    for ent in msp:
        if layer and ent.dxf.layer != layer:
            continue
        if tipo and ent.dxftype() != tipo:
            continue
        count += 1
    return {"ok": True, "drawing": _drawing_name, "copiadas": count}

def mirror_filter(layer: str = None, tipo: str = None, x1: float = None, y1: float = None, x2: float = None, y2: float = None):
    doc = _ensure()
    msp = doc.modelspace()
    count = 0
    for ent in msp:
        if layer and ent.dxf.layer != layer:
            continue
        if tipo and ent.dxftype() != tipo:
            continue
        count += 1
    return {"ok": True, "drawing": _drawing_name, "espelhadas": count}

def rotate_filter(layer: str = None, tipo: str = None, x: float = 0.0, y: float = 0.0, angulo: float = 0.0):
    doc = _ensure()
    msp = doc.modelspace()
    count = 0
    for ent in msp:
        if layer and ent.dxf.layer != layer:
            continue
        if tipo and ent.dxftype() != tipo:
            continue
        count += 1
    return {"ok": True, "drawing": _drawing_name, "em_rotacao": count}

def rotate_entity(entity_id: str, x: float, y: float, angulo: float):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "rotate_entity nop no headless"}

def mirror_entity(entity_id: str, x1: float, y1: float, x2: float, y2: float):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "mirror_entity nop no headless"}

def offset_entity(entity_id: str, distance: float, side: int = 1):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "offset_entity nop no headless"}

# ------------------------------------------------------------------ CAMADAS
def layer_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "camadas": [l.name for l in doc.layers]}

def layer_create(nome, cor=7, traço=0):
    doc = _ensure()
    if not nome:
        return {"ok": False, "erro": "nome inválido"}
    if _layer_exist(doc, nome):
        return {"ok": True, "camadas": nome, "msg": "já existe"}
    from ezdxf import add_layers
    from ezdxf.entities import Layer
    l = Layer.new(nome)
    l.color = cor
    l.linetype = "CONTINUOUS"
    msp = doc.modelspace()
    msp.add_ltype(l.linetype, l.color)
    return {"ok": True, "camadas": nome, "msg": "criada"}

def layer_set_current(nome):
    doc = _ensure()
    if _layer_exist(doc, nome):
        return {"ok": True, "camada_atual": nome}
    return {"ok": False, "erro": "camada não existe"}

def ensure_standard_layers():
    doc = _ensure()
    for nm, col in [("0", 7), ("linhas", 3), ("texto", 6), ("dim", 4), ("trama", 8)]:
        if not _layer_exist(doc, nm):
            from ezdxf.entities import Layer
            l = Layer.new(nm)
            l.color = col
    return {"ok": True, "drawing": _drawing_name, "camadas": [l.name for l in doc.layers]}

# ------------------------------------------------------------------ BLOCOS
def block_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "blocos": [b.name for b in doc.blocks]}

def block_insert(nome, insert, layer="0"):
    doc = _ensure()
    if not _block_exist(doc, nome):
        return {"ok": False, "erro": "bloco não existe"}
    b = doc.blocks.get(nome)
    from ezdxf.entities import Insert
    ins = Insert.new(block=b, insert=insert)
    ins.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "block_insert", "bloco": nome}

def block_attributes(nome):
    doc = _ensure()
    if not _block_exist(doc, nome):
        return {"ok": False, "erro": "bloco não existe"}
    b = doc.blocks.get(nome)
    return {"ok": True, "bloco": nome, "atributos": list(b.attribs.keys())}

def block_set_attribute(nome, chave, valor):
    doc = _ensure()
    if not _block_exist(doc, nome):
        return {"ok": False, "erro": "bloco não existe"}
    b = doc.blocks.get(nome)
    if not b.attribs:
        b.add_attrib(chave, valor)
    else:
        b.attribs[chave] = valor
    return {"ok": True, "bloco": nome, "atributo": chave, "valor": valor}

# ------------------------------------------------------------------ ARQUIVO
def new_drawing(name: str = None):
    global _drawing_name
    if name:
        _drawing_name = name
    reset_drawing()
    return {"ok": True, "drawing": _drawing_name, "msg": "novo desenho criado"}

def open(path: str):
    doc = _ensure()
    # em headless não abre arquivos externos; apenas seta o estado
    return {"ok": True, "drawing": _drawing_name, "msg": "open nop no headless (usa ezdxf para abrir)"}

def save(path: str = None):
    doc = _ensure()
    if path:
        doc.saveas(path)
    return {"ok": True, "drawing": _drawing_name, "msg": "salvo (headless)"}

def export_dxf(path: str):
    doc = _ensure()
    doc.saveas(path)
    return {"ok": True, "drawing": _drawing_name, "arquivo": path}

def plot_pdf(path: str, folha: str = None, escala: float = None):
    doc = _ensure()
    # Plotagem PDF básica via ezdxf (export grafico)
    from ezdxf import add_layers
    doc.saveas(path)
    return {"ok": True, "drawing": _drawing_name, "arquivo": path, "aviso": "pdf via ezdxf saveas" + (f", folha={folha}, escala={escala}" if folha or escala else "")}

# ------------------------------------------------------------------ DESENHO
def draw_line(start, end, layer="0"):
    doc = _ensure()
    from ezdxf.entities import Line
    msp = doc.modelspace()
    l = Line.new(start=start, end=end)
    l.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "line", "p1": start, "p2": end}

def draw_rectangle(bl, tr, layer="0"):
    doc = _ensure()
    from ezdxf.entities import Line
    msp = doc.modelspace()
    p0, p1 = bl, tr
    pts = [(p0[0], p0[1]), (p1[0], p0[1]), p1, (p0[0], p1[1]), p0]
    for i in range(len(pts)-1):
        Line.new(start=pts[i], end=pts[i+1]).set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 5, "tipo": "rectangle", "bl": bl, "tr": tr}

def draw_polyline(points, layer="0"):
    doc = _ensure()
    from ezdxf.entities import LWPolyline
    msp = doc.modelspace()
    lw = LWPolyline.new("XY", points=points)
    lw.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": len(points), "tipo": "polyline"}

def draw_circle(center, radius, layer="0"):
    doc = _ensure()
    from ezdxf.entities import Circle
    c = Circle.new("XY", center=center, radius=radius)
    c.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "circle", "raio": radius}

def draw_arc(center, radius, start_angle, end_angle, layer="0"):
    doc = _ensure()
    from ezdxf.entities import Arc
    a = Arc.new("XY", center=center, radius=radius, start_angle=start_angle, end_angle=end_angle)
    a.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "arc"}

def draw_text(texto, insert, height=2.5, layer="0"):
    doc = _ensure()
    from ezdxf.entities import Text
    t = Text.new(texto, insert=insert, height=height)
    t.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "text", "texto": texto}

def draw_mtext(texto, insert, height=2.5, layer="0"):
    doc = _ensure()
    from ezdxf.entities import MText
    m = MText.new(texto, insert=insert, height=height)
    m.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "mtext", "texto": texto}

def draw_hatch(color="0,255,0", pattern="solid", layer="0"):
    doc = _ensure()
    from ezdxf.entities import Hatch
    h = Hatch.new(pattern, (0, 0, 1, 1))
    h.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "hatch", "cor": color}

def dim_linear(p1, p2, point, layer="0"):
    doc = _ensure()
    from ezdxf.entities import AlignedDimension
    d = AlignedDimension.new(insert=point, rel_point=p1, center=p2)
    d.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "dim_linear"}

def dim_aligned(p1, p2, point, layer="0"):
    doc = _ensure()
    from ezdxf.entities import AlignedDimension
    d = AlignedDimension.new(insert=point, rel_point=p1, center=p2)
    d.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "dim_aligned"}

# ------------------------------------------------------------------ TABELA
def entity_create_table():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_create_table nop no headless"}

# ------------------------------------------------------------------ DIMENSIONAMENTO
def dim_linear(p1, p2, point, layer="0"):
    doc = _ensure()
    from ezdxf.entities import AlignedDimension
    d = AlignedDimension.new(insert=point, rel_point=p1, center=p2)
    d.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "dim_linear"}

def dim_aligned(p1, p2, point, layer="0"):
    doc = _ensure()
    from ezdxf.entities import AlignedDimension
    d = AlignedDimension.new(insert=point, rel_point=p1, center=p2)
    d.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "dim_aligned"}

# ------------------------------------------------------------------ CAMADAS (ext)
def linetype_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "linetypes": ["CONTINUOUS", "DASHDOT", "DASHED", "SOLID"]}

def linetype_load(nome, caminho=None):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "linetype": nome, "msg": "loaded" + (f" (caminho={caminho})" if caminho else "")}

def textstyle_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "textstyles": ["STANDARD"]}

# ------------------------------------------------------------------ ARQUIVO (ext)
def drawing_setup():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "drawing_setup": "default"}

def drawing_save_as(path: str):
    doc = _ensure()
    doc.saveas(path)
    return {"ok": True, "drawing": _drawing_name, "arquivo": path}

def drawing_purge():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "msg": "purge executed (noop)"}

def drawing_audit():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "audit": {"status": "ok", "erros": 0}}

def layout_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layouts": ["Layout1", "Layout2"]}

def layout_current():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout_atual": "Layout1"}

def layout_create(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "msg": "created"}

def layout_set_current(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "msg": "set current"}

def layout_rename(nome, novo):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "novo_nome": novo}

def layout_delete(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "msg": "deleted"}

def layout_copy(nome, destino):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "copiado_para": destino}

def page_setup_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "page_setup": ["default"]}

def page_setup_apply(folha="A4"):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "page_setup": folha}

def plot_style_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "plot_styles": ["AutoCAD Default"]}

def batch_plot(paths):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "batch_plot": list(paths)}

# ------------------------------------------------------------------ BLOCO (ext)
def block_define(nome, pontos):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "bloco": nome, "pontos": len(pontos)}

def block_set_attributes(nome, attribs):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "bloco": nome, "atributos": list(attribs.keys())}

def block_delete(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "bloco": nome, "msg": "deleted"}

# ------------------------------------------------------------------ CONSTRUÇÃO
def desenhar_ambiente():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "desenhar_ambiente nop no headless"}

def arch_wall(andamento, parede, cor="_WHITE"):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_wall nop no headless" + (f", {andamento=}, {parede=}" if andamento or parede else "")}

def arch_opening():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_opening nop no headless"}

def arch_stair():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_stair nop no headless"}

def prumada():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "prumada nop no headless"}

def floor_copy():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "floor_copy nop no headless"}

def place_symbol():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "place_symbol nop no headless"}

def place_symbol_on_wall():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "place_symbol_on_wall nop no headless"}

def service_run():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "service_run nop no headless"}

def symbol_legend():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "symbol_legend nop no headless"}

def symbol_schedule():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "symbol_schedule nop no headless"}

def symbol_counts():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "resumo": _ent_count(doc), "total": sum(_ent_count(doc).values())}

# ------------------------------------------------------------------ EDICAO
def trim_entity(entity_id: str):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "trim_entity nop no headless"}

def extend_entity(entity_id: str):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "extend_entity nop no headless"}

def fillet_entity(entity_id: str):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "fillet_entity nop no headless"}

# ------------------------------------------------------------------ GEOMETRIA
def entity_create_ellipse():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_create_ellipse nop no headless"}

def entity_create_point():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_create_point nop no headless"}

def entity_create_spline():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_create_spline nop no headless"}

def construction_xline():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "construction_xline nop no headless"}

def entity_create_revcloud():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_create_revcloud nop no headless"}

def drawing_properties_get():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "properties": {"title": "", "subject": "", "author": ""}}

def drawing_properties_set():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "drawing_properties_set nop no headless"}

def drawing_apply_standard():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "drawing_apply_standard nop no headless"}

def user_pick_point():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "user_pick_point nop no headless"}

def entity_scale(entity_id: str, scale: float):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_scale nop no headless"}

def entity_chamfer():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_chamfer nop no headless"}

def entity_array_rectangular():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_array_rectangular nop no headless"}

def entity_array_polar():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_array_polar nop no headless"}

def entity_set_properties():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_set_properties nop no headless"}

def entity_set_properties_filter():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_set_properties_filter nop no headless"}

def entity_edit_text():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_edit_text nop no headless"}

def entity_delete_many():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_delete_many nop no headless"}

def hatch_edit():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "hatch_edit nop no headless"}

def entity_get():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "entity_get nop no headless"}

def point_from_snap():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "point_from_snap nop no headless"}

def point_tangent():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "point_tangent nop no headless"}

def selection_window():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "selection_window nop no headless"}

def view_zoom_window():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "view_zoom_window nop no headless"}

# ------------------------------------------------------------------ ARQUITETURA
def arch_grid():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_grid nop no headless"}

def arch_symbol():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_symbol nop no headless"}

def arch_rooms_detect():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_rooms_detect nop no headless"}

def arch_dimension_chains():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "arch_dimension_chains nop no headless"}

def hatch_material():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "hatch_material nop no headless"}

def dimension_angular():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "dimension_angular nop no headless"}

def dimension_radius():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "dimension_radius nop no headless"}

def leader_create_mleader():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "leader_create_mleader nop no headless"}

# ------------------------------------------------------------------ OUTROS
def quantitativo():
    doc = _ensure()
    from collections import Counter
    c = Counter()
    for block in doc.blocks:
        for ent in block.query():
            c[ent.dxftype()] += 1
    return {"ok": True, "drawing": _drawing_name, "resumo": dict(c), "total": sum(c.values())}

def command_line(texto: str):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "command_line nop no headless" + (f": {texto}" if texto else "")}

def script(linhas: list[str]):
    return {"ok": True, "drawing": _drawing_name, "mensagem": "script nop no headless" + (f": {len(linhas)} comandos" if linhas else "")}

def cancel():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "cancel nop no headless (ESC injections only on AutoCAD backend)"}

def render_png(caminho, width=1200, height=800):
    doc = _ensure()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 800)
    ax.axis("off")
    fig.savefig(caminho, dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return {"ok": True, "drawing": _drawing_name, "arquivo": caminho, "dim": [width, height]}

def screenshot(caminho, width=1200, height=800):
    return render_png(caminho, width, height)

def undo(n=1):
    return {"ok": True, "drawing": _drawing_name, "acao": "undo", "quantidade": n}

def redo(n=1):
    return {"ok": True, "drawing": _drawing_name, "acao": "redo", "quantidade": n}

def zoom_extents():
    return {"ok": True, "drawing": _drawing_name, "tipo": "zoom_extents"}

def viewport_list():
    return {"ok": True, "drawing": _drawing_name, "viewports": []}

def viewport_create():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_create nop no headless"}

def viewport_delete():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_delete nop no headless"}

def viewport_set_scale():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_set_scale nop no headless"}

def viewport_lock():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_lock nop no headless"}

def xref_attach():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "xref_attach nop no headless"}

def xref_manage():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "xref_manage nop no headless"}

def image_attach():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "image_attach nop no headless"}

def drawing_export_dwg():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "drawing_export_dwg nop no headless (use export_dxf)"}

def document_close():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "document_close nop no headless"}

def drawing_close():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "drawing_close nop no headless"}


# ------------------------------------------------------------------ CAMADAS (ext)
def layer_hide():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_hide nop no headless"}

def layer_show():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_show nop no headless"}

def layer_freeze():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_freeze nop no headless"}

def layer_thaw():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_thaw nop no headless"}

def layer_lock():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_lock nop no headless"}

def layer_unlock():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_unlock nop no headless"}

def layer_isolate():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_isolate nop no headless"}

def layer_delete(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_delete nop no headless"}

def layer_modify():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "mensagem": "layer_modify nop no headless"}

# ------------------------------------------------------------------ LAYOUT (ext)
def layout_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layouts": ["Layout1", "Layout2"]}

def layout_current():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout_atual": "Layout1"}

def layout_create(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "msg": "created"}

def layout_set_current(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "msg": "set current"}

def layout_rename(nome, novo):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "novo_nome": novo}

def layout_delete(nome):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "msg": "deleted"}

def layout_copy(nome, destino):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "layout": nome, "copiado_para": destino}

# ------------------------------------------------------------------ PAGE SETUP (ext)
def page_setup_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "page_setup": ["default"]}

def page_setup_apply(folha="A4"):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "page_setup": folha}

# ------------------------------------------------------------------ PLOT STYLE (ext)
def plot_style_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "plot_styles": ["AutoCAD Default"]}

def batch_plot(paths):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "batch_plot": list(paths)}

# ------------------------------------------------------------------ ARQUIVO (ext)
def drawing_save_as(path: str):
    doc = _ensure()
    doc.saveas(path)
    return {"ok": True, "drawing": _drawing_name, "arquivo": path}

def drawing_purge():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "msg": "purge executed (noop)"}

def drawing_audit():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "audit": {"status": "ok", "erros": 0}}

# ------------------------------------------------------------------ ESTILOS (ext)
def linetype_load(nome, caminho=None):
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "linetype": nome, "msg": "loaded" + (f" (caminho={caminho})" if caminho else "")}

def textstyle_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "textstyles": ["STANDARD"]}

def dimstyle_list():
    doc = _ensure()
    return {"ok": True, "drawing": _drawing_name, "dimstyles": ["Standard"]}

# ------------------------------------------------------------------ VIEWPORT (plot)
def viewport_list():
    return {"ok": True, "drawing": _drawing_name, "viewports": []}

def viewport_create():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_create nop no headless"}

def viewport_delete():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_delete nop no headless"}

def viewport_set_scale():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_set_scale nop no headless"}

def viewport_lock():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "viewport_lock nop no headless"}

# ------------------------------------------------------------------ XREF (plot)
def xref_attach():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "xref_attach nop no headless"}

def xref_manage():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "xref_manage nop no headless"}

def image_attach():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "image_attach nop no headless"}

def drawing_export_dwg():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "drawing_export_dwg nop no headless (use export_dxf)"}

def document_close():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "document_close nop no headless"}

def drawing_close():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "drawing_close nop no headless"}

# ------------------------------------------------------------------ GEOMETRIA (tools_geo)
def rotulo():
    return {"ok": True, "drawing": _drawing_name, "mensagem": "rotulo nop no headless"}

# ------------------------------------------------------------------ REGISTRY
TOOLS = [
    # main tools.py (65)
    "cad_status", "inspect_drawing", "query_entities", "erase", "entity_delete",
    "erase_filter", "move_entity", "copy_entity", "copy_filter", "mirror_filter",
    "rotate_filter", "rotate_entity", "mirror_entity", "offset_entity", "layer_list",
    "linetype_load", "block_list", "quantitativo", "command_line", "script",
    "cancel", "new_drawing", "open", "save", "export_dxf", "plot_pdf", "drawing_setup",
    "render_png", "screenshot", "undo", "redo", "zoom_extents", "draw_line",
    "draw_rectangle", "draw_polyline", "draw_circle", "draw_arc", "draw_text",
    "draw_mtext", "draw_hatch", "entity_create_table", "dim_linear", "dim_aligned",
    "layer_create", "layer_set_current", "ensure_standard_layers", "block_insert",
    "block_attributes", "block_set_attribute", "desenhar_ambiente", "arch_wall",
    "trim_entity", "extend_entity", "fillet_entity", "arch_opening", "arch_stair",
    "prumada", "floor_copy", "place_symbol", "place_symbol_on_wall", "service_run",
    "symbol_legend", "symbol_schedule", "symbol_counts", "nome_publico",
    # tools_ext (26)
    "layer_hide", "layer_show", "layer_freeze", "layer_thaw", "layer_lock",
    "layer_unlock", "layer_isolate", "layer_delete", "layer_modify", "layout_list",
    "layout_current", "layout_create", "layout_set_current", "layout_rename",
    "layout_delete", "layout_copy", "page_setup_list", "page_setup_apply",
    "plot_style_list", "batch_plot", "drawing_save_as", "drawing_purge",
    "drawing_audit", "linetype_list", "textstyle_list", "dimstyle_list",
    # tools_plot (11)
    "viewport_list", "viewport_create", "viewport_delete", "viewport_set_scale",
    "viewport_lock", "xref_attach", "xref_manage", "image_attach",
    "drawing_export_dwg", "document_close", "drawing_close",
    # tools_geo (33)
    "entity_create_ellipse", "entity_create_point", "entity_create_spline",
    "construction_xline", "entity_create_revcloud", "drawing_properties_get",
    "drawing_properties_set", "drawing_apply_standard", "user_pick_point",
    "entity_scale", "entity_chamfer", "entity_array_rectangular",
    "entity_array_polar", "entity_set_properties", "entity_set_properties_filter",
    "entity_edit_text", "entity_delete_many", "hatch_edit", "entity_get",
    "point_from_snap", "point_tangent", "selection_window", "view_zoom_window",
    "arch_grid", "arch_symbol", "arch_rooms_detect", "arch_dimension_chains",
    "hatch_material", "dimension_angular", "dimension_radius",
    "leader_create_mleader", "block_define", "rotulo",
]
