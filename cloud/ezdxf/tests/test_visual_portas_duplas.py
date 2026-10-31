"""CAD visual hierarchy and genuinely double door leaves in exported DXF."""
import io
from math import hypot

import ezdxf
import pytest

from test_layout_compacto import CASA
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure
from mcp_cad_cloud.topologia_paredes import auditar_paredes_e_vaos_dxf


def test_professional_palette_and_double_leaf_from_dxf():
    p=cad.planta_criar_validada(programa=CASA,template="programa_sob_medida",modo="preview")
    assert p["ok"]
    result=cad.planta_criar_validada(programa=CASA,template="programa_sob_medida",
                                   modo="desenhar",preview_token=p["preview_token"])
    assert result["ok"],result
    buffer=io.StringIO()
    _ensure().write(buffer)
    doc=ezdxf.read(io.StringIO(buffer.getvalue()))
    msp=doc.modelspace()
    physical=list(msp.query('LINE[layer=="PORTAS"]'))
    decorative=list(msp.query('LINE[layer=="PORTAS-DETALHE"]'))
    arcs=list(msp.query('ARC[layer=="PORTAS"]'))
    assert len(physical)==len(decorative)==len(arcs)==5
    for layer in ("PAREDES","PORTAS","PORTAS-DETALHE","JANELAS","MOBILIARIO","COTAS","TEXTOS"):
        assert doc.layers.get(layer).dxf.hasattr("true_color")
        assert doc.layers.get(layer).dxf.lineweight>0
    assert doc.layers.get("PAREDES").dxf.lineweight>doc.layers.get("MOBILIARIO").dxf.lineweight
    for leaf in physical:
        a,b=leaf.dxf.start,leaf.dxf.end
        direction=(b.x-a.x,b.y-a.y)
        length=hypot(*direction)
        matches=[]
        for sec in decorative:
            x,y=sec.dxf.start,sec.dxf.end
            vector=(y.x-x.x,y.y-x.y)
            if abs(vector[0]-direction[0])<1e-7 and abs(vector[1]-direction[1])<1e-7:
                delta=(x.x-a.x,x.y-a.y)
                if abs(hypot(*delta)-.035)<1e-6 and abs(delta[0]*direction[0]+delta[1]*direction[1])<1e-7:
                    matches.append(sec)
        assert len(matches)==1
    topology=auditar_paredes_e_vaos_dxf(doc)
    assert topology["ok"],topology["erros"]
    assert topology["resumo"]["portas"]==5
    assert not doc.audit().has_errors
