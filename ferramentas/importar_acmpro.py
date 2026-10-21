# -*- coding: utf-8 -*-
"""Importa o catalogo do autocad-mcp-pro e mede a nossa cobertura.

Le o codigo vendorizado (ast, sem importar -- ele exige Python 3.11) e compara
as ferramentas dele com as nossas em `src/cad_mcp/tools.py`.

Gera:
    docs/catalogo-acmpro.json   -- todas as ferramentas deles, com resumo/custo
    docs/COBERTURA.md           -- o que temos, o que falta, o que ignorar

Uso:
    python tools/importar_acmpro.py [--json] [--familia arquitetura]
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
VENDOR = RAIZ / "vendor" / "autocad-mcp-pro-1.6.0"
SERVER = VENDOR / "server.py"
NOSSO = RAIZ / "src" / "cad_mcp" / "tools.py"
DOCS = RAIZ / "docs"

# --------------------------------------------------------------- classificacao
# ordem importa: a primeira familia que casar leva a ferramenta
FAMILIAS = [
    ("arquitetura", r"wall|room|door|window|opening|stair|arch|partition|slab|roof|"
                    r"schedule|takeoff|bom|quantit|material"),
    ("mecanica", r"mech_|weld|gd_frame|datum|centre_mark|parts_list|gear|bearing"),
    ("P&ID", r"pid_|instrument|pipe_|valve|line_tag"),
    ("sistema", r"system_|document_|ucs_|cad_|preferences|launch|prompt_message|about|"
                 r"batch|\bdata_extract\b"),
    ("plot/arquivo", r"plot|print|pdf|page|layout|viewport|paper|titleblock|revision|"
                     r"save|open|close|new_drawing|dxf|dwg|export|import|attach|purge"),
    ("3D/solido", r"3d|solid|revolve|extrude|loft|sweep|mesh|surface|region|boolean|"
                  r"union|subtract|intersect"),
    ("bloco", r"block|insert|xref|attribute|attdef|attrib"),
    ("camada/estilo", r"layer|linetype|textstyle|dimstyle|style|plotstyle"),
    ("cota/anotacao", r"dim|leader|mleader|annotat|tolerance|gdt|balloon|callout|"
                      r"revision_cloud|wipeout"),
    ("texto", r"\btext\b|mtext|note|label|tag|field|spell"),
    ("consulta", r"get|list|count|query|inspect|info|measure|extents|snapshot|"
                 r"capabilit|system_variable|sysvar|describe|verify|validate|audit|"
                 r"health|status|explain|diff|understand|boundary|analysis|stats|"
                 r"bounding_box"),
    ("selecao", r"select|filter|find|search"),
    ("edicao", r"move|copy|rotate|scale|mirror|offset|trim|extend|fillet|chamfer|"
               r"array|erase|delete|explode|join|stretch|lengthen|break|align|"
               r"polar|edit|modify|change|replace|set_|undo|redo|transaction|"
               r"checkpoint|rollback|construction_clear"),
    ("visualizacao", r"zoom|view|vport|pan|render|screenshot|capture|png|show"),
    ("desenho", r"line|polyline|circle|arc|ellipse|spline|rectangle|rect|point|"
                r"hatch|gradient|polygon|donut|sketch|draw|curve|table|revcloud|"
                r"sheet_frame"),
]


def familia(nome: str) -> str:
    n = nome.lower()
    for fam, pat in FAMILIAS:
        if re.search(pat, n):
            return fam
    return "outros"


# ------------------------------------------------------------------ extracao
def _kw(no: ast.Call, chave: str):
    for k in no.keywords:
        if k.arg == chave:
            try:
                return ast.literal_eval(k.value)
            except (ValueError, SyntaxError):
                return None
    return None


def ler_deles() -> list[dict]:
    arvore = ast.parse(SERVER.read_text(encoding="utf-8"))
    saida = []
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nome = resumo = custo = None
        titulo = None
        for dec in no.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            alvo = ast.unparse(dec.func) if hasattr(ast, "unparse") else ""
            if alvo.endswith("mcp.tool") or alvo == "tool":
                nome = _kw(dec, "name") or nome
                ann = _kw(dec, "annotations")
                if isinstance(ann, dict):
                    titulo = ann.get("title")
            elif alvo.endswith("cad_tool"):
                resumo = _kw(dec, "summary") or resumo
                custo = _kw(dec, "cost") or custo
        if not resumo and not nome:
            continue
        publico = nome or no.name
        doc = (ast.get_docstring(no) or "").strip().splitlines()
        saida.append({
            "nome": publico,
            "funcao": no.name,
            "resumo": resumo or (doc[0] if doc else ""),
            "titulo": titulo,
            "custo": custo or "",
            "linha": no.lineno,
            "familia": familia(publico),
            "args": [a.arg for a in no.args.args if a.arg not in ("self", "ctx")],
        })
    # dedup por nome publico (o mesmo nome pode aparecer em mais de um registro)
    vistos, unicos = set(), []
    for f in sorted(saida, key=lambda x: x["linha"]):
        if f["nome"] in vistos:
            continue
        vistos.add(f["nome"])
        unicos.append(f)
    return unicos


def ler_nossos() -> list[str]:
    if str(RAIZ / "src") not in sys.path:
        sys.path.insert(0, str(RAIZ / "src"))
    try:
        from cad_mcp import tools as nosso
        itens = nosso.TOOLS
        nomes = []
        for t in itens:
            if isinstance(t, dict):
                nomes.append(t.get("name") or t.get("nome"))
            else:
                # nome PUBLICO (vocabulario do acmpro), nao o nome da funcao
                nomes.append(getattr(nosso, "nome_publico", lambda f: f.__name__)(t))
        return [n for n in nomes if n]
    except Exception as exc:                      # pragma: no cover
        print("aviso: nao consegui importar cad_mcp.tools (%s); usando regex" % exc)
        texto = NOSSO.read_text(encoding="utf-8")
        return sorted(set(re.findall(r'["\']name["\']\s*:\s*["\']([a-z0-9_]+)["\']', texto)))


# -------------------------------------------------------------------- relatorio
def main(argv: list[str]) -> int:
    deles = ler_deles()
    nossos = set(ler_nossos())
    familias = defaultdict(lambda: {"deles": [], "nossos": []})
    for f in deles:
        familias[f["familia"]]["deles"].append(f)
    for n in sorted(nossos):
        familias[familia(n)]["nossos"].append(n)

    comum = sum(1 for n in nossos if n in {f["nome"] for f in deles})
    total_fam = len(familias)

    DOCS.mkdir(exist_ok=True)
    (DOCS / "catalogo-acmpro.json").write_text(json.dumps({
        "origem": "autocad-mcp-pro 1.6.0 (MIT, U-C4N/Autocad-MCP)",
        "baixado": "2026-10-16",
        "ferramentas": deles,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    linhas = [
        "# Cobertura — nós × autocad-mcp-pro 1.6.0",
        "",
        "Gerado por `python tools/importar_acmpro.py`. Não editar à mão.",
        "",
        "| | deles | nossos | mesmo nome |",
        "|---|---|---|---|",
        "| total | %d | %d | %d |" % (len(deles), len(nossos), comum),
        "",
        "**Mesmo nome não é a mesma ferramenta.** `drawing_save` deles e o nosso fazem",
        "coisas diferentes nos detalhes. A comparação serve para achar **buraco**, não",
        "para dizer que já temos.",
        "",
        "## Por família",
        "",
        "| família | deles | nossos | faltando |",
        "|---|---|---|---|",
    ]
    for fam in sorted(familias, key=lambda f: -len(familias[f]["deles"])):
        d, n = familias[fam]["deles"], familias[fam]["nossos"]
        linhas.append("| %s | %d | %d | %d |" % (fam, len(d), len(n), max(0, len(d) - len(n))))

    linhas += ["", "## Nossas ferramentas, com o nome público",
               "",
               "| nossa | exposta como | existe no deles | resumo deles |",
               "|---|---|---|---|"]
    por_nome = {f["nome"]: f for f in deles}
    for nome in sorted(nossos):
        d = por_nome.get(nome)
        linhas.append("| %s | `%s` | %s | %s |"
                      % (nome, nome, "sim" if d else "**não**",
                         (d["resumo"][:70] if d else "só nossa")))

    linhas += ["", "## O que eles têm e nós não (candidatos, por família)", ""]
    for fam in sorted(familias, key=lambda f: -len(familias[f]["deles"])):
        d = [f for f in familias[fam]["deles"] if f["nome"] not in nossos]
        if not d:
            continue
        linhas.append("### %s (%d)" % (fam, len(d)))
        linhas.append("")
        for f in d[:40]:
            linhas.append("- `%s` — %s" % (f["nome"], f["resumo"][:96]))
        if len(d) > 40:
            linhas.append("- … mais %d" % (len(d) - 40))
        linhas.append("")

    (DOCS / "COBERTURA.md").write_text("\n".join(linhas), encoding="utf-8")

    print("deles: %d ferramentas em %d familias" % (len(deles), total_fam))
    print("nossos: %d" % len(nossos))
    print("mesmo nome: %d (%s)" % (comum, ", ".join(sorted(nossos & {f["nome"] for f in deles}))))
    print("\npor familia:")
    for fam in sorted(familias, key=lambda f: -len(familias[f]["deles"])):
        print("  %-14s eles %3d | nos %3d" % (fam, len(familias[fam]["deles"]),
                                             len(familias[fam]["nossos"])))
    print("\ngerado: docs/COBERTURA.md e docs/catalogo-acmpro.json")
    if "--json" in argv:
        print(json.dumps(Counter(f["familia"] for f in deles), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
