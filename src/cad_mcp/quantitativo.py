# -*- coding: utf-8 -*-
"""Quantitativo: lê um DXF e devolve comprimentos, áreas, blocos, textos e cotas por camada.

Funciona em qualquer backend: o backend AutoCAD exporta o desenho vivo para DXF
temporário e a análise roda em cima do arquivo (mesmo extrator que já foi validado
na planta-casa-terrea.dxf).
"""
from __future__ import annotations

import collections
import math
from pathlib import Path

import ezdxf
from ezdxf.math import Vec3
from shapely.geometry import LineString, Polygon

# 0=sem unidade 1=pol 2=pé 4=mm 5=cm 6=m
UNIDADES = {0: "sem unidade", 1: "polegadas", 2: "pés", 4: "mm", 5: "cm", 6: "m",
            8: "micro", 9: "milhas", 10: "jardas", 14: "dm", 15: "dam", 16: "hm", 17: "km"}


def _len_arc(r: float, a0: float, a1: float) -> float:
    return abs(r) * ((a1 - a0) % 360) * math.pi / 180.0


def analisar(path: str | Path, top_textos: int = 40) -> dict:
    """Inventário + quantitativos de um DXF."""
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    hdr = doc.header

    # --- inventário por camada/tipo
    tipos = collections.Counter(e.dxftype() for e in msp)
    por_camada: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    comprimento: dict[str, float] = collections.defaultdict(float)
    area: dict[str, float] = collections.defaultdict(float)
    fechados: dict[str, int] = collections.Counter()

    for e in msp:
        t = e.dxftype()
        lay = e.dxf.layer
        por_camada[lay][t] += 1
        try:
            if t == "LINE":
                comprimento[lay] += (Vec3(e.dxf.end) - Vec3(e.dxf.start)).magnitude
            elif t == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points("xy")]
                if len(pts) > 1:
                    comprimento[lay] += LineString(pts).length
                if e.closed and len(pts) > 2:
                    fechados[lay] += 1
                    pg = Polygon(pts)
                    if pg.is_valid:
                        area[lay] += pg.area
            elif t == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                if len(pts) > 1:
                    comprimento[lay] += LineString(pts).length
            elif t == "ARC":
                comprimento[lay] += _len_arc(e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle)
            elif t == "CIRCLE":
                comprimento[lay] += 2 * math.pi * e.dxf.radius
        except Exception:
            pass

    # --- blocos (com atributos, quando houver)
    blocos: dict[str, int] = collections.Counter()
    atributos: list[dict] = []
    for ins in msp.query("INSERT"):
        try:
            blocos[ins.dxf.name] += 1
            for at in getattr(ins, "attribs", []) or []:
                atributos.append({"bloco": ins.dxf.name, "tag": at.dxf.tag, "valor": at.dxf.text})
        except Exception:
            pass

    # --- textos (decodifica \U+XXXX do DXF)
    def _dec(s: str) -> str:
        out, i = [], 0
        while i < len(s):
            if s[i:i + 3] == "\\U+" and len(s) >= i + 7:
                try:
                    out.append(chr(int(s[i + 3:i + 7], 16))) ; i += 7; continue
                except ValueError:
                    pass
            out.append(s[i]); i += 1
        return "".join(out).strip()

    textos = []
    for e in msp.query("TEXT MTEXT"):
        try:
            raw = e.dxf.text if e.dxftype() == "TEXT" else e.text
            if raw and raw.strip():
                textos.append(_dec(raw))
        except Exception:
            pass

    # --- cotas
    cotas = []
    for d in msp.query("DIMENSION"):
        try:
            cotas.append(round(float(d.get_measurement()), 3))
        except Exception:
            cotas.append(None)

    def _pt(v):
        """$EXTMIN/$EXTMAX vem como Vec3 ou tupla, dependendo da versão do DXF."""
        if v is None:
            return None
        if hasattr(v, "x"):
            return [round(float(v.x), 4), round(float(v.y), 4)]
        try:
            return [round(float(v[0]), 4), round(float(v[1]), 4)]
        except Exception:
            return None

    ext = hdr.get("$EXTMIN"), hdr.get("$EXTMAX")
    return {
        "arquivo": str(path),
        "dxf_version": doc.dxfversion,
        "unidades": UNIDADES.get(hdr.get("$INSUNITS"), hdr.get("$INSUNITS")),
        "insunits": hdr.get("$INSUNITS"),
        "extents": {"min": _pt(ext[0]), "max": _pt(ext[1])},
        "camadas": [{"nome": l.dxf.name, "cor": l.dxf.color, "linetype": l.dxf.linetype}
                    for l in doc.layers],
        "total_entidades": sum(tipos.values()),
        "entidades_por_tipo": dict(tipos),
        "entidades_por_camada": {k: dict(v) for k, v in por_camada.items()},
        "comprimento_por_camada": {k: round(v, 3) for k, v in sorted(comprimento.items(), key=lambda x: -x[1])},
        "area_fechada_por_camada": {k: round(v, 3) for k, v in sorted(area.items(), key=lambda x: -x[1])},
        "contornos_fechados": dict(fechados),
        "blocos": dict(blocos),
        "atributos_de_bloco": atributos[:200],
        "textos": textos[:top_textos],
        "total_textos": len(textos),
        "cotas": cotas[:60],
        "total_cotas": len(cotas),
    }
