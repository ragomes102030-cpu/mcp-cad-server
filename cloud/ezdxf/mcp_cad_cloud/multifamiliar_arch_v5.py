"""Revisao 05: estudo funcional com escada dimensionada e verificacoes.
Base geometrica: DXF real da revisao 04. NAO certifica normas, incendio,
acessibilidade, seguranca, estrutura ou conformidade municipal.
"""
from __future__ import annotations
import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

class FunctionalValidationError(ValueError):
    pass

@dataclass(frozen=True)
class StairDesign:
    floor_to_floor_m: float
    risers: int
    risers_per_flight: int
    riser_height_m: float
    tread_depth_m: float
    treads_per_flight: int
    flight_width_m: float
    landing_depth_m: float
    comfort_2h_plus_p_m: float
    first_flight: tuple
    second_flight: tuple
    landing: tuple
    access_lane: tuple

def design_stair(floor_to_floor_m=3.0):
    if not 2.70 <= floor_to_floor_m <= 3.30:
        raise FunctionalValidationError("Desnivel fora da faixa do piloto")
    candidates=[n for n in range(14,24,2) if .15<=floor_to_floor_m/n<=.18]
    if not candidates:
        raise FunctionalValidationError("Sem solucao preliminar de espelhos")
    n=min(candidates,key=lambda k:abs(floor_to_floor_m/k-.167))
    p=.29
    end=11.44+(n//2-1)*p
    if end+1.20>15.37:
        raise FunctionalValidationError("Patamar extrapola caixa de escada")
    return StairDesign(floor_to_floor_m,n,n//2,round(floor_to_floor_m/n,5),
        p,n//2-1,1.05,1.20,round(2*floor_to_floor_m/n+p,5),
        (28.10,11.44,29.15,end),(29.20,11.44,30.25,end),
        (28.10,end,30.25,end+1.20),(27.13,11.44,28.06,14.08))

def correct_living_room_interferences(doc):
    """Repair V3/V4 furniture geometry that obstructs real apartment doors."""
    from ezdxf import bbox
    from .multifamiliar_arch_v4 import _room_program
    m=doc.modelspace();removed=0;added=0
    for room in _room_program():
        if room.kind!="sala_cozinha":continue
        x0,y0,x1,y1=room.rect
        lower=room.uid in ("AP01","AP02")
        old=[(x0+8.6,y1-.75,x0+11.3,y1-.30),
             (x0+8.9,y0+.43,x0+11.34,y0+.93)]
        if lower:old.append((x0+.65,y0+.45,x0+3.6,y0+.95))
        for e in list(m):
            if e.dxf.layer not in {"ARQ-MOBILIARIO","ARQ-DETALHES"}:continue
            if e.dxftype() not in {"LINE","LWPOLYLINE","CIRCLE"}:continue
            ext=bbox.extents([e],fast=True)
            if not ext.has_data:continue
            xa,ya=ext.extmin.x,ext.extmin.y
            xb,yb=ext.extmax.x,ext.extmax.y
            if any(xa>=a-.03 and ya>=b-.03 and xb<=c+.03 and yb<=d+.03
                   for a,b,c,d in old):
                m.delete_entity(e);removed+=1
        lo,hi=(y1-.85,y1-.38) if lower else (y0+.38,y0+.85)
        a,b=x0+7.35,x0+9.75
        m.add_lwpolyline([(a,lo),(b,lo),(b,hi),(a,hi)],close=True,
                         dxfattribs={"layer":"ARQ-DETALHES"})
        m.add_lwpolyline([(a+.17,lo+.08),(a+.81,lo+.08),
                          (a+.81,hi-.08),(a+.17,hi-.08)],close=True,
                         dxfattribs={"layer":"ARQ-DETALHES"})
        for xx in (b-.48,b-.21):
            m.add_circle((xx,(lo+hi)/2),.07,dxfattribs={"layer":"ARQ-DETALHES"})
        added+=4
        if lower:
            m.add_lwpolyline([(x0+.65,y1-.83),(x0+3.6,y1-.83),
                              (x0+3.6,y1-.37),(x0+.65,y1-.37)],
                              close=True,dxfattribs={"layer":"ARQ-MOBILIARIO"})
            added+=1
    return {"removed_or_repositioned":removed,"new":added}

def correct_stair_access_door(doc):
    """Move stair entry hinge to its upper jamb, clearing the access aisle."""
    from ezdxf import bbox
    m=doc.modelspace()
    arcs=[a for a in m.query("ARC") if a.dxf.layer=="ARQ-PORTAS"
          and abs(a.dxf.center.x-27)<.01 and abs(a.dxf.center.y-12.96)<.01
          and abs(a.dxf.radius-.9)<.01]
    if len(arcs)!=1:return False
    m.delete_entity(arcs[0])
    for e in list(m.query("LWPOLYLINE")):
        if e.dxf.layer!="ARQ-PORTAS":continue
        ext=bbox.extents([e],fast=True)
        if ext.has_data and 26.97<ext.extmin.x<27.04 and 27.85<ext.extmax.x<27.95 and 12.93<ext.extmin.y<12.98 and 12.94<ext.extmax.y<13.01:
            m.delete_entity(e)
    m.add_lwpolyline([(27,13.84),(27.9,13.84),(27.9,13.88),(27,13.88)],
                     close=True,dxfattribs={"layer":"ARQ-PORTAS","lineweight":35})
    m.add_arc((27,13.86),.9,270,360,
              dxfattribs={"layer":"ARQ-PORTAS","lineweight":13})
    return True

def _fixtures(m, room):
    from shapely.geometry import Polygon,box
    x0,y0,x1,y1=room.rect
    region=box(x0+.15,y0+.15,x1-.15,y1-.15)
    obstacles=[]
    for e in m.query("LWPOLYLINE"):
        if e.dxf.layer not in {"ARQ-MOBILIARIO","ARQ-DETALHES"} or not e.closed:
            continue
        pts=list(e.get_points("xy"))
        if len(pts)<3:continue
        poly=Polygon(pts)
        if poly.is_valid and poly.area>=.015 and poly.intersects(region):
            obstacles.append(poly.buffer(.20))
    return obstacles

def _route(start,goal,rect,obstacles,step=.20):
    from shapely.geometry import Point
    x0,y0,x1,y1=rect;inset=.28
    nx=int((x1-x0-2*inset)/step)+1
    ny=int((y1-y0-2*inset)/step)+1
    def node(x,y):return (round((x-x0-inset)/step),round((y-y0-inset)/step))
    def free(i,j):
        if not(0<=i<nx and 0<=j<ny):return False
        p=Point(x0+inset+i*step,y0+inset+j*step)
        return all(not o.contains(p) for o in obstacles)
    src=node(*start);dst=node(*goal)
    if not free(*src):return False
    queue=deque([src]);seen={src}
    while queue:
        i,j=queue.popleft()
        if abs(i-dst[0])<=1 and abs(j-dst[1])<=1:return True
        for nxt in ((i+1,j),(i-1,j),(i,j+1),(i,j-1)):
            if nxt not in seen and free(*nxt):
                seen.add(nxt);queue.append(nxt)
    return False

def audit_functional_v5(doc,stair):
    from shapely.geometry import LineString,box
    from .multifamiliar_arch_v4 import _room_program
    m=doc.modelspace();errors=[];routes={}
    if doc.audit().has_errors:errors.append("DXF invalido")
    if len([a for a in m.query("ARC") if a.dxf.layer=="ARQ-PORTAS"])!=21:
        errors.append("Quantidade de portas alterada")
    if len([a for a in m.query("LINE") if a.dxf.layer=="ARQ-JANELAS"])<60:
        errors.append("Janelas ausentes")
    line=LineString(((3.25,13),(26.8,13)))
    for e in m.query("LWPOLYLINE"):
        if e.dxf.layer!="ARQ-PAREDES":continue
        pts=list(e.get_points("xy"))
        if len(pts)>=3 and LineString(pts+[pts[0]]).intersects(line):
            errors.append("Parede bloqueia o eixo do corredor comum");break
    arcs=[a for a in m.query("ARC") if a.dxf.layer=="ARQ-PORTAS"
          and abs(a.dxf.center.x-27)<.02]
    if len(arcs)!=1 or abs(arcs[0].dxf.center.y-13.86)>.02:
        errors.append("Porta de escada obstrui faixa de acesso")
    for uid in ("AP01","AP02","AP03","AP04"):
        rooms=[r for r in _room_program() if r.uid==uid]
        living=next((r for r in rooms if r.kind=="sala_cozinha"),None)
        if living is None or len(rooms)!=5:
            errors.append(uid+": programa incompleto");continue
        x0,y0,x1,y1=living.rect
        low=uid in ("AP01","AP02")
        front=y1 if low else y0
        rear=y0 if low else y1
        start=(x0+6.05,front+(-.45 if low else .45))
        obstacles=_fixtures(m,living)
        outcomes=[_route(start,(x0+delta,rear+(.45 if low else -.45)),
                         living.rect,obstacles)
                  for delta in (2.80,6.80,9.15,11.05)]
        routes[uid]={"access_paths":outcomes,"connected":all(outcomes)}
        if not all(outcomes):errors.append(uid+": rota interna bloqueada por mobiliario")
    envelope=box(27.10,10.60,30.40,15.40)
    parts={n:box(*getattr(stair,n)) for n in
           ("first_flight","second_flight","landing","access_lane")}
    for name,part in parts.items():
        if not envelope.covers(part):errors.append("Escada fora da caixa: "+name)
    if parts["access_lane"].intersects(parts["first_flight"]) or parts["access_lane"].intersects(parts["second_flight"]):
        errors.append("Acesso sobrepoe lance de escada")
    if not parts["landing"].intersects(parts["first_flight"]) or not parts["landing"].intersects(parts["second_flight"]):
        errors.append("Patamar desconectado")
    if stair.risers%2 or stair.treads_per_flight!=stair.risers_per_flight-1:
        errors.append("Numero de degraus inconsistente")
    if not .60<=stair.comfort_2h_plus_p_m<=.65:
        errors.append("Indice de conforto preliminar fora da faixa")
    if stair.access_lane[2]-stair.access_lane[0]<.90:
        errors.append("Faixa de acesso menor que 0,90 m")
    return {"ok":not errors,"errors":errors,"routes":routes,
            "stair":asdict(stair),"corridor_clear_width_m":2.0,
            "warnings":["Seguranca contra incendio, acesso, corrimaos, guarda-corpos, "
                        "pe-direito livre, acessibilidade e atendimento ABNT nao verificados.",
                        "Terreno e norte apenas ilustrativos."],
            "scope":"estudo funcional geometrico; nao aprovado para execucao"}

def generate_multifamily_v5(output_dir,*,base_dxf=None,floor_to_floor_m=3.0):
    """Build actual DXF and two A3 vector PDF pages, gated by functional QA."""
    import ezdxf
    import matplotlib
    matplotlib.use("Agg",force=True)
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from matplotlib.backends.backend_pdf import PdfPages
    from ezdxf.addons.drawing import Frontend,RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties
    from .multifamiliar_arch_v4 import _preflight_baseline
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    if base_dxf is None:
        from .multifamiliar_arch_v4 import generate_multifamily_v4
        base=generate_multifamily_v4(out/"base_v4")
        if base["status"]!="v4_detailed_preliminary_not_normatively_approved":
            raise FunctionalValidationError("V4 nao aprovada")
        base_dxf=base["dxf"]
    doc=ezdxf.readfile(str(base_dxf));_preflight_baseline(doc)
    if "ARQ-01 A3 REV04" not in doc.layouts:
        raise FunctionalValidationError("Base DXF nao e revisao 04")
    stair=design_stair(floor_to_floor_m)
    correction=correct_living_room_interferences(doc)
    if not correct_stair_access_door(doc):
        raise FunctionalValidationError("Porta escada nao identificada")
    audit=audit_functional_v5(doc,stair)
    audit["furniture_fix"]=correction
    report=out/"auditoria_funcional_v5.json"
    report.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf8")
    if not audit["ok"]:
        raise FunctionalValidationError("Planta reprovada: "+"; ".join(audit["errors"]))
    m=doc.modelspace()
    for e in list(m):
        if e.dxf.layer=="ARQ-ESCADA":m.delete_entity(e)
        elif e.dxftype()=="TEXT" and e.dxf.layer in ("ARQ-SIMBOLOS","ARQ-TEXTOS"):
            if any(t in e.dxf.text.upper() for t in ("PISOS ESQUEMATICOS","ALTURA A VERIFICAR")):
                m.delete_entity(e)
    for layer,color in (("ARQ-ESCADA-PISOS",7),("ARQ-ESCADA-PATAMAR",7),
                        ("ARQ-ESCADA-ANOT",5),("ARQ-ESCADA-ACESSO",8)):
        if layer not in doc.layers:doc.layers.new(layer,dxfattribs={"color":color})
    def cadline(a,b,layer):
        m.add_line(a,b,dxfattribs={"layer":layer,"lineweight":25})
    def boxline(points,layer):
        m.add_lwpolyline(points,close=True,dxfattribs={"layer":layer})
    for flight in (stair.first_flight,stair.second_flight):
        x0,y0,x1,y1=flight
        boxline(((x0,y0),(x1,y0),(x1,y1),(x0,y1)),"ARQ-ESCADA-PATAMAR")
        for i in range(stair.treads_per_flight):
            y=y0+(i+1)*stair.tread_depth_m
            cadline((x0,y),(x1,y),"ARQ-ESCADA-PISOS")
    for name,layer in (("landing","ARQ-ESCADA-PATAMAR"),
                       ("access_lane","ARQ-ESCADA-ACESSO")):
        x0,y0,x1,y1=getattr(stair,name)
        boxline(((x0,y0),(x1,y0),(x1,y1),(x0,y1)),layer)
    for x,y0,y1 in ((28.63,11.7,13.35),(29.73,13.35,11.7)):
        cadline((x,y0),(x,y1),"ARQ-ESCADA-ANOT")
        sign=1 if y1>y0 else -1
        cadline((x,y1),(x-.16,y1-.21*sign),"ARQ-ESCADA-ANOT")
        cadline((x,y1),(x+.16,y1-.21*sign),"ARQ-ESCADA-ANOT")
    for name in list(doc.layouts.names()):
        if name.startswith("ARQ-0"):doc.layouts.delete(name)
    for name,center,height in (("ARQ-01 A3 REV05",(16,13),27.5),
                               ("ARQ-02 A3 ESCADA",(28.7,13),7.0)):
        sheet=doc.layouts.new(name)
        sheet.page_setup(size=(420,297),margins=(8,8,8,8),units="mm")
        sheet.add_viewport(center=(149,148),size=(265,220),
                           view_center_point=center,view_height=height,status=2)
        sheet.add_text(name,dxfattribs={"insert":(298,275),"height":4,
                                       "layer":"ARQ-TEXTOS"})
    if doc.audit().has_errors:raise FunctionalValidationError("DXF CAD invalido")
    dxf=out/"multifamiliar_funcional_v5.dxf"
    pdf=out/"multifamiliar_funcional_v5_A3.pdf"
    doc.saveas(dxf)
    props=LayoutProperties.from_layout(m);props.set_colors("#FFFFFF","#18212B")
    def fig_page(idx):
        fig=Figure(figsize=(420/25.4,297/25.4),facecolor="white")
        ax=fig.add_axes([16/420,43/297,265/420,220/297]);ax.set_axis_off()
        Frontend(RenderContext(doc),MatplotlibBackend(ax)).draw_layout(
            m,finalize=False,layout_properties=props)
        if idx==0:ax.set_xlim(-.5625,32.5625);ax.set_ylim(-.75,26.75)
        else:ax.set_xlim(25.8,31.6);ax.set_ylim(9.5,16.5)
        ax.set_aspect("equal",adjustable="box")
        fig.add_artist(Rectangle((8/420,8/297),404/420,281/297,
            fill=False,transform=fig.transFigure,edgecolor="#263948",linewidth=1))
        fig.add_artist(Line2D((294/420,294/420),(8/297,289/297),
            transform=fig.transFigure,color="#263948",linewidth=.8))
        def title(txt,x,y,size=8,bold=False):
            fig.text(x/420,y/297,txt,fontsize=size,
                     weight="bold" if bold else "normal",color="#1B2936")
        title("MCP CAD CLOUD",299,276,13,True)
        title("MULTIFAMILIAR | REVISAO 05",299,263,8.5,True)
        title("ESTUDO FUNCIONAL / ESCADA",299,247,9,True)
        if idx==0:
            title("ARQ-01 | PLANTA DE PAVIMENTO",299,228,8.5,True)
            title("4 APARTAMENTOS / 20 AMBIENTES",299,212)
            title("CIRCULACAO COMUM: 2,00 m",299,197)
            title("ESCADA: 18 ESPELHOS / 2 LANCES",299,170)
            title("PISO: 0,29 m | ESPELHO: 0,167 m",299,157)
        else:
            title("ARQ-02 | DETALHE DE ESCADA",299,228,9,True)
            title(f"DESNIVEL: {stair.floor_to_floor_m:.2f} m",299,212)
            title(f"{stair.risers} ESPELHOS / {stair.risers_per_flight} POR LANCE",299,198)
            title(f"ESPELHO: {stair.riser_height_m:.3f} m",299,183)
            title(f"PISO: {stair.tread_depth_m:.2f} m",299,169)
            title(f"PATAMAR: {stair.landing_depth_m:.2f} m",299,155)
            title(f"LANCE: {stair.flight_width_m:.2f} m",299,141)
            title("ACESSO/SEGURANCA: A CONFERIR",299,126,8,True)
        title("INCENDIO / ACESSIBILIDADE / NBR",299,103,7.5,True)
        title("SEM VERIFICACAO NORMATIVA",299,91,7.5)
        title("TERRENO HIPOTETICO / NORTE ILUSTRATIVO",299,76,7.2)
        title("A3 | ESCALA DE IMPRESSAO NAO GARANTIDA",299,58,7.2)
        title("NAO UTILIZAR PARA EXECUCAO",299,31,8.5,True)
        title(f"PRANCHA ARQ-0{idx+1} | REV 05 | COTAS EM METROS",19,25,8)
        return fig
    with PdfPages(pdf) as outpdf:
        for i in (0,1):
            figure=fig_page(i);outpdf.savefig(figure);figure.clear()
    if not pdf.read_bytes().startswith(b"%PDF-"):
        raise FunctionalValidationError("PDF nao gerado")
    audit["pdf_a3_pages"]=2
    audit["dxf_audit_errors"]=len(doc.audit().errors)
    audit["status"]="functional_preliminary_checks_passed_not_normative"
    report.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf8")
    return {"status":audit["status"],"pdf":str(pdf),"dxf":str(dxf),"audit":str(report)}

if __name__=="__main__":
    import sys
    print(json.dumps(generate_multifamily_v5(sys.argv[1] if len(sys.argv)>1 else ".",
        base_dxf=sys.argv[2] if len(sys.argv)>2 else None),indent=2))
