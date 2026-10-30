"""Read-only, DXF-only wall alignment and opening reconciliation.

Pilot: orthogonal 2D, metre units, one solid wall axis LINE per stretch.
The continuous span is reconstructed from *actual* DXF LINE endpoints.
Door ARC centers/radii and the PAIR of glazing LINEs are checked against
each gap; no invented opening specifications or pricing.
"""
from __future__ import annotations

from collections import defaultdict
from math import hypot, isfinite

VERSION = "topologia-dxf-1.0.0"
TOL = 0.002
MAX_DXF_ENTITIES = 15000
MAX_RECONSTRUCTIBLE_GAP_M = 1.60


def _positive_or_none(name, v):
    if v is None:
        return None
    try:
        number=float(v)
    except (ValueError, TypeError, OverflowError) as err:
        raise ValueError(f"{name} deve ser número positivo em metros") from err
    if not isfinite(number) or number<=0:
        raise ValueError(f"{name} deve ser positivo e finito")
    return number


def _close(a,b):
    return abs(a-b)<=TOL


def _entry(handle, a,b):
    return (float(a),float(b),handle)


def _window_lines_at_gap(windows, axis, coord, lo, hi):
    """Find real LINE glazing with same endpoints, symmetric about wall axis."""
    found=[]
    for e in windows:
        a,b=e.dxf.start,e.dxf.end
        if axis=="h":
            if not _close(a.y,b.y):
                continue
            o=(float(a.y)+float(b.y))/2-coord
            endpoints=sorted((float(a.x),float(b.x)))
        else:
            if not _close(a.x,b.x):
                continue
            o=(float(a.x)+float(b.x))/2-coord
            endpoints=sorted((float(a.y),float(b.y)))
        if not (0.003<abs(o)<=.10):
            continue
        if _close(endpoints[0],lo) and _close(endpoints[1],hi):
            found.append((e.dxf.handle,o))
    return found


def _door_arcs_at_gap(arcs, axis, coord, lo, hi):
    found=[]
    for a in arcs:
        center=a.dxf.center
        ortho=float(center.y if axis=="h" else center.x)
        para=float(center.x if axis=="h" else center.y)
        width=float(a.dxf.radius)
        if (_close(ortho,coord) and _close(width,hi-lo) and
                (_close(para,lo) or _close(para,hi))):
            found.append(a.dxf.handle)
    return found


def _leaves_at_arc(leaves, arc):
    """A door arc needs an actual matching hinge-to-leaf LINE in the DXF."""
    found=[]
    for leaf in leaves:
        a,b=leaf.dxf.start,leaf.dxf.end
        if (_close(a.x,arc.dxf.center.x) and _close(a.y,arc.dxf.center.y)
                and _close(hypot(b.x-a.x,b.y-a.y),arc.dxf.radius)):
            found.append(leaf.dxf.handle)
    return found


def _new_result(errors=(),status="DADOS_INSUFICIENTES",pendings=(),walls=()):
    walls=list(walls)
    openings=[gap for wall in walls for gap in wall["vaos"]]
    return {
        "ok":not errors,
        "status":status,
        "versao_calculo":VERSION,
        "fonte":"DXF Modelspace serializado; sem dependência de modelo do gerador",
        "paredes":walls,
        "erros":list(errors),
        "pendencias":list(pendings),
        "resumo":{
            "alinhamentos":len(walls),
            "comprimento_bruto_m":round(sum(w["comprimento_bruto_m"] for w in walls),6),
            "comprimento_trechos_solidos_m":round(sum(w["comprimento_trechos_solidos_m"] for w in walls),6),
            "portas":sum(g["tipo"]=="PORTA" for g in openings),
            "janelas":sum(g["tipo"]=="JANELA" for g in openings),
            "vaos_sem_simbolo":sum(g["tipo"]=="VAO_SEM_IDENTIFICACAO" for g in openings),
            "vaos":len(openings),
        },
        "aprovacao_arquitetonica":False,
        "precos":None,
    }


def auditar_paredes_e_vaos_dxf(
    doc, *, altura_paredes_m=None, altura_portas_m=None,
    altura_janelas_m=None, espessura_paredes_m=None,
    altura_passagens_m=None,
):
    """Reconcile evidence independently; conservative about unidentified gaps.

    No wall volume is returned because junction deductions are not defined.
    A missing symbol is NOT silently treated as a door/window or full-height
    passage. Verified gross lengths are not mistaken for built wall lengths.
    """
    wall_height=_positive_or_none("altura_paredes_m",altura_paredes_m)
    door_height=_positive_or_none("altura_portas_m",altura_portas_m)
    window_height=_positive_or_none("altura_janelas_m",altura_janelas_m)
    thickness=_positive_or_none("espessura_paredes_m",espessura_paredes_m)
    passage_height=_positive_or_none("altura_passagens_m",altura_passagens_m)
    entities=list(doc.modelspace())
    if len(entities)>MAX_DXF_ENTITIES:
        return _new_result([{"codigo":"LIMITE_ENTIDADES"}],"LIMITE_EXCEDIDO")
    if doc.header.get("$INSUNITS")!=6:
        return _new_result([{"codigo":"UNIDADES_INVALIDAS"}],"INVALIDO")
    errors=[]
    pendencies=[]
    groups=defaultdict(list)
    axes=list(doc.modelspace().query('LINE[layer=="EIXOS-PAREDES"]'))
    arcs=list(doc.modelspace().query('ARC[layer=="PORTAS"]'))
    leaves=list(doc.modelspace().query('LINE[layer=="PORTAS"]'))
    arc_by_handle={a.dxf.handle:a for a in arcs}
    windows=list(doc.modelspace().query('LINE[layer=="JANELAS"]'))
    for line in axes:
        a,b=line.dxf.start,line.dxf.end
        coords=(float(a.x),float(a.y),float(b.x),float(b.y))
        if any(not isfinite(v) for v in coords):
            errors.append({"codigo":"EIXO_NAO_FINITO","handle":line.dxf.handle})
            continue
        if hypot(coords[0]-coords[2],coords[1]-coords[3])<=TOL:
            errors.append({"codigo":"EIXO_DEGENERADO","handle":line.dxf.handle})
            continue
        if _close(a.y,b.y):
            key=("h",round((a.y+b.y)/2,5))
            groups[key].append(_entry(line.dxf.handle,*sorted((a.x,b.x))))
        elif _close(a.x,b.x):
            key=("v",round((a.x+b.x)/2,5))
            groups[key].append(_entry(line.dxf.handle,*sorted((a.y,b.y))))
        else:
            errors.append({"codigo":"EIXO_NAO_ORTOGONAL","handle":line.dxf.handle})
    if not groups:
        return _new_result(errors,"INVALIDO" if errors else "DADOS_INSUFICIENTES",
                           ["Nenhum eixo mensurável no layer EIXOS-PAREDES."])
    walls=[]
    used_arcs=set()
    used_leaves=set()
    used_windows=set()
    for axis,coord in sorted(groups):
        intervals=sorted(groups[(axis,coord)])
        runs=[]
        current=[intervals[0]]
        for item in intervals[1:]:
            prev=current[-1]
            gap=item[0]-prev[1]
            if gap < -TOL:
                errors.append({"codigo":"EIXOS_SOBREPOSTOS",
                               "handles":[prev[2],item[2]]})
                current.append(item)
            elif gap > MAX_RECONSTRUCTIBLE_GAP_M:
                # Never fabricate wall through a long empty distance.
                runs.append(current)
                current=[item]
                pendencies.append("Eixos colineares separados por grande vão: não concatenados.")
            else:
                current.append(item)
        runs.append(current)
        for run_number,run in enumerate(runs,1):
            start=min(a for a,b,h in run)
            end=max(b for a,b,h in run)
            solid=sum(b-a for a,b,h in run)
            gaps=[]
            for (a,b,ha),(c,d,hb) in zip(run,run[1:]):
                if c-b<=TOL:
                    continue
                matched_arcs=_door_arcs_at_gap(arcs,axis,coord,b,c)
                matched_windows=_window_lines_at_gap(windows,axis,coord,b,c)
                kinds=bool(matched_arcs)+bool(matched_windows)
                if len(matched_arcs)>1 or len(matched_windows)>2 or kinds>1:
                    errors.append({"codigo":"SIMBOLOS_AMBIGUOS",
                                   "eixo":f"{axis}:{coord}","vao":[b,c]})
                if matched_windows and (len(matched_windows)!=2 or
                        matched_windows[0][1]*matched_windows[1][1]>=0 or
                        abs(matched_windows[0][1]+matched_windows[1][1])>TOL):
                    errors.append({"codigo":"JANELA_INCOMPLETA",
                                   "eixo":f"{axis}:{coord}","vao":[b,c]})
                if matched_arcs and kinds==1:
                    leaf_matches=[
                        h for arc_id in matched_arcs
                        for h in _leaves_at_arc(leaves,arc_by_handle[arc_id])
                    ]
                    if len(leaf_matches)!=len(matched_arcs) or len(leaf_matches)!=1:
                        errors.append({"codigo":"FOLHA_PORTA_INCONSISTENTE",
                                       "eixo":f"{axis}:{coord}","vao":[b,c],
                                       "arcos":matched_arcs,"folhas":leaf_matches})
                    kind="PORTA"
                    sym=matched_arcs+leaf_matches
                    used_leaves.update(leaf_matches)
                    height=door_height
                elif len(matched_windows)==2 and kinds==1 and (
                        matched_windows[0][1]*matched_windows[1][1]<0 and
                        abs(matched_windows[0][1]+matched_windows[1][1])<=TOL):
                    kind="JANELA"
                    sym=[x[0] for x in matched_windows]
                    height=window_height
                else:
                    kind="VAO_SEM_IDENTIFICACAO"
                    sym=[]
                    height=None  # Do not apply passage_height to unknown opening.
                    pendencies.append(
                        f"Vão sem identificação no eixo {axis}:{coord} [{b:.3f},{c:.3f}]. "
                        "Confirmar natureza do vão e fornecer altura_passagens_m vinculada ao vão.")
                used_arcs.update(matched_arcs)
                used_windows.update(handle for handle,offset in matched_windows)
                gap={
                    "id":f"vao:{axis}:{coord:.5f}:{b:.5f}:{c:.5f}",
                    "tipo":kind,
                    "largura_m":round(c-b,6),
                    "coordenadas":[round(b,6),round(c,6)],
                    "handles_simbolos":sym,
                    "altura_m":height,
                    "area_m2":round((c-b)*height,6) if height else None,
                    "criterio":"DXF: folga real entre trechos sólidos, com símbolo conferido",
                }
                gaps.append(gap)
            gross=round(end-start,6)
            solid=round(solid,6)
            if not _close(gross,solid+sum(g["largura_m"] for g in gaps)):
                errors.append({"codigo":"COMPRIMENTO_NAO_CONCILIADO",
                               "eixo":f"{axis}:{coord}"})
            gross_area=round(gross*wall_height,6) if wall_height is not None else None
            can_net=(wall_height is not None and
                     all(g["altura_m"] is not None for g in gaps) and
                     all(g["altura_m"]<=wall_height+TOL for g in gaps) and
                     not any(g["tipo"]=="VAO_SEM_IDENTIFICACAO" for g in gaps))
            area_deductions=sum(g["area_m2"] for g in gaps) if can_net else None
            net=(round(gross_area-area_deductions,6)
                 if can_net and gross_area>=area_deductions else None)
            if any(g["altura_m"] is not None and g["altura_m"]>wall_height+TOL
                   for g in gaps) if wall_height is not None else False:
                errors.append({"codigo":"ABERTURA_MAIS_ALTA_QUE_PAREDE",
                               "eixo":f"{axis}:{coord}"})
            walls.append({
                "id_parede":f"eixo:{axis}:{coord:.5f}:{run_number}",
                "eixo":axis,
                "ordenada_m":coord,
                "comprimento_bruto_m":gross,
                "comprimento_trechos_solidos_m":solid,
                "handles_eixos":[h for a,b,h in run],
                "vaos":gaps,
                "area_bruta_m2":gross_area,
                "area_aberturas_m2":round(area_deductions,6) if can_net else None,
                "area_liquida_m2":net,
                "volume_geometrico_m3":None,
                "espessura_declarada_m":thickness,
                "fonte":"DXF EIXOS-PAREDES/PORTAS/JANELAS",
                "criterio":"Alinhamento bruto de eixo reconstituído dos trechos sólidos e vãos reais; "
                           "volume retido por ausência de regra de encontros.",
            })
    leftovers=[e.dxf.handle for e in arcs if e.dxf.handle not in used_arcs]
    leftovers+= [e.dxf.handle for e in leaves if e.dxf.handle not in used_leaves]
    leftovers+= [e.dxf.handle for e in windows if e.dxf.handle not in used_windows]
    if leftovers:
        errors.append({"codigo":"SIMBOLO_SEM_ABERTURA","handles":leftovers})
    if wall_height is None:pendencies.append("altura_paredes_m ausente")
    if door_height is None and used_arcs:pendencies.append("altura_portas_m ausente")
    if window_height is None and used_windows:pendencies.append("altura_janelas_m ausente")
    if passage_height is not None:
        pendencies.append("altura_passagens_m informada, mas não atribuída a vãos sem identificação.")
    pendencies.append("Volumes indisponíveis: encontros de paredes e método de desconto não definidos.")
    return _new_result(errors,"INVALIDO" if errors else "PARCIAL" if pendencies else
                       "VALIDADO_GEOMETRICAMENTE",pendencies,walls)
