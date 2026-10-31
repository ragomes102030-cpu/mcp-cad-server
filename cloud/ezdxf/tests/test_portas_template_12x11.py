"""Regression: every 12x11 door swing must close along its actual wall gap."""
import math
import io
import ezdxf
import pytest

from mcp_cad_cloud.planta_assistida import build_assisted_model
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure


def _near(a,b,tol=0.002):
    return abs(a-b)<tol


def _is_physical_endpoint(x,y,segments):
    return any((_near(x,a) and _near(y,b)) or
               (_near(x,c) and _near(y,d))
               for a,b,c,d in segments)


def _closed_point(hinge,arc_start,leaf_angle,width):
    # The endpoint that is NOT the open leaf should lie at the opposite
    # end of the actual opening. A wrong quadrant will fail this test.
    other=(arc_start+90) % 360
    if _near((leaf_angle-arc_start)%360,90):
        other=arc_start
    return (hinge[0]+width*math.cos(math.radians(other)),
            hinge[1]+width*math.sin(math.radians(other)))


def test_all_11_template_door_arcs_close_into_real_wall_openings():
    model=build_assisted_model()
    assert len(model["portas"])==11
    for i,(x,y,ang,width) in enumerate(model["portas"]):
        leaf_angle=model.get("portas_folhas",[ang]*11)[i] if i<len(model.get("portas_folhas",[])) else ang
        end=_closed_point((x,y),ang,leaf_angle,width)
        assert _is_physical_endpoint(x,y,model["paredes"]),("hinge",i,(x,y))
        assert _is_physical_endpoint(*end,model["paredes"]),("closed leaf",i,end)
        # The leaf is perpendicular to the closed direction at one endpoint.
        open_dir=math.radians(leaf_angle)
        closed_dir=math.atan2(end[1]-y,end[0]-x)
        assert abs(math.cos(open_dir-closed_dir))<1e-6,("angle",i)


def test_real_dxf_preserves_all_eleven_arcs_and_parallel_leaf_strokes():
    preview=cad.planta_criar_validada(template="residencia_unifamiliar_12x11",modo="preview")
    assert preview["ok"]
    drawn=cad.planta_criar_validada(template="residencia_unifamiliar_12x11",
        modo="desenhar",preview_token=preview["preview_token"])
    assert drawn["ok"],drawn
    buffer=io.StringIO()
    _ensure().write(buffer)
    doc=ezdxf.read(io.StringIO(buffer.getvalue()))
    msp=doc.modelspace()
    assert len(msp.query('ARC[layer=="PORTAS"]'))==11
    assert len(msp.query('LINE[layer=="PORTAS"]'))==11
    assert len(msp.query('LINE[layer=="PORTAS-DETALHE"]'))==33
    assert not doc.audit().has_errors
