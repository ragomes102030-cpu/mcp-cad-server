"""Independent geometric engineering quantities from actual DXF entities.

Never estimate construction costs or silently infer wall heights/thicknesses,
opening ownership, finishes or room names. Dimensions are metric modelspace
measurements; drawing sheet graphics and duplicated wall faces are NOT wall axes.

Supported explicit measurement layers:
  EIXOS-PAREDES  LINE           one axis per measurable wall
  VAOS-PORTAS    LINE           one measured door opening per line
  VAOS-JANELAS   LINE           one measured window opening per line
  PISOS          closed LWPOLYLINE, straight edges, one polygon per floor area

Existing layer PAREDES contains wall faces and is intentionally not summed.
"""
from __future__ import annotations

from collections import Counter
from math import hypot, isfinite
from typing import Any

VERSION = "geom-dxf-1.0.0"
TOL = 1e-7
MAX_MEASURABLE_ENTITIES = 15000
_LAYERS = ("EIXOS-PAREDES", "VAOS-PORTAS", "VAOS-JANELAS", "PISOS")


def _point(v):
    x, y = float(v[0]), float(v[1])
    if not (isfinite(x) and isfinite(y)):
        raise ValueError("coordenada não finita no DXF")
    return (x, y)


def _length(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def _polygon_area(points):
    return abs(sum(
        a[0]*b[1] - b[0]*a[1]
        for a, b in zip(points, points[1:]+points[:1])
    )) / 2


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _proper_intersect(a, b, c, d):
    return (_cross(a, b, c) * _cross(a, b, d) < -TOL
            and _cross(c, d, a) * _cross(c, d, b) < -TOL)


def _on_segment(p, a, b, tol=TOL):
    return (abs(_cross(a, b, p)) <= tol * max(1.0, _length(a, b))
            and min(a[0], b[0])-tol <= p[0] <= max(a[0], b[0])+tol
            and min(a[1], b[1])-tol <= p[1] <= max(a[1], b[1])+tol)


def _collinear_overlap(a, b, c, d):
    if (abs(_cross(a, b, c)) > TOL*max(1, _length(a,b))
            or abs(_cross(a, b, d)) > TOL*max(1, _length(a,b))):
        return False
    axis = 0 if abs(b[0]-a[0]) >= abs(b[1]-a[1]) else 1
    return (min(max(a[axis],b[axis]),max(c[axis],d[axis])) -
            max(min(a[axis],b[axis]),min(c[axis],d[axis]))) > TOL


def _simple_polygon(points):
    n = len(points)
    if n < 3 or len(set((round(x,7),round(y,7)) for x,y in points)) != n:
        return False
    edges = list(zip(points, points[1:]+points[:1]))
    if any(_length(a,b) <= TOL for a,b in edges):
        return False
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges):
            if j <= i or (j-i) in (1,n-1):
                continue
            if (_proper_intersect(a,b,c,d) or
                    _on_segment(a,c,d) or _on_segment(b,c,d) or
                    _on_segment(c,a,b) or _on_segment(d,a,b)):
                return False
    return _polygon_area(points) > TOL


def _positive_optional(name, value):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError(f"{name}: valor numérico inválido") from exc
    if not isfinite(v) or v <= 0:
        raise ValueError(f"{name}: deve ser positivo e finito")
    return v


def _item(project_id, kind, handle, description, value, unit,
          metrics, missing=(), origin="", criterion=""):
    missing = list(missing)
    return {
        "id_elemento": f"{kind}:{handle}",
        "id_projeto": project_id,
        "tipo": kind,
        "descricao": description,
        "quantidade": round(value,6),
        "unidade": unit,
        "metricas": metrics,
        "origem_geometrica": origin,
        "premissas": [],
        "criterio_medicao": criterion,
        "completude": "COMPLETO_GEOMETRICAMENTE" if not missing else "DADOS_INSUFICIENTES",
        "campos_ausentes": missing,
        "avisos": [] if not missing else [f"Preencher: {', '.join(missing)}"],
        "versao_calculo": VERSION,
    }


def extrair_quantitativos_dxf(
    doc,
    *,
    projeto_id: str | None = None,
    altura_paredes_m: float | None = None,
    espessura_paredes_m: float | None = None,
    altura_portas_m: float | None = None,
    altura_janelas_m: float | None = None,
    aberturas_por_parede: dict[str, list[str]] | None = None,
    inventario_aberturas_completo: bool = False,
) -> dict[str, Any]:
    """Measure the DXF only, never the generator's advertised area or walls."""
    if projeto_id is not None and (
            not isinstance(projeto_id,str) or not 1 <= len(projeto_id) <= 80
            or not all(c.isascii() and (c.isalnum() or c in "-_") for c in projeto_id)):
        raise ValueError("projeto_id inválido (até 80 caracteres ASCII alfanuméricos, '-' ou '_')")
    if not isinstance(inventario_aberturas_completo,bool):
        raise ValueError("inventario_aberturas_completo deve ser booleano")
    h_wall = _positive_optional("altura_paredes_m",altura_paredes_m)
    t_wall = _positive_optional("espessura_paredes_m",espessura_paredes_m)
    h_door = _positive_optional("altura_portas_m",altura_portas_m)
    h_window = _positive_optional("altura_janelas_m",altura_janelas_m)
    if aberturas_por_parede is not None and not isinstance(aberturas_por_parede,dict):
        raise ValueError("aberturas_por_parede deve mapear handle de parede para lista de handles de aberturas")
    associations = aberturas_por_parede or {}
    if not isinstance(associations,dict) or any(
            not isinstance(k,str) or not isinstance(v,list) or
            any(not isinstance(item,str) for item in v)
            for k,v in associations.items()):
        raise ValueError("aberturas_por_parede inválido")
    entities = list(doc.modelspace())
    if len(entities) > MAX_MEASURABLE_ENTITIES:
        return {"ok":False,"status":"LIMITE_EXCEDIDO","code":"ENTITY_LIMIT",
                "max_entities":MAX_MEASURABLE_ENTITIES}
    if doc.header.get("$INSUNITS") != 6:
        return {"ok":False,"status":"INVALIDO",
                "erros":[{"codigo":"UNIDADES_INVALIDAS","detalhe":"DXF deve usar metros ($INSUNITS=6)"}],
                "itens":[]}
    errors = []
    pendencies = []
    items = []
    lines = {}
    polys = []
    for entity in entities:
        layer=entity.dxf.layer
        if layer not in _LAYERS:
            continue
        typ=entity.dxftype()
        handle=entity.dxf.handle
        if layer == "PISOS" and typ == "LWPOLYLINE":
            polys.append(entity)
            continue
        if layer in _LAYERS[:3] and typ == "LINE":
            try:
                a,b=_point(entity.dxf.start),_point(entity.dxf.end)
                if _length(a,b) <= TOL:
                    raise ValueError("segmento degenerado")
                lines[handle]=(layer,a,b)
            except (ValueError, OverflowError) as exc:
                errors.append({"codigo":"ENTIDADE_INVALIDA","elemento":handle,
                               "detalhe":str(exc)})
            continue
        errors.append({"codigo":"LAYER_ENTIDADE_INCOMPATIVEL",
                       "elemento":handle,"layer":layer,"tipo":typ})
    # These checks are independent of the residential model and generator.
    for handle,(layer,a,b) in lines.items():
        for other,(layer_b,c,d) in lines.items():
            if other <= handle or layer_b != layer:
                continue
            if _collinear_overlap(a,b,c,d):
                errors.append({"codigo":"SEGMENTOS_SOBREPOSTOS",
                               "elementos":[handle,other],"layer":layer})
    by_layer={layer:[(h,a,b) for h,(lay,a,b) in lines.items() if lay==layer]
              for layer in _LAYERS[:3]}
    doors=by_layer["VAOS-PORTAS"]
    windows=by_layer["VAOS-JANELAS"]
    walls=by_layer["EIXOS-PAREDES"]
    open_by_id={h:(layer,a,b) for h,(layer,a,b) in lines.items()
                if layer in ("VAOS-PORTAS","VAOS-JANELAS")}

    assigned={}
    for wall_id, opening_ids in associations.items():
        if wall_id not in dict((h,None) for h,_,_ in walls):
            errors.append({"codigo":"PAREDE_REFERENCIADA_INEXISTENTE","elemento":wall_id})
            continue
        wall_a,wall_b=lines[wall_id][1:]
        for opening_id in opening_ids:
            if opening_id not in open_by_id:
                errors.append({"codigo":"ABERTURA_REFERENCIADA_INEXISTENTE",
                               "elemento":opening_id})
                continue
            if opening_id in assigned:
                errors.append({"codigo":"ABERTURA_DUPLAMENTE_ASSOCIADA",
                               "elemento":opening_id})
            assigned[opening_id]=wall_id
            _,oa,ob=open_by_id[opening_id]
            if not (_on_segment(oa,wall_a,wall_b) and
                    _on_segment(ob,wall_a,wall_b)):
                errors.append({"codigo":"ABERTURA_FORA_EIXO_PAREDE",
                               "elementos":[wall_id,opening_id]})
    if inventario_aberturas_completo:
        unassigned=set(open_by_id)-set(assigned)
        if unassigned:
            errors.append({"codigo":"ABERTURAS_SEM_PAREDE",
                           "elementos":sorted(unassigned)})

    for handle,a,b in walls:
        length=_length(a,b)
        gross=length*h_wall if h_wall is not None else None
        opening_area=0.0
        count=0
        possible_net=(inventario_aberturas_completo and
                      gross is not None and not errors)
        used_openings=[]
        for op_id in associations.get(handle,[]):
            record=open_by_id.get(op_id)
            if record is None:
                possible_net=False
                continue
            layer,oa,ob=record
            opheight=h_door if layer=="VAOS-PORTAS" else h_window
            used_openings.append((oa,ob))
            if opheight is None:
                possible_net=False
            else:
                opening_area+=_length(oa,ob)*opheight
                count+=1
        for i,(oa,ob) in enumerate(used_openings):
            if any(_collinear_overlap(oa,ob,ca,cb) for ca,cb in used_openings[i+1:]):
                errors.append({"codigo":"ABERTURAS_SOBREPOSTAS","elemento":handle})
                possible_net=False
        if gross is not None and opening_area > gross + TOL:
            errors.append({"codigo":"DESCONTO_SUPERA_AREA_BRUTA","elemento":handle})
            possible_net=False
        net=round(gross-opening_area,6) if possible_net else None
        volume=round(net*t_wall,6) if net is not None and t_wall is not None else None
        missing=[]
        if h_wall is None:missing.append("altura_paredes_m")
        if t_wall is None:missing.append("espessura_paredes_m")
        if not inventario_aberturas_completo:missing.append("inventario_aberturas_completo")
        if (any(open_by_id.get(o,("VAOS-PORTAS",))[0]=="VAOS-PORTAS"
                for o in associations.get(handle,[])) and h_door is None):
            missing.append("altura_portas_m")
        if (any(open_by_id.get(o,("VAOS-JANELAS",))[0]=="VAOS-JANELAS"
                for o in associations.get(handle,[])) and h_window is None):
            missing.append("altura_janelas_m")
        item=_item(projeto_id,"parede",handle,"Eixo de parede",
                   length,"m",{
                       "comprimento_m":round(length,6),
                       "espessura_m":t_wall,"altura_m":h_wall,
                       "area_bruta_m2":round(gross,6) if gross is not None else None,
                       "area_aberturas_m2":round(opening_area,6) if possible_net else None,
                       "area_liquida_m2":net,
                       "volume_geometrico_m3":volume,
                       "aberturas_associadas":associations.get(handle,[]),
                   },missing,origin=f"DXF LINE handle={handle} layer=EIXOS-PAREDES",
                   criterion="comprimento do eixo sem desconto; faces não somadas; descontos só com inventário completo")
        items.append(item)
    for layer,kind,height in (("VAOS-PORTAS","porta",h_door),
                              ("VAOS-JANELAS","janela",h_window)):
        for handle,a,b in by_layer[layer]:
            length=_length(a,b)
            missing=["altura_"+("portas" if kind=="porta" else "janelas")+"_m"] if height is None else []
            if handle not in assigned:missing.append("parede_associada")
            item=_item(projeto_id,kind,handle,
                       "Abertura geométrica de "+kind,1,"un",{
                           "largura_m":round(length,6),
                           "altura_m":height,
                           "area_abertura_m2":round(length*height,6) if height is not None else None,
                           "parede_associada":assigned.get(handle),
                           "ambiente_associado":None,
                       },missing+["ambiente_associado"],
                       origin=f"DXF LINE handle={handle} layer={layer}",
                       criterion="vão representado por segmento; área largura × altura explícita")
            items.append(item)
    for poly in polys:
        handle=poly.dxf.handle
        if not poly.closed:
            errors.append({"codigo":"PISO_ABERTO","elemento":handle})
            continue
        try:
            vertices=list(poly.get_points("xyb"))
            if any(abs(float(v[2]))>TOL for v in vertices):
                raise ValueError("arcos/bulges não suportados no piso piloto")
            points=[_point(v) for v in vertices]
            if not _simple_polygon(points):
                raise ValueError("polígono aberto, degenerado ou autointersectante")
            area=_polygon_area(points)
            perim=sum(_length(a,b) for a,b in zip(points,points[1:]+points[:1]))
            items.append(_item(
                projeto_id,"piso",handle,"Área de piso geométrica",area,"m²",
                {"area_m2":round(area,6),"perimetro_m":round(perim,6),
                 "ambiente_associado":None},
                ["ambiente_associado"],
                origin=f"DXF LWPOLYLINE handle={handle} layer=PISOS",
                criterion="fórmula de Gauss (shoelace) e perímetro de polígono fechado em metros"
            ))
        except (ValueError,OverflowError) as exc:
            errors.append({"codigo":"PISO_CONTORNO_INVALIDO",
                           "elemento":handle,"detalhe":str(exc)})
    if not walls:
        pendencies.append("Sem eixos na camada EIXOS-PAREDES: faces PAREDES não são metragem linear de paredes.")
    if not doors and not windows:
        pendencies.append("Sem aberturas medidas em VAOS-PORTAS ou VAOS-JANELAS.")
    if not polys:
        pendencies.append("Sem polígonos de pisos fechados na camada PISOS.")
    if h_wall is None:
        pendencies.append("Altura de paredes ausente; não calcular áreas ou volumes de paredes.")
    if t_wall is None:
        pendencies.append("Espessura de paredes ausente; não calcular volume.")
    if not inventario_aberturas_completo:
        pendencies.append("Inventário de aberturas não confirmado; não descontar área líquida de paredes.")
    pendencies.append("Revestimentos não medidos: faltam superfícies/critério de desconto e materiais explicitamente associados.")
    if errors:
        status="INVALIDO"
    elif not items:
        status="DADOS_INSUFICIENTES"
    elif pendencies or any(x["completude"]=="DADOS_INSUFICIENTES" for x in items):
        status="PARCIAL"
    else:
        status="VALIDADO_GEOMETRICAMENTE"
    return {
        "ok":not errors,"status":status,"projeto_id":projeto_id,
        "unidade_base":"m","versao_calculo":VERSION,
        "itens":items,"pendencias":pendencies,"erros":errors,
        "resumo":{
            "itens":len(items),"paredes":len(walls),
            "portas":len(doors),"janelas":len(windows),"pisos":len(polys),
            "comprimento_paredes_m":round(sum(_length(a,b) for _,a,b in walls),6),
            "area_pisos_m2":round(sum(item["quantidade"] for item in items
                                      if item["tipo"]=="piso"),6),
        },
        "integracao":{
            "precos":None,"custos":None,"bdi":None,
            "destino_sugerido":"MCP Custos ou agente orquestrador",
            "dependencia_obrigatoria":False,
        },
        "limitacoes":[
            "Auditoria geométrica piloto não certifica aprovação NBR ou projeto executivo.",
            "Cotas de folhas e paredes de faces duplas não são eixos construtivos medíveis.",
            "Sem especificação de revestimento não se calcula acabamento nem preço.",
        ],
    }
