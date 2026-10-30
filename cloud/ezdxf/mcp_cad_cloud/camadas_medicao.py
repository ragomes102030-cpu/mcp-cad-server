"""Conservative measurement evidence layers for compact 2-bedroom DXF.

These are non-printing auxiliary entities, never finished construction
quantities. Wall axes are SOLID wall segments (already interrupted at doors
and windows); room rectangles are preliminary zoning surfaces, not a finish
schedule. Independent DXF validation checks physical face support and exact
geometry after serialization.
"""
from __future__ import annotations

from collections import Counter
from math import hypot, isfinite
from mcp_cad_cloud.quantitativos_engenharia import _simple_polygon, _polygon_area

TOL=1e-5
WALL="EIXOS-PAREDES"
FLOOR="PISOS"


def _rect(room):
    return (
        (float(room["x1"]),float(room["y1"])),
        (float(room["x2"]),float(room["y1"])),
        (float(room["x2"]),float(room["y2"])),
        (float(room["x1"]),float(room["y2"])),
    )


def adicionar_evidencias_de_medicao(doc, model):
    """Append only for a verified compact-house model; original art unchanged."""
    if model.get("estrategia") != "compacto_2quartos":
        return {"aplicado":False,"motivo":"template sem contrato de medição"}
    for layer in (WALL,FLOOR):
        if layer in doc.layers:
            raise ValueError("camada de medição já existe; não sobrepor entidades")
        item=doc.layers.new(layer,dxfattribs={"color":8,"plot":0})
        item.off()
    msp=doc.modelspace()
    for coords in model["paredes"]:
        x1,y1,x2,y2=map(float,coords)
        msp.add_line((x1,y1),(x2,y2),dxfattribs={"layer":WALL})
    for room in model["ambientes"]:
        msp.add_lwpolyline(_rect(room),close=True,dxfattribs={"layer":FLOOR})
    return {"aplicado":True,"eixos_trechos_solidos":len(model["paredes"]),
            "poligonos_zonas_ambientes":len(model["ambientes"]),
            "natureza":"evidencias_preliminares_nao_executivas"}


def _p(p):
    return (round(float(p[0]),6),round(float(p[1]),6))


def _line_key(a,b):
    return tuple(sorted((_p(a),_p(b))))


def _poly_key(points):
    return tuple(sorted(_p(point) for point in points))


def _point_on_segment(p,a,b):
    x,y=p
    (x1,y1),(x2,y2)=a,b
    if abs(x1-x2)<TOL and abs(x-x1)<TOL:
        return min(y1,y2)-TOL<=y<=max(y1,y2)+TOL
    if abs(y1-y2)<TOL and abs(y-y1)<TOL:
        return min(x1,x2)-TOL<=x<=max(x1,x2)+TOL
    return False


def _wall_supported(axis,wall_faces,thickness):
    x1,y1,x2,y2=axis
    good=0
    for fraction in (.2,.5,.8):
        x=x1+(x2-x1)*fraction
        y=y1+(y2-y1)*fraction
        if abs(y2-y1)<TOL:
            targets=((x,y-thickness/2),(x,y+thickness/2))
        else:
            targets=((x-thickness/2,y),(x+thickness/2,y))
        if all(any(_point_on_segment(pt,a,b) for a,b in wall_faces)
               for pt in targets):
            good+=1
    # Allow T junctions to absorb one cross-section (the physical boundary
    # is absent where wall solids meet), but never accept an unsupported
    # axis floating outside the real walls.
    return good>=2


def auditar_evidencias_de_medicao(model, doc):
    """Inspect DXF entities only; no call to the shared wall face generator."""
    if model.get("estrategia") != "compacto_2quartos":
        return []
    msp=doc.modelspace()
    errors=[]
    axis_entities=list(msp.query(f'LINE[layer=="{WALL}"]'))
    area_entities=list(msp.query(f'LWPOLYLINE[layer=="{FLOOR}"]'))
    unexpected=[
        e for e in msp if (e.dxf.layer in (WALL,FLOOR)
            and (e.dxftype() != ("LINE" if e.dxf.layer==WALL else "LWPOLYLINE")))
    ]
    if unexpected:
        errors.append({"chave":"medicao-entidades-inesperadas",
                       "handles":[e.dxf.handle for e in unexpected]})
    expected_lines=Counter(_line_key(v[:2],v[2:]) for v in model["paredes"])
    real_lines=Counter(_line_key(e.dxf.start,e.dxf.end) for e in axis_entities)
    if expected_lines!=real_lines:
        errors.append({"chave":"medicao-eixos-divergentes",
                       "esperado":sum(expected_lines.values()),
                       "encontrado":sum(real_lines.values())})
    expected_polys=Counter(_poly_key(_rect(r)) for r in model["ambientes"])
    real_polys=Counter()
    boxes=[]
    for e in area_entities:
        points=list(e.get_points("xy"))
        normalized=[(float(a),float(b)) for a,b in points]
        if not e.closed or len(points)!=4 or not _simple_polygon(normalized):
            errors.append({"chave":"medicao-pisos-contorno-invalido",
                           "handle":e.dxf.handle})
            continue
        xs=[x for x,y in normalized]
        ys=[y for x,y in normalized]
        rectangle=(min(xs),min(ys),max(xs),max(ys))
        if len({_p((x,y)) for x,y in normalized})!=4 or abs(
                _polygon_area(normalized)-(rectangle[2]-rectangle[0])*
                (rectangle[3]-rectangle[1]))>TOL:
            errors.append({"chave":"medicao-pisos-contorno-invalido",
                           "handle":e.dxf.handle})
        real_polys[_poly_key(normalized)]+=1
        boxes.append((e.dxf.handle,rectangle))
    if real_polys!=expected_polys:
        errors.append({"chave":"medicao-pisos-divergentes",
                       "esperado":sum(expected_polys.values()),
                       "encontrado":sum(real_polys.values())})
    for i,(a,ra) in enumerate(boxes):
        for b,rb in boxes[i+1:]:
            intersection=max(0,min(ra[2],rb[2])-max(ra[0],rb[0]))*max(
                0,min(ra[3],rb[3])-max(ra[1],rb[1]))
            if intersection>TOL:
                errors.append({"chave":"medicao-pisos-sobrepostos",
                               "handles":[a,b],"sobreposicao_m2":intersection})
    faces=[(_p(e.dxf.start),_p(e.dxf.end))
           for e in msp.query('LINE[layer=="PAREDES"]')]
    thickness=float(model["espessura_parede"])
    unsupported=[]
    for e in axis_entities:
        coords=(*_p(e.dxf.start),*_p(e.dxf.end))
        if not all(isfinite(c) for c in coords) or hypot(
                coords[0]-coords[2],coords[1]-coords[3])<=TOL:
            unsupported.append(e.dxf.handle)
        elif not _wall_supported(coords,faces,thickness):
            unsupported.append(e.dxf.handle)
    if unsupported:
        errors.append({"chave":"medicao-eixos-sem-suporte-fisico",
                       "handles":unsupported})
    if doc.header.get("$INSUNITS")!=6:
        errors.append({"chave":"medicao-unidades-invalidas"})
    return errors
