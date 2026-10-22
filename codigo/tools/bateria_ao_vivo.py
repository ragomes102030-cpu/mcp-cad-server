# -*- coding: utf-8 -*-
"""Bateria AO VIVO: exercita cada ferramenta do MCP contra o AutoCAD aberto e
registra o resultado real em C:/temp/bateria_vivo.json."""
import asyncio, json, os, sys, time
from pathlib import Path

os.environ["CAD_MCP_BACKEND"] = "auto"
os.environ.setdefault("MCP_CAD_TEMP", "C:/temp/mcp_cad_com")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(os.environ.get("CAD_RAIZ", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(RAIZ / "src"))

import cad_mcp.tools as T  # noqa
from cad_mcp.backend_manager import MANAGER  # noqa

SAIDA = Path("C:/temp/bateria_vivo.json")
TMP = Path("C:/temp/mcp_audit"); TMP.mkdir(parents=True, exist_ok=True)
DWG = TMP / "auditoria.dwg"; DXF = TMP / "auditoria.dxf"
PDF = TMP / "auditoria.pdf"; PNG = TMP / "auditoria.png"

RESULTADOS, FALHAS = [], []

def _bom(r):
    if not isinstance(r, dict):
        return True
    if "ok" in r:
        return bool(r["ok"])
    return not (r.get("error") or r.get("erro"))

def registrar(nome, args, res):
    bom = _bom(res)
    erro = None
    if isinstance(res, dict):
        erro = res.get("error") or res.get("erro")
    RESULTADOS.append({"ferramenta": nome, "args": args, "ok": bom, "erro": erro})
    if not bom:
        FALHAS.append(nome)
    print(("  OK    " if bom else "  FALHA ") + "%-30s %s" % (nome, (str(erro) if erro else "")[:110]))
    return res

async def P(nome, args, fn, *a, **k):
    try:
        return registrar(nome, args, await fn(*a, **k))
    except Exception as e:
        registrar(nome, args, {"ok": False, "erro": "%s: %s" % (type(e).__name__, e)})
        return None

def pl(r):
    return (r or {}).get("payload") if isinstance(r, dict) else r

async def principal():
    st = await MANAGER.status()
    print("BACKEND:", st.get("backend"), "|", st.get("selecao"))
    print("\n=== desenho base ===")
    await P("drawing_new", {"name": "auditoria.dwg"}, T.new_drawing, name=str(DWG))
    await P("drawing_setup", {"unidades": 6}, T.drawing_setup, unidades=6)
    await P("drawing_apply_iso_layers", {}, T.ensure_standard_layers)
    await P("drawing_info", {}, T.inspect_drawing)
    await P("system_status", {}, T.cad_status)

    print("\n=== camadas ===")
    await P("layer_create", {"name": "AUD_L1"}, T.layer_create, "AUD_L1", color=1)
    await P("layer_set_current", {"name": "AUD_L1"}, T.layer_set_current, "AUD_L1")
    await P("layer_list", {}, T.layer_list)
    await P("layer_hide", {"name": "AUD_L1"}, T.layer_hide, "AUD_L1")
    await P("layer_show", {"name": "AUD_L1"}, T.layer_show, "AUD_L1")
    await P("layer_freeze", {"name": "AUD_L1"}, T.layer_freeze, "AUD_L1")
    await P("layer_thaw", {"name": "AUD_L1"}, T.layer_thaw, "AUD_L1")
    await P("layer_lock", {"name": "AUD_L1"}, T.layer_lock, "AUD_L1")
    await P("layer_unlock", {"name": "AUD_L1"}, T.layer_unlock, "AUD_L1")
    await P("layer_isolate", {"name": "AUD_L1"}, T.layer_isolate, "AUD_L1")
    await P("layer_modify", {"name": "AUD_L1", "color": 3}, T.layer_modify, "AUD_L1", color=3)
    await P("linetype_list", {}, T.linetype_list)
    await P("layer_linetype_load", {"nome": "DASHED"}, T.linetype_load, "DASHED")
    await P("dimstyle_list", {}, T.dimstyle_list)
    await P("textstyle_list", {}, T.textstyle_list)
    await P("plot_style_list", {}, T.plot_style_list)

    print("\n=== entidades ===")
    await P("entity_create_line", {}, T.draw_line, 0, 0, 10, 0, layer="AUD_L1")
    _rect = pl(await T.draw_rectangle(0, 0, 8, 6, layer="AUD_L1"))
    h_rect = _rect if isinstance(_rect, str) else ((_rect or {}).get("handle") if isinstance(_rect, dict) else None)
    registrar("entity_create_rectangle", {}, {"ok": True, "handle": h_rect})
    await P("entity_create_circle", {}, T.draw_circle, 20, 5, 3, layer="AUD_L1")
    await P("entity_create_arc", {}, T.draw_arc, 20, 5, 5, 0, 90, layer="AUD_L1")
    await P("entity_create_polyline", {}, T.draw_polyline, [[0, 0], [4, 0], [4, 4], [0, 4]], True, layer="AUD_L1")
    await P("entity_create_text", {}, T.draw_text, 1, 7, "AUDITORIA", height=0.5, layer="AUD_L1")
    await P("entity_create_mtext", {}, T.draw_mtext, 1, 8, 6, "Nota de auditoria", height=0.4, layer="AUD_L1")
    await P("entity_create_point", {}, T.entity_create_point, 30, 5, layer="AUD_L1")
    await P("entity_create_spline", {}, T.entity_create_spline, [[0, 10], [3, 13], [6, 10]], layer="AUD_L1")
    await P("entity_create_ellipse", {}, T.entity_create_ellipse, 40, 5, 6, 0, 0.6, layer="AUD_L1")
    await P("entity_create_revcloud", {}, T.entity_create_revcloud, [[50, 0], [54, 0], [54, 4], [50, 4]], layer="AUD_L1")
    await P("construction_xline", {}, T.construction_xline, 0, 20, 30, layer="AUD_L1")
    await P("entity_list", {}, T.query_entities, layer="AUD_L1")
    await P("quantitativo", {"layer": "AUD_L1"}, T.quantitativo, layer="AUD_L1")

    print("\n=== cotas / anotacao / arquitetura ===")
    await P("dimension_linear", {}, T.dim_linear, 0, 0, 10, 0, -2.0, 0)
    await P("dimension_aligned", {}, T.dim_aligned, 0, 0, 10, 6, 1.5)
    await P("dimension_angular", {}, T.dimension_angular, 0, 0, 5, 0, 0, 5)
    await P("dimension_radius", {}, T.dimension_radius, 20, 5, 3)
    await P("leader_create_mleader", {}, T.leader_create_mleader, [[0, 0], [3, 2]], "LEGDA")
    await P("arch_grid", {}, T.arch_grid, [0, 5, 10], [0, 5], extension=0.5)
    await P("arch_symbol", {"kind": "north"}, T.arch_symbol, "north", 0, 0)
    await P("arch_room", {}, T.desenhar_ambiente, "SALA", 0, 0, 6, 4)
    await P("hatch_material", {"material": "concreto"}, T.hatch_material, "concreto", handles=[h_rect] if h_rect else None)
    await P("arch_dimension_chains", {}, T.arch_dimension_chains)
    await P("arch_rooms_detect", {}, T.arch_rooms_detect, layers=["AUD_L1"])

    print("\n=== edicao ===")
    _q = pl(await T.query_entities(layer="AUD_L1")) or {}
    ents = _q.get("entities") if isinstance(_q, dict) else _q
    ents = ents or []
    h = ents[0].get("handle") if ents and isinstance(ents[0], dict) else None
    print("   primeiro handle em AUD_L1:", h)
    if h:
        await P("entity_get", {}, T.entity_get, h)
        await P("entity_move", {}, T.move_entity, h, 1, 0)
        await P("entity_copy", {}, T.copy_entity, h, 0, 2)
        await P("entity_rotate", {}, T.rotate_entity, h, 0, 0, 45)
        await P("entity_mirror", {}, T.mirror_entity, h, 0, 0, 10, 0)
        await P("entity_offset", {}, T.offset_entity, h, 0.5)
        await P("entity_scale", {}, T.entity_scale, h, 0, 0, 2)
        await P("entity_array_polar", {}, T.entity_array_polar, h, 4, 360, 0, 0)
        await P("entity_array_rectangular", {}, T.entity_array_rectangular, h, 2, 3, 1, 1)
        await P("entity_set_properties", {}, T.entity_set_properties, h, color=2)
        await P("entity_edit_text", {}, T.entity_edit_text, h, text="TROCADO")
        await P("point_from_snap", {"snap": "mid"}, T.point_from_snap, h, "mid")
        await P("point_tangent", {}, T.point_tangent, h, 0, 20)
        await P("selection_window", {}, T.selection_window, 0, 0, 200, 200)
        await P("entity_trim", {}, T.trim_entity, h, h, [5, 5])
        await P("entity_extend", {}, T.extend_entity, h, h)
        await P("entity_fillet", {}, T.fillet_entity, h, h, 0.5)
        await P("entity_chamfer", {}, T.entity_chamfer, h, h, 0.3, 0.3)
        await P("block_get_attributes", {}, T.block_attributes, h)
        await P("block_set_attributes", {}, T.block_set_attribute, h, "TAG", "V")
        await P("entity_delete_many", {"confirmar": True}, T.entity_delete_many, [h], confirmar=True)
    await P("entity_copy_filter", {}, T.copy_filter, layer="AUD_L1", dx=50, dy=0)
    await P("entity_mirror_filter", {}, T.mirror_filter, layer="AUD_L1", x1=0, y1=0, x2=0, y2=50)
    await P("entity_rotate_filter", {}, T.rotate_filter, layer="AUD_L1", angulo=15)
    await P("entity_erase_filter", {"confirmar": False}, T.erase_filter, layer="AUD_L1")
    await P("user_pick_point", {}, T.user_pick_point, "clique fora")

    print("\n=== blocos ===")
    await P("block_list", {}, T.block_list)
    await P("block_define", {}, T.block_define, "AUD_BLOCK", [])

    print("\n=== arquivos / saida ===")
    await P("drawing_save", {}, T.save)
    await P("drawing_export_dxf", {"path": "auditoria.dxf"}, T.export_dxf, str(DXF))
    print("   DXF no disco:", DXF.exists(), DXF.stat().st_size if DXF.exists() else 0)
    await P("drawing_properties_set", {"title": "Auditoria"}, T.drawing_properties_set, title="Auditoria")
    await P("drawing_properties_get", {}, T.drawing_properties_get)
    await P("drawing_audit", {}, T.drawing_audit)
    await P("drawing_purge", {}, T.drawing_purge)
    await P("drawing_undo", {}, T.undo)
    await P("drawing_redo", {}, T.redo)
    await P("view_zoom_extents", {}, T.zoom_extents)
    await P("view_zoom_window", {}, T.view_zoom_window, 0, 0, 100, 100)
    await P("view_screenshot", {"path": "auditoria.png"}, T.screenshot, str(PNG))
    print("   PNG no disco:", PNG.exists(), PNG.stat().st_size if PNG.exists() else 0)
    await P("view_render_png", {}, T.render_png, str(TMP / "render.png"))
    _lisp = chr(40) + "setvar " + chr(34) + "CMDECHO" + chr(34) + " 1" + chr(41)
    await P("script", {}, T.script, [_lisp])
    await P("system_run_command", {}, T.command_line, "_.ZOOM _E")
    await P("cancel", {}, T.cancel)

    print("\n=== layout / viewport / plot / xref ===")
    await P("layout_list", {}, T.layout_list)
    await P("layout_create", {"name": "AUD_A3"}, T.layout_create, "AUD_A3")
    await P("layout_set_current", {"name": "AUD_A3"}, T.layout_set_current, "AUD_A3")
    await P("page_setup_list", {}, T.page_setup_list, "AUD_A3")
    await P("page_setup_apply", {}, T.page_setup_apply, "AUD_A3", paper="A3", orientation="landscape")
    await P("viewport_create", {}, T.viewport_create, "AUD_A3", 50, 50, 200, 150)
    await P("viewport_list", {}, T.viewport_list, "AUD_A3")
    await P("viewport_set_scale", {}, T.viewport_set_scale, "AUD_A3", "__h__", 50)
    await P("viewport_lock", {}, T.viewport_lock, "AUD_A3", "__h__", True)
    await P("viewport_delete", {}, T.viewport_delete, "AUD_A3", "__h__")
    await P("xref_attach", {"path": "auditoria.dwg"}, T.xref_attach, str(DWG))
    await P("xref_manage", {}, T.xref_manage, "auditoria", "list")
    await P("image_attach", {"path": "auditoria.png"}, T.image_attach, str(PNG))
    await P("layout_rename", {}, T.layout_rename, "AUD_A3", "AUD_A3B")
    await P("layout_copy", {}, T.layout_copy, "AUD_A3B", "AUD_A3C")
    await P("batch_plot", {}, T.batch_plot, out_dir=str(TMP))
    await P("drawing_export_dwg", {}, T.drawing_export_dwg, str(TMP / "auditoria_out.dwg"))
    print("   DWG out:", (TMP / "auditoria_out.dwg").exists())

    print("\n=== PDF (lento) ===")
    await P("drawing_export_pdf", {"path": "auditoria.pdf"}, T.plot_pdf, str(PDF), escala=50)
    print("   PDF no disco:", PDF.exists(), PDF.stat().st_size if PDF.exists() else 0)
    await P("drawing_save_as", {}, T.drawing_save_as, str(TMP / "save_as.dwg"))
    print("   save_as:", (TMP / "save_as.dwg").exists())
    await P("layer_delete", {"name": "AUD_L1"}, T.layer_delete, "AUD_L1")
    await P("document_close", {"salvar": False}, T.document_close, salvar=False)
    await P("drawing_close", {"salvar": False}, T.drawing_close, salvar=False)

    SAIDA.write_text(json.dumps({"total": len(RESULTADOS), "falhas": FALHAS,
                                 "resultados": RESULTADOS}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n================ RESUMO ================")
    print("executadas:", len(RESULTADOS), "| falhas:", len(FALHAS))
    for f in FALHAS:
        print("  FALHA:", f)
    print("json:", SAIDA)

asyncio.run(principal())
