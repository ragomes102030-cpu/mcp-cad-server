# -*- coding: utf-8 -*-
"""mcp-cad-cloud — MCP HTTP server (ezdxf headless, sem AutoCAD).

Lançamento cloud-ready: substitui o backend COM/Win32 do mcp-cad-server pela
instância ezdxf headless, expondo as mesmas ferramentas de mapeamento via FastMCP.
"""

__version__ = "0.1.0"

# Contrato de ferramentas (compatibiliza com o CADCraft / prompts antigos)
CONTRATO = [
    # núcleo
    "inspect_drawing", "query_entities", "command_line", "script",
    "new_drawing", "open", "save", "cancel",
    # desenho
    "draw_line", "draw_rectangle", "draw_polyline", "draw_circle", "draw_arc",
    "draw_text", "draw_mtext", "draw_hatch", "dim_linear", "dim_aligned",
    "layer_list", "layer_create", "layer_set_current",
    "block_list", "block_insert", "block_attributes", "block_set_attribute",
    "export_dxf", "plot_pdf", "render_png", "screenshot",
    "undo", "redo", "zoom_extents",
    # diferenciais
    "ensure_standard_layers", "desenhar_ambiente", "quantitativo",
]
