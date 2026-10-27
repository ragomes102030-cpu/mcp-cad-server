# -*- coding: utf-8 -*-
"""mcp-cad-server — motor CAD próprio (AutoCAD + headless DXF).

Contrato de ferramentas compatível com o que o CADCraft já expõe, para que
prompts e skills do usuário continuem válidos ao trocar de motor.
"""
__version__ = "0.2.4"

CONTRATO = [
    # núcleo compatível com CADCraft
    "inspect_drawing", "query_entities", "command_line", "script",
    "new_drawing", "open", "save", "cancel",
    # desenho (extras nossos)
    "draw_line", "draw_rectangle", "draw_polyline", "draw_circle", "draw_arc",
    "draw_text", "draw_mtext", "draw_hatch", "dim_linear", "dim_aligned",
    "layer_list", "layer_create", "layer_set_current",
    "block_list", "block_insert", "block_attributes", "block_set_attribute",
    "export_dxf", "plot_pdf", "render_png", "screenshot",
    "undo", "redo", "zoom_extents",
    # nossos diferenciais
    "ensure_standard_layers", "desenhar_ambiente", "quantitativo",
    "planta_templates", "planta_assistida", "validar_planta",
]
