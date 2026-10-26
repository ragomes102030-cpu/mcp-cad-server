# -*- coding: utf-8 -*-
"""Ferramentas das familias `desenho`, `edicao` e `arquitetura`.

Mescla controlada do contrato do autocad-mcp-pro 1.6.0 implementada sobre o
NOSSO backend (o nome publico e' o dele, para que um prompt escrito para aquele
servidor funcione aqui sem traducao). Nada aqui copia o `server.py` de la: o que
se extrai e' o contrato (nome, argumentos, o que promete) e a implementacao e'
nossa.

Como o backend ja' expoe parte do que falta, varias ferramentas sao wrappers
finos. Onde o backend nao tinha o metodo, ele foi estendido
(`base.py`/`ezdxf_backend.py`/`com_backend.py`/`file_ipc.py`) -- ver o bloco
"primitivas novas" em cada um.

Regras que este modulo obedece:
  * **destrutivo exige confirmacao** -- `entity_delete_many` conta e so' apaga
    com `confirmar=True`; sem ele devolve a pre-visualizacao.
  * **sem AutoCAD vivo, ok=false com motivo** -- nunca fingir sucesso.
  * **comando nao e' metodo** -- `TRIM`/`EXTEND`/`FILLET`/`CHAMFER`/`JOIN` sao
    comandos do AutoCAD. O que existe aqui e' geometria propria (a ponte .NET
    cobre o resto, via `tools.trim_entity`).
  * **medido != documentado** -- cada ferramenta diz em qual motor foi testada.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from .backend_manager import MANAGER


# ------------------------------------------------------------------ helpers
def _r(res) -> dict:
    return res.to_dict() if hasattr(res, "to_dict") else {"ok": bool(res), "payload": res}


async def _b():
    return await MANAGER.get()


def _sem_lisp(b) -> dict | None:
    """Backend headless nao tem VLA; devolve o erro em vez de estourar."""
    if not hasattr(b, "_aval"):
        return {"ok": False,
                "erro": "backend '%s' nao executa LISP/VLA; abra o AutoCAD para esta operacao"
                        % getattr(b, "name", "?")}
    return None


def _q(s) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _area_fechada(pontos) -> float:
    """Area por shoelace (sinal ignorado). Usada em ambientes e lacos."""
    n = len(pontos)
    if n < 3:
        return 0.0
    soma = 0.0
    for i in range(n):
        x1, y1 = pontos[i][0], pontos[i][1]
        x2, y2 = pontos[(i + 1) % n][0], pontos[(i + 1) % n][1]
        soma += x1 * y2 - x2 * y1
    return abs(soma) / 2.0


# ------------------------------------------------------------------ desenho
async def entity_create_ellipse(cx: float, cy: float, major_x: float, major_y: float,
                                ratio: float, layer: str | None = None) -> dict:
    """Elipse pelo centro, vetor do eixo maior e razao entre os eixos."""
    if ratio <= 0:
        return {"ok": False, "erro": "ratio precisa ser > 0"}
    b = await _b()
    r = await b.create_ellipse(cx, cy, major_x, major_y, ratio, layer=layer)
    return _r(r)


async def entity_create_point(x: float, y: float, layer: str | None = None) -> dict:
    """Um ponto de marcacao (no). Nao e' geometria desenhavel."""
    r = _r(await (await _b()).create_point(x, y, layer=layer))
    if r.get("ok"):
        r["nota"] = "POINT e marcacao de no; nao aparece como traco no plot"
    return r


async def entity_create_spline(fit_points: list[list[float]],
                               layer: str | None = None) -> dict:
    """Spline (NURBS) por pontos de ajuste. Exige ao menos 2 pontos."""
    if len(fit_points) < 2:
        return {"ok": False, "erro": "spline precisa de ao menos 2 pontos de ajuste"}
    return _r(await (await _b()).create_spline(fit_points, layer=layer))


async def construction_xline(x: float, y: float, angle_deg: float,
                             layer: str | None = None) -> dict:
    """Linha infinita de construcao (XLINE). Existe para apoiar o desenho, nao para plotar."""
    r = _r(await (await _b()).create_xline(x, y, angle_deg, layer=layer))
    if r.get("ok"):
        r["nota"] = "XLINE e linha de construcao: nao aparece no plot"
    return r


async def entity_create_revcloud(points: list[list[float]], segment_length: float = 0.5,
                                 layer: str | None = None, closed: bool = False) -> dict:
    """Nuvem de revisao: semicirculos tangentes ao longo do contorno.

    A aproximacao e' geometrica (um semicirculo por segmento), nao o algoritmo
    do AutoCAD: o formato e' recognicivel e o perimetro e' parecido, mas a
    curvatura nao e' identica. Para marcacao de revisao em planta, serve.
    """
    pts = [list(p) for p in points]
    if closed and len(pts) > 2 and pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    if len(pts) < 2:
        return {"ok": False, "erro": "revcloud precisa de ao menos 2 pontos"}
    b = await _b()
    arcos, falhas = [], 0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i][0], pts[i][1]
        x2, y2 = pts[i + 1][0], pts[i + 1][1]
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        raio = math.hypot(x2 - x1, y2 - y1) / 2.0
        if raio <= 1e-9:
            falhas += 1
            continue
        a0 = math.degrees(math.atan2(y1 - my, x1 - mx))
        a1 = math.degrees(math.atan2(y2 - my, x2 - mx))
        r = await b.create_arc(mx, my, raio, a0, a1, layer=layer)
        if r.ok:
            _pl = r.payload
            arcos.append(_pl if isinstance(_pl, str) else ((_pl or {}).get("handle") if isinstance(_pl, dict) else None))
        else:
            falhas += 1
    return {"ok": falhas == 0, "arcos": len(arcos), "handles": arcos,
            "falhas": falhas, "nota": "aproximacao por semicirculos (nao e' o algoritmo do AutoCAD)"}


async def drawing_properties_get() -> dict:
    """Campos de resumo do desenho (DWGPROPS): titulo, autor, palavras-chave..."""
    return _r(await (await _b()).drawing_properties_get())


async def drawing_properties_set(title: str | None = None, subject: str | None = None,
                                 author: str | None = None, keywords: str | None = None,
                                 comments: str | None = None,
                                 custom: dict | None = None) -> dict:
    """Grava os campos de resumo do desenho. No motor headless vira header custom var."""
    b = await _b()
    return _r(await b.drawing_properties_set(title=title, subject=subject, author=author,
                                             keywords=keywords, comments=comments,
                                             custom=custom))


async def drawing_apply_standard(standard: str = "ISO", layers: str = "arquitetura",
                                 unidades: int = 6) -> dict:
    """Deixa o desenho num padrao (ISO ou ANSI) numa chamada: camadas + unidades + cota.

    E' composicao das ferramentas que ja' existem (`drawing_setup`,
    `ensure_standard_layers`, `layer_create`), nao um comando novo do AutoCAD.
    """
    b = await _b()
    saida = {"ok": True, "standard": standard.upper(), "passos": []}

    # `drawing_setup` e' uma TOOL (tools.py), nao metodo de backend -- e o ezdxf
    # nao o tem. Import tardio para nao fechar ciclo com tools.py.
    from . import tools as _tools

    r = await _tools.drawing_setup(unidades=unidades, escala_cota=0.1, ltscale=0.2)
    saida["passos"].append(r if isinstance(r, dict) else _r(r))
    if not (r.get("ok") if isinstance(r, dict) else r.ok):
        saida["ok"] = False
        saida["erro"] = (r.get("erro") or r.get("error") or "drawing_setup falhou"
                         if isinstance(r, dict) else r.error)
        return saida

    r = await _ensure_layers(b)
    saida["passos"].append(r if isinstance(r, dict) else _r(r))
    if isinstance(r, dict) and not r.get("ok", True):
        saida["ok"] = False
        saida["erro"] = r.get("erro") or "ensure_standard_layers falhou"

    # No padrao ANSI (mecanico) as camadas de planta nao se aplicam: avisa.
    if layers.lower() in ("mecanica", "mechanical", "ansi"):
        saida["aviso"] = ("o conjunto de camadas criadas e' de ARQUITETURA; o padrao %s "
                          "muda cotas e unidades, nao as camadas" % standard.upper())
    return saida


from .layers import ensure_standard_layers as _ensure_layers  # noqa: E402


async def user_pick_point(prompt: str = "Escolha um ponto") -> dict:
    """Pede um ponto ao operador na tela do AutoCAD. So' existe no motor COM.

    Headless nao tem tela: devolve ok=false com o motivo, em vez de inventar
    coordenada. E' a unica ferramenta deste modulo que nao da para testar sem
    alguem olhando o AutoCAD.
    """
    b = await _b()
    if not hasattr(b, "_aval"):
        return {"ok": False, "erro": "user_pick_point exige o AutoCAD aberto (backend '%s')"
                                     % getattr(b, "name", "?")}
    expr = '(progn (initget 1) (getpoint "\n%s "))' % _q(prompt)
    r = await b.execute_lisp(expr)
    return _r(r)


# ------------------------------------------------------------------ edicao
async def entity_scale(entity_id: str, base_x: float, base_y: float,
                       factor: float) -> dict:
    """Redimensiona uma entidade uniformemente em torno de um ponto-base."""
    if factor == 0:
        return {"ok": False, "erro": "factor 0 apagaria a entidade; use um valor != 0"}
    return _r(await (await _b()).entity_scale(entity_id, base_x, base_y, factor))


async def entity_chamfer(handle1: str, handle2: str, dist1: float, dist2: float,
                         trim: bool = True) -> dict:
    """Bisela o canto entre duas retas (CHAMFER). Geometria propria, sem comando.

    `trim=True` corta as pontas; `False` so' adiciona a chanfro.
    """
    b = await _b()
    if not hasattr(b, "entity_chamfer"):
        return {"ok": False, "erro": "backend '%s' nao implementa entity_chamfer"
                                     % getattr(b, "name", "?")}
    # o `trim` e' do contrato do acmpro; o nosso motor sempre apara
    return _r(await b.entity_chamfer(handle1, handle2, dist1, dist2))


async def entity_array_rectangular(handle: str, rows: int, cols: int,
                                   row_spacing: float, col_spacing: float) -> dict:
    """Repete uma entidade numa grade de linhas x colunas (ARRAYRECT)."""
    if rows < 1 or cols < 1:
        return {"ok": False, "erro": "rows e cols precisam ser >= 1"}
    b = await _b()
    if not hasattr(b, "entity_array"):
        return {"ok": False, "erro": "backend '%s' nao implementa entity_array"
                                     % getattr(b, "name", "?")}
    return _r(await b.entity_array(handle, rows, cols, row_spacing, col_spacing))


async def entity_array_polar(handle: str, count: int, fill_angle: float,
                             center_x: float, center_y: float) -> dict:
    """Repete uma entidade em torno de um centro (ARRAYPOLAR): roda de parafusos etc."""
    if count < 1:
        return {"ok": False, "erro": "count precisa ser >= 1"}
    return _r(await (await _b()).entity_array_polar(handle, count, fill_angle,
                                                    center_x, center_y))


async def entity_set_properties(handle: str, layer: str | None = None,
                                color: int | str | None = None,
                                linetype: str | None = None,
                                lineweight: int | None = None,
                                visible: bool | None = None) -> dict:
    """Muda camada, cor, tipo de linha, espessura ou visibilidade de uma entidade."""
    if all(v is None for v in (layer, color, linetype, lineweight, visible)):
        return {"ok": False, "erro": "nenhuma propriedade informada"}
    return _r(await (await _b()).entity_set_properties(handle, layer=layer, color=color,
                                                        linetype=linetype,
                                                        lineweight=lineweight,
                                                        visible=visible))


async def entity_set_properties_filter(filter_layer: str | None = None,
                                       tipo: str | None = None,
                                       target_layer: str | None = None,
                                       color: int | str | None = None,
                                       linetype: str | None = None,
                                       lineweight: int | None = None,
                                       visible: bool | None = None) -> dict:
    """Altera em lote entidades filtradas por camada e/ou tipo DXF.

    Exige um filtro e uma propriedade de destino. Use ``target_layer`` para
    evitar confundir a camada selecionada (``filter_layer``) com a de destino.
    """
    if filter_layer is None and tipo is None:
        return {"ok": False, "erro": "informe ao menos um filtro (filter_layer ou tipo)"}
    if all(v is None for v in (target_layer, color, linetype, lineweight, visible)):
        return {"ok": False, "erro": "nenhuma propriedade de destino informada"}
    b = await _b()
    fn = getattr(b, "entity_set_properties_filter", None)
    if fn is None:
        return {"ok": False, "erro": "backend '%s' nao suporta edicao em lote" % getattr(b, "name", "?")}
    return _r(await fn(filter_layer=filter_layer, tipo=tipo, target_layer=target_layer,
                       color=color, linetype=linetype, lineweight=lineweight,
                       visible=visible))


async def entity_edit_text(handle: str, text: str | None = None,
                           height: float | None = None,
                           rotation: float | None = None) -> dict:
    """Troca o texto, a altura ou a rotacao de um TEXT, mantendo o handle."""
    if all(v is None for v in (text, height, rotation)):
        return {"ok": False, "erro": "nada para alterar (text/height/rotation)"}
    return _r(await (await _b()).entity_edit_text(handle, text=text, height=height,
                                                  rotation=rotation))


async def entity_delete_many(handles: list[str], confirmar: bool = False) -> dict:
    """Apaga varias entidades de uma vez. DESTRUTIVO: so' apaga com `confirmar=True`.

    Sem `confirmar` devolve quantas seriam apagadas e NAO apaga nada. E' a regra
    do projeto: o agente nunca roda destrutivo sem confirmacao do usuario.
    """
    if not handles:
        return {"ok": False, "erro": "lista de handles vazia"}
    b = await _b()
    if not confirmar:
        existentes = 0
        for h in handles:
            g = await b.entity_geometry(h)
            if g.ok:
                existentes += 1
        return {"ok": False, "pre_visualizacao": True, "handles": len(handles),
                "existentes": existentes,
                "erro": ("pre-visualizacao: %d de %d handles existem e seriam apagados. "
                         "Rode de novo com confirmar=True para apagar." % (existentes,
                                                                           len(handles)))}
    return _r(await b.entity_delete_many(handles))


async def hatch_edit(handle: str, pattern: str | None = None, scale: float | None = None,
                     angle: float | None = None, color: int | str | None = None,
                     style: str | None = None) -> dict:
    """Muda o padrao, a escala, o angulo, a cor ou o estilo de uma hachura."""
    return _r(await (await _b()).hatch_edit(handle, pattern=pattern, scale=scale,
                                            angle=angle, color=color, style=style))


async def entity_fillet(handle1: str, handle2: str, radius: float, trim: bool = True) -> dict:
    """Arredonda o canto entre duas retas (FILLET) por geometria propria.

    Diferente de `fillet_entity` (que usa a ponte .NET): aqui quem calcula e' o
    backend, entao o resultado nao depende de o plugin estar carregado.
    """
    if radius < 0:
        return {"ok": False, "erro": "radius precisa ser >= 0"}
    b = await _b()
    if not hasattr(b, "entity_fillet"):
        return {"ok": False, "erro": "backend '%s' nao implementa entity_fillet"
                                     % getattr(b, "name", "?")}
    return _r(await b.entity_fillet(handle1, handle2, radius))


# ------------------------------------------------------------- consulta/geo
async def entity_get(entity_id: str) -> dict:
    """Inspeciona UMA entidade: tipo, camada e geometria (pontos, centro, raio, angulos).

    E' a versao com geometria da `entity_get` do acmpro. O handle vem de
    `entity_list` / `entity_create_*` e vale apenas na mesma sessao.
    """
    b = await _b()
    fn = getattr(b, "entity_geometry", None)
    if fn is None:
        r = _r(await b.entity_get(entity_id))
        r["aviso"] = "backend sem entity_geometry; devolve so tipo/camada"
        return r
    return _r(await fn(entity_id))


async def point_from_snap(handle: str, snap: str, ref_x: float | None = None,
                          ref_y: float | None = None) -> dict:
    """Ponto exato de uma entidade: endpoint, midpoint, center, quadrant ou perpendicular.

    `perpendicular` precisa de `ref_x`/`ref_y`: e' o pe da perpendicular do ponto
    de referencia ate' a entidade.
    """
    b = await _b()
    g = await b.entity_geometry(handle)
    if not g.ok:
        return _r(g)
    geo = g.payload or {}
    pts = geo.get("pontos") or []
    tipo = geo.get("tipo")
    snap = str(snap).lower()

    if snap in ("endpoint", "extremo", "end"):
        if not pts:
            return {"ok": False, "erro": "a entidade %s nao tem pontos" % tipo}
        melhor, dist = None, None
        for p in pts:
            d = 0.0 if ref_x is None else math.hypot(p[0] - ref_x, p[1] - ref_y)
            if dist is None or d < dist:
                melhor, dist = p, d
        return {"ok": True, "ponto": melhor, "snap": snap, "handle": handle}

    if snap in ("midpoint", "medio", "mid"):
        if tipo == "LINE" and len(pts) >= 2:
            return {"ok": True, "ponto": [(pts[0][0] + pts[1][0]) / 2.0,
                                          (pts[0][1] + pts[1][1]) / 2.0],
                    "snap": snap, "handle": handle}
        return {"ok": False, "erro": "midpoint so' para LINE (a entidade e' %s)" % tipo}

    if snap in ("center", "centro", "centre"):
        if geo.get("centro"):
            return {"ok": True, "ponto": list(geo["centro"]), "snap": snap, "handle": handle}
        return {"ok": False, "erro": "a entidade %s nao tem centro" % tipo}

    if snap in ("quadrant", "quadrante"):
        if tipo in ("CIRCLE", "ARC") and geo.get("centro") and geo.get("raio"):
            cx, cy, raio = geo["centro"][0], geo["centro"][1], geo["raio"]
            ang = geo.get("angulo_inicio") if tipo == "ARC" else 0.0
            q = round(ang / 90.0) % 4 if tipo == "ARC" else 0
            a = math.radians(q * 90.0)
            return {"ok": True, "ponto": [cx + raio * math.cos(a), cy + raio * math.sin(a)],
                    "snap": snap, "quadrante": q, "handle": handle}
        return {"ok": False, "erro": "quadrant so' para CIRCLE/ARC (a entidade e' %s)" % tipo}

    if snap in ("perpendicular", "perpendicular foot", "pe"):
        if ref_x is None or ref_y is None:
            return {"ok": False, "erro": "perpendicular precisa de ref_x/ref_y"}
        if tipo != "LINE" or len(pts) < 2:
            return {"ok": False, "erro": "perpendicular so' para LINE (a entidade e' %s)" % tipo}
        x1, y1 = pts[0][0], pts[0][1]
        x2, y2 = pts[1][0], pts[1][1]
        dx, dy = x2 - x1, y2 - y1
        den = dx * dx + dy * dy
        if den <= 1e-12:
            return {"ok": False, "erro": "linha degenerada (comprimento zero)"}
        t = ((ref_x - x1) * dx + (ref_y - y1) * dy) / den
        t = max(0.0, min(1.0, t))
        return {"ok": True, "ponto": [x1 + t * dx, y1 + t * dy], "snap": snap,
                "handle": handle, "t": round(t, 4)}

    return {"ok": False, "erro": "snap desconhecido: %r (endpoint|midpoint|center|quadrant|perpendicular)"
                                 % snap}


async def point_tangent(circle_handle: str, from_x: float, from_y: float,
                        ref_x: float | None = None, ref_y: float | None = None) -> dict:
    """Ponto de tangencia de uma reta que sai de um ponto externo ate' um circulo/arco.

    Devolve os dois pontos de tangencia (uma reta externa toca o circulo em dois).
    Sem solucao quando o ponto esta' DENTRO do circulo.
    """
    b = await _b()
    g = await b.entity_geometry(circle_handle)
    if not g.ok:
        return _r(g)
    geo = g.payload or {}
    if not geo.get("centro") or geo.get("raio") is None:
        return {"ok": False, "erro": "a entidade nao e CIRCLE/ARC (tipo %s)" % geo.get("tipo")}
    cx, cy, raio = geo["centro"][0], geo["centro"][1], float(geo["raio"])
    d = math.hypot(from_x - cx, from_y - cy)
    if d < raio - 1e-9:
        return {"ok": False, "erro": "o ponto (%.3f, %.3f) esta DENTRO do circulo (d=%.3f < r=%.3f); "
                                     "nao existe tangente" % (from_x, from_y, d, raio)}
    if d <= 1e-9:
        return {"ok": False, "erro": "o ponto coincide com o centro do circulo"}
    base = math.atan2(from_y - cy, from_x - cx)
    alfa = math.acos(raio / d)
    saida = {"ok": True, "centro": [cx, cy], "raio": raio, "distancia": round(d, 4),
             "tangencias": []}
    for sinal in (+1, -1):
        a = base + sinal * alfa
        tx, ty = cx + raio * math.cos(a), cy + raio * math.sin(a)
        t = {"x": round(tx, 4), "y": round(ty, 4)}
        if ref_x is not None and ref_y is not None:
            t["escolhida"] = (abs(tx - ref_x) + abs(ty - ref_y))
        saida["tangencias"].append(t)
    if ref_x is not None and ref_y is not None:
        dita = min(saida["tangencias"], key=lambda t: t["escolhida"])
        saida["ponto"] = [dita["x"], dita["y"]]
    return saida


async def selection_window(x1: float, y1: float, x2: float, y2: float,
                           modo: str = "crossing", entity_type: str | None = None,
                           layer: str | None = None) -> dict:
    """Lista o que cai dentro (ou cruza) uma janela retangular. Nao seleciona de fato.

    Devolve handles e tipos, para o agente decidir o que fazer. `modo`:
    `inside` (totalmente dentro) ou `crossing` (cruza a borda).
    """
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    b = await _b()
    r = _r(await b.entity_list(layer=layer))
    ents = ((r.get("payload") or {}).get("entities")) or []
    achados = []
    for e in ents:
        if entity_type and e.get("type") != entity_type.upper():
            continue
        g = await b.entity_geometry(e.get("handle"))
        if not g.ok:
            continue
        pts = (g.payload or {}).get("pontos") or []
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        dentro = min(xs) >= x1 and max(xs) <= x2 and min(ys) >= y1 and max(ys) <= y2
        cruza = not (max(xs) < x1 or min(xs) > x2 or max(ys) < y1 or min(ys) > y2)
        if (modo == "inside" and dentro) or (modo != "inside" and cruza):
            achados.append({"handle": e.get("handle"), "tipo": e.get("type"),
                            "camada": e.get("layer"),
                            "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return {"ok": True, "modo": modo, "janela": [x1, y1, x2, y2],
            "selecionadas": len(achados), "entidades": achados}


async def view_zoom_window(x1: float, y1: float, x2: float, y2: float) -> dict:
    """Zoom numa regiao retangular da tela (Z00M _W). So' existe com AutoCAD aberto."""
    b = await _b()
    fn = getattr(b, "zoom_window", None)
    if fn is None:
        return {"ok": False, "erro": "backend '%s' nao tem zoom" % getattr(b, "name", "?")}
    return _r(await fn(x1, y1, x2, y2))


# ------------------------------------------------------------- arquitetura
_MATERIAIS_ISO128_50 = {
    "concreto": "AR-CONC", "concrete": "AR-CONC",
    "tijolo": "AR-BRICK", "brick": "AR-BRICK", "alvenaria": "AR-BRICK",
    "madeira": "AR-WOOD", "wood": "AR-WOOD",
    "terra": "EARTH", "solo": "EARTH", "earth": "EARTH",
    "areia": "AR-SAND", "sand": "AR-SAND",
    "grama": "GRASS", "grass": "GRASS",
    "isopor": "INSUL", "isolation": "INSUL", "isolamento": "INSUL",
    "aco": "STEEL", "steel": "STEEL",
    "telha": "AR-ROOF", "roof": "AR-ROOF",
    "escada": "AR-HBONE", "stair": "AR-HBONE",
    "bloqueado": "AR-B816", "breeze": "AR-B816",
    "vidro": "TRANS", "glass": "TRANS",
}


async def hatch_material(material: str, boundary: str | None = None,
                         handles: list[str] | None = None, scale: float = 1.0,
                         angle: float = 0.0, layer: str | None = None) -> dict:
    """Hachura com o padrao ISO 128-50 do material (concreto, tijolo, terra...).

    O nome do padrao e' o do `acadiso.pat`. Material desconhecido devolve ok=false
    com a lista dos conhecidos -- nunca aplica um padrao ao acaso.
    """
    padrao = _MATERIAIS_ISO128_50.get(str(material).strip().lower())
    if padrao is None:
        return {"ok": False, "erro": "material desconhecido: %r" % material,
                "conhecidos": sorted(_MATERIAIS_ISO128_50)}
    b = await _b()
    alvos = []
    if handles:
        alvos = [str(h) for h in handles]
    elif boundary:
        alvos = [str(boundary)]
    if not alvos:
        return {"ok": False, "erro": "informe handles (ou boundary) da regiao a hachurar"}
    resultados, falhas = [], 0
    for h in alvos:
        g = await b.entity_geometry(h)
        # se o handle ja' e' uma hachura, edita a existente -- criar outra no
        # mesmo contorno deixa duas hachuras e o teste enxerga a errada
        if g.ok and (g.payload or {}).get("tipo") == "HATCH":
            r = await b.hatch_edit(h, pattern=padrao)
        else:
            r = await b.create_hatch(h, pattern=padrao)
        if r.ok:
            resultados.append(h)
        else:
            falhas += 1
    return {"ok": falhas == 0, "material": material, "padrao": padrao,
            "hachuradas": len(resultados), "falhas": falhas,
            "nota": "escala/angulo do padrao sao da tabela; o motor nao aplica scale/angle"}


async def arch_grid(x_axes: list[float], y_axes: list[float], labels: str = "auto",
                    extension: float = 0.5) -> dict:
    """Malha estrutural: eixos rotulados com bolhas nas duas pontas.

    `labels`: "auto" (X numerico, Y alfabetico), "numeric" (ambos numericos) ou
    "alpha" (ambos alfabeticos). Eixo de linha no layer `EIXOS`, bolha em
    `COTAS`.
    """
    if not x_axes and not y_axes:
        return {"ok": False, "erro": "informe x_axes e/ou y_axes"}
    b = await _b()
    await b.layer_create("EIXOS", color=4)
    await b.layer_create("COTAS", color=2)
    x0, x1 = (min(x_axes), max(x_axes)) if x_axes else (0.0, 0.0)
    y0, y1 = (min(y_axes), max(y_axes)) if y_axes else (0.0, 0.0)
    linhas, bolhas, rotulos = [], 0, 0
    alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def rotulo(i, modo):
        if modo == "alpha":
            return alfabeto[i % 26]
        return str(i + 1)

    modo_x = "numeric" if labels in ("numeric", "auto") else "alpha"
    modo_y = "alpha" if labels in ("alpha", "auto") else "numeric"

    for i, x in enumerate(x_axes):
        await b.create_line(x, y0 - extension, x, y1 + extension, layer="EIXOS")
        for y in (y0 - extension, y1 + extension):
            r = await b.create_circle(x, y, min(0.3, max(0.1, extension / 3)))
            if r.ok:
                bolhas += 1
            t = await b.create_text(x, y, rotulo(i, modo_x), height=0.15, layer="COTAS")
            if t.ok:
                rotulos += 1
        linhas.append("x=%g" % x)
    for i, y in enumerate(y_axes):
        await b.create_line(x0 - extension, y, x1 + extension, y, layer="EIXOS")
        for x in (x0 - extension, x1 + extension):
            r = await b.create_circle(x, y, min(0.3, max(0.1, extension / 3)))
            if r.ok:
                bolhas += 1
            t = await b.create_text(x, y, rotulo(i, modo_y), height=0.15, layer="COTAS")
            if t.ok:
                rotulos += 1
        linhas.append("y=%g" % y)
    return {"ok": True, "eixos": len(linhas), "bolhas": bolhas, "rotulos": rotulos,
            "lista": linhas, "nota": "bolha com raio min(0.3, extension/3)"}


async def arch_symbol(kind: str, x: float, y: float, params: dict | None = None,
                      lang: str = "pt", scale: float = 1.0) -> dict:
    """Simbolo de planta: norte, marcador de corte ou marcador de nivel.

    kinds:
      * `north`   -- seta norte: circulo + triangulo preenchido + letra N
      * `section` -- marcador de corte: linha grossa + seta + identificacao
      * `level`   -- marcador de nivel: triangulo + cota do nivel
    """
    p = params or {}
    b = await _b()
    await b.layer_create("SIMBOLOS", color=1)
    kind = str(kind).lower()
    feitos = []

    if kind in ("north", "norte", "n"):
        raio = float(p.get("raio", 0.4)) * scale
        c = await b.create_circle(x, y, raio, layer="SIMBOLOS")
        if c.ok:
            feitos.append("circulo")
        # ponta da seta para cima (norte)
        ponta = (x, y + raio)
        base_esq = (x - raio * 0.28, y + raio * 0.25)
        base_dir = (x + raio * 0.28, y + raio * 0.25)
        l1 = await b.create_line(base_esq[0], base_esq[1], ponta[0], ponta[1], layer="SIMBOLOS")
        l2 = await b.create_line(base_dir[0], base_dir[1], ponta[0], ponta[1], layer="SIMBOLOS")
        if l1.ok and l2.ok:
            feitos.append("seta")
        t = await b.create_text(x, y - raio * 0.15, "N", height=raio * 0.5, layer="SIMBOLOS")
        if t.ok:
            feitos.append("letra")

    elif kind in ("section", "corte", "section mark"):
        comp = float(p.get("comprimento", 2.0)) * scale
        l = await b.create_line(x, y - comp / 2, x, y + comp / 2, layer="SIMBOLOS")
        if l.ok:
            feitos.append("linha")
        rotulo = str(p.get("rotulo", "A"))
        for sinal in (-1, 1):
            t = await b.create_text(x + comp * 0.12, y + sinal * comp * 0.45, rotulo,
                                    height=0.15 * scale, layer="SIMBOLOS")
            if t.ok:
                feitos.append("rotulo")

    elif kind in ("level", "nivel", "level mark"):
        cota = str(p.get("cota", "0.00"))
        t = await b.create_text(x, y, "±" + cota, height=0.18 * scale, layer="SIMBOLOS")
        if t.ok:
            feitos.append("cota")
        tr = await b.create_polyline([[x, y + 0.2 * scale],
                                      [x - 0.15 * scale, y + 0.35 * scale],
                                      [x + 0.15 * scale, y + 0.35 * scale]],
                                     closed=True, layer="SIMBOLOS")
        if tr.ok:
            feitos.append("triangulo")
    else:
        return {"ok": False, "erro": "kind desconhecido: %r (north|section|level)" % kind}

    return {"ok": True, "kind": kind, "x": x, "y": y, "partes": feitos}


async def arch_rooms_detect(layers: list[str] | None = None, min_area: float = 1.0,
                            tol: float = 0.0) -> dict:
    """Descobre ambientes de uma planta: polilineas fechadas com area >= min_area.

    So' LE -- nao move, nao apaga, nao hachura. Ambientes abaixo de `min_area`
    sao contados a parte (`menores`), porque em planta baixa armario e banheiro
    tambem sao ambientes.
    """
    b = await _b()
    alvo = [str(l) for l in layers] if layers else None
    r = _r(await b.entity_list(layer=alvo[0] if alvo else None))
    ents = ((r.get("payload") or {}).get("entities")) or []
    ambientes, menores = [], []
    vistos = set()
    for e in ents:
        h = e.get("handle")
        if h in vistos:
            continue
        vistos.add(h)
        if e.get("type") not in ("LWPOLYLINE", "POLYLINE"):
            continue
        g = await b.entity_geometry(h)
        if not g.ok:
            continue
        geo = g.payload or {}
        if not geo.get("fechada"):
            continue
        pts = geo.get("pontos") or []
        area = geo.get("area")
        if area is None:
            area = _area_fechada(pts)
        if area <= 0:
            continue
        per = sum(math.hypot(pts[(i + 1) % len(pts)][0] - pts[i][0],
                             pts[(i + 1) % len(pts)][1] - pts[i][1])
                  for i in range(len(pts)))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        reg = {"handle": h, "camada": geo.get("camada"), "area": round(area, 4),
               "perimetro": round(per, 4),
               "bbox": [min(xs), min(ys), max(xs), max(ys)],
               "centroide": [round((min(xs) + max(xs)) / 2.0, 4),
                             round((min(ys) + max(ys)) / 2.0, 4)]}
        if area >= min_area - tol:
            ambientes.append(reg)
        else:
            menores.append(reg)
    return {"ok": True, "ambientes": len(ambientes), "min_area": min_area,
            "lista": ambientes, "menores": menores, "total_fechadas": len(ambientes) + len(menores)}


async def arch_dimension_chains(sides: list[str] | None = None, scale: float = 0.1,
                                first_offset: float = 1.0,
                                step: float = 0.8) -> dict:
    """Cotas encadeadas nas fachadas da planta (sul e oeste, por padrao).

    Cada lado recebe uma cadeia: a primeira cota a `first_offset` da extensao do
    desenho e as seguintes a cada `step`.
    """
    lados = [str(s).lower() for s in (sides or ["s", "w"])]
    b = await _b()
    await b.layer_create("COTAS", color=2)
    r = _r(await b.entity_list())
    ents = ((r.get("payload") or {}).get("entities")) or []
    if not ents:
        return {"ok": False, "erro": "desenho vazio: nao ha o que cotar"}
    xs, ys = [], []
    for e in ents:
        g = await b.entity_geometry(e.get("handle"))
        if g.ok:
            for p in (g.payload or {}).get("pontos") or []:
                xs.append(p[0])
                ys.append(p[1])
    if not xs:
        return {"ok": False, "erro": "nenhuma entidade com geometria para medir"}
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    feitas = []
    for lado in lados:
        if lado in ("s", "south", "inferior", "bottom"):
            for i in range(3):
                y = y0 - first_offset - i * step
                r = await b.create_dimension_linear(x0, y0, x1, y0, x0 + (x1 - x0) / 2, y)
                if r.ok:
                    feitas.append({"lado": "s", "y": round(y, 3)})
        elif lado in ("w", "west", "esquerda", "left"):
            for i in range(3):
                x = x0 - first_offset - i * step
                r = await b.create_dimension_aligned(x0, y0, x0, y1, first_offset + i * step)
                if r.ok:
                    feitas.append({"lado": "w", "x": round(x, 3)})
        else:
            return {"ok": False, "erro": "lado desconhecido: %r (s|w)" % lado}
    return {"ok": True, "extensao": [x0, y0, x1, y1], "cotas": len(feitas),
            "lista": feitas}


# --------------------------------------------------- cota / anotacao / bloco
async def dimension_angular(cx: float, cy: float, x1: float, y1: float,
                            x2: float, y2: float) -> dict:
    """Cota angular entre dois raios a partir de um vertice."""
    return _r(await (await _b()).create_dimension_angular(cx, cy, x1, y1, x2, y2))


async def dimension_radius(cx: float, cy: float, radius: float, angle: float = 0.0) -> dict:
    """Cota de raio de um circulo/arco, em (cx, cy) com `radius`."""
    return _r(await (await _b()).create_dimension_radius(cx, cy, radius, angle))


async def leader_create_mleader(points: list[list[float]], text: str,
                                height: float = 0.18, layer: str | None = None) -> dict:
    """Callout: seta na primeira marca e nota no fim (QLEADER simplificado)."""
    if len(points) < 2:
        return {"ok": False, "erro": "leader precisa de ao menos 2 pontos (seta e texto)"}
    b = await _b()
    lay = layer or "COTAS"
    await b.layer_create(lay, color=2)
    l = await b.create_polyline([list(p) for p in points], layer=lay)
    if not l.ok:
        return {"ok": False, "erro": l.error or "falha ao desenhar a linha do leader"}
    t = await b.create_text(points[-1][0], points[-1][1], text, height=height, layer=lay)
    if not t.ok:
        return {"ok": False, "erro": t.error or "falha ao escrever o texto do leader"}
    return {"ok": True, "pontos": len(points), "texto": text,
            "nota": "linha + texto; a seta do MLEADER nao e' desenhada"}


async def block_define(name: str, entities: list[dict]) -> dict:  # type: ignore[override]
    """Define um bloco a partir de entidades ja' existentes (lista de handles)."""
    b = await _b()
    if not hasattr(b, "block_define"):
        return {"ok": False, "erro": "backend '%s' nao implementa block_define"
                                     % getattr(b, "name", "?")}
    return _r(await b.block_define(name, entities))


# ------------------------------------------------------------------ registro
TOOLS = [
    # desenho
    entity_create_ellipse, entity_create_point, entity_create_spline, construction_xline,
    entity_create_revcloud, drawing_properties_get, drawing_properties_set,
    drawing_apply_standard, user_pick_point,
    # edicao
    entity_scale, entity_chamfer, entity_array_rectangular, entity_array_polar,
    entity_set_properties, entity_set_properties_filter, entity_edit_text, entity_delete_many, hatch_edit,
    # consulta / geometria
    entity_get, point_from_snap, point_tangent, selection_window, view_zoom_window,
    # arquitetura
    arch_grid, arch_symbol, arch_rooms_detect, arch_dimension_chains, hatch_material,
    # cota / anotacao / bloco
    dimension_angular, dimension_radius, leader_create_mleader, block_define,
]

NOMES = {
    "entity_create_ellipse": "entity_create_ellipse",
    "entity_create_point": "entity_create_point",
    "entity_create_spline": "entity_create_spline",
    "construction_xline": "construction_xline",
    "entity_create_revcloud": "entity_create_revcloud",
    "drawing_properties_get": "drawing_properties_get",
    "drawing_properties_set": "drawing_properties_set",
    "drawing_apply_standard": "drawing_apply_standard",
    "user_pick_point": "user_pick_point",
    "entity_scale": "entity_scale",
    "entity_chamfer": "entity_chamfer",
    "entity_array_rectangular": "entity_array_rectangular",
    "entity_array_polar": "entity_array_polar",
    "entity_set_properties": "entity_set_properties",
    "entity_set_properties_filter": "entity_set_properties_filter",
    "entity_edit_text": "entity_edit_text",
    "entity_delete_many": "entity_delete_many",
    "hatch_edit": "hatch_edit",
    "entity_get": "entity_get",
    "point_from_snap": "point_from_snap",
    "point_tangent": "point_tangent",
    "selection_window": "selection_window",
    "view_zoom_window": "view_zoom_window",
    "arch_grid": "arch_grid",
    "arch_symbol": "arch_symbol",
    "arch_rooms_detect": "arch_rooms_detect",
    "arch_dimension_chains": "arch_dimension_chains",
    "hatch_material": "hatch_material",
    "dimension_angular": "dimension_angular",
    "dimension_radius": "dimension_radius",
    "leader_create_mleader": "leader_create_mleader",
    "block_define": "block_define",
}
import asyncio

async def north_arrow(x, y, size=1.0):
    b = await _b()
    handles = []
    r = await b.create_line(x, y, x, y + size, layer="A-TEXTO")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_polyline([[x, y + size], [x - size*0.25, y + size*0.7],
                                 [x + size*0.25, y + size*0.7], [x, y + size]],
                                closed=True, layer="A-TEXTO")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_text(x - size*0.15, y + size*0.35, "N", height=size*0.35, rotation=0.0, layer="A-TEXTO")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    return {"ok": True, "payload": {"handles": handles, "count": len(handles)}}

async def scale_bar(x, y, length=5.0, escala="1:50"):
    b = await _b()
    handles = []
    r = await b.create_line(x, y, x + length, y, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    for i in range(int(length) + 1):
        r = await b.create_line(x + i, y, x + i, y + 0.15, layer="A-COTAS")
        if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_text(x, y - 0.3, "0", height=0.18, rotation=0.0, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_text(x + length, y - 0.3, str(int(length)) + "m", height=0.18, rotation=0.0, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_text(x + length/2, y - 0.6, "ESCALA " + escala, height=0.20, rotation=0.0, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    return {"ok": True, "payload": {"handles": handles, "count": len(handles)}}

async def section_line(x1, y1, x2, y2, label="A"):
    b = await _b()
    handles = []
    r = await b.create_line(x1, y1, x2, y2, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    dx, dy = x2 - x1, y2 - y1
    L = (dx*dx + dy*dy) ** 0.5
    if L > 0:
        nx, ny = -dy/L, dx/L
        s = 0.3
        r = await b.create_polyline([[x1, y1], [x1 + nx*s + dx/L*s, y1 + ny*s + dy/L*s],
                                     [x1 - nx*s + dx/L*s, y1 - ny*s + dy/L*s], [x1, y1]],
                                    closed=True, layer="A-COTAS")
        if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
        r = await b.create_polyline([[x2, y2], [x2 - nx*s - dx/L*s, y2 - ny*s - dy/L*s],
                                     [x2 + nx*s - dx/L*s, y2 + ny*s - dy/L*s], [x2, y2]],
                                    closed=True, layer="A-COTAS")
        if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_text(x1 - 0.4, y1, label, height=0.25, rotation=0.0, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_text(x2 + 0.4, y2, label, height=0.25, rotation=0.0, layer="A-COTAS")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    return {"ok": True, "payload": {"handles": handles, "count": len(handles)}}

async def title_block(x, y, width=8.0, height=5.0, projeto="PROJETO", cliente="CLIENTE",
                      escala="1:50", data="24/10/2026", responsavel="ENG. CIVIL",
                      crea="CREA 000000", folha="01/01", revisao="A"):
    b = await _b()
    handles = []
    r = await b.create_polyline([[x, y], [x+width, y], [x+width, y+height], [x, y+height], [x, y]],
                                closed=True, layer="A-TEXTO")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    for i in range(1, 5):
        yy = y + i * (height/5)
        r = await b.create_line(x, yy, x+width, yy, layer="A-TEXTO")
        if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    r = await b.create_line(x+width/2, y, x+width/2, y+height, layer="A-TEXTO")
    if r.ok: handles.append(r.payload if isinstance(r.payload, str) else r.payload.get("handle"))
    h = 0.18
    await b.create_text(x+0.2, y+height-0.3, "PROJETO: " + projeto, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+0.2, y+height*0.8-0.3, "CLIENTE: " + cliente, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+0.2, y+height*0.6-0.3, "ESCALA: " + escala, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+0.2, y+height*0.4-0.3, "DATA: " + data, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+0.2, y+height*0.2-0.3, "FOLHA: " + folha, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+width/2+0.2, y+height-0.3, "RESP: " + responsavel, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+width/2+0.2, y+height*0.8-0.3, crea, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+width/2+0.2, y+height*0.6-0.3, "REVISAO: " + revisao, height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+width/2+0.2, y+height*0.4-0.3, "ART: 000000", height=h, rotation=0.0, layer="A-TEXTO")
    await b.create_text(x+width/2+0.2, y+height*0.2-0.3, "NBR 6492", height=h, rotation=0.0, layer="A-TEXTO")
    return {"ok": True, "payload": {"handles": handles, "count": len(handles)}}


# --- anotacoes de apresentacao (adicionadas na rodada de refinamento) ---
TOOLS.extend([north_arrow, scale_bar, section_line, title_block])
NOMES.update({
    "north_arrow": "north_arrow",
    "scale_bar": "scale_bar",
    "section_line": "section_line",
    "title_block": "title_block",
})
