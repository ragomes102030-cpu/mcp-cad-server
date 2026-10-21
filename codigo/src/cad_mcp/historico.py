# -*- coding: utf-8 -*-
"""Historico de falhas -- a memoria que nao depende de mim lembrar.

A ideia e simples: **o que nao da certo vira experiencia**, mas so se ficar
registrado. Toda vez que um desenho falha (arco torto, PDF esmagado, DWG que
nao salva) fica aqui uma linha com o sintoma, o contexto e -- quando possivel
-- o menor modelo que reproduz o problema.

Arquivo: `historico/ocorrencias.jsonl` (uma linha JSON por ocorrencia,
append-only; nunca reescrevemos o passado). Contar ocorrencias = contar linhas.

Regra de promocao (importante):
    um sintoma NAO vira verificacao de codigo na primeira vez que aparece.
    So na TERCEIRA ocorrencia ele e promovido -- ver `promovidos()`.
    Antes disso, um sintoma pode ser ruido, ambiente, ou erro de quem chamou.

Uso:
    from cad_mcp.historico import registrar, ocorrencias, vezes, promovidos
    registrar("arco-graus-em-radianos", "arco de 90 saiu com 116,62",
              contexto={"arquivo": "probe_arco4.py"}, sugestao="usar angtof")

    python -m cad_mcp.historico                 # tabela
    python -m cad_mcp.historico --json          # tudo
    python -m cad_mcp.historico --chave X       # so um sintoma
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "DIR", "ARQUIVO", "registrar", "ocorrencias", "vezes", "promovidos",
    "limpar", "formatar_tabela",
]

DIR = Path(os.environ.get("MCP_CAD_SERVER",
                          str(Path(__file__).resolve().parents[2]))) / "historico"
ARQUIVO = DIR / "ocorrencias.jsonl"

MAX_EXEMPLOS = 3          # modelos guardados por sintoma (o resto vira contagem)
PROMOCAO = 3              # ocorrencias necessarias para virar verificacao


# ------------------------------------------------------------------ utilidades
def _slug(chave: str) -> str:
    """Chave estavel: minuscula, sem acento, hifens."""
    s = unicodedata.normalize("NFKD", str(chave))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "sem-chave"


def _agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _uma_linha(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


# --------------------------------------------------------------------- escrita
def registrar(chave: str, sintoma: str, modelo: dict | None = None,
              contexto: dict | None = None, sugestao: str = "",
              acadver: str | None = None) -> dict:
    """Grava UMA ocorrencia. Devolve o resumo acumulado do sintoma.

    `modelo` deve ser o menor dicionario que reproduz o problema (pode ser um
    recorte do modelo completo). Guardamos no maximo `MAX_EXEMPLOS` modelos.
    """
    chave = _slug(chave)
    antes = _resumo(chave)

    linha = {
        "quando": _agora(),
        "chave": chave,
        "sintoma": str(sintoma)[:400],
        "sugestao": str(sugestao)[:400],
        "acadver": acadver or os.environ.get("ACADVER"),
        "contexto": contexto or {},
    }
    if modelo and antes["vezes"] < MAX_EXEMPLOS:
        linha["modelo"] = modelo

    DIR.mkdir(parents=True, exist_ok=True)
    with ARQUIVO.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_uma_linha(linha) + "\n")
    return _resumo(chave)


def limpar(chave: str | None = None) -> int:
    """Apaga ocorrencias (de um sintoma ou todas). Devolve quantas sairam."""
    if not ARQUIVO.exists():
        return 0
    linhas = ARQUIVO.read_text(encoding="utf-8").splitlines()
    if chave is None:
        ARQUIVO.unlink()
        return len([l for l in linhas if l.strip()])
    alvo = _slug(chave)
    ficam, sairam = [], 0
    for l in linhas:
        if not l.strip():
            continue
        try:
            if json.loads(l).get("chave") == alvo:
                sairam += 1
                continue
        except ValueError:
            pass
        ficam.append(l)
    ARQUIVO.write_text("\n".join(ficam) + ("\n" if ficam else ""), encoding="utf-8")
    return sairam


# --------------------------------------------------------------------- leitura
def ocorrencias(chave: str | None = None) -> list[dict]:
    """Todas as ocorrencias, da mais antiga para a mais recente."""
    if not ARQUIVO.exists():
        return []
    alvo = _slug(chave) if chave else None
    out = []
    for n, linha in enumerate(ARQUIVO.read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip():
            continue
        try:
            obj = json.loads(linha)
        except ValueError:
            continue                      # linha corrompida nao derruba o resto
        if alvo and obj.get("chave") != alvo:
            continue
        obj.setdefault("linha", n)
        out.append(obj)
    return out


def _resumo(chave: str) -> dict:
    alvo = _slug(chave)
    ev = [o for o in ocorrencias() if o.get("chave") == alvo]
    if not ev:
        return {"chave": alvo, "vezes": 0, "primeira": None, "ultima": None,
                "sintoma": "", "sugestao": "", "promovido": False, "modelos": 0}
    return {
        "chave": alvo,
        "vezes": len(ev),
        "primeira": ev[0]["quando"],
        "ultima": ev[-1]["quando"],
        "sintoma": ev[-1].get("sintoma", ""),
        "sugestao": ev[-1].get("sugestao", ""),
        "promovido": len(ev) >= PROMOCAO,
        "modelos": sum(1 for o in ev if o.get("modelo")),
    }


def vezes(chave: str) -> int:
    return _resumo(chave)["vezes"]


def promovidos() -> list[str]:
    """Sintomas que atingiram a 3a ocorrencia e merecem virar verificacao."""
    return [r["chave"] for r in _todos() if r["promovido"]]


def _todos() -> list[dict]:
    chaves = []
    for o in ocorrencias():
        if o["chave"] not in chaves:
            chaves.append(o["chave"])
    resumos = [_resumo(c) for c in chaves]
    return sorted(resumos, key=lambda r: r["ultima"] or "", reverse=True)


def formatar_tabela(resumos=None) -> str:
    resumos = resumos if resumos is not None else _todos()
    if not resumos:
        return "historico vazio (%s)" % ARQUIVO
    largura = max(len(r["chave"]) for r in resumos)
    linhas = ["%-*s  %3s  %-6s  %s" % (largura, "CHAVE", "VEZ", "STATUS", "SINTOMA")]
    for r in resumos:
        status = "PROMOVER" if r["promovido"] else "observar"
        linhas.append("%-*s  %3d  %-6s  %s"
                      % (largura, r["chave"], r["vezes"], status, r["sintoma"][:70]))
    return "\n".join(linhas)


# ------------------------------------------------------------------------- CLI
def _main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if "--chave" in argv:
        chave = argv[argv.index("--chave") + 1]
        ev = ocorrencias(chave)
        if not ev:
            print("nenhuma ocorrencia de %r" % chave)
            return 1
        for o in ev:
            print("%s  %s" % (o["quando"], o["sintoma"]))
            if o.get("sugestao"):
                print("    -> %s" % o["sugestao"])
            if o.get("contexto"):
                print("    contexto: %s" % json.dumps(o["contexto"], ensure_ascii=False))
        return 0
    if "--json" in argv:
        print(json.dumps({"arquivo": str(ARQUIVO), "sintomas": _todos(),
                          "ocorrencias": ocorrencias()},
                         ensure_ascii=False, indent=2))
        return 0
    print(formatar_tabela())
    p = promovidos()
    if p:
        print("\nprontos para virar verificacao: %s" % ", ".join(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
