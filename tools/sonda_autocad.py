# -*- coding: utf-8 -*-
"""Sonda viva do AutoCAD: comandos e variaveis de sistema, com o valor de agora.

Por que existe: o `mapear_com.py` le a type library e o `acad.pgp` sem abrir o
AutoCAD, mas nao sabe o que esta carregado NESTA sessao nem quanto vale OSMODE,
FILEDIA, MEASUREMENT... Isso so da para ler de dentro, com o desenho aberto.

Onde cada lista vem (nada de achismo):
    comandos em LISP   `(atoms-family 1)` -> nomes "C:XXX"
    comandos de menu   macros do `acad.CUIX` (via mapear_com.ler_cui)
    apelidos           `acad.pgp` (via mapear_com.ler_pgp)
    sysvars            `MsiKeyFile_<NOME>.dll` na instalacao (603 nomes, um por
                       variavel localizavel) + `$VARS` do DXF + uma lista curta
                       das classicas que o MsiKeyFile nao lista
    valor              `(getvar "NOME")` ao vivo; devolve nil = nao existe aqui

O AutoCAD NAO expoe uma API de enumeracao de sysvars (nem COM, nem .NET, nem
LISP). Por isso a lista e de candidatos e o valor e que confirma: o que responde
nil nao entra no mapa.

Uso (AutoCAD aberto, com um desenho):
    python tools/sonda_autocad.py [--json]

Escreve `docs/catalogo-autocad.json` e `docs/MAPA-AUTOCAD.md`.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
DOCS.mkdir(parents=True, exist_ok=True)
AUTOCAD = Path(r"C:\Program Files\Autodesk\AutoCAD 2025")
MSI = AUTOCAD / "MsiKeyFile"
DXF = RAIZ / "saida" / "planta_3q.dxf"

# As classicas que importam para desenhar por codigo e que o MsiKeyFile (feito
# para localizacao) nao lista. Nao ha significado inventado aqui: so o nome.
CURADOS = """
OSMODE OSMISSING SNAPMODE SNAPUNIT SNAPBASE ORTHOMODE POLARMODE POLARADDANG
POLARANG GRIDMODE GRIDUNIT LIMCHECK LIMMIN LIMMAX PICKBOX APERTURE GRIPS
GRIPSIZE CMDECHO CMDDIA FILEDIA EXPERT INSUNITS INSUNITSDEFSOURCE
INSUNITSDEFTARGET MEASUREMENT LUNITS LUPREC AUNITS AUPREC ANGBASE ANGDIR
DIMASSOC DIMSCALE DIMTXT CLAYER CECOLOR CELTYPE LTSCALE PSLTSCALE MSLTSCALE
CELWEIGHT LWDISPLAY TEXTSIZE TEXTSTYLE MIRRTEXT FILLMODE ATTREQ ATTDIA
TRIMEXTENDMODE LEGACYCODESEARCH SECURELOAD TRUSTEDPATHS PEDITACCEPT
PROXYGRAPHICS XREFCTL DWGNAME DWGPREFIX DWGTTDESTAMP ACADVER
""".split()


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def nomes_msi() -> list[str]:
    """603 nomes declarados pela instalacao (MsiKeyFile_<NOME>.dll)."""
    if not MSI.is_dir():
        return []
    saida = []
    for f in MSI.glob("MsiKeyFile_*.dll"):
        nome = f.stem[len("MsiKeyFile_"):]
        if re.fullmatch(r"[A-Z0-9_]{2,40}", nome):
            saida.append(nome)
    return sorted(set(saida))


def nomes_dxf() -> list[str]:
    """Variaveis que o desenho salva (secao HEADER do DXF), lidas do exemplo."""
    if not DXF.exists():
        return []
    try:
        import ezdxf

        doc = ezdxf.readfile(str(DXF))
        return sorted({str(v).lstrip("$") for v in doc.header.varnames()})
    except Exception as exc:  # noqa: BLE001 - arquivo velho nao pode derrubar a sonda
        print(f"  (DXF ignorado: {exc})")
        return []


def fonte_comandos() -> dict[str, list[str]]:
    sys.path.insert(0, str(RAIZ / "tools"))
    try:
        import mapear_com

        apelidos = [cmd for _alias, cmd in mapear_com.ler_pgp()]
        cui = dict(mapear_com.ler_cui())
    except Exception as exc:  # noqa: BLE001
        print(f"  (pgp/CUIX ignorados: {exc})")
        apelidos, cui = [], {}
    return {"pgp": sorted(set(apelidos)), "cuix": sorted(cui), "cuix_com_hifen": sorted(
        c for c, hifen in cui.items() if hifen)}


def classificar(valor) -> str:
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, (list, tuple)):
        return "ponto/lista"
    if isinstance(valor, int):
        return "inteiro"
    if isinstance(valor, float):
        return "real"
    if valor is None:
        return "nulo"
    return "texto"


def main() -> int:
    from cad_mcp.com_backend import ComBackend

    print("conectando ao AutoCAD...")
    b = ComBackend()
    try:
        asyncio.run(b.initialize())
    except Exception as exc:  # noqa: BLE001
        print(f"falhou: {exc}\nAbra o AutoCAD, com um desenho, e tente de novo.")
        return 1

    def av(expr: str, timeout: int = 60):
        try:
            return b._aval(expr, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            class _R:
                ok = False
                payload = None
                error = str(exc)
            return _R()

    # ---- produto e desenho ----
    info = {}
    for chave, expr in (("acadver", '(getvar "ACADVER")'),
                        ("desenho", '(getvar "DWGNAME")'),
                        ("pasta", '(getvar "DWGPREFIX")')):
        r = av(expr)
        info[chave] = r.payload if r.ok else None
    print(f"  {info['acadver']} / {info['desenho']}")

    # ---- comandos ----
    print("1) simbolos de comando (atoms-family)...")
    r = av("(atoms-family 1)", timeout=120)
    nomes = [str(x) for x in (r.payload or [])] if r.ok else []
    c_simbolo = sorted({n[2:] for n in nomes if n.upper().startswith("C:") and len(n) > 2})
    fontes = fonte_comandos()
    todos_comandos = sorted(set(c_simbolo) | set(fontes["pgp"]) | set(fontes["cuix"]))
    print(f"   {len(nomes)} simbolos, {len(c_simbolo)} comandos C:, "
          f"{len(fontes['cuix'])} de menu, {len(fontes['pgp'])} apelidos")

    # ---- variaveis candidatas ----
    print("2) variaveis candidatas...")
    candidatas = set(nomes_msi()) | set(nomes_dxf()) | set(CURADOS)
    candidatas = sorted(c for c in candidatas if c and not c.startswith("$"))
    print(f"   {len(candidatas)} candidatas (MsiKeyFile + DXF + classicas)")

    print("3) lendo o valor de cada uma (getvar)...")
    t0 = time.perf_counter()
    sysvars: dict[str, dict] = {}
    ausentes: list[str] = []
    for i, nome in enumerate(candidatas, 1):
        r = av(f'(getvar "{nome}")', timeout=20)
        if r.ok and r.payload is not None:
            valor = r.payload
            if isinstance(valor, tuple):
                valor = list(valor)
            sysvars[nome] = {"valor": valor, "tipo": classificar(valor)}
        else:
            ausentes.append(nome)
        if i % 100 == 0:
            print(f"   {i}/{len(candidatas)}...")
    dur = round(time.perf_counter() - t0, 1)
    print(f"   {len(sysvars)} vivas, {len(ausentes)} ausentes ({dur}s)")

    # ---- grava ----
    dados = {
        "gerado_em": agora(),
        "produto": info,
        "comandos": {
            "total_uniao": len(todos_comandos),
            "c_simbolo": c_simbolo,
            "cuix": fontes["cuix"],
            "pgp": fontes["pgp"],
            "cuix_com_hifen": fontes["cuix_com_hifen"],
        },
        "sysvars": sysvars,
        "sysvars_ausentes": ausentes,
        "fontes": {
            "comandos_c": "(atoms-family 1) na sessao",
            "comandos_menu": "acad.CUIX",
            "apelidos": "acad.pgp",
            "sysvars": f"MsiKeyFile ({len(nomes_msi())}) + $VARS do DXF + {len(CURADOS)} classicas",
        },
    }
    (DOCS / "catalogo-autocad.json").write_text(
        json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")

    linhas = [
        "# Mapa do AutoCAD — medido ao vivo",
        "",
        f"Gerado em **{agora()}** por `tools/sonda_autocad.py`, com o AutoCAD aberto.",
        "",
        f"- Produto: `{info['acadver']}`",
        f"- Desenho: `{info['desenho']}` em `{info['pasta']}`",
        "",
        "## Comandos",
        "",
        "| fonte | quantos | o que prova |",
        "|---|---|---|",
        f"| `(atoms-family 1)` → `C:XXX` | {len(c_simbolo)} | comandos registrados em LISP nesta sessão |",
        f"| macros do `acad.CUIX` | {len(fontes['cuix'])} | comandos que o menu chama |",
        f"| `acad.pgp` | {len(fontes['pgp'])} | apelidos digitáveis |",
        f"| **união** | **{len(todos_comandos)}** | nomes distintos |",
        "",
        f"Com variante sem diálogo (`-COMANDO`) no menu: **{len(fontes['cuix_com_hifen'])}** — "
        + (", ".join(f"`-{c}`" for c in fontes["cuix_com_hifen"]) or "nenhuma"),
        "",
        "Um comando aparecer no menu **não** garante que exista nesta instalação "
        "(pode ser de um módulo não carregado). A lista de comandos em LISP é a "
        "que existe de fato.",
        "",
        "## Variáveis de sistema",
        "",
        f"**{len(sysvars)}** responderam a `(getvar)` e estão vivas; "
        f"{len(ausentes)} candidatas responderam `nil` (não existem aqui).",
        "",
        "| variável | tipo | valor agora |",
        "|---|---|---|",
    ]
    for nome in sorted(sysvars):
        v = sysvars[nome]
        texto = ", ".join(f"{x:g}" for x in v["valor"]) if isinstance(v["valor"], list) \
            else str(v["valor"])
        texto = texto.replace("|", "\\|")
        linhas.append(f"| `{nome}` | {v['tipo']} | `{texto}` |")

    if ausentes:
        linhas += ["", "### Candidatas que não existem nesta instalação", "",
                   ", ".join(f"`{n}`" for n in ausentes), ""]

    linhas += [
        "",
        "## Como isto foi medido",
        "",
        "- As variáveis não são enumeráveis por API (nem COM, nem .NET, nem LISP): "
        "os nomes vieram dos recursos da instalação (`MsiKeyFile_<NOME>.dll`), do "
        "cabeçalho do DXF de exemplo e de uma lista curta das clássicas.",
        "- O valor é o do momento da leitura. `FILEDIA`, `OSMODE` e companhia mudam "
        "com o uso; o mapa diz o que estava valendo, não o que deveria valer.",
        "- Ângulos em variável (`ANGBASE`, `POLARANG`) são **radianos** no `getvar` — "
        "a mesma regra do `entmake`.",
    ]
    (DOCS / "MAPA-AUTOCAD.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print(f"\nok: docs/MAPA-AUTOCAD.md e docs/catalogo-autocad.json")
    print(f"   {len(todos_comandos)} comandos, {len(sysvars)} variaveis vivas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
