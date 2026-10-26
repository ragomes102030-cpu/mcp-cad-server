import asyncio, sys
sys.path.insert(0, "src")
from cad_mcp.tools import (arch_wall, arch_opening, place_symbol, draw_text,
                           dim_linear, ensure_standard_layers, new_drawing, drawing_setup,
                           save, plot_pdf, draw_line, draw_rectangle,
                           north_arrow, scale_bar, section_line, title_block)
from cad_mcp.tools import symbol_legend, symbol_schedule
from cad_mcp.tools_geo import arch_grid

async def main():
    await new_drawing()
    await drawing_setup(unidades=6)
    await ensure_standard_layers()

    # === PAREDES (planta 9x12m) ===
    await arch_wall([[[0,0],[9,0],[9,12],[0,12],[0,0]]], poche=True)
    await arch_wall([[[0,6],[9,6]]], poche=True)
    await arch_wall([[[4.5,0],[4.5,6]]], poche=True)
    await arch_wall([[[6,6],[6,12]]], poche=True)
    await arch_wall([[[4.5,3],[6.5,3]]], poche=True)
    await arch_wall([[[6.5,0],[6.5,3]]], poche=True)

    # === ABERTURAS (portas + janelas) ===
    from cad_mcp.backend_manager import MANAGER
    b = await MANAGER.get()
    r = await b.entity_list(layer="PAREDES")
    ents = r.payload if isinstance(r.payload, list) else r.payload.get("entities", [])
    ext_handle = ents[0]["handle"]
    # Janelas
    await arch_opening(ext_handle, offset=2.0, width=1.5, kind="window", sill=1.0, tag="J01")
    await arch_opening(ext_handle, offset=6.0, width=2.0, kind="window", sill=1.0, tag="J02")
    # Porta de entrada (parede externa)
    await arch_opening(ext_handle, offset=0.5, width=0.9, kind="door", tag="P01")
    # Porta sala-cozinha (parede interna horizontal)
    int_handle = ents[1]["handle"]  # parede [0,6]-[9,6]
    await arch_opening(int_handle, offset=7.0, width=0.8, kind="door", tag="P02")
    # Porta sala-quarto2 (parede interna vertical)
    v_handle = ents[2]["handle"]  # parede [4.5,0]-[4.5,6]
    await arch_opening(v_handle, offset=4.0, width=0.8, kind="door", tag="P03")
    # Porta quarto1-banho
    b_handle = ents[4]["handle"]  # parede [4.5,3]-[6.5,3]
    await arch_opening(b_handle, offset=0.5, width=0.7, kind="door", tag="P04")
    # Porta quarto1-corredor
    v2_handle = ents[5]["handle"]  # parede [6.5,0]-[6.5,3]
    await arch_opening(v2_handle, offset=1.5, width=0.8, kind="door", tag="P05")
    # Porta cozinha-area servico
    v3_handle = ents[3]["handle"]  # parede [6,6]-[6,12]
    await arch_opening(v3_handle, offset=7.0, width=0.8, kind="door", tag="P06")

    # === SIMBODOS ===
    await place_symbol("luminaria_teto", 2.25, 3.0)
    await place_symbol("tomada_baixa", 0.3, 2.0)
    await place_symbol("tomada_baixa", 4.2, 2.0)
    await place_symbol("luminaria_teto", 7.5, 9.0)
    await place_symbol("tomada_baixa", 6.3, 7.0)
    await place_symbol("tomada_baixa", 8.7, 7.0)
    await place_symbol("luminaria_teto", 2.25, 9.0)
    await place_symbol("tomada_baixa", 0.3, 7.0)
    await place_symbol("tomada_baixa", 4.2, 7.0)
    await place_symbol("chuveiro", 5.5, 1.5)
    await place_symbol("lavatorio", 5.5, 2.5)
    await place_symbol("bacia", 6.0, 1.5)
    await place_symbol("ralo", 5.0, 1.0)
    await place_symbol("tomada_baixa", 8.7, 10.0)
    await place_symbol("tomada_baixa", 7.0, 11.5)

    # === TEXTOS (ambientes) ===
    await draw_text(2.25, 3.0, "SALA ESTAR", height=0.25)
    await draw_text(2.25, 2.7, "18,00 m2  PD 2,80", height=0.18)
    await draw_text(7.5, 9.0, "COZINHA", height=0.25)
    await draw_text(7.5, 8.7, "9,00 m2", height=0.18)
    await draw_text(2.25, 9.0, "QUARTO 1", height=0.25)
    await draw_text(2.25, 8.7, "18,00 m2", height=0.18)
    await draw_text(7.5, 3.0, "QUARTO 2", height=0.25)
    await draw_text(7.5, 2.7, "18,00 m2", height=0.18)
    await draw_text(5.5, 1.5, "BANHO", height=0.22)
    await draw_text(5.5, 1.2, "4,00 m2", height=0.16)
    await draw_text(7.5, 11.0, "AREA SERV.", height=0.22)
    await draw_text(7.5, 10.7, "6,00 m2", height=0.16)

    # === NIVEIS ===
    await draw_text(-1.5, -0.3, "RUA 0,00", height=0.18)
    await draw_text(-1.5, 0.0, "PISO INT. +0,15", height=0.18)
    await draw_text(-1.5, 0.3, "VARANDA +0,05", height=0.18)

    # === COTAS ===
    await dim_linear(0, 0, 9, 0, 4.5, -1.5)
    await dim_linear(0, 0, 0, 12, -1.5, 6.0)
    await dim_linear(0, 6, 4.5, 6, 2.25, 5.5)
    await dim_linear(4.5, 6, 9, 6, 6.75, 5.5)
    await dim_linear(0, 0, 0, 6, -0.8, 3.0)
    await dim_linear(9, 0, 9, 6, 9.8, 3.0)
    await dim_linear(0, 6, 0, 12, -0.8, 9.0)
    await dim_linear(9, 6, 9, 12, 9.8, 9.0)
    await dim_linear(4.5, 0, 4.5, 6, 4.0, 3.0)
    await dim_linear(6.5, 0, 6.5, 3, 6.0, 1.5)

    # === NORTE ===
    await north_arrow(10.5, 12.0, 1.0)

    # === ESCALA ===
    await scale_bar(0, -2.5, 5.0, "1:50")

    # === CORTES ===
    await section_line(-0.5, 6, 0, 6, "A")
    await section_line(9, 6, 9.5, 6, "A")
    await section_line(4.5, -0.5, 4.5, 0, "B")
    await section_line(4.5, 12, 4.5, 12.5, "B")

    # === CARIMBO ===
    await title_block(10.5, -4.0, width=7.0, height=4.5,
                      projeto="RESIDENCIA UNIFAMILIAR 2D",
                      cliente="CLIENTE",
                      escala="1:50",
                      data="24/10/2026",
                      responsavel="ENG. CIVIL",
                      crea="CREA 000000",
                      folha="01/01",
                      revisao="A")

    # === QUADRO DE ESQUADRIAS ===
    qx, qy = 10.5, 1.0
    await draw_rectangle(qx, qy, qx+7.0, qy+2.5)
    for i in range(1, 5):
        await draw_line(qx, qy+i*0.5, qx+7.0, qy+i*0.5)
    await draw_line(qx+1.2, qy, qx+1.2, qy+2.5)
    await draw_line(qx+3.5, qy, qx+3.5, qy+2.5)
    await draw_line(qx+5.5, qy, qx+5.5, qy+2.5)
    await draw_text(qx+0.1, qy+2.1, "COD", height=0.16)
    await draw_text(qx+1.4, qy+2.1, "TIPO", height=0.16)
    await draw_text(qx+3.7, qy+2.1, "DIMENSAO", height=0.16)
    await draw_text(qx+5.7, qy+2.1, "QTD", height=0.16)
    await draw_text(qx+0.1, qy+1.6, "P01", height=0.16)
    await draw_text(qx+1.4, qy+1.6, "PORTA", height=0.16)
    await draw_text(qx+3.7, qy+1.6, "0,90x2,10", height=0.16)
    await draw_text(qx+5.7, qy+1.6, "1", height=0.16)
    await draw_text(qx+0.1, qy+1.1, "P02", height=0.16)
    await draw_text(qx+1.4, qy+1.1, "PORTA", height=0.16)
    await draw_text(qx+3.7, qy+1.1, "0,80x2,10", height=0.16)
    await draw_text(qx+5.7, qy+1.1, "4", height=0.16)
    await draw_text(qx+0.1, qy+0.6, "P03", height=0.16)
    await draw_text(qx+1.4, qy+0.6, "PORTA", height=0.16)
    await draw_text(qx+3.7, qy+0.6, "0,70x2,10", height=0.16)
    await draw_text(qx+5.7, qy+0.6, "1", height=0.16)
    await draw_text(qx+0.1, qy+0.1, "J01", height=0.16)
    await draw_text(qx+1.4, qy+0.1, "JANELA", height=0.16)
    await draw_text(qx+3.7, qy+0.1, "1,50x1,20", height=0.16)
    await draw_text(qx+5.7, qy+0.1, "2", height=0.16)
    await draw_text(qx+2.0, qy+2.7, "QUADRO DE ESQUADRIAS", height=0.18)

    # === LEGENDA + SCHEDULE ===
    await symbol_legend(x=10.5, y=4.0)
    await symbol_schedule(x=10.5, y=8.0)

    # === GRID ===
    await arch_grid(x_axes=[0, 4.5, 6.5, 9], y_axes=[0, 3, 6, 12])

    # === SALVAR ===
    HERMES = "C:/Users/Correta Engenharia/AppData/Roaming/Arquimedes/arquimedes/conversations/users/system_default_user/2026/10/23/hermes-temp-21004193"
    sv = await save(f"{HERMES}/EVOLUCAO_02_v2.dwg")
    print("save:", sv)
    pdf = await plot_pdf(f"{HERMES}/EVOLUCAO_02.pdf", folha="A1", escala=50)
    print("pdf:", pdf)

    # Render for verification
    from cad_mcp.tools import zoom_extents, render_png
    await zoom_extents()
    r = await render_png(f"{HERMES}/EVOLUCAO_02_preview.png")
    print("render:", r)

asyncio.run(main())
PYEOF