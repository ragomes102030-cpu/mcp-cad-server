"""Revisao 04: detailing the verified V3 architectural DXF, not redrawing it.

The real ezdxf modelspace is preserved. CAD layers contain dimension chains,
room area labels, kitchen/bath/utility equipment and demonstrative north arrow.
The A3 PDF renders the same DXF. Areas are gross rectangular approximations;
this is not a code-compliance or permit-ready architectural project.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

class ArchitecturalDetailError(ValueError):
    """Detailed CAD drawing failed geometric or representation preflight."""

@dataclass(frozen=True)
class Room:
    uid: str
    kind: str
    rect: tuple[float,float,float,float]

    @property
    def gross_area(self) -> float:
        x0,y0,x1,y1=self.rect
        return round((x1-x0)*(y1-y0),2)

def _room_program() -> list[Room]:
    rooms=[]
    for row in range(2):
        y_bed,y_living=(4.,(8.5,11.9)) if row==0 else (17.5,(14.1,17.5))
        for col in range(2):
            x0=3.+12.*col
            uid=f"AP{row*2+col+1:02d}"
            y1=y_bed+4.5
            rooms.extend((
                Room(uid,'sala_cozinha',(x0,y_living[0],x0+12.,y_living[1])),
                Room(uid,'quarto1',(x0,y_bed,x0+4.,y1)),
                Room(uid,'quarto2',(x0+4.,y_bed,x0+8.,y1)),
                Room(uid,'banheiro',(x0+8.,y_bed,x0+10.2,y1)),
                Room(uid,'servico',(x0+10.2,y_bed,x0+12.,y1)),
            ))
    return rooms

def _preflight_baseline(doc) -> None:
    m=doc.modelspace()
    if 'ARQ-01 A3' not in doc.layouts:
        raise ArchitecturalDetailError('Base V3 sem prancha A3 CAD')
    if len(m.query('ARC'))!=21:
        raise ArchitecturalDetailError('Base V3 com quantidade incorreta de portas')
    wall_loops=[e for e in m.query('LWPOLYLINE') if e.dxf.layer=='ARQ-PAREDES']
    win_lines=[e for e in m.query('LINE') if e.dxf.layer=='ARQ-JANELAS']
    if not wall_loops or len(win_lines)<60:
        raise ArchitecturalDetailError('Paredes ou janelas V3 incompletas')
    if not any(('TERRENO' in e.dxf.text.upper() or 'LOTE HIPOTETICO' in e.dxf.text.upper())
               for e in m.query('TEXT')):
        raise ArchitecturalDetailError('Marcacao do terreno ausente')

def generate_multifamily_v4(output_dir: str | Path, *,
                            base_dxf: str | Path | None = None) -> dict[str,Any]:
    """Generate DXF/A3 from verified V3 geometry, with extra CAD layer QA."""
    import ezdxf
    import matplotlib
    matplotlib.use('Agg',force=True)
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from ezdxf.addons.drawing import Frontend,RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties
    from shapely.geometry import box,LineString
    from shapely.ops import unary_union
    import math

    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    if base_dxf is None:
        from .multifamiliar_arch_v3 import generate_multifamily_v3
        result=generate_multifamily_v3(out/'base_v3')
        if result['status']!='geometry_preliminarily_approved_not_code_approved':
            raise ArchitecturalDetailError('Baseline V3 nao aprovada')
        base_dxf=result['dxf']
    doc=ezdxf.readfile(str(base_dxf))
    _preflight_baseline(doc)
    msp=doc.modelspace()
    for lname,color,weight in (
        ('ARQ-COTAS-INTERNAS',7,13),('ARQ-AREAS',7,13),
        ('ARQ-DETALHES',8,13),('ARQ-SIMBOLOS',5,18)):
        if lname not in doc.layers:
            doc.layers.new(lname,dxfattribs={'color':color,'lineweight':weight})

    def line(x0,y0,x1,y1,layer='ARQ-DETALHES',lw=13):
        return msp.add_line((x0,y0),(x1,y1),dxfattribs={'layer':layer,'lineweight':lw})
    def rect(x0,y0,x1,y1,layer='ARQ-DETALHES'):
        return msp.add_lwpolyline(((x0,y0),(x1,y0),(x1,y1),(x0,y1)),
                                  close=True,dxfattribs={'layer':layer,'lineweight':13})
    def txt(label,x,y,height=.21,layer='ARQ-AREAS'):
        return msp.add_text(label,dxfattribs={'insert':(x,y),'height':height,'layer':layer})

    # Original wall contours and door arcs are the authoritative CAD source.
    boundaries=[]
    for e in msp.query('LWPOLYLINE'):
        if e.dxf.layer=='ARQ-PAREDES':
            xy=list(e.get_points('xy'))
            if len(xy)>=3:
                boundaries.append(LineString(xy+[xy[0]]))
    wall_edges=unary_union(boundaries)
    door_sweeps=[]
    for arc in msp.query('ARC'):
        if arc.dxf.layer!='ARQ-PORTAS':
            continue
        a=float(arc.dxf.start_angle);b=float(arc.dxf.end_angle)
        if b<a:b+=360.
        cx,cy=arc.dxf.center.x,arc.dxf.center.y
        rad=float(arc.dxf.radius)
        pts=[(cx+rad*math.cos(math.radians(a+(b-a)*i/15)),
              cy+rad*math.sin(math.radians(a+(b-a)*i/15))) for i in range(16)]
        door_sweeps.append(LineString(pts).buffer(.08))
    forbidden=unary_union(door_sweeps)

    rooms=_room_program()
    placed=[];errors=[]
    for room in rooms:
        x0,y0,x1,y1=room.rect
        inner=box(x0+.18,y0+.18,x1-.18,y1-.18)
        if room.kind in ('quarto1','quarto2'):
            new=[('guarda-roupa',(x1-.69,y0+2.25,x1-.30,y0+3.75))]
        elif room.kind=='banheiro':
            new=[('box-banho',(x0+.22,y0+1.55,x0+1.19,y0+2.52))]
        elif room.kind=='servico':
            new=[('tanque',(x0+.33,y0+1.65,x0+1.20,y0+2.32))]
        else:
            new=[('bancada-cozinha',(x1-3.10,y0+.43,x1-.66,y0+.93))]
        for name,coords in new:
            obj=box(*coords)
            if not inner.covers(obj):
                errors.append(f'{room.uid}/{name}: fora do ambiente')
            if obj.buffer(.02).intersects(wall_edges):
                errors.append(f'{room.uid}/{name}: colide com parede')
            if obj.intersects(forbidden):
                errors.append(f'{room.uid}/{name}: interfere na porta')
            placed.append((room.uid,room.kind,name,coords))
        label_x=x0+.60 if room.kind=='sala_cozinha' else x0+.27
        label_y=(y0+y1)/2-.35 if room.kind=='sala_cozinha' else y1-1.06
        txt(f'{room.gross_area:.1f} m2 (BR.)',label_x,label_y,.185)
    if errors:
        raise ArchitecturalDetailError('QA de mobiliario recusou V4: '+'; '.join(errors))

    for uid,kind,name,(x0,y0,x1,y1) in placed:
        rect(x0,y0,x1,y1)
        if name=='box-banho':
            line(x0,y0,x1,y1)
            txt('BOX',x0+.17,(y0+y1)/2,.14,'ARQ-DETALHES')
        elif name=='tanque':
            rect(x0+.07,y0+.08,x1-.07,y1-.08)
            msp.add_circle(((x0+x1)/2,(y0+y1)/2),.09,
                           dxfattribs={'layer':'ARQ-DETALHES'})
        elif name=='bancada-cozinha':
            rect(x0+.18,y0+.08,x0+.91,y1-.09)
            msp.add_circle((x0+.55,(y0+y1)/2),.07,
                           dxfattribs={'layer':'ARQ-DETALHES'})
            for cx in (x1-.53,x1-.26):
                msp.add_circle((cx,(y0+y1)/2),.075,
                               dxfattribs={'layer':'ARQ-DETALHES'})
        elif name=='guarda-roupa':
            line((x0+x1)/2,y0,(x0+x1)/2,y1)

    chain=[3.,7.,11.,13.2,15.,19.,23.,25.2,27.]
    dim_y=3.32
    line(chain[0],dim_y,chain[-1],dim_y,'ARQ-COTAS-INTERNAS')
    for xx in chain:
        line(xx,dim_y-.10,xx,dim_y+.10,'ARQ-COTAS-INTERNAS')
    for lo,hi in zip(chain,chain[1:]):
        txt(f'{hi-lo:.2f}',(lo+hi)/2-.24,dim_y+.12,.17,'ARQ-COTAS-INTERNAS')
    chain_y=[4.,8.5,11.9,14.1,17.5,22.]
    xx=2.03
    line(xx,chain_y[0],xx,chain_y[-1],'ARQ-COTAS-INTERNAS')
    for yy in chain_y:
        line(xx-.09,yy,xx+.09,yy,'ARQ-COTAS-INTERNAS')
    for lo,hi in zip(chain_y,chain_y[1:]):
        if hi-lo<2.3:continue
        txt(f'{hi-lo:.2f}',xx-.53,(lo+hi)/2,.19,'ARQ-COTAS-INTERNAS')
    txt('16 PISOS ESQUEMATICOS',27.12,16.55,.195,'ARQ-SIMBOLOS')
    txt('ALTURA A VERIFICAR',27.15,16.22,.19,'ARQ-SIMBOLOS')
    nx,ny=29.45,23.85
    line(nx,ny-.66,nx,ny+.45,'ARQ-SIMBOLOS',25)
    msp.add_solid([(nx,ny+.79),(nx-.24,ny+.36),(nx+.24,ny+.36)],
                  dxfattribs={'layer':'ARQ-SIMBOLOS'})
    txt('N*',nx-.20,ny+1.,.35,'ARQ-SIMBOLOS')
    txt('* NORTE ILUSTRATIVO',23.8,24.95,.21,'ARQ-SIMBOLOS')

    ca=doc.audit()
    if ca.has_errors:
        raise ArchitecturalDetailError(f'DXF V4 inconsistente: {len(ca.errors)} erros')
    dxf=out/'multifamiliar_detalhamento_v4.dxf'
    pdf=out/'multifamiliar_detalhamento_v4_A3.pdf'
    report=out/'auditoria_detalhamento_v4.json'

    # The DXF paper space has a real CAD-editable A3 title block and viewport.
    sheet=doc.layouts.new('ARQ-01 A3 REV04')
    sheet.page_setup(size=(420,297),margins=(8,8,8,8),units='mm')
    def pline(x0,y0,x1,y1):
        sheet.add_line((x0,y0),(x1,y1),dxfattribs={'layer':'ARQ-TEXTOS'})
    def ptext(s,x,y,h=2.5):
        sheet.add_text(s,dxfattribs={'layer':'ARQ-TEXTOS','insert':(x,y),'height':h})
    for a,b,c,d in ((8,8,412,8),(412,8,412,289),(412,289,8,289),
                    (8,289,8,8),(294,8,294,289)):
        pline(a,b,c,d)
    for y in (42,67,118,180,257):
        pline(294,y,412,y)
    ptext('MCP CAD CLOUD | REVISAO 04',298,273,4.2)
    ptext('PAVIMENTO MULTIFAMILIAR',298,263,3)
    ptext('AREAS BRUTAS INDICATIVAS',298,235,2.8)
    for i in range(4):
        ptext(f'AP{i+1:02d}: 94,80 m2 BRUTOS',298,223-i*11,2.6)
    ptext('LOTE HIPOTETICO: 32 x 26 m',298,166,2.6)
    ptext('EDIFICACAO: 24 x 18 m',298,155,2.6)
    ptext('ESCADA: DIMENSIONAR',298,143,2.6)
    ptext('NORTE: ILUSTRATIVO',298,132,2.6)
    ptext('FORMATO A3 | ESCALA 1:125',298,102,2.7)
    ptext('RESPONSAVEL: NAO INFORMADO',298,89,2.5)
    ptext('NAO UTILIZAR PARA EXECUCAO',298,29,3)
    sheet.add_viewport(center=(149,148),size=(265,220),
                       view_center_point=(16,13),view_height=27.5,status=2)
    doc.saveas(dxf)

    # Render the real resulting modelspace, never a manually drawn image.
    fig=Figure(figsize=(420/25.4,297/25.4),facecolor='white')
    ax=fig.add_axes([16/420,43/297,265/420,220/297])
    ax.set_axis_off()
    props=LayoutProperties.from_layout(msp)
    props.set_colors('#FFFFFF','#17202B')
    Frontend(RenderContext(doc),MatplotlibBackend(ax)).draw_layout(
        msp,finalize=False,layout_properties=props)
    ax.set_xlim(-.5625,32.5625)
    ax.set_ylim(-.75,26.75)
    ax.set_aspect('equal',adjustable='box')
    def rule(x0,y0,x1,y1,lw=.8):
        fig.add_artist(Line2D((x0/420,x1/420),(y0/297,y1/297),
                              transform=fig.transFigure,color='#263948',linewidth=lw))
    fig.add_artist(Rectangle((8/420,8/297),404/420,281/297,
                             fill=False,transform=fig.transFigure,
                             edgecolor='#263948',linewidth=1))
    rule(294,8,294,289)
    for y in (42,67,118,180,257):
        rule(294,y,412,y)
    def ft(s,x,y,size=8,bold=False):
        fig.text(x/420,y/297,s,fontsize=size,weight='bold' if bold else 'normal',
                 color='#1B2936')
    ft('MCP CAD CLOUD',299,276,14,True)
    ft('PAVIMENTO MULTIFAMILIAR',299,264,9,True)
    ft('REVISAO 04 | DETALHAMENTO',299,247,9.5,True)
    ft('QUADRO DE AREAS - BRUTAS',299,235,8,True)
    for i in range(4):
        ft(f'AP{i+1:02d}   94,80 m2 (aprox.)',299,222-i*10.5,8.5)
    ft('TERRENO HIPOTETICO: 32,00 x 26,00 m',299,165,8)
    ft('PROJECAO: 24,00 x 18,00 m',299,152,8)
    ft('NORTE ILUSTRATIVO; RECUOS A VERIFICAR',299,139,7.4)
    ft('ESCADA: DIMENSIONAMENTO PENDENTE',299,126,7.7,True)
    ft('A3   |   ESCALA: 1:125 (100%)',299,102,8.5,True)
    ft('RESPONSAVEL: NAO INFORMADO',299,87,7.7)
    ft('EMISSAO: 01/11/2026',299,76,7.7)
    ft('LEGENDA: BR. = AREA GEOMETRICA BRUTA',299,55,7.4)
    ft('NAO UTILIZAR PARA EXECUCAO',299,31,9,True)
    ft('SEM VALIDACAO NORMATIVA',299,19,8,True)
    ft('ARQ-01  |  PAVIMENTO TIPO  |  COTAS EM METROS',19,25,8.3)
    fig.savefig(pdf,format='pdf',dpi=200)
    fig.clear()
    if not pdf.read_bytes().startswith(b'%PDF-'):
        raise ArchitecturalDetailError('PDF nao foi renderizado')

    qa={
        'status':'v4_detailed_preliminary_not_normatively_approved',
        'approved_for':'architectural preliminary study only',
        'room_count':len(rooms),'unit_count':4,
        'gross_area_each_unit_m2':94.8,
        'area_basis':'gross geometric rectangles including wall zones, NOT usable area',
        'additional_fixture_count':len(placed),'existing_door_arcs':len(door_sweeps),
        'dimension_segments':len(chain)-1+len(chain_y)-1,
        'dxf_audit_errors':len(ca.errors),'furniture_collision_errors':errors,
        'assumptions':['hypothetical site','illustrative north',
            'stair has no verified riser/landing calculations',
            'fire and accessibility not validated'],
        'pdf_bytes':pdf.stat().st_size
    }
    report.write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
    return {'status':qa['status'],'dxf':str(dxf),'pdf':str(pdf),'audit':str(report)}

if __name__=='__main__':
    import sys
    print(json.dumps(generate_multifamily_v4(
        sys.argv[1] if len(sys.argv)>1 else '.',
        base_dxf=sys.argv[2] if len(sys.argv)>2 else None),indent=2))
