# -*- coding: utf-8 -*-
"""Transforma `docs/catalogo-dotnet.json` no mapa legivel `docs/MAPA-DOTNET.md`.

O JSON sai do `tools/MapaDotnet` (metadata das DLLs gerenciadas do AutoCAD).
Aqui so organizamos: contagem, o que o COM nao tem e o .NET tem, e as classes
que vamos usar. Nenhuma capacidade e afirmada sem estar no catalogo: a tabela
de "o que o .NET resolve" e conferida membro por membro.

Uso:
    python tools/resumir_dotnet.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ.parent / "docs"
ENTRADA = DOCS / "catalogo-dotnet.json"
SAIDA = DOCS / "MAPA-DOTNET.md"

# (o que queremos fazer, classe, membro, por que importa)
CAPACIDADES = [
    ("Cortar curva por intersecoes", "Curve", "GetSplitCurves", "TRIM/EXTEND sem comando"),
    ("Onde a curva cruza outra", "Entity", "IntersectWith", "achar o ponto de corte"),
    ("Ponto mais proximo na curva", "Curve", "GetClosestPointTo", "saber qual trecho apagar"),
    ("Parametro no ponto", "Curve", "GetParameterAtPoint", "dividir no lugar certo"),
    ("Hatch com contorno proprio", "Hatch", "AppendLoop", "preencher ambiente desenhado por nos"),
    ("Hatch: padrao", "Hatch", "SetHatchPattern", "escolher o padrao sem dialogo"),
    ("Tabela: escrever celula", "Table", "SetTextString", "selo/quantitativo de verdade"),
    ("Tabela: celulas", "Table", "Cells", "formatar coluna/linha"),
    ("Bloco dinamico: propriedades", "BlockReference", "DynamicBlockReferencePropertyCollection", "mudar visibilidade/medida do bloco"),
    ("Atributos do bloco", "AttributeCollection", "GetEnumerator", "ler/escrever ATTDEF"),
    ("Campo (Field)", "Field", "GetFieldCode", "texto que se atualiza sozinho"),
    ("Layouts", "LayoutManager", "CurrentLayout", "prancha e viewport"),
    ("Plotagem", "PlotEngine", "BeginPlot", "PDF/DWF sem depender do driver"),
    ("Validar plot", "PlotSettingsValidator", "SetPlotWindowArea", "enquadrar sem Extents"),
    ("XData", "DBObject", "GetXDataForApplication", "guardar dado nosso no desenho"),
    ("Dicionario da entidade", "DBObject", "ExtensionDictionary", "pendurar dado sem XData"),
    ("Multi-leader", "MLeader", "MText", "texto com seta"),
    ("Dimensao: medir", "Dimension", "Measurement", "conferir cota"),
    ("Regenerar", "Editor", "Regen", "atualizar tela apos editar"),
    ("Selecionar por filtro", "Editor", "SelectAll", "pecas sem clique"),
    ("Transacao", "Transaction", "Commit", "editar em lote"),
]

# Classes que merecem uma secao propria: (classe, quantos membros mostrar)
SECOES = [
    ("Curve", 18),
    ("Hatch", 10),
    ("Table", 12),
    ("BlockReference", 10),
    ("Editor", 12),
    ("Database", 10),
    ("Transaction", 6),
    ("LayoutManager", 6),
    ("PlotEngine", 6),
    ("Polyline", 12),
]


def carregar() -> dict:
    if not ENTRADA.exists():
        raise SystemExit(
            f"falta {ENTRADA}.\nRode antes: tools\\MapaDotnet\\bin\\Release\\net8.0\\MapaDotnet.exe "
            f"docs\\catalogo-dotnet.json <acdbmgd.dll> <acmgd.dll> <accoremgd.dll>"
        )
    return json.loads(ENTRADA.read_text(encoding="utf-8"))


def main() -> int:
    dados = carregar()
    tipos = dados["tipos"]
    assemblies = dados.get("assemblies", {})

    # construtor nao e' capacidade; sobrecarga repetida nao acrescenta
    for t in tipos:
        vistos, limpos = set(), []
        for m in t.get("m", []):
            if m.startswith("."):
                continue
            if m in vistos:
                continue
            vistos.add(m)
            limpos.append(m)
        t["m"] = limpos

    por_nome: dict[str, list[dict]] = {}
    for t in tipos:
        por_nome.setdefault(t["t"], []).append(t)

    def achar(classe: str, membro: str | None = None):
        for t in por_nome.get(classe, []):
            if membro is None:
                return t
            if any(m.split("/")[0] == membro for m in t.get("m", [])) or membro in t.get("p", []):
                return t
        return None

    linhas = [
        "# Mapa do .NET do AutoCAD — medido nas DLLs",
        "",
        f"Gerado em **{dados.get('gerado_em', '?')}** a partir da metadata de "
        + ", ".join(f"`{a}.dll`" for a in assemblies) + ".",
        "",
        "Não é documentação da Autodesk: é o que **existe de fato** nestas DLLs. "
        "Nomes de parâmetros não foram lidos (só a contagem) — o mapa diz que o "
        "membro existe, não a assinatura completa.",
        "",
        "| assembly | tipos públicos com membros |",
        "|---|---|",
    ]
    for a, n in assemblies.items():
        linhas.append(f"| `{a}.dll` | {n} |")
    linhas += ["", f"**Total: {len(tipos)} tipos.**", ""]

    # ---- o que o COM nao resolve ----
    linhas += [
        "## O que o COM não resolve (e o .NET resolve)",
        "",
        "| fazer | membro | existe? | onde |",
        "|---|---|---|---|",
    ]
    faltando = []
    for _oque, classe, membro, _porque in CAPACIDADES:
        t = achar(classe, membro)
        if t:
            linhas.append(f"| {_oque} | `{classe}.{membro}` | **sim** | `{t['ns']}.{t['t']}` |")
        else:
            faltando.append(f"{classe}.{membro}")
            linhas.append(f"| {_oque} | `{classe}.{membro}` | **não achei** | — |")
    linhas.append("")

    if faltando:
        linhas += [
            "> Membros que não apareceram nesta leitura: " + ", ".join(f"`{f}`" for f in faltando)
            + ". Pode ser nome diferente, tipo interno, ou estar em outra DLL (`AcWindows`, `AcCui`, …).",
            "",
        ]

    # ---- secoes por classe ----
    linhas += ["## As classes que vamos usar", ""]
    for classe, limite in SECOES:
        achados = por_nome.get(classe, [])
        if not achados:
            linhas += [f"### {classe}", "", "_não encontrada_", ""]
            continue
        for t in achados[:2]:
            metodos = [m for m in t.get("m", [])]
            props = t.get("p", [])
            linhas += [
                f"### {t['t']}  ·  `{t['ns']}`",
                "",
                f"herda de `{t['b'] or '—'}`" + (f" · assembly `{t['a']}.dll`" if t.get("a") else ""),
                "",
            ]
            if metodos:
                mostra = metodos[:limite]
                linhas.append("métodos: " + ", ".join(f"`{m}`" for m in mostra)
                              + (f" … (+{len(metodos) - len(mostra)})" if len(metodos) > len(mostra) else ""))
            if props:
                mostra = props[:limite]
                linhas.append("")
                linhas.append("propriedades: " + ", ".join(f"`{p}`" for p in mostra)
                              + (f" … (+{len(props) - len(mostra)})" if len(props) > len(mostra) else ""))
            linhas.append("")

    # ---- onde ficam as coisas ----
    ns = Counter(t["ns"] for t in tipos)
    linhas += ["## Onde ficam as coisas", "", "| namespace | tipos |", "|---|---|"]
    for nome, n in ns.most_common(15):
        linhas.append(f"| `{nome or '(sem namespace)'}` | {n} |")
    linhas.append("")

    linhas += [
        "## O corte por geometria — o que substitui o TRIM",
        "",
        "O comando TRIM precisa de clique e não devolve resultado (ver `historico/`).",
        "Com os membros acima o corte vira conta, dentro de uma transação:",
        "",
        "1. `Entity.IntersectWith` entre a curva e cada corte → pontos de interseção;",
        "2. `Curve.GetParameterAtPoint` em cada ponto → parâmetros ordenados;",
        "3. `Curve.GetSplitCurves(pontos)` → as N partes;",
        "4. `Curve.GetClosestPointTo(ponto_do_clique)` em cada parte → a parte clicada;",
        "5. apagar essa parte e adicionar as outras, tudo no mesmo `Transaction.Commit`.",
        "",
        "Isso resolve TRIM e EXTEND sem tela, sem prompt e sem depender de `TRIMEXTENDMODE`.",
        "Falta implementar no plugin e testar com o AutoCAD aberto.",
        "",
    ]

    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"ok: {SAIDA} ({len(linhas)} linhas)")
    print(f"   {len(tipos)} tipos, {len(assemblies)} assemblies, {len(faltando)} membros nao achados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
