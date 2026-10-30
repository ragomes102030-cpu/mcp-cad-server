"""Arquimedes CAD Engineering Benchmark — independent known-value test cases.

Produces an auditable JSON report including expected, obtained, difference,
tolerance, status, git commit and package version. The references are simple
analytic shapes, NOT outputs from the application geometry generator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from math import hypot

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud" / "ezdxf"))
from mcp_cad_cloud import __version__
from mcp_cad_cloud.quantitativos_engenharia import extrair_quantitativos_dxf, VERSION


def _document():
    doc=ezdxf.new("R2013")
    doc.header["$INSUNITS"]=6
    for layer in ("PISOS","EIXOS-PAREDES","VAOS-PORTAS","VAOS-JANELAS"):
        doc.layers.new(layer)
    return doc


def _case(name, expected, observed, tolerance, commit):
    difference=(observed-expected if observed is not None else None)
    return {
        "entrada":name,"esperado":expected,"obtido":observed,
        "diferenca":difference,"tolerancia":tolerance,
        "status":"APROVADO" if difference is not None and abs(difference)<=tolerance
                 else "REPROVADO",
        "commit":commit,"versao":__version__,"versao_calculo":VERSION,
    }


def run():
    try:
        sha=subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True,timeout=3).strip()
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
        sha="indisponivel"
    cases=[]
    # Floor polygons: all expected values can be calculated by hand,
    # independent of ezdxf or the application's shoelace implementation.
    for width,depth,expected_area,expected_perimeter in (
        (2,3,6,10),(4,3,12,14),(3,5,15,16),(5,5,25,20),(1.5,4,6,11),
    ):
        doc=_document()
        doc.modelspace().add_lwpolyline(
            [(0,0),(width,0),(width,depth),(0,depth)],
            close=True,dxfattribs={"layer":"PISOS"})
        r=extrair_quantitativos_dxf(doc)
        floor=next(item for item in r["itens"] if item["tipo"]=="piso")
        title=f"piso retangular {width} x {depth} m"
        cases.append(_case(title+" area m2",expected_area,
                           floor["metricas"]["area_m2"],1e-6,sha))
        cases.append(_case(title+" perimetro m",expected_perimeter,
                           floor["metricas"]["perimetro_m"],1e-6,sha))
    doc=_document()
    doc.modelspace().add_lwpolyline(
        [(0,0),(3,0),(0,4)],close=True,dxfattribs={"layer":"PISOS"})
    q=extrair_quantitativos_dxf(doc)
    floor=next(item for item in q["itens"] if item["tipo"]=="piso")
    cases.append(_case("triangulo retangulo 3-4-5 area m2",6,
                       floor["metricas"]["area_m2"],1e-6,sha))
    cases.append(_case("triangulo retangulo 3-4-5 perimetro m",12,
                       floor["metricas"]["perimetro_m"],1e-6,sha))
    doc=_document()
    msp=doc.modelspace()
    wall=msp.add_line((0,0),(4,0),dxfattribs={"layer":"EIXOS-PAREDES"})
    door=msp.add_line((1,0),(1.9,0),dxfattribs={"layer":"VAOS-PORTAS"})
    window=msp.add_line((2,0),(3.2,0),dxfattribs={"layer":"VAOS-JANELAS"})
    q=extrair_quantitativos_dxf(
        doc,projeto_id="BENCH-RESIDENCIA-001",
        altura_paredes_m=3,espessura_paredes_m=.15,
        altura_portas_m=2,altura_janelas_m=1.2,
        aberturas_por_parede={wall.dxf.handle:[door.dxf.handle,window.dxf.handle]},
        inventario_aberturas_completo=True)
    item=next(item for item in q["itens"] if item["tipo"]=="parede")
    for name,expected,key in (
        ("comprimento eixo parede m",4,"comprimento_m"),
        ("area bruta parede m2",12,"area_bruta_m2"),
        ("desconto vao porta+janela m2",3.24,"area_aberturas_m2"),
        ("area liquida parede m2",8.76,"area_liquida_m2"),
        ("volume geometrico parede m3",1.314,"volume_geometrico_m3"),
    ):
        cases.append(_case(name,expected,item["metricas"][key],1e-6,sha))
    doc=_document()
    poly=doc.modelspace().add_lwpolyline(
        [(0,0),(3,3),(3,0),(0,3)],close=True,dxfattribs={"layer":"PISOS"})
    mutation=extrair_quantitativos_dxf(doc)
    cases.append({
        "entrada":"poligono autointersectante (bow-tie) deve falhar",
        "esperado":"PISO_CONTORNO_INVALIDO",
        "obtido":[err["codigo"] for err in mutation["erros"]],
        "diferenca":None,"tolerancia":None,
        "status":"APROVADO" if any(
            err["codigo"]=="PISO_CONTORNO_INVALIDO" for err in mutation["erros"])
            else "REPROVADO",
        "commit":sha,"versao":__version__,"versao_calculo":VERSION,
    })
    passed=sum(x["status"]=="APROVADO" for x in cases)
    return {"nome":"Arquimedes CAD Engineering Benchmark",
            "version":"1.0.0","commit":sha,"cases":cases,
            "summary":{"total":len(cases),"passed":passed,
                       "failed":len(cases)-passed}}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"out"/"cad-engineering-benchmark.json")
    args=parser.parse_args()
    result=run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["summary"],ensure_ascii=False))
    return 0 if result["summary"]["failed"]==0 else 1


if __name__=="__main__":
    raise SystemExit(main())
