# -*- coding: utf-8 -*-
"""Testa UMA lacuna do COM por vez (uso: python3 sonda_lacuna.py <nome>)."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from cad_mcp.backend_manager import BackendManager  # noqa


async def principal(qual):
    m = BackendManager("auto")
    b = await m.get()
    print("backend:", b.name)
    r = None
    if qual == "ellipse":
        r = await b.create_ellipse(10, 10, 6, 0, 0.5, layer="LAC")
    elif qual == "dimangular":
        r = await b.create_dimension_angular(0, 0, 5, 0, 0, 5)
    elif qual == "dimradius":
        c = await b.create_circle(30, 10, 4, layer="LAC")
        print("  circulo:", c.to_dict())
        r = await b.create_dimension_radius(30, 10, 4, 30.0)
    elif qual == "scale":
        l = await b.create_line(0, 0, 10, 0, layer="LAC")
        h = l.to_dict().get("payload")
        print("  linha:", h)
        r = await b.entity_scale(h, 0, 0, 2.0)
    elif qual == "chamfer":
        l1 = (await b.create_line(50, 0, 60, 0, layer="LAC")).to_dict().get("payload")
        l2 = (await b.create_line(60, 0, 60, 10, layer="LAC")).to_dict().get("payload")
        print("  linhas:", l1, l2)
        r = await b.entity_chamfer(l1, l2, 1.0, 1.0)
    elif qual == "array":
        l = await b.create_line(0, 0, 10, 0, layer="LAC")
        h = l.to_dict().get("payload")
        print("  linha:", h)
        r = await b.entity_array(h, 2, 3, 2.0, 3.0)
    elif qual == "blockdefine":
        r = await b.block_define("LAC_BLOCK", [
            {"type": "LINE", "x1": 0, "y1": 0, "x2": 10, "y2": 0},
            {"type": "LINE", "x1": 10, "y1": 0, "x2": 10, "y2": 5},
            {"type": "CIRCLE", "cx": 5, "cy": 2.5, "radius": 1},
            {"type": "ATTDEF", "x": 0, "y": -2, "height": 0.5,
             "tag": "COD", "prompt": "Codigo", "value": "A1"},
        ])
    elif qual == "attrs":
        ins = await b.block_insert("LAC_BLOCK", 0, 30, scale=1.0)
        ih = ins.to_dict().get("payload")
        print("  insert:", ih)
        g = await b.block_get_attributes(ih)
        print("  leu:", json.dumps(g.to_dict(), ensure_ascii=False)[:200])
        r = await b.block_update_attribute(ih, "COD", "ZZ9")
        g2 = await b.block_get_attributes(ih)
        print("  leu2:", json.dumps(g2.to_dict(), ensure_ascii=False)[:200])
    else:
        raise SystemExit("lacuna desconhecida: %s" % qual)
    print("RESULTADO:", json.dumps(r.to_dict(), ensure_ascii=False)[:300])


asyncio.run(principal(sys.argv[1]))
