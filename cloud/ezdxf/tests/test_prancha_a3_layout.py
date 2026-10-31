"""A3 sheet smoke test: real DXF rendering and PDF generation."""
import ezdxf

from mcp_cad_cloud.prancha_dxf import renderizar_prancha


def test_a3_sheet_frame_and_title_block_render_from_dxf():
    doc = ezdxf.new("R2010")
    doc.modelspace().add_line((0, 0), (9, 8.6))
    pdf, png = renderizar_prancha(
        doc, "Residencia piloto",
        {"largura": 9.0, "profundidade": 8.6,
         "area_construida": 77.4, "area_util_total": 62.508},
    )
    assert pdf.startswith(b"%PDF-")
    assert png.startswith(bytes.fromhex("89504e470d0a1a0a"))
    assert len(pdf) > 3000
    assert len(png) > 3000
