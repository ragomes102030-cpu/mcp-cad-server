"""MCP CAD Cloud / multifamily four-unit geometry-first pilot.

Output is an actual ezdxf architectural drawing and its A3 PDF rendering.
The program validates connectivity and graphic geometry; it does NOT validate
Brazilian building, fire, accessibility or structural standards.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from math import cos, sin, radians
from pathlib import Path

SITE = (0.0, 0.0, 32.0, 26.0)  # assumed demonstration lot, not user-supplied land survey
BUILDING = (3.0, 4.0, 27.0, 22.0)  # four units plus the shared passage
STAIR = (27.0, 10.5, 30.5, 15.5)
CORRIDOR = (3.0, 12.0, 27.0, 14.0)
EXTERIOR_WALL = .20
PARTITION_WALL = .12


@dataclass(frozen=True)
class Opening:
    id: str
    type: str
    axis: str  # 'h' for horizontal host wall, 'v' for vertical host wall
    wall_coord: float
    start: float
    width: float
    side: int = 1  # door inward swing along +/- perpendicular axis
    unit: str = "common"

    @property
    def end(self) -> float:
        return self.start + self.width


@dataclass(frozen=True)
class Space:
    id: str
    kind: str
    rect: tuple[float, float, float, float]
    unit: str


class ArchitecturalValidationError(ValueError):
    pass


def _build_geometry():
    """Define walls as material, NOT overlapping line entities. Openings cut material."""
    from shapely.geometry import box
    from shapely.ops import unary_union

    raw_walls = []
    openings: list[Opening] = []
    spaces: list[Space] = []

    def hwall(x1, x2, y, thickness):
        raw_walls.append(box(x1, y-thickness/2, x2, y+thickness/2))

    def vwall(x, y1, y2, thickness):
        raw_walls.append(box(x-thickness/2, y1, x+thickness/2, y2))

    bx0, by0, bx1, by1 = BUILDING
    hwall(bx0,bx1,by0,EXTERIOR_WALL)
    hwall(bx0,bx1,by1,EXTERIOR_WALL)
    vwall(bx0,by0,by1,EXTERIOR_WALL)
    vwall(bx1,by0,by1,EXTERIOR_WALL)
    # Shared corridor has guaranteed 2m nominal clear centerline separation.
    hwall(bx0,bx1,12,EXTERIOR_WALL)
    hwall(bx0,bx1,14,EXTERIOR_WALL)
    # Two party-wall segments; NEVER block the shared corridor.
    vwall(15,4,12,EXTERIOR_WALL)
    vwall(15,14,22,EXTERIOR_WALL)
    for row in range(2):
        y0=4 if row==0 else 14
        room_boundary=(y0+4.5 if row==0 else y0+3.5)
        unit_rear=(y0 if row==0 else y0+8)
        room_ylo=min(room_boundary,unit_rear)
        room_yhi=max(room_boundary,unit_rear)
        inside_y=(room_boundary + (2 if row==0 else -2))
        for col in range(2):
            x0=3+12*col
            uid=f"AP{row*2+col+1:02d}"
            hwall(x0,x0+12,room_boundary,PARTITION_WALL)
            for offset in (4,8,10.2):
                vwall(x0+offset,room_ylo,room_yhi,PARTITION_WALL)
            # Each functional room is independently entered FROM living/dining.
            for label,offset,w in (("q1",2.35,.90),("q2",6.35,.90),
                                   ("banho",8.75,.80),("servico",10.65,.80)):
                openings.append(Opening(uid+"-"+label,"door","h",room_boundary,
                                        x0+offset,w,-1 if row==0 else +1,uid))
            # Unit entrance from the common corridor, swings INSIDE the unit.
            front=y0+8 if row==0 else y0
            openings.append(Opening(uid+"-entrada","door","h",front,
                                    x0+5.55,1.0,-1 if row==0 else +1,uid))
            # Bedroom windows on real exterior facade, plus wet room vents.
            outer=y0 if row==0 else y0+8
            for label,start,w in (("janela-q1",1.10,1.55),("janela-q2",5.10,1.55),
                                  ("janela-banho",8.75,.70),("janela-servico",10.7,.75)):
                openings.append(Opening(uid+"-"+label,"window","h",outer,
                                        x0+start,w,0,uid))
            # One vertical facade opening lights/vents the living room.
            side_x=x0 if col==0 else x0+12
            living_ylo=min(room_boundary,front)
            # East facade touches the stair annex near the corridor; keep
            # windows entirely on the exposed facade, never into the stair.
            if col == 1:
                glazed_y = 9.0 if row == 0 else 16.0
                glazed_w = 1.20
            else:
                glazed_y = living_ylo + .75
                glazed_w = 1.50
            openings.append(Opening(uid+"-janela-sala","window","v",side_x,
                                    glazed_y,glazed_w,0,uid))
            spaces.extend([
                Space(uid+"-sala","sala_cozinha",(x0,living_ylo,x0+12,max(room_boundary,front)),uid),
                Space(uid+"-quarto1","quarto",(x0,room_ylo,x0+4,room_yhi),uid),
                Space(uid+"-quarto2","quarto",(x0+4,room_ylo,x0+8,room_yhi),uid),
                Space(uid+"-banho","banheiro",(x0+8,room_ylo,x0+10.2,room_yhi),uid),
                Space(uid+"-servico","servico",(x0+10.2,room_ylo,x0+12,room_yhi),uid),
            ])
    # Annex provides the stair but does NOT consume the uninterrupted corridor.
    sx0,sy0,sx1,sy1=STAIR
    hwall(sx0,sx1,sy0,EXTERIOR_WALL)
    hwall(sx0,sx1,sy1,EXTERIOR_WALL)
    vwall(sx1,sy0,sy1,EXTERIOR_WALL)
    vwall(sx0,sy0,sy1,EXTERIOR_WALL)
    openings.append(Opening("circulacao-escada","door","v",27,12.96,.90,+1,"common"))
    spaces.append(Space("circulacao-comum","circulacao",CORRIDOR,"common"))
    spaces.append(Space("escada","escada",STAIR,"common"))

    raw=unary_union(raw_walls)
    voids=[]
    for op in openings:
        # Cut through entire wall thickness with clearance, no painted-over lines.
        if op.axis=="h":
            voids.append(box(op.start,op.wall_coord-.16,op.end,op.wall_coord+.16))
        else:
            voids.append(box(op.wall_coord-.16,op.start,op.wall_coord+.16,op.end))
    material=raw.difference(unary_union(voids))
    return material,raw,openings,spaces


def audit_multifamily_internal(material, raw, openings, spaces) -> dict:
    """Reject bad construction before any A3 sheet is generated."""
    from shapely.geometry import Point, box
    errors=[]
    if not material.is_valid or material.is_empty:
        errors.append("Material das paredes geometricamente invalido")
    if material.area <= 0 or material.area >= raw.area:
        errors.append("Vazios de portas/janelas nao foram subtraidos das paredes")
    if SITE[2] < STAIR[2] or SITE[3] < BUILDING[3]:
        errors.append("Implantacao extrapola o terreno de demonstracao")
    for uid in ("AP01","AP02","AP03","AP04"):
        unit_spaces=[s for s in spaces if s.unit==uid]
        if len(unit_spaces)!=5:
            errors.append(uid+": ambientes incompletos")
        unit_openings=[op for op in openings if op.unit==uid]
        if len([op for op in unit_openings if op.type=="door"])!=5:
            errors.append(uid+": portas internas ou de acesso faltando")
        if len([op for op in unit_openings if op.type=="window"])!=5:
            errors.append(uid+": janelas/ventilacao faltando")
        for op in unit_openings:
            # Opening must coincide with material before cut and be empty after.
            p=(op.start+op.width/2,op.wall_coord) if op.axis=="h" else (op.wall_coord,op.start+op.width/2)
            if not raw.buffer(.0001).covers(Point(*p)):
                errors.append(op.id+": nao ancorada em parede")
            if material.buffer(-.001).contains(Point(*p)):
                errors.append(op.id+": vao obstruido por parede")
    entrances={op.id for op in openings if op.id.endswith("-entrada")}
    if len(entrances)!=4:
        errors.append("Nao ha quatro acessos independentes ao corredor")
    if not any(op.id=="circulacao-escada" for op in openings):
        errors.append("Corredor sem acesso a caixa de escada")
    # Corridor central strip must be geometrically open its entire length,
    # aside from vertical midpoint unit boundary, which is intentionally
    # handled by a cross-corridor pass-through gap below.
    for x in (3.4,4,8,12,14.9,15,15.1,16,20,24,26,26.7):
        p=Point(x,13)
        if material.buffer(-.001).contains(p):
            errors.append(f"Corredor obstruido em x={x}")
    if material.buffer(-.001).contains(Point(27,13.4)):
        errors.append("Acesso corredor-escada obstruido")
    # A FULL transverse corridor sweep catches the central party-wall defect.
    from shapely.geometry import LineString
    passage=LineString([(3.25,13.0),(26.85,13.0)])
    if material.intersects(passage):
        errors.append("Eixo do corredor interrompido por paredes")
    for o in openings:
        if o.type == "window" and o.axis == "v" and o.wall_coord==27:
            if not (o.end <= STAIR[1] or o.start >= STAIR[3]):
                errors.append(o.id+": abre diretamente na caixa da escada")
    area_by_kind={}
    for s in spaces:
        x0,y0,x1,y1=s.rect
        if x1<=x0 or y1<=y0:
            errors.append(s.id+": dimensao invalida")
        area_by_kind[s.id]=round((x1-x0)*(y1-y0),2)
    return {"ok":not errors,"errors":errors,"wall_polygon_valid":material.is_valid,
            "wall_area_m2":round(material.area,3),"room_areas_m2":area_by_kind,
            "units":4,"doors":sum(op.type=="door" for op in openings),
            "windows":sum(op.type=="window" for op in openings),
            "scale":"1:125 at A3 100%",
            "scope":"geometric and graphical preliminary study only"}


def generate_multifamily_v3(output_dir: str | Path) -> dict:
    """Produce and gate the real DXF, A3 PDF and audit JSON in that order."""
    import ezdxf
    import matplotlib
    matplotlib.use("Agg",force=True)
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from ezdxf.addons.drawing import Frontend,RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    material,raw,openings,spaces=_build_geometry()
    audit=audit_multifamily_internal(material,raw,openings,spaces)
    report=out/"auditoria_interna_v3.json"
    report.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    if not audit["ok"]:
        raise ArchitecturalValidationError("Planta interna REPROVADA: "+"; ".join(audit["errors"]))

    doc=ezdxf.new("R2013")
    doc.header["$INSUNITS"]=6 # metres
    for name,color in (("ARQ-PAREDES",7),("ARQ-PORTAS",3),
                       ("ARQ-JANELAS",4),("ARQ-ESCADA",6),
                       ("ARQ-MOBILIARIO",8),("ARQ-TEXTOS",7),
                       ("ARQ-IMPLANTACAO",9),("ARQ-COTAS",7)):
        doc.layers.new(name,dxfattribs={"color":color})
    m=doc.modelspace()
    def line(a,b,layer="ARQ-PAREDES",weight=18):
        m.add_line(a,b,dxfattribs={"layer":layer,"lineweight":weight})
    def rectangle(x1,y1,x2,y2,layer="ARQ-MOBILIARIO",weight=13):
        m.add_lwpolyline(((x1,y1),(x2,y1),(x2,y2),(x1,y2)),close=True,
                         dxfattribs={"layer":layer,"lineweight":weight})
    def label(s,x,y,size=.25,layer="ARQ-TEXTOS"):
        m.add_text(s,dxfattribs={"layer":layer,"height":size,
                                "insert":(x,y),"color":7})
    # The walls are a clean CSG union after openings are genuinely subtracted.
    components=list(material.geoms) if material.geom_type=="MultiPolygon" else [material]
    for poly in components:
        if poly.geom_type!="Polygon":
            continue
        for ring in [poly.exterior,*poly.interiors]:
            pts=list(ring.coords)[:-1]
            m.add_lwpolyline(pts,close=True,
                             dxfattribs={"layer":"ARQ-PAREDES","lineweight":35})
    for op in openings:
        if op.type=="window":
            # Three longitudinal glazing tracks anchored within the wall gap.
            if op.axis=="h":
                for dy in (-.055,0,.055):
                    line((op.start,op.wall_coord+dy),
                         (op.end,op.wall_coord+dy),"ARQ-JANELAS",25)
                for x in (op.start,op.end):
                    line((x,op.wall_coord-.10),(x,op.wall_coord+.10),"ARQ-JANELAS",18)
            else:
                for dx in (-.055,0,.055):
                    line((op.wall_coord+dx,op.start),
                         (op.wall_coord+dx,op.end),"ARQ-JANELAS",25)
                for y in (op.start,op.end):
                    line((op.wall_coord-.10,y),(op.wall_coord+.10,y),"ARQ-JANELAS",18)
        else:
            # Swing leaf is a 4cm-thick closed CAD element, not a loose line.
            # Each hinge is explicitly on its actual door opening jamb.
            if op.axis=="h":
                x,y=op.start,op.wall_coord
                sign=op.side
                rectangle(x-.02,min(y,y+sign*op.width),x+.02,max(y,y+sign*op.width),
                          "ARQ-PORTAS",35)
                start,end=(0,90) if sign>0 else (270,360)
                line((x,y-.11),(x,y+.11),"ARQ-PORTAS",35)
                line((op.end,y-.11),(op.end,y+.11),"ARQ-PORTAS",35)
            else:
                x,y=op.wall_coord,op.start
                sign=op.side
                rectangle(min(x,x+sign*op.width),y-.02,max(x,x+sign*op.width),y+.02,
                          "ARQ-PORTAS",35)
                start,end=(0,90) if sign>0 else (90,180)
                line((x-.11,y),(x+.11,y),"ARQ-PORTAS",35)
                line((x-.11,op.end),(x+.11,op.end),"ARQ-PORTAS",35)
            m.add_arc((x,y),op.width,start,end,
                      dxfattribs={"layer":"ARQ-PORTAS","lineweight":13})
    # Rooms, furnishings and wet fixtures, kept clear of door hinge zones.
    for s in spaces:
        if s.unit=="common":
            continue
        x0,y0,x1,y1=s.rect
        cx=(x0+x1)/2; cy=(y0+y1)/2
        if s.kind=="sala_cozinha":
            label(s.unit+"  SALA / COZINHA",x0+.55,cy+.18,.30)
            rectangle(x0+.65,y0+.45,x0+3.6,y0+.95)
            rectangle(x1-3.4,y1-.75,x1-.7,y1-.3)
            rectangle(x0+5.3,cy-.7,x0+6.7,cy+.2)
        elif s.kind=="quarto":
            label("QUARTO 1" if "quarto1" in s.id else "QUARTO 2",x0+.5,y1-.65,.24)
            rectangle(x0+.6,y0+.65,x0+2.0,y0+2.55)
            rectangle(x0+.71,y0+2.15,x0+1.89,y0+2.46)
        elif s.kind=="banheiro":
            label("BANHO",x0+.30,y1-.55,.21)
            m.add_circle((x0+.45,y0+.75),.24,
                         dxfattribs={"layer":"ARQ-MOBILIARIO"})
            rectangle(x0+1.18,y0+.40,x0+1.8,y0+.99)
        elif s.kind=="servico":
            label("SERVICO",x0+.22,y1-.55,.21)
            rectangle(x0+.3,y0+.55,x0+1.05,y0+1.25)
            m.add_circle((x0+.67,y0+.9),.22,
                         dxfattribs={"layer":"ARQ-MOBILIARIO"})
    label("CIRCULACAO COMUM | 2,00 m",10.0,13.05,.32)
    # Stair annex with two actual drawn flights, treads and turn landing.
    sx0,sy0,sx1,sy1=STAIR
    for i in range(8):
        y=10.9+i*.27
        line((27.35,y),(28.5,y),"ARQ-ESCADA",25)
        line((29.0,y),(30.15,y),"ARQ-ESCADA",25)
    line((28.75,10.86),(28.75,15.14),"ARQ-ESCADA",25)
    rectangle(27.35,13.25,30.15,14.03,"ARQ-ESCADA",13)
    label("SOBE",27.55,11.15,.23)
    label("ESCADA",27.8,15.8,.29)
    # Arrow indicating ascending direction.
    line((28.30,11.0),(28.30,12.75),"ARQ-ESCADA",25)
    line((28.30,12.75),(28.10,12.49),"ARQ-ESCADA",25)
    line((28.30,12.75),(28.50,12.49),"ARQ-ESCADA",25)
    # Lot boundary and building placement are both CAD layers.
    x0,y0,x1,y1=SITE
    rectangle(x0,y0,x1,y1,"ARQ-IMPLANTACAO",13)
    label("LOTE HIPOTETICO 32,00 x 26,00 m",.6,25.1,.37)
    label("PROJECAO EDIFICADA 24,00 x 18,00 m",3.3,22.65,.28)
    label("RECUOS: A CONFERIR COM LEVANTAMENTO E LEGISLACAO",.6,.9,.24)
    for a,b in [((3,3),(27,3)),((2.4,4),(2.4,22))]:
        line(a,b,"ARQ-COTAS",18)
    label("24,00 m",13.7,2.55,.28)
    label("18,00 m",1.22,12.6,.28)
    # AUDIT: verify CAD geometry did not produce invalid ezdxf entities.
    dxf_audit=doc.audit()
    if dxf_audit.has_errors:
        raise ArchitecturalValidationError("DXF estruturalmente invalido: "+str(len(dxf_audit.errors)))
    audit["dxf_audit_errors"]=len(dxf_audit.errors)
    audit["geometry_primitives"]={
        "wall_loops":len(m.query('LWPOLYLINE')),
        "door_arcs":len(m.query('ARC')),
        "window_lines":sum(1 for e in m.query('LINE') if e.dxf.layer=='ARQ-JANELAS'),
    }
    if audit["geometry_primitives"]["door_arcs"] != audit["doors"]:
        raise ArchitecturalValidationError("Quantidade de arcos e portas nao coincide")
    # CAD sheet with border / title block in true A3 paper layout (mm).
    sheet=doc.layouts.new("ARQ-01 A3")
    sheet.page_setup(size=(420,297),margins=(8,8,8,8),units="mm")
    def paperline(a,b):
        sheet.add_line(a,b,dxfattribs={"layer":"ARQ-TEXTOS","lineweight":25})
    def papertext(s,x,y,h=2.8):
        sheet.add_text(s,dxfattribs={"insert":(x,y),"height":h,"layer":"ARQ-TEXTOS"})
    for a,b in [((8,8),(412,8)),((412,8),(412,289)),
                ((412,289),(8,289)),((8,289),(8,8)),
                ((290,8),(290,289)),((290,66),(412,66)),
                ((290,115),(412,115)),((290,180),(412,180))]:
        paperline(a,b)
    papertext("MCP CAD CLOUD / ESTUDO PRELIMINAR",298,275,4.2)
    papertext("PAVIMENTO MULTIFAMILIAR",298,257,4.0)
    papertext("4 UNIDADES / 2 QUARTOS",298,244,3.2)
    papertext("CARIMBO - ARQ-01",298,165,4.0)
    papertext("LOCAL: NAO INFORMADO",298,148)
    papertext("RESPONSAVEL: NAO INFORMADO",298,138)
    papertext("AREA TERRENO HIPOT.: 832 m2",298,129)
    papertext("FORMATO A3 | ESCALA 1:125",298,103,3.2)
    papertext("REVISAO: 03 | DATA: 2026-11-01",298,90,3.0)
    papertext("SEM APROVACAO NORMATIVA",298,52,3.2)
    papertext("NAO UTILIZAR PARA EXECUCAO",298,39,3.2)
    # Paper-space viewport is an actual DXF VIEWPORT, not a screenshot.
    sheet.add_viewport(center=(149,148),size=(265,220),
                       view_center_point=(16,13),view_height=27.5,status=2)
    dxf=out/"multifamiliar_validacao_interna_v3.dxf"
    pdf=out/"multifamiliar_validacao_interna_v3_A3.pdf"
    doc.saveas(dxf)

    # PDF rendered from the SAME modelspace entities, with geometric A3 scaling.
    fig=Figure(figsize=(420/25.4,297/25.4),facecolor="white")
    ax=fig.add_axes([16/420,43/297,265/420,220/297])
    ax.set_axis_off()
    props=LayoutProperties.from_layout(m)
    props.set_colors("#FFFFFF","#161B22")
    Frontend(RenderContext(doc),MatplotlibBackend(ax)).draw_layout(
        m,finalize=False,layout_properties=props)
    ax.set_xlim(-.5625,32.5625)
    ax.set_ylim(-.75,26.75)
    ax.set_aspect("equal",adjustable="box")
    # Overlay mirrors the real CAD paper-space carimbo; no invented personnel.
    def rule(x1,y1,x2,y2,width=.75):
        fig.add_artist(Line2D((x1,x2),(y1,y2),transform=fig.transFigure,
                              color="#253442",linewidth=width))
    fig.add_artist(Rectangle((8/420,8/297),404/420,281/297,
                             fill=False,transform=fig.transFigure,
                             edgecolor="#253442",linewidth=1))
    for yy in (42,67,118,180,257):
        rule(294/420,yy/297,411/420,yy/297)
    rule(294/420,8/297,294/420,289/297)
    fig.text(299/420,272/297,"MCP CAD CLOUD",fontsize=14,weight="bold",color="#172B39")
    fig.text(299/420,258/297,"PAVIMENTO MULTIFAMILIAR",fontsize=10,weight="bold")
    fig.text(299/420,249/297,"4 UNIDADES | 2 QUARTOS CADA",fontsize=8.5)
    fig.text(299/420,232/297,"ESTUDO PRELIMINAR",fontsize=9,weight="bold")
    fig.text(299/420,219/297,"Planta interna submetida a auditoria",fontsize=8)
    fig.text(299/420,208/297,"geometrica e de conectividade.",fontsize=8)
    fig.text(299/420,188/297,"ARQ-01  |  REVISAO 03",fontsize=9.5,weight="bold")
    fig.text(299/420,164/297,"TERRENO: 32,00 x 26,00 m *",fontsize=9)
    fig.text(299/420,153/297,"EDIFICACAO: 24,00 x 18,00 m",fontsize=9)
    fig.text(299/420,142/297,"LOCAL: NAO INFORMADO",fontsize=8.2)
    fig.text(299/420,131/297,"RESPONSAVEL: NAO INFORMADO",fontsize=8.2)
    fig.text(299/420,122/297,"* Terreno apenas hipotetico",fontsize=7.5)
    fig.text(299/420,101/297,"ESCALA: 1:125  (IMPRESSAO 100%)",fontsize=8.5)
    fig.text(299/420,88/297,"FORMATO: A3 | REVISAO: 03",fontsize=8.5)
    fig.text(299/420,77/297,"EMISSAO: 01/11/2026",fontsize=8)
    fig.text(299/420,54/297,"SEM VALIDACAO NORMATIVA",fontsize=8.5,weight="bold")
    fig.text(299/420,31/297,"NAO UTILIZAR PARA EXECUCAO",fontsize=8.5,weight="bold")
    fig.text(19/420,25/297,"PLANTA DE PAVIMENTO | LIMITES DO TERRENO / ESCADA / AMBIENTES",fontsize=8.5)
    fig.savefig(pdf,format="pdf",dpi=200)
    fig.clear()
    if not pdf.read_bytes().startswith(b"%PDF-"):
        raise ArchitecturalValidationError("Renderizacao do PDF falhou")
    audit["pdf_a3_file_bytes"]=pdf.stat().st_size
    audit["status"]="geometry_preliminarily_approved_not_code_approved"
    report.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"status":audit["status"],"dxf":str(dxf),"pdf":str(pdf),"audit":str(report)}


if __name__=="__main__":
    import sys
    print(json.dumps(generate_multifamily_v3(sys.argv[1] if len(sys.argv)>1 else "."),indent=2))