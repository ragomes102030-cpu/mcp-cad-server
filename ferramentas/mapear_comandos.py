# -*- coding: utf-8 -*-
"""Gravador de prompts: descobre o que cada comando PEDE, para poder dirigi-lo.

O mapa de comandos (`MAPA-AUTOCAD.md`) diz que `TRIM` existe; nao diz que ele
espera "Select object to trim or shift-select to extend". Sem isso, mandar
`_.TRIM` e torcer.

DUAS FALHAS MEDIDAS no AutoCAD 2025 (20/10/2026) que explicam este codigo:

  1. `doc.SendCommand("_.LINE\n")` **bloqueia** enquanto o comando espera ponto.
     O `--iniciar` antigo travava para sempre (medido: 60 s e nao voltou).
     Quem inicia e' a ponte .NET (`SendStringToExecute`, assincrono, ~3 ms).
  2. `LASTPROMPT` lido por COM enquanto o comando esta' pendente devolve
     `RPC_E_CALL_REJECTED` ("A chamada foi rejeitada pelo chamado") e, depois do
     cancelamento, vira `'Command: *Cancel*'` -- o prompt NAO fica guardado.
     Quem le' e' a ponte, de dentro do processo (`CMDACTIVE` + `LASTPROMPT`,
     `plugin/CadMcpBridge/Ponte.cs:Confirmar`).
  3. `LASTPROMPT` guarda a **ultima linha** do command line (prompt + entrada
     ecoada), nao so' o prompt. Por isso o gravador manda um ponto neutro e
     separa o prompt do eco.

Custos medidos: `exec(confirmar=True)` espera `CMDACTIVE` voltar a zero e leva
ate 20 s por comando. `--prompt` e' o modo de uma fase; `--iniciar`/`--ler`
continuam existindo (o `--ler` re-envia o comando, porque e' assim que a ponte
consegue ler).

CONFIABILIDADE (medida em 20/10/2026, AutoCAD 2025): **a captura e' intermitente**.
A ponte le `LASTPROMPT` de dentro do processo com um prazo de 500 ms por leitura
(`plugin/CadMcpBridge/Ponte.cs:Confirmar`); enquanto o comando espera selecao a
thread principal esta' ocupada e a leitura da `TimeoutException`. Resultado
observado: uma rodada devolveu os prompts reais (TRIM -> "Select object to trim
or shift-select to extend"), a seguinte devolveu `None` ou o eco do comando
("Command: _.TRIM"), e uma terceira deixou o AutoCAD travado.

**Antes de uma varredura longa, salve o desenho.** O pior caso medido foi o
AutoCAD com a thread principal ocupada, recusando COM (`RPC_E_CALL_REJECTED`)
e sem responder a ESC; so' encerrou com o processo.

Uso:
    python tools/mapear_comandos.py --lista
    python tools/mapear_comandos.py --iniciar TRIM        # manda TRIM (assincrono)
    python tools/mapear_comandos.py --ler TRIM            # le o prompt e grava
    python tools/mapear_comandos.py --prompt TRIM         # as duas fases, uma chamada
    python tools/mapear_comandos.py --varrer A,B,C        # varios de uma vez

Grava em `historico/prompts.jsonl` (append-only).
"""
from __future__ import annotations

import argparse
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
HIST = RAIZ / "historico"
CATALOGO = RAIZ / "docs" / "catalogo-autocad.json"

PONTO_NEUTRO = [0.0, 0.0]     # um ponto que nao desenha nada de util


def _ponte():
    """Ponte .NET (assincrona). Sem ela, o gravador nao funciona nesta versao."""
    try:
        sys.path.insert(0, str(RAIZ / "src"))
        from cad_mcp.bridge import Ponte

        return Ponte(timeout=60)
    except Exception:
        return None


def _cancelar(p) -> None:
    """ESC de verdade, por PostMessage.

    MEDIDO: mandar ESC pela ponte (`SendStringToExecute`) deixa a linha de
    comando em estado ruim e a leitura seguinte devolve valor defasado. O ESC
    por PostMessage na janela do AutoCAD e' o que limpa de verdade.
    """
    try:
        sys.path.insert(0, str(RAIZ / "src"))
        from cad_mcp import win32_bridge

        h = win32_bridge.find_autocad_window()
        if h:
            win32_bridge.enviar_esc(h, forcado=True)
            time.sleep(0.5)
            return
    except Exception:
        pass
    if p is not None:
        try:
            p.exec("", pontos=[], confirmar=False)
            time.sleep(0.4)
        except Exception:
            pass


def candidatos() -> list[str]:
    if not CATALOGO.exists():
        return []
    dados = json.loads(CATALOGO.read_text(encoding="utf-8"))
    c = dados.get("comandos", {})
    nomes = set(c.get("c_simbolo", [])) | set(c.get("cuix", []))
    lixo = {"CLOSE", "QUIT", "EXIT", "NEW", "OPEN", "SAVEAS", "QSAVE", "PLOT", "PUBLISH",
            "OPTIONS", "NETLOAD", "SCRIPT", "DEL", "UNDEFINE", "REDEFINE", "RECOVER"}
    return sorted(n for n in nomes if n.isalpha() and n.upper() not in lixo)


def _limpar_eco(bruto: str, eco: list[float]) -> str:
    """`LASTPROMPT` traz o prompt + a entrada ecoada. Corta o eco do fim."""
    texto = (bruto or "").strip()
    if not eco:
        return texto
    for forma in (",".join("%g" % v for v in eco), " ".join("%g" % v for v in eco)):
        if forma and texto.endswith(forma):
            corte = texto[: -len(forma)].rstrip(" :")
            if corte:
                return corte
    return texto


def iniciar(nome: str, p) -> int:
    if p is None:
        print("a ponte .NET nao respondeu: sem ela o --iniciar bloqueia nesta versao.")
        print("abra o AutoCAD (o bundle CadMcpBridge carrega no startup) e rode de novo.")
        return 2
    t0 = time.perf_counter()
    r = p.exec("_.%s" % nome, pontos=[], confirmar=False)
    print("enviado: _.%s (%.0f ms) ok=%s" % (nome, (time.perf_counter() - t0) * 1000,
                                             r.get("ok")))
    _cancelar(p)
    print("agora: python tools/mapear_comandos.py --ler " + nome)
    return 0


def ler(nome: str, p) -> int:
    """Le o prompt de dentro do processo. Re-envia o comando: e' assim que funciona."""
    if p is None:
        print("a ponte .NET nao respondeu; sem ela nao da para ler o prompt.")
        return 2
    bruto = None
    try:
        # SEM ponto: com um ponto, o que a ponte devolve e' o prompt da etapa
        # SEGUINTE (ex.: TRIM com ponto -> "Specify next fence point"), nao o
        # prompt que o comando mostra ao ser chamado.
        r = p.exec("_.%s" % nome, pontos=[], confirmar=True)
        bruto = r.get("lastprompt")
    except Exception as exc:  # noqa: BLE001
        print("nao consegui ler (%s)." % str(exc)[:80])
        return 1
    finally:
        _cancelar(p)

    if not bruto:
        print("%s: a ponte nao devolveu LASTPROMPT." % nome)
        return 1

    registro = {
        "quando": datetime.now().astimezone().isoformat(timespec="seconds"),
        "comando": nome,
        "prompt_bruto": bruto,
        "prompt": _limpar_eco(bruto, PONTO_NEUTRO),
        "via": "ponte .NET (LASTPROMPT de dentro do processo)",
    }
    HIST.mkdir(exist_ok=True)
    with (HIST / "prompts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    print("%s: %r" % (nome, registro["prompt"]))
    print("gravado em %s" % (HIST / "prompts.jsonl"))
    return 0


def varrer(nomes: list[str]) -> int:
    p = _ponte()
    if p is None:
        print("a ponte .NET nao respondeu; nada foi gravado.")
        return 2
    ok = 0
    for nome in nomes:
        if ler(nome, p) == 0:
            ok += 1
        print("")
    print("%d/%d com prompt" % (ok, len(nomes)))
    return 0 if ok == len(nomes) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Grava o prompt de um comando.")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--iniciar", metavar="COMANDO")
    ap.add_argument("--ler", metavar="COMANDO")
    ap.add_argument("--prompt", metavar="COMANDO", help="inicia e le numa chamada")
    ap.add_argument("--varrer", metavar="A,B,C", help="varios comandos de uma vez")
    args = ap.parse_args()

    if args.lista:
        nomes = candidatos()
        print("%d candidatos:" % len(nomes))
        print(" ".join(nomes))
        return 0

    try:
        if args.varrer:
            return varrer([n.strip().upper() for n in args.varrer.split(",") if n.strip()])
        p = _ponte()
        if args.prompt:
            if p is None:
                print("a ponte .NET nao respondeu; nada foi gravado.")
                return 2
            return ler(args.prompt, p)
        if args.iniciar:
            return iniciar(args.iniciar, p)
        if args.ler:
            return ler(args.ler, p)
    except Exception as exc:  # noqa: BLE001
        print("falhou: %s" % exc)
        print("o AutoCAD esta aberto, com um desenho?")
        return 1

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
