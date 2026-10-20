# -*- coding: utf-8 -*-
"""Testa o CLIENTE da ponte contra um servidor falso (sem AutoCAD).

O que se prova: protocolo de uma linha, token, resposta de erro, e o que
acontece quando o plugin nao esta carregado. O plugin de verdade so pode ser
testado depois de reiniciar o AutoCAD (Autoloader) -- isso e um teste manual:
    python -m cad_mcp.bridge ping
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path
from socketserver import StreamRequestHandler, ThreadingTCPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cad_mcp.bridge import Ponte, PonteIndisponivel  # noqa: E402

TOKEN = "abc123"
falhas = []


def checar(nome: str, cond: bool, extra="") -> None:
    print("  %s  %s%s" % ("ok  " if cond else "FALHA", nome,
                          (" -- " + str(extra)) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)


class Tratador(StreamRequestHandler):
    def handle(self):
        linha = self.rfile.readline().decode("utf-8")
        try:
            carga = json.loads(linha)
        except ValueError:
            self.wfile.write(b'{"ok":false,"erro":"json invalido"}\n')
            return
        if carga.get("token") != TOKEN:
            self.wfile.write(b'{"ok":false,"erro":"token invalido"}\n')
            return
        metodo, args = carga.get("metodo"), carga.get("args", {})
        if metodo == "ping":
            resp = {"ok": True, "produto": "CadMcpBridge", "acad": "25.0s"}
        elif metodo == "exec":
            resp = {"ok": True, "comando": args.get("comando"),
                    "pontos": args.get("pontos"), "duracao_ms": 12}
        elif metodo == "transaction":
            resp = {"ok": True, "resultados": [{"handle": o.get("handle"),
                                                "op": o.get("op"), "ok": True}
                                               for o in args.get("ops", [])]}
        else:
            resp = {"ok": False, "erro": "metodo desconhecido"}
        self.wfile.write((json.dumps(resp) + "\n").encode("utf-8"))


def main() -> int:
    srv = ThreadingTCPServer(("127.0.0.1", 0), Tratador)
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    tmp = Path(tempfile.mkdtemp()) / "ponte.json"
    tmp.write_text(json.dumps({"porta": porta, "token": TOKEN, "pid": 1}), encoding="utf-8")

    print("1) caminho feliz")
    p = Ponte(info=tmp, timeout=5)
    r = p.ping()
    checar("ping responde ok", r.get("ok") is True and r.get("acad") == "25.0s", r)

    r = p.exec("_.TRIM", pontos=[[0, 0], [5, 2.5]])
    checar("exec devolve o comando", r.get("comando") == "_.TRIM", r)
    checar("pontos chegam como lista", r.get("pontos") == [[0, 0], [5, 2.5]], r.get("pontos"))

    r = p.transacao([{"op": "move", "handle": "1A2", "de": [0, 0], "para": [1, 0]},
                     {"op": "erase", "handle": "1A3"}])
    checar("2 operacoes executadas", len(r.get("resultados", [])) == 2, r)

    print("\n2) falhas previsiveis")
    ruim = Path(tempfile.mkdtemp()) / "ponte.json"
    ruim.write_text(json.dumps({"porta": porta, "token": "errado"}), encoding="utf-8")
    checar("token errado -> erro do plugin", Ponte(info=ruim, timeout=5).ping().get("ok") is False)

    inexistente = Path(tempfile.mkdtemp()) / "nao_existe.json"
    try:
        Ponte(info=inexistente)
        checar("sem arquivo -> PonteIndisponivel", False)
    except PonteIndisponivel as exc:
        checar("sem arquivo -> PonteIndisponivel", "plugin roda dentro do AutoCAD" in str(exc))

    # porta que estava livre: bind e close, para garantir "recusada", nao "filtrada"
    import socket
    _s = socket.socket()
    _s.bind(("127.0.0.1", 0))
    porto_morto = _s.getsockname()[1]
    _s.close()
    morto = Path(tempfile.mkdtemp()) / "ponte.json"
    morto.write_text(json.dumps({"porta": porto_morto, "token": TOKEN}), encoding="utf-8")
    try:
        Ponte(info=morto, timeout=2).ping()
        checar("porta morta -> PonteIndisponivel", False)
    except PonteIndisponivel:
        checar("porta morta -> PonteIndisponivel", True)
    except ConnectionRefusedError:
        checar("porta morta -> PonteIndisponivel", False, "vazou ConnectionRefusedError")

    srv.shutdown()

    print()
    if falhas:
        print("FALHOU: %s" % ", ".join(falhas))
        return 1
    print("TUDO OK -- protocolo da ponte fechado. Falta so o plugin carregar no AutoCAD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
