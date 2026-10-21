# -*- coding: utf-8 -*-
"""Mapeia o COM do AutoCAD a partir da type library oficial (sem abrir o AutoCAD).

Fonte: `C:\\Program Files\\Common Files\\Autodesk Shared\\acax25enu.tlb`
(47 MB de verdade espalhada em 476 KB de metadados). O comtypes le a TLB e gera
interfaces com `_methods_`: `_get_X`/`_set_X` sao propriedade, o resto e metodo.

Isso responde com dado, nao com opiniao:
    - quantos objetos/metodos o COM expoe;
    - o que AcadDocument e AcadModelSpace sabem fazer;
    - se existe metodo para TRIM/EXTEND/FILLET/OFFSET (a resposta e a base do
      plugin .NET: o que nao for metodo tem de ser comando).

Tambem le `acad.pgp` (apelidos de comando) e os macros do `acad.CUIX`, para
cruzar: comando de menu x comando de API.

Uso:
    python tools/mapear_com.py [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ.parent / "docs"
TLB = Path(r"C:\Program Files\Common Files\Autodesk Shared\acax25enu.tlb")
PGP = Path(os.environ["APPDATA"]) / r"Autodesk\AutoCAD 2025\R25.0\enu\Support\acad.pgp"
CUIX = PGP.parent / "acad.CUIX"

# Nomes reais da TLB. Nao existe IAcadModelSpace: ModelSpace/PaperSpace
# sao IAcadBlock (o mesmo objeto que AddLine/AddCircle vivem).
ALVO = [
    "IAcadApplication", "IAcadDocument", "IAcadDatabase", "IAcadBlock",
    "IAcadBlocks", "IAcadEntity", "IAcadLine", "IAcadArc", "IAcadCircle",
    "IAcadLWPolyline", "IAcadPolyline", "IAcadText", "IAcadMText",
    "IAcadHatch", "IAcadDimension", "IAcadDimRotated", "IAcadDimAligned",
    "IAcadSelectionSet", "IAcadSelectionSets", "IAcadLayout", "IAcadLayouts",
    "IAcadPlot", "IAcadPlotConfiguration", "IAcadAttributeReference",
    "IAcadBlockReference", "IAcadGroup", "IAcadGroups", "IAcadLayer",
    "IAcadLayers", "IAcadAcCmColor", "IAcadRegion", "IAcadTable",
    "IAcadPreferences", "IAcadUtility", "IAcadState",
]

TERMOS = ("trim", "extend", "fillet", "chamfer", "offset", "boundary", "join", "explode",
          "mirror", "rotate", "move", "copy", "erase", "array", "stretch", "scale")


def ler_com() -> dict:
    import comtypes.client as cc
    mod = cc.GetModule(str(TLB))
    classes = {}
    for nome in dir(mod):
        obj = getattr(mod, nome)
        metodos = getattr(obj, "_methods_", None)
        if not metodos:
            continue
        props, funcoes = {}, []
        for m in metodos:
            nome_m = m[1]
            if nome_m.startswith("_get_"):
                props.setdefault(nome_m[5:], {"get": True, "set": False})["get"] = True
            elif nome_m.startswith("_set_"):
                props.setdefault(nome_m[5:], {"get": False, "set": False})["set"] = True
            elif nome_m.startswith("_put_"):
                continue
            else:
                funcoes.append(nome_m)
        classes[nome] = {
            "metodos": sorted(funcoes),
            "propriedades": sorted(props),
            "prop_escrita": sorted(k for k, v in props.items() if v["set"]),
        }
    return classes


def ler_pgp() -> list[tuple[str, str]]:
    """Apelidos do acad.pgp: `A, *ARC` -> (A, ARC).

    O arquivo nao usa secoes `[X]`; o que separa apelido de comando externo e o
    asterisco. Comando externo (`DEL, DEL, 8,...`) nao tem `*` e fica de fora.
    """
    if not PGP.exists():
        return []
    pares = []
    for linha in PGP.read_text(encoding="latin-1").splitlines():
        s = linha.strip()
        if not s or s.startswith(";"):
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*,\s*\*([A-Za-z0-9_\-]+)\s*$", s)
        if m:
            pares.append((m.group(1).upper(), m.group(2).upper()))
    return pares


def ler_cui() -> dict[str, bool]:
    """Comandos chamados por macro de menu: `^C^C_wblock` -> {WBLOCK: False}.

    O valor diz se o macro usa a variante com hifen (`-wblock`), que e a pista
    de "linha de comando, sem dialogo". So o primeiro token depois de ^C^C conta;
    o resto sao respostas/opcoes, nao comandos.
    """
    if not CUIX.exists():
        return {}
    with zipfile.ZipFile(CUIX) as z:
        xml = z.read("MenuGroup.cui").decode("utf-8", errors="replace")
    macros = re.findall(r"<Command>([^<]*)</Command>", xml)
    achados: dict[str, bool] = {}
    ignorar = {"COMMAND", "SETVAR", "PROGN", "IF", "PROMPT", "PRINC", "GETVAR",
               "VL", "LOAD", "MENUCMD", "PAUSE", "BACKSLASH"}
    for mac in macros:
        for m in re.finditer(r"\^C\^C\^?C?\s*[_.]*(-?)([A-Za-z][A-Za-z0-9_]{1,30})", mac):
            nome = m.group(2).upper()
            if nome in ignorar:
                continue
            achados[nome] = achados.get(nome, False) or bool(m.group(1))
    return achados


def main(argv: list[str]) -> int:
    if not TLB.exists():
        print("type library nao encontrada: %s" % TLB)
        return 2
    print("lendo %s ..." % TLB)
    classes = ler_com()
    total_m = sum(len(c["metodos"]) for c in classes.values())
    total_p = sum(len(c["propriedades"]) for c in classes.values())
    print("   %d interfaces, %d metodos, %d propriedades" % (len(classes), total_m, total_p))

    aliases = ler_pgp()
    menus = ler_cui()
    comandos_menu = sorted(menus)
    com_hifen = sorted(n for n, h in menus.items() if h)
    print("   %d apelidos (pgp), %d comandos em macro (cui), %d usados com hifen"
          % (len(aliases), len(comandos_menu), len(com_hifen)))

    # existe metodo de edicao no COM?
    achados = {}
    for termo in TERMOS:
        onde = [(c, m) for c, d in classes.items() for m in d["metodos"] if termo in m.lower()]
        achados[termo] = onde

    dados = {
        "quando": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tlb": str(TLB),
        "totais": {"interfaces": len(classes), "metodos": total_m, "propriedades": total_p},
        "classes": classes,
        "aliases": aliases,
        "comandos_menu": comandos_menu,
        "comandos_menu_hifen": com_hifen,
        "metodos_de_edicao": {k: [f"{c}.{m}" for c, m in v] for k, v in achados.items()},
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "com-acad-2025.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")

    linhas = [
        "# Mapa do COM do AutoCAD 2025 (type library oficial)",
        "",
        "Fonte: `%s` (lida com `comtypes`; o AutoCAD não precisa estar aberto)." % TLB.name,
        "Gerado por `tools/mapear_com.py` em %s. Não editar à mão." % dados["quando"],
        "",
        "| | |",
        "|---|---|",
        "| interfaces | %d |" % len(classes),
        "| métodos | %d |" % total_m,
        "| propriedades | %d |" % total_p,
        "| apelidos de comando (`acad.pgp`) | %d |" % len(aliases),
        "| comandos citados em macro de menu | %d |" % len(comandos_menu),
        "",
        "## O teste que importa: existe método de edição?",
        "",
        "| operação | método COM encontrado |",
        "|---|---|",
    ]
    for termo in TERMOS:
        lista = dados["metodos_de_edicao"][termo]
        linhas.append("| `%s` | %s |" % (termo, ", ".join("`%s`" % x for x in lista) or "**nenhum**"))

    linhas += ["", "## Objetos que usamos de perto", "",
               "ModelSpace e PaperSpace **são** `IAcadBlock` (não existe `IAcadModelSpace`).",
               "Método herdado aparece só na interface base: `AddLine` está em `IAcadBlock`,",
               "não em `IAcadDocument`.", ""]
    for nome in ALVO:
        d = classes.get(nome)
        if not d:
            continue
        linhas.append("### %s — %d métodos, %d propriedades" % (nome, len(d["metodos"]),
                                                               len(d["propriedades"])))
        if d["metodos"]:
            linhas.append("")
            linhas.append("`" + "`, `".join(d["metodos"][:28]) + "`"
                          + (" …" if len(d["metodos"]) > 28 else ""))
        linhas.append("")

    linhas += ["## Os 15 objetos com mais métodos", "", "| objeto | métodos |", "|---|---|"]
    for nome, d in sorted(classes.items(), key=lambda kv: -len(kv[1]["metodos"]))[:15]:
        linhas.append("| `%s` | %d |" % (nome, len(d["metodos"])))

    (DOCS / "MAPA-COM.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    al = ["# Apelidos de comando (acad.pgp)", "",
          "%d apelidos lidos de `%s`." % (len(aliases), PGP), "",
          "| apelido | comando |", "|---|---|"]
    for a, c in aliases:
        al.append("| `%s` | `%s` |" % (a, c))
    (DOCS / "ALIASES.md").write_text("\n".join(al) + "\n", encoding="utf-8")

    print("\ngerado: docs/MAPA-COM.md, docs/com-acad-2025.json, docs/ALIASES.md")
    for termo in ("trim", "extend", "fillet", "offset"):
        print("  %-7s -> %s" % (termo, dados["metodos_de_edicao"][termo] or "nenhum metodo COM"))
    if "--json" in argv:
        print(json.dumps(dados["totais"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
