"""Auditoria preliminar de circulacao e interferencias no CAD da casa compacta.

Contrato delimitado: planta ortogonal, em metros, paredes de eixo e mobiliario
retangular. O auditor exige que o DXF tenha passado previamente pela auditoria
geometrica de correspondencia. Nao representa uma certificacao de NBR 9050,
codigo de obras, ergonomia ou projeto arquitetonico.
"""
from __future__ import annotations

from collections import deque
import math

STEP = 0.10  # grade de verificacao em metros (aproximacao, nao tolerancia legal)
CLEARANCE = 0.25  # raio de reserva para detectar possivel estrangulamento; apenas aviso
MIN_PORTA_PILOTO = 0.80  # criterio interno de estudo, NAO largura legal
EPS = 1e-8


def _rect(entity):
    points = list(entity.get_points("xy"))
    if not entity.closed or len(points) != 4:
        return None
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _walls(model):
    # Eixos reais das paredes segmentadas nos vaos, validados contra o DXF
    # previamente por auditar_dxf_serializado.
    return [tuple(map(float, seg)) for seg in model["paredes"]]


def _blocked(x, y, walls, furniture, thickness, clearance):
    margin = thickness / 2 + clearance
    for a, b, c, d in walls:
        if abs(a-c) < EPS:
            if abs(x-a) <= margin and min(b,d)-margin <= y <= max(b,d)+margin:
                return True
        elif abs(b-d) < EPS:
            if abs(y-b) <= margin and min(a,c)-margin <= x <= max(a,c)+margin:
                return True
    for a,b,c,d in furniture:
        if a-clearance <= x <= c+clearance and b-clearance <= y <= d+clearance:
            return True
    return False


def _walk_grid(width, height, walls, furniture, thickness, clearance):
    nx, ny = math.ceil(width/STEP), math.ceil(height/STEP)
    free = set()
    for i in range(nx):
        x = (i+.5)*STEP
        if x >= width:
            continue
        for j in range(ny):
            y = (j+.5)*STEP
            if y < height and not _blocked(x,y,walls,furniture,thickness,clearance):
                free.add((i,j))
    return free


def _entrance_seeds(model, free):
    house = model["resumo_geometria"]
    width, height = float(house["largura"]), float(house["profundidade"])
    doors = [tuple(map(float,p)) for p in model["portas"]]
    candidates = []
    for i,(x,y,_angle,w) in enumerate(doors,1):
        if w <= 0:
            continue
        if abs(y-.075)<.11:
            candidates.append((i,x+w/2,.36))
        elif abs(y-(height-.075))<.11:
            candidates.append((i,x+w/2,height-.36))
        elif abs(x-.075)<.11:
            candidates.append((i,.36,y+w/2))
        elif abs(x-(width-.075))<.11:
            candidates.append((i,width-.36,y+w/2))
    starts = []
    for door,x,y in candidates:
        nearest = sorted(
            (i,j) for i,j in free
            if abs((i+.5)*STEP-x)<.31 and abs((j+.5)*STEP-y)<.31
        )
        nearest.sort(key=lambda p: ((p[0]+.5)*STEP-x)**2+((p[1]+.5)*STEP-y)**2)
        if nearest:
            starts.append((door,nearest[0]))
    return starts


def _reach(free, starts):
    seen=set(starts)
    q=deque(starts)
    while q:
        i,j=q.popleft()
        for pt in ((i+1,j),(i-1,j),(i,j+1),(i,j-1)):
            if pt in free and pt not in seen:
                seen.add(pt)
                q.append(pt)
    return seen


def _rooms_reached(rooms, free, reached):
    report = []
    for room in rooms:
        x1,y1,x2,y2=(float(room[k]) for k in ("x1","y1","x2","y2"))
        inside = [(i,j) for i,j in free
                  if x1+.03 <= (i+.5)*STEP <= x2-.03
                  and y1+.03 <= (j+.5)*STEP <= y2-.03]
        n_connected = sum(c in reached for c in inside)
        report.append({
            "ambiente": room["nome"],
            "celulas_livres": len(inside),
            "celulas_alcancaveis": n_connected,
            "conectado": n_connected > 0,
        })
    return report


def _angle_inside(angle, start):
    return (angle - start) % 360 <= 90+1e-6


def _inside_swing(x, y, hinge, radius, start):
    dx,dy=x-hinge[0],y-hinge[1]
    d2=dx*dx+dy*dy
    if d2 > (radius-.012)**2 or d2 < .12**2:
        return False
    angle=math.degrees(math.atan2(dy,dx)) % 360
    return _angle_inside(angle,start)


def _swing_bounds(hinge,radius,start):
    xs=[hinge[0],hinge[0]+radius*math.cos(math.radians(start)),
        hinge[0]+radius*math.cos(math.radians(start+90))]
    ys=[hinge[1],hinge[1]+radius*math.sin(math.radians(start)),
        hinge[1]+radius*math.sin(math.radians(start+90))]
    return min(xs),min(ys),max(xs),max(ys)


def _grid_intersection(box_a,box_b,measure):
    x1=max(box_a[0],box_b[0]); y1=max(box_a[1],box_b[1])
    x2=min(box_a[2],box_b[2]); y2=min(box_a[3],box_b[3])
    if x2 <= x1+.01 or y2 <= y1+.01:
        return False
    # Sample cell centres at up to 5 cm increments; ignore tangent contact.
    nx=max(1,math.ceil((x2-x1)/.05))
    ny=max(1,math.ceil((y2-y1)/.05))
    for i in range(nx):
        x=x1+(i+.5)*(x2-x1)/nx
        for j in range(ny):
            y=y1+(j+.5)*(y2-y1)/ny
            if measure(x,y):
                return True
    return False


def auditar_circulacao(model: dict, doc) -> dict:
    """Audit real DXF door arcs/furniture plus model's validated wall axes.

    Must run AFTER auditar_dxf_serializado (DXF/model equality); if the
    contract differs, the preceding audit blocks delivery.
    """
    erros, avisos = [], []
    def emit(dst,key,where,detail):
        dst.append({"chave":key,"onde":where,"detalhe":detail})

    msp=doc.modelspace()
    walls=_walls(model)
    furniture=[]
    for entity in msp.query('LWPOLYLINE[layer=="MOBILIARIO"]'):
        rect=_rect(entity)
        if rect is None:
            emit(erros,"mobiliario-nao-retangular","MOBILIARIO",
                 "Nao foi possivel calcular a interferencia do mobiliario no DXF")
        else:
            furniture.append(rect)

    arcs=list(msp.query('ARC[layer=="PORTAS"]'))
    if len(arcs)!=len(model["portas"]):
        emit(erros,"portas-incompletas","PORTAS",
             "Quantidade de arcos fisicos diverge das portas do programa")
    # Windows are glazed barriers, not walkable passages. The model's
    # walls are intentionally cut at windows; without the DXF glazing,
    # the flood-fill may reach an isolated room through an exterior window.
    glazing = [
        (float(e.dxf.start.x), float(e.dxf.start.y),
         float(e.dxf.end.x), float(e.dxf.end.y))
        for e in msp.query('LINE[layer=="JANELAS"]')
    ]
    movement_barriers = walls + glazing

    t=float(model["espessura_parede"])
    info=model["resumo_geometria"]
    width,height=float(info["largura"]),float(info["profundidade"])

    # Check real door sweep sectors, not the endpoints of the leaf only.
    door_geometries=[]
    for idx,arc in enumerate(arcs,1):
        hinge=(float(arc.dxf.center.x),float(arc.dxf.center.y))
        radius=float(arc.dxf.radius)
        start=float(arc.dxf.start_angle) % 360
        area=_swing_bounds(hinge,radius,start)
        door_geometries.append((idx,hinge,radius,start,area))
        if radius < MIN_PORTA_PILOTO-1e-6:
            emit(avisos,"porta-estreita-piloto",f"porta {idx}",
                 f"Vao nominal {radius:.2f} m abaixo do criterio piloto {MIN_PORTA_PILOTO:.2f} m")
        for k,rect in enumerate(furniture,1):
            if _grid_intersection(area,rect,
                 lambda x,y: _inside_swing(x,y,hinge,radius,start)):
                emit(erros,"porta-colide-mobiliario",f"porta {idx} / movel {k}",
                     "Setor de giro da porta intercepta mobiliario real no DXF")
        # Wall clash is an advisory for this pilot: door hinges are on the
        # wall and near-tangent clearance requires more precise geometry.
        wall_hits=0
        for fraction in (.30,.60,.88):
            for offset in (15,35,55,75):
                a=math.radians(start+offset)
                x=hinge[0]+radius*fraction*math.cos(a)
                y=hinge[1]+radius*fraction*math.sin(a)
                if _blocked(x,y,walls,[],t,.005):
                    wall_hits+=1
        if wall_hits:
            emit(avisos,"giro-proximo-parede",f"porta {idx}",
                 "Setor de giro amostrado intercepta parede; conferir sentido e batente")

    for i,pa in enumerate(door_geometries):
        ida,ca,ra,aa,ba=pa
        for idb,cb,rb,ab,bb in door_geometries[i+1:]:
            if _grid_intersection(ba,bb,
                lambda x,y: _inside_swing(x,y,ca,ra,aa) and
                            _inside_swing(x,y,cb,rb,ab)):
                emit(avisos,"giros-portas-sobrepostos",f"portas {ida}/{idb}",
                     "Setores de giro podem interferir com aberturas simultaneas")

    free=_walk_grid(width,height,movement_barriers,furniture,t,0.0)
    entrances=_entrance_seeds(model,free)
    if not entrances:
        emit(erros,"entrada-inexistente","entrada",
             "Nenhuma porta de fachada gera ponto de entrada livre na malha")
    reachable=_reach(free,[seed for _,seed in entrances])
    rooms=_rooms_reached(model["ambientes"],free,reachable)
    for room in rooms:
        if not room["celulas_livres"]:
            emit(erros,"ambiente-sem-area-livre",room["ambiente"],
                 "Nao ha celulas transitaveis amostradas no ambiente")
        elif not room["conectado"]:
            emit(erros,"ambiente-inacessivel",room["ambiente"],
                 "Nao existe percurso continuo amostrado desde a porta de entrada")

    # Clearance pass: narrower than the configured pilot radius is a warning
    # rather than a regulatory assertion or a false hard stop.
    clearance_free=_walk_grid(width,height,movement_barriers,furniture,t,CLEARANCE)
    wide_entrances=_entrance_seeds(model,clearance_free)
    wide_reach=_reach(clearance_free,[seed for _,seed in wide_entrances])
    wide_rooms=_rooms_reached(model["ambientes"],clearance_free,wide_reach)
    for room in wide_rooms:
        if not room["conectado"]:
            emit(avisos,"passagem-estreita-estimada",room["ambiente"],
                 f"Malha com reserva lateral de {CLEARANCE:.2f} m nao alcanca "
                 "o ambiente. Verificar largura livre em CAD e escala real.")

    return {
        "ok":not erros,
        "tipo":"auditoria_preliminar_circulacao_interferencias",
        "erros":erros,"avisos":avisos,
        "metricas":{
            "grade_m":STEP,"reserva_lateral_m":CLEARANCE,
            "portas_verificadas":len(arcs),
            "moveis_verificados":len(furniture),
            "linhas_vidro_verificadas":len(glazing),
            "entradas_detectadas":len(entrances),
            "ambientes":rooms,
            "ambientes_conectados":sum(x["conectado"] for x in rooms),
            "ambientes_total":len(rooms),
        },
        "limitacoes":[
            "Conectividade aproximada por malha de 0,10 m; janelas de vidro sao barreiras. Nao constitui rota acessivel NBR 9050.",
            "Eixos de paredes do modelo sao usados apos confrontacao com DXF; "
            "erros compartilhados por modelo e desenho podem nao ser detectados.",
            "Giros sao avaliados em setores geometricos; sobreposicao entre portas "
            "nao comprova colisao em uso real.",
            "Reserva de 0,25 m e porta de 0,80 m sao parametros de teste, "
            "nao exigencias legais verificadas.",
        ],
    }
