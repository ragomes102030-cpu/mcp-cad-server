"""Architectural V2 pilot drawn as actual ezdxf entities and rendered from DXF.

Dimensions in metres. Four mirrored two-bedroom units, shared corridor and
external stair annex. This is an architectural study, not permit-ready.
"""
from __future__ import annotations

from pathlib import Path
from math import pi, sin, cos


def generate_multifamily_architectural_v2(output_dir: str | Path) -> dict:
    import ezdxf
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.figure import Figure
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2013")
    layers = {"WALL":7, "DOOR":3, "WINDOW":4, "STAIR":6,
              "FURNITURE":8, "LABEL":7, "DIM":7}
    for name, color in layers.items():
        doc.layers.new(name, dxfattribs={"color":color})
    m = doc.modelspace()
    def line(x1,y1,x2,y2,layer="WALL"):
        m.add_line((x1,y1),(x2,y2),dxfattribs={"layer":layer})
    def rect(x,y,w,h,layer="WALL"):
        for a,b,c,d in ((x,y,x+w,y),(x+w,y,x+w,y+h),
                        (x+w,y+h,x,y+h),(x,y+h,x,y)):
            line(a,b,c,d,layer)
    def text(s,x,y,h=.22):
        m.add_text(s,dxfattribs={"height":h,"insert":(x,y),"layer":"LABEL"})
    def wall_h(x1,x2,y,gaps=(),t=.14):
        intervals=sorted((max(x1,a),min(x2,b)) for a,b in gaps if a<x2 and b>x1)
        cursor=x1
        for a,b in intervals+[(x2,x2)]:
            if a>cursor+.001: rect(cursor,y-t/2,a-cursor,t)
            cursor=max(cursor,b)
    def wall_v(x,y1,y2,gaps=(),t=.14):
        intervals=sorted((max(y1,a),min(y2,b)) for a,b in gaps if a<y2 and b>y1)
        cursor=y1
        for a,b in intervals+[(y2,y2)]:
            if a>cursor+.001: rect(x-t/2,cursor,t,a-cursor)
            cursor=max(cursor,b)
    def door(x,y,hinge,vertical=False,flip=False,w=.85):
        # Leaf and quarter-circle swing are real CAD entities.
        if vertical:
            line(x,y,x+(w if not flip else -w),y,"DOOR")
            m.add_arc((x,y),w,0 if not flip else 90,90 if not flip else 180,
                      dxfattribs={"layer":"DOOR"})
        else:
            line(x,y,x,y+(w if not flip else -w),"DOOR")
            m.add_arc((x,y),w,0 if not flip else 270,90 if not flip else 360,
                      dxfattribs={"layer":"DOOR"})
    def window_h(x,y,w=1.5):
        for yy in (y-.045,y+.045):line(x,yy,x+w,yy,"WINDOW")
        line(x,y-.10,x,y+.10,"WINDOW");line(x+w,y-.10,x+w,y+.10,"WINDOW")
    def bed(x,y):
        rect(x,y,1.40,1.90,"FURNITURE")
        rect(x+.08,y+1.45,1.24,.35,"FURNITURE")
    def bathroom(x,y):
        m.add_circle((x+.5,y+.50),.25,dxfattribs={"layer":"FURNITURE"})
        rect(x+1.3,y+.2,.65,.5,"FURNITURE")
        rect(x+.2,y+1.05,.85,.55,"FURNITURE")
    # Footprint: 24x18m, two 8m-deep apartment bands and 2m corridor.
    # Stairs occupy a separate 4x4m annex, keeping the corridor unobstructed.
    wall_h(0,24,0,[(2.4,3.9),(8.4,9.9),(14.4,15.9),(20.4,21.9)])
    wall_h(0,24,18,[(2.4,3.9),(8.4,9.9),(14.4,15.9),(20.4,21.9)])
    wall_v(0,0,18)
    wall_v(24,0,18,[(7,11)])
    wall_v(12,0,18)
    wall_h(0,24,8,[(7.0,7.9),(19.0,19.9)])
    wall_h(0,24,10,[(7.0,7.9),(19.0,19.9)])
    for x in (7.0,19.0):
        door(x,8,0,flip=True,w=.9)
        door(x,10,0,flip=False,w=.9)
    # Four independent two-bedroom units. Living rooms face the shared hall.
    for row in range(2):
        y0=0 if row==0 else 10
        # living room strip near corridor: bottom row 5..8, top row 10..13
        living_y=y0+5 if row==0 else y0
        service_y=y0+3.25 if row==0 else y0+3
        bedrooms_y=y0 if row==0 else y0+5
        for col in range(2):
            x0=col*12
            uid=f"AP{row*2+col+1:02d}"
            # service band 3.25..5 or 13..15; bedroom band 0..3.25 / 15..18
            sep1=y0+3.25 if row==0 else y0+5
            sep2=y0+5 if row==0 else y0+3
            wall_h(x0,x0+12,sep1,[(x0+8.15,x0+9.0)])
            wall_h(x0,x0+12,sep2,[(x0+8.15,x0+9.0)])
            # two bedrooms, bathroom, laundry, private hall
            wall_v(x0+6,bedrooms_y,bedrooms_y+(3.25 if row==0 else 3),
                   [(bedrooms_y+1.15,bedrooms_y+2.0)])
            wall_v(x0+4.2,min(sep1,sep2),max(sep1,sep2),
                   [(min(sep1,sep2)+.5,min(sep1,sep2)+1.3)])
            wall_v(x0+6.7,min(sep1,sep2),max(sep1,sep2),
                   [(min(sep1,sep2)+.5,min(sep1,sep2)+1.3)])
            text(uid+" SALA / COZINHA",x0+1.1,living_y+1.5,.25)
            text("QUARTO 1",x0+.9,bedrooms_y+2.5)
            text("QUARTO 2",x0+6.8,bedrooms_y+2.5)
            text("BANHO",x0+.45,min(sep1,sep2)+.85,.18)
            text("SERV.",x0+4.45,min(sep1,sep2)+.85,.18)
            text("HALL",x0+8,min(sep1,sep2)+.85,.18)
            bed(x0+.7,bedrooms_y+.25)
            bed(x0+7.0,bedrooms_y+.25)
            bathroom(x0+.4,min(sep1,sep2)+.1)
            rect(x0+4.5,living_y+.35,3.2,.60,"FURNITURE")
            rect(x0+9,living_y+.6,1.5,.75,"FURNITURE")
            # doors to service/bedroom strip, drawn at actual gaps
            door(x0+8.15,sep1,0,w=.85)
            door(x0+8.15,sep2,0,w=.85)
            door(x0+6,bedrooms_y+1.15,0,vertical=True,w=.85)
            door(x0+4.2,min(sep1,sep2)+.5,0,vertical=True,w=.8)
            door(x0+6.7,min(sep1,sep2)+.5,0,vertical=True,w=.8)
            window_h(x0+2.4,y0 if row==0 else y0+8)
            window_h(x0+8.4,y0 if row==0 else y0+8)
    # Real stair flights in annex, independent of the 2m-wide corridor.
    rect(24,7,4,4)
    wall_v(24,7,11,[(8.0,9.1)])
    door(24,8.0,0,vertical=True,w=.9)
    wall_v(26,7.3,10.7)
    for i in range(9):
        yy=7.35+i*.36
        line(24.35,yy,25.75,yy,"STAIR")
        line(26.25,yy,27.65,yy,"STAIR")
    text("ESCADA - ESTUDO",24.2,11.35,.20)
    text("CIRCULACAO COMUM - 2.00 m",8.1,8.85,.28)
    # Dimensions and identification outside geometry.
    line(0,-.75,24,-.75,"DIM")
    for x in (0,12,24):
        line(x,-.95,x,-.5,"DIM")
    text("24.00 m",10.7,-1.25,.27)
    line(-.8,0,-.8,18,"DIM")
    text("18.00 m",-1.5,9,.25)
    audit=doc.audit()
    if audit.has_errors:
        raise RuntimeError(f"DXF audit found {len(audit.errors)} errors")
    dxf=out/"multifamiliar_arquitetonico_v2.dxf"
    pdf=out/"multifamiliar_arquitetonico_v2_A3.pdf"
    doc.saveas(dxf)
    fig=Figure(figsize=(420/25.4,297/25.4),facecolor="white")
    ax=fig.add_axes([.055,.17,.89,.69])
    ax.set_axis_off()
    props=LayoutProperties.from_layout(m)
    props.set_colors("#FFFFFF","#101820")
    Frontend(RenderContext(doc),MatplotlibBackend(ax)).draw_layout(
        m,finalize=False,layout_properties=props)
    ax.set_xlim(-2.1,29)
    ax.set_ylim(-2.0,19.5)
    ax.set_aspect("equal",adjustable="box")
    fig.text(.055,.925,"MCP CAD CLOUD | PAVIMENTO MULTIFAMILIAR - REVISAO 02",
             fontsize=16,weight="bold")
    fig.text(.055,.889,"4 apartamentos / 2 quartos por unidade / circulacao comum / escada",
             fontsize=10)
    fig.text(.055,.092,"ESTUDO PRELIMINAR A3 - NAO UTILIZAR PARA EXECUCAO",
             fontsize=10,weight="bold")
    fig.text(.055,.065,"Sem verificacao de acessibilidade, incendio, estrutura ou codigo de obras.",
             fontsize=8)
    fig.savefig(pdf,format="pdf")
    fig.clear()
    assert pdf.read_bytes().startswith(b"%PDF-")
    return {"pdf":str(pdf),"dxf":str(dxf),"status":"architectural_study_not_code_approved"}
