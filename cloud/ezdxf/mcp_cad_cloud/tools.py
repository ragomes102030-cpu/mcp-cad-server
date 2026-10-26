# -*- coding: utf-8 -*-
"""Ferramentas de mapeamento da planta (FastMCP, ezdxf headless).

Cada ferramenta é uma função que recebe parâmetros e devolve um dicionário
(de: sucesso, mensagem, dados, ...).

O estado da sessão fica no backend do ezdxf via MANAGER (mcp_cad_cloud/backend.py).
"""

from __future__ import annotations

from mcp_cad_cloud.backend import (
    _ent_count,
    ezx_version,
    reset_drawing,
    _ensure,
)

# ------------------------------------------------------------------ Estado
_drawing_name = "planta_vazia"
_default_scale = 1.0


# ----------------------------------------------------------------_____ draw
def draw_line(start, end, layer="0"):
    doc = _ensure()
    from ezdxf.addons.drawing import draw_metadata
    from ezdxf.entities import LWPolyline

    msp = doc.modelspace()
    p0 = start
    p1 = end
    lw = LWPolyline.new("XY", points=[p0, p1])
    lw.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "line"}


def draw_rectangle(bl, tr, layer="0"):
    doc = _ensure()
    msp = doc.modelspace()
    from ezdxf.entities import LWPolyline

    p0 = bl
    p1 = tr
    lw = LWPolyline.new("XY", points=[p0, (p1[0], p0[1]), p1, (p0[0], p1[1]), p0])
    lw.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "rectangle"}


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


def draw_text(text, insert, height=2.5, layer="0"):
    doc = _ensure()
    from ezdxf.entities import Text

    t = Text.new(text, insert=insert, height=height)
    t.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "text", "texto": text}


def draw_mtext(text, insert, height=2.5, layer="0"):
    doc = _ensure()
    from ezdxf.entities import MText

    m = MText.new(text, insert=insert, height=height)
    m.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "mtext", "texto": text}


def draw_hatch(color="0,255,0", pattern="solid", layer="0"):
    doc = _ensure()
    from ezdxf.entities import Hatch

    h = Hatch.new("solid", (0, 0, 1, 1))
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


# -------------------------------------------------------------------- camadas
def layer_list():
    doc = _ensure()
    return {"ok": True, "camadas": [l.name for l in doc.layers]}


def layer_create(nome, cor=7, traço=0):
    doc = _ensure()
    if not nome:
        return {"ok": False, "erro": "nome inválido"}
    if nome in [l.name for l in doc.layers]:
        return {"ok": True, "camadas": nome, "msg": "já existe"}
    from ezdxf.entities import Layer

    l = Layer.new(nome)
    l.color = cor
    l.linetype = "CONTINUOUS"
    return {"ok": True, "camadas": nome, "msg": "criada"}


def layer_set_current(nome):
    doc = _ensure()
    if nome in [l.name for l in doc.layers]:
        return {"ok": True, "camada_atual": nome}
    return {"ok": False, "erro": "camada não existe"}


def ensure_standard_layers():
    doc = _ensure()
    for nm, col in [("0", 7), ("linhas", 3), ("texto", 6), ("dim", 4), ("trama", 8)]:
        if nm not in [l.name for l in doc.layers]:
            from ezdxf.entities import Layer

            l = Layer.new(nm)
            l.color = col
    return {"ok": True, "camadas": [l.name for l in doc.layers]}


# ----------------------------------------------------------------- blocos
def block_list():
    doc = _ensure()
    return {"ok": True, "blocos": [b.name for b in doc.blocks]}


def block_insert(nome, insert, layer="0"):
    doc = _ensure()
    msp = doc.modelspace()
    from ezdxf.blocks import Block

    if nome not in [b.name for b in doc.blocks]:
        return {"ok": False, "erro": "bloco não existe"}
    b = doc.blocks.get(nome)
    from ezdxf.entities import Insert

    ins = Insert.new(block=b, insert=insert)
    ins.set_layer(layer)
    return {"ok": True, "drawing": _drawing_name, "entidades": 1, "tipo": "block_insert", "bloco": nome}


def block_attributes(nome):
    doc = _ensure()
    if nome not in [b.name for b in doc.blocks]:
        return {"ok": False, "erro": "bloco não existe"}
    b = doc.blocks.get(nome)
    return {"ok": True, "bloco": nome, "atributos": list(b.attribs.keys())}


def block_set_attribute(nome, chave, valor):
    doc = _ensure()
    if nome not in [b.name for b in doc.blocks]:
        return {"ok": False, "erro": "bloco não existe"}
    b = doc.blocks.get(nome)
    if not b.attribs:
        b.add_attrib(chave, valor)
    else:
        b.attribs[chave] = valor
    return {"ok": True, "bloco": nome, "atributo": chave, "valor": valor}


# -------------------------------------------------------------- exportar
def export_dxf(caminho):
    doc = _ensure()
    doc.saveas(caminho)
    return {"ok": True, "drawing": _drawing_name, "arquivo": caminho}


def plot_pdf(caminho, layout="Model"):
    doc = _ensure()
    # DRWPlot é a saída de PDF no ezdxf
    from ezdxf.protocol import DRWPlot

    plot = DRWPlot.new(None, layout=layout)
    plot.plot(caminho)
    return {"ok": True, "drawing": _drawing_name, "arquivo": caminho, "layout": layout}


def render_png(caminho, width=1200, height=800):
    doc = _ensure()
    # Para renderização PNG no ezdxf headless, usamos a renderização do
    # ezdxf (ExportsPNG). Implementação simplificada: salva PNG via matplolib.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 800)
    ax.axis("off")
    fig.savefig(caminho, dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return {"ok": True, "drawing": _drawing_name, "arquivo": caminho, "dim": [width, height]}


def screenshot(caminho, width=1200, height=800):
    return render_png(caminho, width, height)


# --------------------------------------------------------------- undo/redo
def undo(n=1):
    return {"ok": True, "acao": "undo", "quantidade": n, "drawing": _drawing_name}


def redo(n=1):
    return {"ok": True, "acao": "redo", "quantidade": n, "drawing": _drawing_name}


def zoom_extents():
    return {"ok": True, "drawing": _drawing_name, "tipo": "zoom_extents"}


# --------------------------------------------------------------- quantitativo
def quantitativo():
    doc = _ensure()
    from collections import Counter

    c = Counter()
    for block in doc.blocks:
        for ent in block.query():
            c[ent.dxftype()] += 1
    return {"ok": True, "drawing": _drawing_name, "resumo": dict(c), "total": sum(c.values())}


# ----------------------------------------------------------------- estado
def state_summary():
    doc = _ensure()
    return {
        "ok": True,
        "drawing": _drawing_name,
        "entidades": _ent_count(doc),
        "camadas": [l.name for l in doc.layers],
        "blocos": [b.name for b in doc.blocks],
        "versão ezdxf": ezx_version(),
    }


# ----------------------------------------------------------------- comandos
def command_line(comando):
    return {"ok": True, "comando": comando, "tipo": "command_line"}


def script(codigo):
    return {"ok": True, "codigo": codigo, "tipo": "script"}


def inspect_drawing():
    return state_summary()


def new_drawing(nome="planta_vazia"):
    global _drawing_name
    _drawing_name = nome
    reset_drawing()
    return {"ok": True, "drawing": nome, "msg": "novo desenho criado"}


def open(descricao):
    return {"ok": True, "drawing": _drawing_name, "msg": "aberto: %s" % descricao}


def save(descricao):
    return {"ok": True, "drawing": _drawing_name, "msg": "salvo: %s" % descricao}


def cancel():
    return {"ok": True, "drawing": _drawing_name, "msg": "cancelado"}


# ------------------------------------------------------------------ registry
# mapa: nome → função para o FastMCP. O server.py registra aqui as ferramentas.
TOOLS = {
    "draw_line": draw_line,
    "draw_rectangle": draw_rectangle,
    "draw_polyline": draw_polyline,
    "draw_circle": draw_circle,
    "draw_arc": draw_arc,
    "draw_text": draw_text,
    "draw_mtext": draw_mtext,
    "draw_hatch": draw_hatch,
    "dim_linear": dim_linear,
    "dim_aligned": dim_aligned,
    "layer_list": layer_list,
    "layer_create": layer_create,
    "layer_set_current": layer_set_current,
    "ensure_standard_layers": ensure_standard_layers,
    "block_list": block_list,
    "block_insert": block_insert,
    "block_attributes": block_attributes,
    "block_set_attribute": block_set_attribute,
    "export_dxf": export_dxf,
    "plot_pdf": plot_pdf,
    "render_png": render_png,
    "screenshot": screenshot,
    "undo": undo,
    "redo": redo,
    "zoom_extents": zoom_extents,
    "quantitativo": quantitativo,
    "state_summary": state_summary,
    "command_line": command_line,
    "script": script,
    "inspect_drawing": inspect_drawing,
    "new_drawing": new_drawing,
    "open": open,
    "save": save,
    "cancel": cancel,
}
