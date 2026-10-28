"""Template residencial determinístico para o MCP cloud (ezdxf)."""
from __future__ import annotations

import math
from copy import deepcopy

from mcp_cad_cloud.backend import _ensure, reset_drawing
from mcp_cad_cloud.planta_catalogo import TEMPLATE_PADRAO, listar_templates


ROOMS = (
    "Sala de estar/jantar", "Cozinha", "Área de serviço", "Banheiro social",
    "Circulação", "Quarto 2", "Quarto 3", "Suíte", "Banheiro da suíte",
    "Hall/closet",
)


def _split_wall(wall, openings):
    x1, y1, x2, y2 = wall
    horizontal = abs(y2 - y1) < 1e-9
    lo, hi = (min(x1, x2), max(x1, x2)) if horizontal else (min(y1, y2), max(y1, y2))
    cuts = sorted((max(lo, p), min(hi, p + width)) for p, width in openings)
    out, cursor = [], lo
    for start, end in cuts:
        if end <= cursor or start >= hi:
            continue
        if start > cursor + 0.02:
            out.append([cursor, y1, start, y2] if horizontal else [x1, cursor, x2, start])
        cursor = max(cursor, end)
    if cursor < hi - 0.02:
        out.append([cursor, y1, hi, y2] if horizontal else [x1, cursor, x2, hi])
    return out


def _rooms():
    values = [
        ("Sala de estar/jantar", .075, .075, 4.925, 4.925),
        ("Cozinha", 5.075, .075, 8.525, 4.925),
        ("Área de serviço", 8.675, .075, 11.925, 2.525),
        ("Banheiro social", 8.675, 2.675, 11.925, 4.925),
        ("Circulação", .075, 5.075, 11.925, 6.125),
        ("Quarto 2", 4.675, 6.275, 8.525, 10.925),
        ("Quarto 3", 8.675, 6.275, 11.925, 10.925),
        ("Suíte", .075, 8.675, 4.525, 10.925),
        ("Banheiro da suíte", .075, 6.275, 2.325, 8.525),
        ("Hall/closet", 2.475, 6.275, 4.525, 8.525),
    ]
    out = []
    for name, x1, y1, x2, y2 in values:
        h = min(.22, max(.12, .82 * (x2 - x1) / (.9 * len(name))))
        out.append({"nome": name, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "h": h})
    return out


def build_assisted_model(programa=None):
    programa = deepcopy(programa or {})
    if (float(programa.get("largura_externa", 12.0)) != 12.0 or
            float(programa.get("profundidade_externa", 11.0)) != 11.0):
        raise ValueError("o template exige casa externa de 12,00 x 11,00 m")
    if abs(float(programa.get("espessura_parede", .15)) - .15) > 1e-9:
        raise ValueError("o template exige parede de 0,15 m")
    if float(programa.get("pe_direito", 2.8)) <= 2.4:
        raise ValueError("pé-direito incompatível")

    specs = [
        ((0, 0, 12, 0), [(.5, .9), (2.2, 2.0), (5.9, 1.4), (9.4, 1.2)]),
        ((0, 11, 12, 11), [(1.0, 1.2), (5.5, 2.0), (9.4, 1.5)]),
        ((0, 0, 0, 11), [(2.0, 1.4), (6.9, .8)]),
        ((12, 0, 12, 11), [(3.2, 1.0), (7.5, 2.0)]),
        ((0, 5, 12, 5), [(2.2, .9), (6.4, .9), (10.2, .7)]),
        ((0, 6.2, 12, 6.2), [(3.2, .9), (5.6, .9), (9.6, .9)]),
        ((8.6, 2.6, 12, 2.6), []), ((0, 8.6, 4.6, 8.6), [(3.2, .9)]),
        ((5, 0, 5, 5), [(2, .9)]), ((8.6, 0, 8.6, 5), [(.9, .9)]),
        ((8.6, 6.2, 8.6, 11), []), ((4.6, 6.2, 4.6, 11), []),
        ((2.4, 6.2, 2.4, 8.6), [(6.6, .9)]),
    ]
    walls = [seg for wall, openings in specs for seg in (_split_wall(wall, openings) if openings else [list(wall)])]
    return {
        "titulo": programa.get("titulo", "PLANTA ASSISTIDA - RESIDÊNCIA UNIFAMILIAR"),
        "espessura_parede": .15, "pe_direito": float(programa.get("pe_direito", 2.8)),
        "terreno": (-1.5, -5.0, 13.5, 16.0), "paredes": walls,
        "parede_sem_sobreposicao": True, "ambientes": _rooms(),
        "portas": [(0.5, 0, 90, .9), (2.2, 5, 270, .9), (6.4, 5, 270, .9),
                   (10.2, 5, 270, .7), (3.2, 6.2, 90, .9), (5.6, 6.2, 90, .9),
                   (9.6, 6.2, 90, .9), (3.2, 8.6, 90, .9), (5, 2, 0, .9),
                   (8.6, .9, 0, .9), (2.4, 6.6, 180, .9)],
        "janelas": [(2.2, 0, 4.2, 0), (5.9, 0, 7.3, 0), (9.4, 0, 10.6, 0),
                    (12, 3.2, 12, 4.2), (12, 7.5, 12, 9.5), (1, 11, 2.2, 11),
                    (5.5, 11, 7.5, 11), (9.4, 11, 10.9, 11), (0, 2, 0, 3.4),
                    (0, 6.9, 0, 7.7)],
        "moveis": [(1.5, 1.3, 3.9, 2.1), (3.4, 3.4, 4.7, 4.6),
                   (5.15, .15, 8.45, .75), (7.9, 4, 8.45, 4.85),
                   (8.8, 1.85, 9.7, 2.45), (10, 1.85, 10.9, 2.45),
                   (8.8, 2.8, 9.4, 3.5), (11.2, 2.8, 11.8, 3.3),
                   (5.6, 9.3, 7.2, 10.85), (4.9, 10, 5.4, 10.5),
                   (7.95, 6.4, 8.45, 8), (9.1, 9.3, 10.8, 10.85),
                   (10.8, 6.5, 11.8, 7.2), (11.3, 8.3, 11.85, 10.6),
                   (.25, 8.8, 1.75, 10.6), (.2, 6.35, 1.1, 7),
                   (.3, 7.9, .9, 8.45), (1.3, 7.9, 2.1, 8.45)],
        "cotas_h": [(0, 5, -1, -1), (5, 8.6, -1, -1), (8.6, 12, -1, -1),
                    (0, 12, -2, -2), (0, 4.6, 12, 12), (4.6, 8.6, 12, 12),
                    (8.6, 12, 12, 12), (0, 12, 13, 13)],
        "cotas_v": [(12.8, 0, 6, 12.8), (12.8, 6, 11, 12.8), (13.8, 0, 11, 13.8)],
        "selo": [(-1.4, -5.45, "PLANTA BAIXA - RESIDÊNCIA UNIFAMILIAR", .16),
                 (-1.4, -5.7, "Área útil: 120,67 m²", .16),
                 (-1.4, -5.95, "Área construída: 132,00 m²", .16),
                 (-1.4, -6.2, "Terreno: 15,00 x 21,00 m", .16),
                 (-1.4, -6.45, "Recuos assumidos: frente/fundos 5,00 m; laterais 1,50 m", .16),
                 (-1.4, -6.7, "Pé-direito: 2,80 m | Cotas em metros", .16)],
        "area_pedida": float(programa.get("area_util_minima", 120.67)),
    }


def wall_boundary_segments(walls, t=.15):
    """Contorno VISÍVEL da união das paredes, sem faces internas sobrepostas.

    Cada trecho axial origina um retângulo de espessura `t`. Em ligações
    perpendiculares, o eixo é prolongado por meia espessura somente na ponta
    conectada, para fechar os cantos sem fechar vãos de portas e janelas.
    Uma malha ortogonal limitada extrai apenas faces que separam parede de
    vazio. Segmentos colineares vizinhos são fundidos no resultado.
    As unidades são metros; o resultado contém LINEs 2D.
    """
    if not math.isfinite(float(t)) or t <= 0:
        raise ValueError("espessura da parede deve ser positiva e finita")
    half = t / 2.0
    axes = []
    for index, p in enumerate(walls, 1):
        if len(p) != 4:
            raise ValueError(f"parede {index}: são necessárias quatro coordenadas")
        x1, y1, x2, y2 = (float(v) for v in p)
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            raise ValueError(f"parede {index}: coordenadas inválidas")
        if abs(y1 - y2) < 1e-8 and abs(x1 - x2) > 1e-8:
            axes.append(("h", y1, min(x1, x2), max(x1, x2)))
        elif abs(x1 - x2) < 1e-8 and abs(y1 - y2) > 1e-8:
            axes.append(("v", x1, min(y1, y2), max(y1, y2)))
        else:
            raise ValueError(f"parede {index}: segmento inválido (usar eixos ortogonais)")

    if not axes:
        return []

    def conectado(kind, coordinate, endpoint):
        for other_kind, other_coord, lo, hi in axes:
            if other_kind != kind and abs(other_coord - endpoint) <= 1e-7:
                if lo - 1e-7 <= coordinate <= hi + 1e-7:
                    return True
        return False

    # União espacial dos retângulos efetivos, com cantos alinhados.
    rectangles = []
    for kind, coordinate, lo, hi in axes:
        if kind == "h":
            a = lo - (half if conectado(kind, coordinate, lo) else 0)
            b = hi + (half if conectado(kind, coordinate, hi) else 0)
            rectangles.append((a, coordinate - half, b, coordinate + half))
        else:
            a = lo - (half if conectado(kind, coordinate, lo) else 0)
            b = hi + (half if conectado(kind, coordinate, hi) else 0)
            rectangles.append((coordinate - half, a, coordinate + half, b))

    # Remover ruído de ponto flutuante: paredes que coincidem compartilham
    # as mesmas coordenadas de grade (precisão 10 nm no DXF em metros).
    rectangles = [tuple(round(v, 8) for v in r) for r in rectangles]
    xs = sorted({v for x1, _, x2, _ in rectangles for v in (x1, x2)})
    ys = sorted({v for _, y1, _, y2 in rectangles for v in (y1, y2)})
    nx, ny = len(xs) - 1, len(ys) - 1
    if nx * ny > 200_000:
        raise ValueError("planta excede limite de complexidade da malha de paredes")
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    inside = [[False] * nx for _ in range(ny)]
    for x1, y1, x2, y2 in rectangles:
        left, right, bottom, top = xi[x1], xi[x2], yi[y1], yi[y2]
        for j in range(bottom, top):
            row = inside[j]
            for i in range(left, right):
                row[i] = True

    horizontal, vertical = {}, {}
    for j in range(ny):
        for i in range(nx):
            if not inside[j][i]:
                continue
            if j == 0 or not inside[j - 1][i]:
                horizontal.setdefault(j, []).append(i)
            if j == ny - 1 or not inside[j + 1][i]:
                horizontal.setdefault(j + 1, []).append(i)
            if i == 0 or not inside[j][i - 1]:
                vertical.setdefault(i, []).append(j)
            if i == nx - 1 or not inside[j][i + 1]:
                vertical.setdefault(i + 1, []).append(j)

    def runs(indices):
        """Consolida células contíguas para não criar LINEs duplicadas."""
        values = sorted(set(indices))
        if not values:
            return
        lo, hi = values[0], values[0] + 1
        for value in values[1:]:
            if value == hi:
                hi += 1
            else:
                yield lo, hi
                lo, hi = value, value + 1
        yield lo, hi

    output = []
    for j, values in sorted(horizontal.items()):
        for lo, hi in runs(values):
            output.append((xs[lo], ys[j], xs[hi], ys[j]))
    for i, values in sorted(vertical.items()):
        for lo, hi in runs(values):
            output.append((xs[i], ys[lo], xs[i], ys[hi]))
    return output

def _summary(model):
    areas = {a["nome"]: round((a["x2"]-a["x1"])*(a["y2"]-a["y1"]), 4) for a in model["ambientes"]}
    return {"titulo": model["titulo"], "ambientes": len(model["ambientes"]),
            "paredes": len(model["paredes"]), "portas": len(model["portas"]),
            "janelas": len(model["janelas"]), "areas": areas,
            "area_util": round(sum(areas.values()), 4), "espessura_parede": .15,
            "pe_direito": model["pe_direito"], "unidades": "metros"}


def _ensure_layers(doc):
    for name, color in (("TERRENO", 6), ("PAREDES", 7), ("PORTAS", 3), ("JANELAS", 5),
                        ("MOBILIARIO", 2), ("COTAS", 1), ("COTAS_INT", 8), ("TEXTOS", 7)):
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": color})


def planta_assistida(programa=None, modo="preview", nome=None, preview_token=None):
    programa = programa or {}
    if not isinstance(programa, dict):
        return {"ok": False, "code": "PROGRAMA_INVALIDO", "error": "programa deve ser JSON"}
    solicitado = str(programa.get("template") or
                    ("programa_sob_medida" if "ambientes" in programa else TEMPLATE_PADRAO)).strip()
    if solicitado not in {TEMPLATE_PADRAO, "tiny_house_10m2", "programa_sob_medida"}:
        return {"ok": False, "code": "TEMPLATE_NOT_SUPPORTED",
                "error": f"template '{solicitado}' ainda nao esta disponivel",
                "templates": listar_templates(),
                "proxima_acao": "escolher um template suportado"}
    if solicitado == "programa_sob_medida":
        from mcp_cad_cloud.planta_gerador import gerar_modelo, ErroPrograma
        try:
            model = gerar_modelo(programa)
        except ErroPrograma as exc:
            return {"ok": False, "code": "PROGRAMA_INVALIDO", "error": str(exc),
                    "proxima_acao": "revisar programa, áreas e dimensões"}
    else:
        largura_padrao = 12.0 if solicitado == TEMPLATE_PADRAO else 2.5
        profundidade_padrao = 11.0 if solicitado == TEMPLATE_PADRAO else 4.0
        if (("largura_externa" in programa and float(programa["largura_externa"]) != largura_padrao) or
                ("profundidade_externa" in programa and float(programa["profundidade_externa"]) != profundidade_padrao)):
            return {"ok": False, "code": "TEMPLATE_NOT_SUPPORTED",
                    "error": "as dimensoes pedidas nao pertencem a um template disponivel",
                    "templates": listar_templates(),
                    "proxima_acao": "escolher um template suportado"}
        if solicitado == "tiny_house_10m2":
            from mcp_cad_cloud.tiny_house_assistida import build_tiny_house_model
            model = build_tiny_house_model(programa)
        else:
            model = build_assisted_model(programa)
    from mcp_cad_cloud.validar_modelo import validar
    from mcp_cad_cloud.plant_workflow import consume, issue
    validacao = validar(model)
    if validacao.get("erros"):
        return {"ok": False, "code": "INVALID_LAYOUT",
                "error": "o template foi rejeitado pela validação geométrica",
                "validacao": validacao}
    summary = _summary(model)
    if modo == "preview":
        return {"ok": True, "etapa": "preview", "backend": "ezdxf", "resumo": summary,
                "validacao": validacao, "modelo": model,
                "avisos": model.get("avisos", []),
                "resumo_geometria": model.get("resumo_geometria"),
                "preview_token": issue(model, solicitado),
                "proxima_acao": "desenhar"}
    if modo != "desenhar":
        return {"ok": False, "code": "INVALID_MODE", "error": "modo deve ser preview ou desenhar"}
    if not consume(preview_token, model, solicitado):
        return {"ok": False,
                "code": "WORKFLOW_REQUIRED" if not preview_token else "PREVIEW_TOKEN_INVALID",
                "error": "o desenho exige um preview aprovado para exatamente este modelo",
                "proxima_acao": "chamar planta_criar_validada(modo='preview')"}

    reset_drawing()
    doc = _ensure(); _ensure_layers(doc); msp = doc.modelspace()
    if nome: global DRAWING_NAME; DRAWING_NAME = str(nome)
    for x1, y1, x2, y2 in wall_boundary_segments(model["paredes"]):
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "PAREDES"})
    x1, y1, x2, y2 = model["terreno"]
    msp.add_lwpolyline([(x1,y1),(x2,y1),(x2,y2),(x1,y2)], close=True, dxfattribs={"layer":"TERRENO"})
    folhas = model.get("portas_folhas", [])
    for i, (px, py, ang, width) in enumerate(model["portas"]):
        msp.add_arc((px, py), width, ang, ang + 90, dxfattribs={"layer":"PORTAS"})
        # O desenho compacto informa a direção da folha aberta, separadamente
        # do início do arco. Os templates antigos mantêm seu contrato original.
        ang_folha = folhas[i] if i < len(folhas) else ang
        r = math.radians(ang_folha)
        msp.add_line((px,py),(px+width*math.cos(r),py+width*math.sin(r)),
                     dxfattribs={"layer":"PORTAS"})
    half = .15 / 2
    for a, b, c, d in model["janelas"]:
        if abs(d-b) < 1e-9:
            msp.add_line((a,b-half/2),(c,d-half/2), dxfattribs={"layer":"JANELAS"})
            msp.add_line((a,b+half/2),(c,d+half/2), dxfattribs={"layer":"JANELAS"})
        else:
            msp.add_line((a-half/2,b),(c-half/2,d), dxfattribs={"layer":"JANELAS"})
            msp.add_line((a+half/2,b),(c+half/2,d), dxfattribs={"layer":"JANELAS"})
    for x1, y1, x2, y2 in model["moveis"]:
        msp.add_lwpolyline([(x1,y1),(x2,y1),(x2,y2),(x1,y2)], close=True, dxfattribs={"layer":"MOBILIARIO"})
    # Texto técnico centrado nos ambientes; quebra rótulos extensos para
    # evitar a invasão de paredes em cômodos estreitos.
    from ezdxf.enums import TextEntityAlignment
    for amb in model["ambientes"]:
        cx, cy = (amb["x1"]+amb["x2"])/2, (amb["y1"]+amb["y2"])/2
        cx, cy = float(amb.get("texto_x", cx)), float(amb.get("texto_y", cy))
        largura = amb["x2"] - amb["x1"]
        nome = amb["nome"]
        tamanho = max(0.10, min(0.20, float(amb["h"])))
        max_chars = max(4, int((largura - 0.18) / (tamanho * 0.85)))
        palavras = nome.split()
        linhas, atual = [], ""
        for palavra in palavras:
            tentativa = (atual + " " + palavra).strip()
            if atual and len(tentativa) > max_chars:
                linhas.append(atual)
                atual = palavra
            else:
                atual = tentativa
        if atual:
            linhas.append(atual)
        if not linhas:
            linhas = [nome]
        comprimento_maior = max(len(linha) for linha in linhas)
        if comprimento_maior * tamanho * 0.85 > largura - 0.16:
            tamanho = max(0.05, (largura - 0.16) / max(1, comprimento_maior) / 0.85)
        espacamento = tamanho * 1.40
        for i, linha in enumerate(linhas):
            y_texto = cy + (len(linhas) - 1 - 2*i) * espacamento / 2
            entidade = msp.add_text(linha, dxfattribs={"height":tamanho,"layer":"TEXTOS"})
            entidade.set_placement((cx,y_texto), align=TextEntityAlignment.MIDDLE_CENTER)

    # EZDXF possui DIMLFAC=100 por padrão, gerando '900' para 9 metros.
    # Esta planta é desenhada em metros (INSUNITS=6); escrever 9,00 m.
    dim_override = {"dimlfac":1.0, "dimdec":2, "dimzin":0,
                    "dimpost":"<> m", "dimtxt":0.18, "dimasz":0.12,
                    "dimexe":0.10, "dimexo":0.08}
    if model.get("cotas_h_2d") and model.get("cotas_v_2d"):
        # Cotas associadas aos limites geométricos: parciais e totais.
        # Eixos em metros. A própria entidade DIMENSION calcula o valor.
        partial_style = dict(dim_override, dimtxt=0.14, dimasz=0.10,
                             dimexe=0.07, dimexo=0.06)
        for c in model["cotas_h_2d"]:
            style = partial_style if c["nivel"] == "parcial" else dim_override
            dim = msp.add_aligned_dim(
                p1=(c["x1"], c["y_ref"]), p2=(c["x2"], c["y_ref"]),
                distance=c["y_dim"]-c["y_ref"], override=style,
                dxfattribs={"layer":"COTAS"})
            dim.render()
        for c in model["cotas_v_2d"]:
            style = partial_style if c["nivel"] == "parcial" else dim_override
            dim = msp.add_aligned_dim(
                p1=(c["x_ref"], c["y1"]), p2=(c["x_ref"], c["y2"]),
                distance=c["x_ref"]-c["x_dim"], override=style,
                dxfattribs={"layer":"COTAS"})
            dim.render()
        # Anotação legível das larguras e profundidades úteis de cada
        # ambiente, também calculadas do mesmo objeto geométrico.
        for c in model.get("cotas_ambientes", []):
            texto = f'{c["largura"]:.2f} x {c["profundidade"]:.2f} m'
            entidade = msp.add_text(
                texto, dxfattribs={"height":0.115, "layer":"COTAS_INT"})
            entidade.set_placement(
                (c["x"], c["y"]-0.33),
                align=TextEntityAlignment.MIDDLE_CENTER)
    else:
        # Preserva contratos e cotas dos templates clássicos.
        for x1, x2, y, distance in model["cotas_h"]:
            dim = msp.add_aligned_dim((x1,0),(x2,0),distance=distance,
                                      override=dim_override,dxfattribs={"layer":"COTAS"}); dim.render()
        for x, y1, y2, distance in model["cotas_v"]:
            dim = msp.add_aligned_dim((x,y1),(x,y2),distance=distance,
                                      override=dim_override,dxfattribs={"layer":"COTAS"}); dim.render()
    for x, y, text, height in model["selo"]:
        msp.add_text(text, dxfattribs={"height":height,"insert":(x,y),"layer":"TEXTOS"})
    return {"ok": True, "etapa": "desenho", "backend": "ezdxf", "resumo": summary,
            "validacao": validacao, "entities": len(msp), "drawing": DRAWING_NAME}


DRAWING_NAME = "planta_sem_nome"
