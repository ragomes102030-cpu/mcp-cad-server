# -*- coding: utf-8 -*-
"""Mapa dos campos DXF de cada entidade, lido do ezdxf (nao do AutoCAD).

Por que esta fonte: o AutoCAD nao publica uma tabela consultavel por API; o DXF
e o contrato publico, e o `ezdxf` ja traz essa tabela (`DXFATTRIBS`) pronta e
versionada. O que sai daqui e o que o `entmake`/`entget` aceita — com o nome do
campo, o codigo do grupo e o valor padrao.

Regra que ja custou caro (ver historico): codigos 50/51 sao ANGULO. No arquivo
DXF aparecem em GRAUS; no `entmake`/`entget` sao RADIANOS.

Uso:
    python tools/mapear_entidades.py
Escreve `docs/MAPA-ENTIDADES.md` e `docs/catalogo-entidades.json`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"

# entidades que merecem tabela completa no .md (o resto vai so no JSON)
DESTAQUE = [
    "LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE",
    "POINT", "SOLID", "HATCH", "TEXT", "MTEXT", "DIMENSION", "LEADER", "MLEADER",
    "INSERT", "ATTRIB", "ATTDEF", "TABLE", "VIEWPORT", "IMAGE", "WIPEOUT",
    "LAYER", "LTYPE", "STYLE", "DIMSTYLE", "BLOCK_RECORD", "MLINE",
]

COMUNS = {0, 5, 8, 62, 6, 370, 48, 60, 420, 430, 440, 100, 67, 410, 330, 360, 347, 102}


def tipo_de_grupo(codigo: int) -> str:
    """Faixa do codigo de grupo DXF -> tipo de dado (tabela publica do formato)."""
    # 38 (elevation) e 39 (thickness) NAO sao coordenada Z: sao reais.
    if 10 <= codigo <= 18 or 20 <= codigo <= 28 or 30 <= codigo <= 37:
        return "ponto"
    if codigo in (50, 51):
        return "angulo"
    if 38 <= codigo <= 59:
        return "real"
    if 60 <= codigo <= 79:
        return "inteiro"
    if 90 <= codigo <= 99:
        return "inteiro32"
    if 100 <= codigo <= 109 or 320 <= codigo <= 369 or 390 <= codigo <= 399:
        return "texto/handle"
    if 210 <= codigo <= 239:
        return "vetor"
    if 170 <= codigo <= 179:
        return "inteiro16"
    if codigo in (1, 2, 3, 4, 6, 7, 8, 9):
        return "texto"
    return "outro"


def valor_padrao(v) -> str:
    if isinstance(v, (list, tuple)):
        return "(" + ", ".join(str(x) for x in v) + ")"
    if v is None:
        return "—"
    return str(v)


def coletar() -> dict[str, dict]:
    import ezdxf.entities as ents
    from ezdxf.entities import DXFEntity

    saida: dict[str, dict] = {}
    for nome in dir(ents):
        cls = getattr(ents, nome)
        if not (isinstance(cls, type) and issubclass(cls, DXFEntity)):
            continue
        atributos = getattr(cls, "DXFATTRIBS", None)
        if not atributos:
            continue
        # no ezdxf 1.4 DXFTYPE e' atributo de classe (str), nao metodo; as classes
        # abstratas nao tem ou tem vazio
        tipo = getattr(cls, "DXFTYPE", None)
        if not isinstance(tipo, str) or not tipo:
            continue
        campos = []
        for attr in atributos._attribs.values():
            campos.append({
                "codigo": int(attr.code),
                "nome": attr.name,
                "tipo": tipo_de_grupo(int(attr.code)),
                "padrao": valor_padrao(attr.default),
            })
        campos.sort(key=lambda c: c["codigo"])
        saida[tipo] = {"classe": nome, "campos": campos}
    return saida


def main() -> int:
    try:
        import ezdxf
    except ImportError:
        print("ezdxf nao instalado: pip install ezdxf")
        return 1

    entidades = coletar()
    DOCS.mkdir(exist_ok=True)
    (DOCS / "catalogo-entidades.json").write_text(
        json.dumps({"fonte": f"ezdxf {ezdxf.__version__} (DXFATTRIBS)",
                    "entidades": entidades}, indent=1, ensure_ascii=False),
        encoding="utf-8")

    linhas = [
        "# Mapa das entidades — campos DXF",
        "",
        f"Gerado de `ezdxf {ezdxf.__version__}` (`DXFATTRIBS`, a tabela do formato DXF).",
        "Vale para `entmake`/`entget` e para o arquivo DXF — **não** para as propriedades",
        "COM, que têm outro nome (o COM está em `MAPA-COM.md`).",
        "",
        "## Antes de tudo: ângulo",
        "",
        "Códigos **50 e 51** são ângulo. No arquivo DXF ficam em **graus**; no",
        "`entmake`/`entget` são **radianos**. Passar grau onde o `entmake` espera",
        "radiano não dá erro — dá geometria errada (90° virou 116,62°).",
        "",
        "## Campos que quase toda entidade tem",
        "",
        "| código | nome | o que é |",
        "|---|---|---|",
        "| 0 | — | tipo da entidade |",
        "| 5 | handle | identificador único no desenho |",
        "| 8 | layer | camada |",
        "| 6 | linetype | tipo de linha (`BYLAYER` se omitido) |",
        "| 62 | color | cor ACI (256 = BYLAYER) |",
        "| 370 | lineweight | espessura em centésimos de mm |",
        "| 48 | ltscale | escala do tipo de linha |",
        "| 67 | paperspace | 1 = espaço do papel |",
        "| 410 | layout | nome do layout |",
        "| 330 | owner | dono (bloco/espaço) |",
        "",
    ]

    outros = sorted({
        (tipo, c["codigo"], c["nome"])
        for tipo, d in entidades.items()
        for c in d["campos"]
        if "angle" in c["nome"].lower() and c["codigo"] not in (50, 51)
    })
    if outros:
        linhas += [
            "## Outros campos com \"angle\" no nome",
            "",
            "São ângulo, mas a regra de radiano foi confirmada só em 50/51. Se usar",
            "algum destes, teste e registre no `historico/` — não assuma.",
            "",
            "| entidade | código | campo |",
            "|---|---|---|",
        ]
        for tipo, codigo, nome in outros:
            linhas.append(f"| `{tipo}` | {codigo} | `{nome}` |")
        linhas.append("")

    linhas += [
        f"**{len(entidades)}** entidades mapeadas. Tabela completa em",
        "`catalogo-entidades.json`.",
        "",
        "## Entidades em destaque",
        "",
    ]

    for tipo in DESTAQUE:
        dados = entidades.get(tipo)
        if not dados:
            linhas += [f"### {tipo}", "", "_não encontrada no ezdxf_", ""]
            continue
        linhas += [f"### {tipo}", "", "| código | campo | tipo | padrão |", "|---|---|---|---|"]
        for campo in dados["campos"]:
            if campo["codigo"] in COMUNS:
                continue
            marca = " ⚠" if campo["tipo"] == "angulo" else ""
            linhas.append(
                f"| {campo['codigo']} | `{campo['nome']}`{marca} | {campo['tipo']} | {campo['padrao']} |")
        linhas.append("")

    # resumo de todas
    linhas += ["## Todas as entidades", "", "| DXF | classe ezdxf | campos |", "|---|---|---|"]
    for tipo in sorted(entidades):
        d = entidades[tipo]
        linhas.append(f"| `{tipo}` | `{d['classe']}` | {len(d['campos'])} |")
    linhas.append("")

    (DOCS / "MAPA-ENTIDADES.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"ok: docs/MAPA-ENTIDADES.md e docs/catalogo-entidades.json")
    print(f"   {len(entidades)} entidades, "
          f"{sum(len(d['campos']) for d in entidades.values())} campos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
