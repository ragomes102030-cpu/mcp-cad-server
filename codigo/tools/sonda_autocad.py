# -*- coding: utf-8 -*-
"""Sonda o AutoCAD ABERTO e mapeia o que ele realmente tem: comandos e variaveis.

Le do proprio programa, nao da documentacao:
    (atoms-family 1)  -> todos os simbolos;  C:XXX = comando;  XXX = variavel
    (getvar "XXX")    -> valor atual (so leitura, nao altera nada)

O que sai:
    docs/catalogo-autocad.json   -- dados brutos (comandos, variaveis, valores)
    docs/MAPA-AUTOCAD.md         -- resumo legivel + listas de risco

Nada aqui abre dialogo, muda desenho ou salva arquivo. Toda leitura vai dentro de
`vl-catch-all-apply`, entao simbolo que nao e variavel simplesmente nao responde.

Uso:
    python tools/sonda_autocad.py            # usa o AutoCAD ja aberto
    python tools/sonda_autocad.py --json     # imprime o resumo em JSON
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

DOCS = RAIZ.parent / "docs"
CHUNK = 150

# comandos que historicamente abrem caixa de dialogo
RISCO = (
    "WBLOCK|LAYER|PLOT|INSERT|XREF|PURGE|SAVEAS|OPEN|IMAGE|DIMSTYLE|STYLE|UNITS|"
    "OPTIONS|HATCH|BLOCK|GROUP|TABLE|FIELD|DATAEXTRACTION|ATTEXT|IMPORT|EXPORT|"
    "PREVIEW|PUBLISH|SSM|SHEETSET|EATTEXT|QSELECT|FILTER|BATTMAN|SCALETEXT|"
    "MLEDIT|SPLINEDIT|PEDIT|HATCHEDIT|REFEDIT|XATTACH|ATTACH|PDFATTACH|PLOTSTYLE"
)

# variaveis que decidem se a automacao trava ou nao
CRITICAS = (
    "FILEDIA", "CMDDIA", "ATTDIA", "EXPERT", "SECURELOAD", "TRUSTEDPATHS",
    "CMDECHO", "OSMODE", "INSUNITS", "MEASUREMENT", "LUPREC", "LUNITS", "DIMZIN",
    "QAFLAGS", "CMDACTIVE", "SDI", "LISPINIT", "ACADVER", "PRODUCT", "LOCALE",
    "DWGPREFIX", "DWGNAME", "DWGTITLED", "PROXYSHOW", "XLOADCTL", "DEMANDLOAD",
    "LEGACYCODESEARCH", "AUTOSNAP", "GRIDMODE", "UCSFOLLOW", "TARGET", "VIEWDIR",
)


def lisp_lista(valores: list[str]) -> str:
    return "(" + " ".join('"%s"' % v.replace("\\", "/") for v in valores) + ")"


def main(argv: list[str]) -> int:
    from cad_mcp.com_backend import ComBackend

    b = ComBackend()
    t0 = time.perf_counter()
    r = asyncio.run(b.initialize())
    if not r.ok:
        print("SEM AUTOCAD: %s" % r.error)
        return 2
    inicial = r.payload
    print("conectado: %s" % inicial)

    # ------------------------------------------------------------------ 1. simbolos
    print("\n1) lendo (atoms-family 1)...")
    t = time.perf_counter()
    r = b._aval("(mapcar 'vl-symbol-name (atoms-family 1))", timeout=120)
    if not r.ok:
        print("falhou: %s" % r.error)
        return 1
    simbolos = [str(s) for s in (r.payload or [])]
    comandos = sorted(s for s in simbolos if s.upper().startswith("C:"))
    print("   %d simbolos, %d comandos (C:*), %.1f s"
          % (len(simbolos), len(comandos), time.perf_counter() - t))

    # ------------------------------------------------------------- 2. variaveis
    print("\n2) testando quais simbolos respondem a (getvar)...")
    t = time.perf_counter()
    expr = (
        "(vl-remove-if-not"
        " '(lambda (s) (not (vl-catch-all-error-p (vl-catch-all-apply 'getvar (list s)))))"
        " (mapcar 'vl-symbol-name (atoms-family 1)))"
    )
    r = b._aval(expr, timeout=120)
    if not r.ok:
        print("falhou: %s" % r.error)
        return 1
    variaveis = sorted(str(s) for s in (r.payload or []))
    print("   %d variaveis, %.1f s" % (len(variaveis), time.perf_counter() - t))

    print("\n3) lendo valores em blocos de %d..." % CHUNK)
    valores: dict[str, str] = {}
    for i in range(0, len(variaveis), CHUNK):
        bloco = variaveis[i:i + CHUNK]
        expr = (
            "(mapcar '(lambda (s) (list s (vl-princ-to-string"
            " (vl-catch-all-apply 'getvar (list s))))) %s)" % lisp_lista(bloco)
        )
        r = b._aval(expr, timeout=120)
        if not r.ok:
            print("   bloco %d falhou: %s" % (i // CHUNK, r.error))
            continue
        for par in r.payload or []:
            if isinstance(par, (list, tuple)) and len(par) >= 2:
                valores[str(par[0])] = str(par[1])
        print("   %d/%d" % (min(i + CHUNK, len(variaveis)), len(variaveis)))

    # ---------------------------------------------------------------- 4. relatorio
    presentes = set(comandos)
    com_variante = [c for c in comandos if ("-" + c) in presentes]
    riscos = []
    for c in comandos:
        nome = c[2:]
        if any(k in nome.upper() for k in RISCO.split("|")):
            riscos.append({"comando": c, "variante": ("-" + c) in presentes})
    criticas = {n: valores.get(n) for n in CRITICAS if n in valores}

    dados = {
        "quando": datetime.now().astimezone().isoformat(timespec="seconds"),
        "acad": inicial,
        "contagem": {"simbolos": len(simbolos), "comandos": len(comandos),
                     "variaveis": len(variaveis)},
        "comandos": comandos,
        "com_variante_de_linha": com_variante,
        "variaveis": valores,
        "criticas": criticas,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "catalogo-autocad.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")

    _escrever_mapa(dados, riscos, presentes)
    print("\ngerado: docs/MAPA-AUTOCAD.md e docs/catalogo-autocad.json")

    sem_variante = [r_ for r_ in riscos if not r_["variante"]]
    print("\nresumo: %d comandos, %d com variante '-', %d comandos de risco (%d sem variante)"
          % (len(comandos), len(com_variante), len(riscos), len(sem_variante)))
    print("variaveis: %d | criticas presentes: %d/%d" % (len(variaveis), len(criticas), len(CRITICAS)))
    print("tempo total: %.1f s" % (time.perf_counter() - t0))
    if "--json" in argv:
        print(json.dumps({"contagem": dados["contagem"], "criticas": criticas},
                         ensure_ascii=False, indent=2))
    return 0


def _escrever_mapa(d: dict, riscos: list[dict], presentes: set[str]) -> None:
    c = d["contagem"]
    linhas = [
        "# Mapa do AutoCAD (lido do programa, não da documentação)",
        "",
        "Fonte: `(atoms-family 1)` + `(getvar)` na sessão de %s. Gerado por "
        "`tools/sonda_autocad.py`; não editar à mão." % d["quando"],
        "",
        "| | |",
        "|---|---|",
        "| símbolos | %d |" % c["simbolos"],
        "| comandos (`C:*`) | %d |" % c["comandos"],
        "| comandos com variante `-` | %d |" % len(d["com_variante_de_linha"]),
        "| variáveis de sistema | %d |" % c["variaveis"],
        "",
        "## O que decide se a automação trava",
        "",
        "| variável | valor agora | por que importa |",
        "|---|---|---|",
    ]
    notas = {
        "FILEDIA": "1 = abre caixa de arquivo em SAVEAS/OPEN/WBLOCK. Automatizar com 1 é travar.",
        "CMDDIA": "1 = diálogo em PLOT/LAYER. Igual acima.",
        "ATTDIA": "1 = diálogo ao inserir bloco com atributos.",
        "EXPERT": "5 suprime perguntas de rotina em alguns comandos.",
        "SECURELOAD": "0 = aceita carregar código sem perguntar (cuidado).",
        "INSUNITS": "6 = metro (é o nosso padrão).",
        "MEASUREMENT": "1 = métrico (2 = polegadas).",
        "QAFLAGS": "bits de eco/regeneracao de LISP; 2 costuma ajudar em script.",
        "CMDACTIVE": "!= 0 significa comando em andamento: nunca chamar COM agora.",
    }
    for nome, valor in d["criticas"].items():
        linhas.append("| `%s` | `%s` | %s |" % (nome, valor, notas.get(nome, "")))

    linhas += ["", "## Comandos que historicamente abrem diálogo", "",
               "`variante` = existe `C:<comando com hífen>` (a versão de linha de comando).",
               "Sem variante, o caminho é `FILEDIA=0`/`CMDDIA=0` — ou não usar.", "",
               "| comando | variante `-` | |", "|---|---|---|"]
    for r_ in sorted(riscos, key=lambda x: (x["variante"], x["comando"])):
        marca = "sim" if r_["variante"] else "**não**"
        linhas.append("| `%s` | %s | |" % (r_["comando"], marca))

    sem = [r_ for r_ in riscos if not r_["variante"]]
    linhas += ["", "## Sinais de que dá para automatizar com segurança", "",
               "- o comando tem `-`variante → use a variante;",
               "- a variável crítica está no valor esperado (`FILEDIA=0`, `CMDDIA=0`);",
               "- o comando aparece como `C:XXX` (é comando real, não alias de menu).", "",
               "Comandos de risco sem variante: %d — esses exigem `FILEDIA=0` "
               "ou caminho alternativo (entidade direta)." % len(sem)]
    (DOCS / "MAPA-AUTOCAD.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
