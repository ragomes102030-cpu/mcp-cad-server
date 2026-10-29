"""Diagnostico espacial quantificado, estritamente preliminar, para CAD compacto.

Estima maior folga minimax de um percurso no interior (malha de 0,10 m).
NAO fornece largura livre normativa ou levantamento preciso de construcao.
Fonte de paredes: eixos previamente confrontados com o DXF; vidros, portas e
mobiliario: entidades DXF reais. Chamar somente apos auditoria geometrica.
"""
from __future__ import annotations

from heapq import heappop, heappush
import math

from mcp_cad_cloud.auditoria_circulacao import STEP, _blocked, _reach, _entrance_seeds

MAX_OBSTACLES = 3


def _point_rect_dist(x, y, rect):
    a,b,c,d=rect
    dx=max(a-x, 0.0, x-c)
    dy=max(b-y, 0.0, y-d)
    return math.hypot(dx,dy)


def _point_segment_dist(x, y, segment):
    a,b,c,d=segment
    dx=c-a; dy=d-b
    length2=dx*dx+dy*dy
    if length2==0:
        return math.hypot(x-a,y-b)
    t=max(0.0,min(1.0,((x-a)*dx+(y-b)*dy)/length2))
    return math.hypot(x-a-t*dx,y-b-t*dy)


def _obstacles(model,doc):
    thickness=float(model["espessura_parede"])
    walls=[(f"PAREDE-{i:02d}",tuple(map(float,seg)),thickness/2,"segmento")
           for i,seg in enumerate(model["paredes"],1)]
    panes=[(f"VIDRO-{i:02d}",(float(e.dxf.start.x),float(e.dxf.start.y),
                               float(e.dxf.end.x),float(e.dxf.end.y)),
            thickness/2,"segmento")
           for i,e in enumerate(doc.modelspace().query('LINE[layer=="JANELAS"]'),1)]
    furniture=[]
    for i,e in enumerate(doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]'),1):
        pts=list(e.get_points("xy"))
        if not e.closed or len(pts)!=4:
            continue
        xs=[float(p[0]) for p in pts]
        ys=[float(p[1]) for p in pts]
        furniture.append((f"MOVEL-{i:02d}",(min(xs),min(ys),max(xs),max(ys)),0.0,"retangulo"))
    return walls+panes+furniture


def _distance_to_objects(x,y,obstacles,width,height):
    values=[]
    for name,geometry,padding,kind in obstacles:
        if kind=="retangulo":
            dist=_point_rect_dist(x,y,geometry)
        else:
            dist=_point_segment_dist(x,y,geometry)-padding
        values.append((max(0.0,dist),name))
    values.extend((
        (x,"CONTORNO-ESQUERDO"),
        (width-x,"CONTORNO-DIREITO"),
        (y,"CONTORNO-FRONTAL"),
        (height-y,"CONTORNO-FUNDO"),
    ))
    values.sort(key=lambda v:(v[0],v[1]))
    return values


def _inside(room,i,j):
    x=(i+.5)*STEP
    y=(j+.5)*STEP
    return (float(room["x1"])+.03 <= x <= float(room["x2"])-.03
            and float(room["y1"])+.03 <= y <= float(room["y2"])-.03)


def _neighbors(c):
    i,j=c
    return ((i+1,j),(i-1,j),(i,j+1),(i,j-1))


def diagnosticar_larguras(model,doc,livres,alcancaveis) -> dict:
    """Estimate widest-safe *interior* route, excluding the facade doorstep.

    For each room choose a reachable point with maximal minimum obstacle
    clearance along a route from a safe point inside the living room.
    The resulting diameter 2*r is indicative; not the legal free width.
    """
    summary=model["resumo_geometria"]
    width=float(summary["largura"])
    height=float(summary["profundidade"])
    obstacles=_obstacles(model,doc)
    rooms=model["ambientes"]
    living=next((a for a in rooms if "sala" in a["nome"].casefold()
                 or "estar" in a["nome"].casefold()),None)
    if not living or not alcancaveis:
        return {"metodo":"raio_livre_por_malha_e_rota_maximin",
                "grade_m":STEP,"larguras":[],"observacao":"Sem sala alcançavel"}

    clearance={}
    for i,j in alcancaveis:
        x=(i+.5)*STEP; y=(j+.5)*STEP
        clearance[(i,j)]=_distance_to_objects(x,y,obstacles,width,height)[0][0]
    sources=[c for c in alcancaveis if _inside(living,*c)]
    if not sources:
        return {"metodo":"raio_livre_por_malha_e_rota_maximin",
                "grade_m":STEP,"larguras":[],"observacao":"Sala sem ponto livre alcancavel"}

    # Begin at a spacious point in the entrance room. Door clearances are
    # reported separately by the existing per-door report.
    source=max(sources,key=lambda c:(clearance[c],-c[0],-c[1]))
    capacity={source:clearance[source]}
    previous={}
    pq=[(-clearance[source],source)]
    while pq:
        neg,c=heappop(pq)
        best=-neg
        if best < capacity[c]-1e-10:
            continue
        for nb in _neighbors(c):
            if nb not in clearance:
                continue
            candidate=min(best,clearance[nb])
            if candidate>capacity.get(nb,-1)+1e-10:
                capacity[nb]=candidate
                previous[nb]=c
                heappush(pq,(-candidate,nb))

    results=[]
    for room in rooms:
        cells=[c for c in capacity if _inside(room,*c)]
        if not cells:
            results.append({"ambiente":room["nome"],"largura_estimativa_m":None,
                            "ponto_critico_m":None,"obstaculos_proximos":[],
                            "situacao":"sem_rota_estimavel"})
            continue
        dest=max(cells,key=lambda c:(capacity[c],clearance[c]))
        path=[dest]
        while path[-1]!=source:
            path.append(previous[path[-1]])
        critical=min(path,key=lambda c:clearance[c])
        radius=clearance[critical]
        x=round((critical[0]+.5)*STEP,3)
        y=round((critical[1]+.5)*STEP,3)
        near=_distance_to_objects(x,y,obstacles,width,height)
        results.append({
            "ambiente":room["nome"],
            "largura_estimativa_m":round(2*radius,3),
            "ponto_critico_m":[x,y],
            "obstaculos_proximos":[
                {"id":name,"distancia_aproximada_m":round(dist,3)}
                for dist,name in near[:MAX_OBSTACLES]],
            "situacao":"estimada",
        })
    return {
        "metodo":"raio_livre_por_malha_e_rota_maximin",
        "grade_m":STEP,
        "incerteza_quantizacao_aproximada_m":round(2*STEP,3),
        "origem_percurso":"ponto_interno_da_sala; porta_externa_verificada_separadamente",
        "larguras":results,
        "limitacao":"Diametro do espaco livre ao longo da melhor rota na malha; "
                    "pode variar com discretizacao e nao representa largura "
                    "minima legal, espaco de giro ou acesso acessivel.",
    }


def verificar_integracao_sala_cozinha(model,doc) -> dict:
    """Check physical continuity at the boundary of two named zones."""
    rooms=model["ambientes"]
    sala=next((a for a in rooms if "sala" in a["nome"].casefold()),None)
    cozinha=next((a for a in rooms if "cozinha" in a["nome"].casefold()),None)
    if sala is None or cozinha is None:
        return {"ok":False,"verificado":False,"largura_abertura_estimada_m":None,
                "motivo":"Sala ou cozinha ausente do programa"}
    # Pilot layout defines adjacent rectangles, separated by <= 0.35 m.
    lx=float(sala["x2"])
    rx=float(cozinha["x1"])
    gap=rx-lx
    lower=max(float(sala["y1"]),float(cozinha["y1"]))
    upper=min(float(sala["y2"]),float(cozinha["y2"]))
    if gap>0.35 or gap<-.35 or upper-lower<.75:
        return {"ok":False,"verificado":False,"largura_abertura_estimada_m":None,
                "motivo":"Geometria fora do contrato de zonas adjacentes do modelo compacto"}
    width=float(model["resumo_geometria"]["largura"])
    height=float(model["resumo_geometria"]["profundidade"])
    thickness=float(model["espessura_parede"])
    obstacles=_obstacles(model,doc)
    solid=[o for o in obstacles if o[0].startswith(("PAREDE","VIDRO"))]
    furniture=[o for o in obstacles if o[0].startswith("MOVEL")]
    # Sample three cross-section coordinates to ensure the passage is not
    # a blind corridor or a room-to-room contact in labels only.
    xa=(lx+rx)/2
    xs=(xa-.10,xa,xa+.10)
    step=.025
    n=max(0, int((upper-lower)/step))
    free_runs=[]
    start=None
    for index in range(n):
        y=lower+(index+.5)*step
        passable=True
        for x in xs:
            if x<0 or x>width or y<0 or y>height:
                passable=False
                break
            for _,line,padding,_kind in solid:
                if _point_segment_dist(x,y,line)<=padding+.005:
                    passable=False
                    break
            if not passable:
                break
            for _,rect,_,_ in furniture:
                if _point_rect_dist(x,y,rect)<.005:
                    passable=False
                    break
            if not passable:
                break
        if passable and start is None:
            start=y-step/2
        if not passable and start is not None:
            free_runs.append((start,y-step/2))
            start=None
    if start is not None:
        free_runs.append((start,lower+n*step))
    if not free_runs:
        return {"ok":False,"verificado":True,
                "largura_abertura_estimada_m":0.0,
                "ponto_passagem_m":None,"motivo":"Sem faixa aberta entre as zonas"}
    lo,hi=max(free_runs,key=lambda item:item[1]-item[0])
    span=hi-lo
    return {"ok":span>=.6,"verificado":True,
            "largura_abertura_estimada_m":round(span,3),
            "ponto_passagem_m":[round(xa,3),round((lo+hi)/2,3)],
            "intervalo_aberto_y_m":[round(lo,3),round(hi,3)],
            "separacao_entre_zonas_m":round(gap,3),
            "metodo":"seccao transversal amostrada a cada 0,025 m em 3 linhas",
            "motivo":"Abertura no plano" if span>=.6 else "Abertura inferior ao criterio piloto de 0,60 m",
            "limitacao":"Estimativa geometrica 2D sem garantia de acessibilidade, "
                        "acabamento, vaos efetivos ou norma.",
    }
