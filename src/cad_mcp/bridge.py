# -*- coding: utf-8 -*-
"""Cliente da ponte .NET (plugin `CadMcpBridge`) que roda dentro do AutoCAD.

Por que existe: `TRIM`, `EXTEND`, `FILLET`, `CHAMFER` nao sao metodos de API em
COM -- sao comandos. Chamados por `SendCommand` eles dependem de foco, sofrem com
espaco virando ENTER e travam em dialogo. Dentro do processo (Editor.Command)
nada disso acontece: o comando roda, espera terminar e devolve o resultado.

Protocolo: uma linha JSON por requisicao em 127.0.0.1, resposta em uma linha.
Porta e token ficam em `%TEMP%\\cad_mcp_bridge.json`, escritos pelo plugin a cada
carga. Sem HTTP, sem dependencia, sem porta na rede.

Uso:
    from cad_mcp.bridge import Ponte
    p = Ponte()
    p.ping()
    p.exec("_.TRIM", pontos=[[0, 0], [5, 0]])
    p.transacao([{"op": "move", "handle": "1A2", "de": [0, 0], "para": [1, 0]}])

    python -m cad_mcp.bridge ping
    python -m cad_mcp.bridge info
    python -m cad_mcp.bridge exec "_.ZOOM" "_E"
    python -m cad_mcp.bridge transacao '[{"op":"erase","handle":"1A2"}]'
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path

__all__ = ["Ponte", "PonteIndisponivel", "INFO", "disponivel"]

INFO = Path(tempfile.gettempdir()) / "cad_mcp_bridge.json"


class PonteIndisponivel(RuntimeError):
    """Plugin nao carregado (ou AutoCAD fechado)."""


def disponivel() -> bool:
    try:
        Ponte(timeout=1.5).ping()
        return True
    except Exception:
        return False


class Ponte:
    """Uma conexao por chamada: abre, manda uma linha, le uma linha, fecha."""

    def __init__(self, info: Path | str = INFO, timeout: float = 30.0):
        self.info_path = Path(info)
        self.timeout = timeout
        self._info = None
        self._ler_info()

    # ------------------------------------------------------------- protocolo
    def _ler_info(self) -> dict:
        if not self.info_path.exists():
            raise PonteIndisponivel(
                "ponte nao encontrada em %s\n"
                "o plugin roda dentro do AutoCAD: instale com plugin\\deploy.ps1 e "
                "REINICIE o AutoCAD (o Autoloader carrega no comeco).\n"
                "conferir: no AutoCAD, comando MPCBRIDGE" % self.info_path)
        texto = self.info_path.read_text(encoding="utf-8")
        try:
            self._info = json.loads(texto)
        except ValueError:
            raise PonteIndisponivel("arquivo da ponte ilegivel: %s" % texto[:120])
        return self._info

    @property
    def info(self) -> dict:
        return self._info

    def pedir(self, metodo: str, **args) -> dict:
        if self._info is None:
            self._ler_info()
        porta = int(self._info["porta"])
        carga = {"token": self._info["token"], "metodo": metodo, "args": args}
        linha = json.dumps(carga, ensure_ascii=False) + "\n"
        try:
            # conecta com prazo curto: servidor ausente nao pode parecer "comando preso"
            s = socket.create_connection(("127.0.0.1", porta), timeout=min(self.timeout, 3.0))
        except ConnectionRefusedError:
            raise PonteIndisponivel(
                "porta %d recusou conexao: o AutoCAD reiniciou e a ponte mudou de "
                "porta? apague %s e tente de novo" % (porta, self.info_path))
        except (socket.timeout, TimeoutError):
            raise PonteIndisponivel(
                "porta %d nao aceitou conexao em 3 s -- ponte de uma sessao antiga? "
                "apague %s e reabra o AutoCAD" % (porta, self.info_path))
        try:
            with s:
                s.settimeout(self.timeout)
                s.sendall(linha.encode("utf-8"))
                pedacos, total = [], 0
                while True:
                    pedaco = s.recv(65536)
                    if not pedaco:
                        break
                    pedacos.append(pedaco)
                    total += len(pedaco)
                    if total > 8 * 1024 * 1024:      # sanidade
                        break
                    if pedaco.endswith(b"\n"):
                        break
        except socket.timeout:
            raise RuntimeError("ponte nao respondeu em %.0f s (comando preso?)" % self.timeout)
        resposta = b"".join(pedacos).decode("utf-8", errors="replace").strip()
        if not resposta:
            raise RuntimeError("ponte respondeu vazio")
        try:
            return json.loads(resposta)
        except ValueError:
            raise RuntimeError("resposta nao e JSON: %r" % resposta[:200])

    # ---------------------------------------------------------------- atalhos
    def ping(self) -> dict:
        return self.pedir("ping")

    def info_desenho(self) -> dict:
        return self.pedir("info")

    def exec(self, comando: str, pontos: list[list[float]] | None = None) -> dict:
        """Executa um comando e espera. `pontos` entram como Point3d."""
        return self.pedir("exec", comando=comando, pontos=pontos or [])

    def transacao(self, ops: list[dict]) -> dict:
        """move / copy / erase / rotacao / prop por handle, numa transacao."""
        return self.pedir("transaction", ops=ops)

    # ------------------------------------------------------------------ extra
    def esperar(self, segundos: float = 10.0) -> bool:
        """Espera a ponte subir (util logo apos abrir o AutoCAD)."""
        limite = time.time() + segundos
        while time.time() < limite:
            try:
                self._ler_info()
                self.ping()
                return True
            except Exception:
                time.sleep(0.4)
        return False


# ------------------------------------------------------------------------- CLI
def _main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        p = Ponte()
    except PonteIndisponivel as exc:
        print("INDISPONIVEL: %s" % exc)
        return 2

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "ping":
        r = p.ping()
    elif cmd == "info":
        r = p.info_desenho()
    elif cmd == "exec":
        if len(argv) < 2:
            print("falta o comando")
            return 2
        r = p.exec(argv[1])
    elif cmd == "transacao":
        r = p.transacao(json.loads(argv[1]))
    else:
        print("metodo desconhecido: %s" % cmd)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
