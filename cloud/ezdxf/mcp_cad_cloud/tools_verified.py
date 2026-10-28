"""Verified ezdxf cloud tools. No stub that falsely reports success is registered."""
from __future__ import annotations
import base64
from collections import Counter
import io
import math
import os
from pathlib import Path
import tempfile
import zipfile
from functools import wraps
from mcp_cad_cloud.backend import _ensure, _ent_count, ezx_version, reset_drawing, state_summary, drawing_name, set_drawing_name
from mcp_cad_cloud import __version__
from mcp_cad_cloud.build_identity import info
from mcp_cad_cloud.planta_catalogo import TEMPLATE_PADRAO, listar_templates


MAX_DXF_BYTES = 3_000_000

def _point(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} deve ser [x,y] em metros")
    x, y = map(float, value)
    if not all(map(math.isfinite, (x, y))):
        raise ValueError(f"{label} deve ter coordenadas finitas")
    return x, y

def _positive(value, label):
    v = float(value)
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{label} deve ser positivo e finito")
    return v

def _layer(doc, layer):
    if not isinstance(layer, str) or not layer or len(layer) > 128:
        raise ValueError("nome de layer inválido")
    if layer not in doc.layers:
        raise ValueError(f"layer inexistente: {layer}; crie com layer_create")
    return layer

def _wrap(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError, KeyError) as exc:
            return {"ok": False, "code": "INVALID_INPUT", "error": str(exc)}
        except Exception as exc:
            return {"ok": False, "code": "BACKEND_ERROR", "error": str(exc)}
    return call


@_wrap
def planta_assistida(programa: dict | None = None, modo: str = "preview",
                     nome: str | None = None, template: str | None = None,
                     preview_token: str | None = None) -> dict:
    """Create the deterministic residential template in headless ezdxf.

    The cloud variant never opens or edits AutoCAD; ``desenhar`` changes only
    the ephemeral DXF held by this HTTP session.
    """
    if programa is not None and not isinstance(programa, dict):
        return {"ok": False, "code": "INVALID_INPUT", "error": "programa deve ser JSON"}
    programa = dict(programa or {})
    solicitado = str(template or programa.get("template") or
                     ("programa_sob_medida" if "ambientes" in programa else TEMPLATE_PADRAO)).strip()
    if solicitado not in {TEMPLATE_PADRAO, "tiny_house_10m2", "programa_sob_medida"}:
        return {"ok": False, "code": "TEMPLATE_NOT_SUPPORTED",
                "error": f"template '{solicitado}' ainda nao esta disponivel",
                "templates": listar_templates(),
                "proxima_acao": "escolher um template suportado"}
    if solicitado != "programa_sob_medida":
        largura_padrao = 12.0 if solicitado == TEMPLATE_PADRAO else 2.5
        profundidade_padrao = 11.0 if solicitado == TEMPLATE_PADRAO else 4.0
        if (("largura_externa" in programa and float(programa["largura_externa"]) != largura_padrao) or
                ("profundidade_externa" in programa and float(programa["profundidade_externa"]) != profundidade_padrao)):
            return {"ok": False, "code": "TEMPLATE_NOT_SUPPORTED",
                    "error": "as dimensoes pedidas nao pertencem a um template disponivel",
                    "templates": listar_templates(),
                    "proxima_acao": "escolher um template suportado"}
    programa["template"] = solicitado
    from mcp_cad_cloud.planta_assistida import planta_assistida as build
    result = build(programa=programa, modo=modo, nome=nome,
                   preview_token=preview_token)
    if nome and result.get("ok"):
        set_drawing_name(str(nome))
    return result


@_wrap
def planta_criar_validada(programa: dict | None = None, modo: str = "preview",
                          nome: str | None = None, template: str | None = None,
                          preview_token: str | None = None) -> dict:
    """Entrada recomendada: gera preview e exige token para desenhar."""
    return planta_assistida(programa, modo, nome, template, preview_token)


@_wrap
def planta_templates() -> dict:
    """Lista templates e impede que o agente improvise uma tipologia."""
    return {
        "ok": True,
        "ambiente": "cloud_headless_ezdxf",
        "autocad": {"disponivel": False, "acao": "nao tentar abrir, conectar ou reiniciar o AutoCAD"},
        "template_padrao": TEMPLATE_PADRAO,
        "templates": listar_templates(),
        "fluxo_obrigatorio": [
            "planta_templates",
            "planta_criar_validada(modo='preview')",
            "planta_criar_validada(modo='desenhar', preview_token=preview_token)",
        ],
        "selecao_de_ferramentas": {
            "template_compativel": "use planta_criar_validada; nao reconstrua com linhas e retangulos",
            "tipologia_sem_template": "use validar_planta e depois primitivas em sequencia controlada",
            "cad_avancado": "use primitivas somente quando o pedido exigir edicao ou geometria fora do template",
        },
        "ordem_primitivas": [
            "cad_status",
            "new_drawing",
            "layer_create",
            "validar_planta(modelo, estrito=true)",
            "paredes em segmentos que respeitem os vaos",
            "portas e janelas",
            "mobiliario, textos e cotas",
            "drawing_audit, inspect_drawing",
            "export_dxf",
        ],
        "proibido": [
            "desenhar uma parede continua por baixo de uma porta",
            "colocar arco de porta sem vao correspondente",
            "usar retangulos sobrepostos para simular encontros de paredes",
            "entregar sem auditoria",
        ],
        "regra": "preview e token sao obrigatorios para template; primitivas exigem validacao, sequencia e auditoria",
    }

@_wrap
def validar_planta(modelo: dict | None = None, estrito: bool = False) -> dict:
    """Validate a parametric floor-plan model without changing the DXF."""
    if modelo is None:
        from mcp_cad_cloud.planta_assistida import build_assisted_model
        modelo = build_assisted_model({})
    if not isinstance(modelo, dict):
        raise ValueError("modelo deve ser um objeto JSON")
    from mcp_cad_cloud.validar_modelo import validar
    result = validar(modelo, estrito=bool(estrito))
    return {"ok": bool(result.get("ok")),
            "code": "VALID_LAYOUT" if result.get("ok") else "INVALID_LAYOUT",
            "validacao": result,
            "proxima_acao": "desenhar" if result.get("ok") else "corrigir o modelo e validar novamente"}

@_wrap
def cad_status() -> dict:
    """Return the cloud/headless boundary before any drawing operation."""
    return {**state_summary(), "version_ezdxf": ezx_version(), "drawing": drawing_name(),
            "profile": PROFILE,
            "backend": "ezdxf",
            "execution_mode": "cloud_headless",
            "autocad_available": False,
            "desktop_access": False,
            "dwg_access": False,
            "next_step": "use planta_templates; nao tente abrir ou controlar o AutoCAD",
            "capabilities": list(PUBLIC_TOOLS),
            "build": info(__version__, "http", "ezdxf")}

@_wrap
def new_drawing(name: str = "planta_sem_nome") -> dict:
    """Reset to a new empty metric DXF, discarding previously unsaved work."""
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise ValueError("nome de desenho inválido")
    reset_drawing()
    set_drawing_name(name)
    return {"ok": True, "drawing": drawing_name(), "entities": 0}

@_wrap
def layer_list() -> dict:
    """List actual DXF layers."""
    return {"ok": True, "layers": [x.dxf.name for x in _ensure().layers]}

@_wrap
def layer_create(nome: str, cor: int = 7) -> dict:
    """Create layer using an AutoCAD ACI color index from 1 to 255."""
    doc = _ensure()
    if not isinstance(nome, str) or not nome.strip() or len(nome) > 128:
        raise ValueError("nome de camada inválido")
    if not (isinstance(cor, int) and 1 <= cor <= 255):
        raise ValueError("cor deve ser índice ACI 1..255")
    if nome in doc.layers:
        return {"ok": True, "layer": nome, "created": False}
    doc.layers.new(nome, dxfattribs={"color": cor})
    return {"ok": True, "layer": nome, "created": True}

@_wrap
def inspect_drawing() -> dict:
    """Inspect a drawing, counting real modelspace entities."""
    doc = _ensure()
    return {"ok": True, "drawing": drawing_name(), "entities": len(doc.modelspace()),
            "by_type": _ent_count(doc), "layers": [x.dxf.name for x in doc.layers],
            "units": doc.header.get("$INSUNITS")}

@_wrap
def query_entities(layer: str | None = None, tipo: str | None = None) -> dict:
    """Find DXF entity handles by layer and type."""
    msp = _ensure().modelspace()
    items = [{"handle": e.dxf.handle, "type": e.dxftype(), "layer": e.dxf.layer}
             for e in msp if (not layer or e.dxf.layer == layer)
             and (not tipo or e.dxftype() == tipo.upper())]
    return {"ok": True, "entities": items, "count": len(items)}

@_wrap
def draw_line(start: list[float], end: list[float], layer: str = "0") -> dict:
    """Add an actual LINE in metres and return its handle."""
    doc = _ensure()
    ent = doc.modelspace().add_line(_point(start, "start"), _point(end, "end"),
                                    dxfattribs={"layer": _layer(doc, layer)})
    return {"ok": True, "handle": ent.dxf.handle, "type": "LINE"}

@_wrap
def draw_rectangle(bl: list[float], tr: list[float], layer: str = "0") -> dict:
    """Draw a nondegenerate closed rectangular LWPOLYLINE."""
    doc = _ensure()
    x0, y0 = _point(bl, "bl")
    x1, y1 = _point(tr, "tr")
    if x0 >= x1 or y0 >= y1:
        raise ValueError("tr deve estar acima e à direita de bl")
    ent = doc.modelspace().add_lwpolyline(
        [(x0,y0),(x1,y0),(x1,y1),(x0,y1)], close=True,
        dxfattribs={"layer": _layer(doc, layer)})
    return {"ok": True, "handle": ent.dxf.handle, "type": "LWPOLYLINE", "closed": True}

@_wrap
def draw_polyline(points: list[list[float]], layer: str = "0", closed: bool = False) -> dict:
    """Draw a polyline with at least two points (three when closed)."""
    doc = _ensure()
    if len(points) < (3 if closed else 2):
        raise ValueError("pontos insuficientes")
    p = [_point(v, "point") for v in points]
    ent = doc.modelspace().add_lwpolyline(p, close=closed, dxfattribs={"layer": _layer(doc, layer)})
    return {"ok": True, "handle": ent.dxf.handle, "type": "LWPOLYLINE"}

@_wrap
def draw_circle(center: list[float], radius: float, layer: str = "0") -> dict:
    """Draw a circle of given radius in metres."""
    doc = _ensure()
    ent = doc.modelspace().add_circle(_point(center, "center"), _positive(radius, "radius"),
                                      dxfattribs={"layer": _layer(doc, layer)})
    return {"ok": True, "handle": ent.dxf.handle, "type": "CIRCLE"}

@_wrap
def draw_arc(center: list[float], radius: float, start_angle: float, end_angle: float,
             layer: str = "0") -> dict:
    """Draw an arc with counterclockwise degree angles."""
    doc = _ensure()
    start, end = float(start_angle), float(end_angle)
    if not math.isfinite(start) or not math.isfinite(end):
        raise ValueError("ângulos não finitos")
    ent = doc.modelspace().add_arc(_point(center, "center"), _positive(radius, "radius"),
                                   start_angle=start, end_angle=end,
                                   dxfattribs={"layer": _layer(doc, layer)})
    return {"ok": True, "handle": ent.dxf.handle, "type": "ARC"}

@_wrap
def draw_text(texto: str, insert: list[float], height: float = 0.2,
              layer: str = "0") -> dict:
    """Draw actual DXF text using metres for height."""
    doc = _ensure()
    if not isinstance(texto, str) or not texto or len(texto) > 500:
        raise ValueError("texto inválido")
    ent = doc.modelspace().add_text(texto, dxfattribs={
        "height": _positive(height, "height"), "insert": _point(insert, "insert"),
        "layer": _layer(doc, layer)})
    return {"ok": True, "handle": ent.dxf.handle, "type": "TEXT"}

@_wrap
def dim_aligned(p1: list[float], p2: list[float], distance: float = 0.5,
                layer: str = "0") -> dict:
    """Create an aligned DXF dimension in metres."""
    doc = _ensure()
    a, b = _point(p1, "p1"), _point(p2, "p2")
    if a == b:
        raise ValueError("cota sem comprimento")
    dim = doc.modelspace().add_aligned_dim(p1=a, p2=b, distance=_positive(distance, "distance"),
                                           dimstyle="EZDXF", dxfattribs={"layer": _layer(doc, layer)})
    dim.render()
    return {"ok": True, "handle": dim.dimension.dxf.handle, "type": "DIMENSION"}

@_wrap
def erase(entity_id: str, confirmar: bool = False) -> dict:
    """Delete a DXF entity by handle only after explicit confirmation."""
    doc = _ensure()
    ent = doc.entitydb.get(entity_id)
    if ent is None or ent not in doc.modelspace():
        return {"ok": False, "code": "NOT_FOUND", "handle": entity_id}
    if not confirmar:
        return {"ok": True, "preview": True, "handle": entity_id, "type": ent.dxftype()}
    doc.modelspace().delete_entity(ent)
    return {"ok": True, "deleted": True, "handle": entity_id}

@_wrap
def drawing_audit() -> dict:
    """Execute ezdxf audit. This is NOT an architectural approval."""
    auditor = _ensure().audit()
    return {"ok": not auditor.has_errors, "errors": len(auditor.errors),
            "fixes": len(auditor.fixes), "warning": "Não substitui análise arquitetônica"}

@_wrap
def quantitativo() -> dict:
    """Return counts of actual entities by type and layer, not architectural quantities."""
    entities = list(_ensure().modelspace())
    return {"ok": True, "entities": len(entities),
            "by_type": dict(Counter(e.dxftype() for e in entities)),
            "by_layer": dict(Counter(e.dxf.layer for e in entities)),
            "warning": "Contagem de entidades; não mede paredes nem portas"}

@_wrap
def export_dxf() -> dict:
    """Export real DXF as zip/base64; refuses files larger than 3 MB."""
    doc = _ensure()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "desenho.dxf"
        doc.saveas(path)
        raw = path.read_bytes()
    if len(raw) > MAX_DXF_BYTES:
        return {"ok": False, "code": "SIZE_LIMIT", "bytes": len(raw)}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("desenho.dxf", raw)
    payload = buf.getvalue()
    return {"ok": True, "filename": "desenho.dxf.zip", "format": "zip/base64",
            "bytes": len(payload), "data_base64": base64.b64encode(payload).decode()}

TOOLS = ("cad_status", "new_drawing", "layer_list", "layer_create", "inspect_drawing",
         "query_entities", "draw_line", "draw_rectangle", "draw_polyline", "draw_circle",
         "draw_arc", "draw_text", "dim_aligned", "erase", "drawing_audit",
         "quantitativo", "export_dxf", "planta_templates", "planta_assistida",
         "planta_criar_validada", "validar_planta")

# The cloud implementation also contains the headless equivalents of the
# lower-level CAD operations.  Keep the verified floor-plan functions as the
# canonical implementation for overlapping names, and add the primitive
# registry only when the caller explicitly selects the full profile.
from mcp_cad_cloud import tools as _headless_tools

_HEADLESS_TOOLS = tuple(
    name for name in _headless_tools.TOOLS
    if name != "nome_publico" and hasattr(_headless_tools, name)
)

_PLANTA_SEGURA = {
    "cad_status", "new_drawing", "layer_list", "inspect_drawing", "query_entities",
    "drawing_audit", "quantitativo", "export_dxf", "planta_templates",
    "planta_assistida", "planta_criar_validada", "validar_planta",
}
_perfil = os.getenv("MCP_CAD_PROFILE", "full").strip().lower()
PROFILE = "full" if _perfil in {"full", "livre", "avancado"} else "planta_segura"
PUBLIC_TOOLS = tuple(dict.fromkeys(
    (*TOOLS, *_HEADLESS_TOOLS)
)) if PROFILE == "full" else tuple(
    name for name in TOOLS if name in _PLANTA_SEGURA
)
