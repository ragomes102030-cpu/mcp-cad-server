"""JSON Schema for consumer interoperability, no CAD-to-money conversion."""
import json
from pathlib import Path
import ezdxf
from jsonschema import Draft202012Validator

from mcp_cad_cloud.quantitativos_engenharia import extrair_quantitativos_dxf


ROOT=Path(__file__).resolve().parents[1]
SCHEMA=ROOT/"schemas"/"cad-quantitativos-v1.schema.json"


def test_quantities_match_public_schema_and_never_contain_money():
    schema=json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    doc=ezdxf.new("R2013")
    doc.header["$INSUNITS"]=6
    doc.layers.new("PISOS")
    doc.modelspace().add_lwpolyline(
        [(0,0),(2,0),(2,3),(0,3)],close=True,
        dxfattribs={"layer":"PISOS"})
    data=extrair_quantitativos_dxf(doc,projeto_id="QA-001")
    Draft202012Validator(schema).validate(data)
    assert data["integracao"]["precos"] is None
    assert data["integracao"]["custos"] is None
    assert data["integracao"]["bdi"] is None
    assert all("preco" not in str(k).lower() and "valor_financeiro" not in str(k).lower()
               for item in data["itens"] for k in item)
