# -*- coding: utf-8 -*-
"""Gravador de prompts: descobre o que cada comando PEDE, para poder dirigi-lo.

O mapa de comandos (`MAPA-AUTOCAD.md`) diz que `TRIM` existe; nao diz que ele
espera "Select cutting edges" e depois "Select object to trim". Sem isso, mandar
`_.TRIM` e torcer — foi o que falhou.

Metodo: iniciar o comando, CANCELAR, e ler `(getvar "LASTPROMPT")` — o ultimo
prompt fica guardado depois do cancelamento. Nada roda de verdade.

Por que em DUAS FASES (e nao tudo de uma vez):
    Ler variavel de sistema enquanto um comando espera selecao TRAVA o COM e o
    AutoCAD para de responder (ver historico: `editor-command-trava-autocad`).
    Separando, o pior caso e' um comando pendente que voce cancela com ESC.

Uso:
    python tools/mapear_comandos.py --lista
    python tools/mapear_comandos.py --iniciar TRIM          # manda TRIM e cancela
    python tools/mapear_comandos.py --ler TRIM              # le o prompt e grava

Grava em `historico/prompts.jsonl` (append-only).

Se o `--ler` ficar parado, o comando nao foi cancelado: aperte ESC no AutoCAD e
rode de novo.
"""
from __future__ import annotations

import argparse
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
HIST = RAIZ / "historico"
CATALOGO = RAIZ / "docs" / "catalogo-autocad.json"


def _doc():
    import win32com.client as w

    return w.GetActiveObject("AutoCAD.Application").ActiveDocument


def candidatos() -> list[str]:
    if not CATALOGO.exists():
        return []
    dados = json.loads(CATALOGO.read_text(encoding="utf-8"))
    c = dados.get("comandos", {})
    nomes = set(c.get("c_simbolo", [])) | set(c.get("cuix", []))
    lixo = {"CLOSE", "QUIT", "EXIT", "NEW", "OPEN", "SAVEAS", "QSAVE", "PLOT", "PUBLISH",
            "OPTIONS", "NETLOAD", "SCRIPT", "DEL", "UNDEFINE", "REDEFINE", "RECOVER"}
    return sorted(n for n in nomes if n.isalpha() and n.upper() not in lixo)


def iniciar(nome: str, cancelar: bool) -> int:
    doc = _doc()
    doc.SendCommand(f"_.{nome}\n")
    print(f"enviado: _.{nome}")
    time.sleep(0.8)
    if cancelar:
        # ESC = cancelar. SendCommand nao espera resposta, entao nao trava.
        doc.SendCommand("\x1b")
        time.sleep(0.4)
        doc.SendCommand("\x1b")
        print("cancelado (2x ESC)")
    print("agora: python tools/mapear_comandos.py --ler " + nome)
    return 0


def ler(nome: str) -> int:
    doc = _doc()
    try:
        prompt = doc.GetVariable("LASTPROMPT")
    except Exception as exc:  # noqa: BLE001
        print(f"nao consegui ler ({str(exc)[:60]}).")
        print("se o AutoCAD estiver parado, aperte ESC na tela e rode de novo.")
        return 1

    registro = {
        "quando": datetime.now().astimezone().isoformat(timespec="seconds"),
        "comando": nome,
        "prompt": prompt,
    }
    HIST.mkdir(exist_ok=True)
    with (HIST / "prompts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    print(f"{nome}: {prompt!r}")
    print(f"gravado em {HIST / 'prompts.jsonl'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Grava o prompt de um comando (2 fases).")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--iniciar", metavar="COMANDO")
    ap.add_argument("--ler", metavar="COMANDO")
    ap.add_argument("--sem-cancelar", action="store_true", help="nao manda ESC; cancele na mao")
    args = ap.parse_args()

    if args.lista:
        nomes = candidatos()
        print(f"{len(nomes)} candidatos:")
        print(" ".join(nomes))
        return 0

    try:
        if args.iniciar:
            return iniciar(args.iniciar, cancelar=not args.sem_cancelar)
        if args.ler:
            return ler(args.ler)
    except Exception as exc:  # noqa: BLE001
        print(f"falhou: {exc}")
        print("o AutoCAD esta aberto, com um desenho?")
        return 1

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
