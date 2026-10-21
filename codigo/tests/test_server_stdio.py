# -*- coding: utf-8 -*-
"""Handshake MCP cru por stdio, para validar o servidor antes de registrar."""
from __future__ import annotations

import json
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PY = r"C:\Users\Correta Engenharia\AppData\Local\Programs\Python\Python310\python.exe"
SRV = r"C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad\codigo\src\cad_mcp\server.py"


def ler_uma(proc, timeout=25.0):
    """Le uma linha JSON do stdout (o servidor pode logar em stderr)."""
    fim = time.time() + timeout
    while time.time() < fim:
        linha = proc.stdout.readline()
        if not linha:
            return None
        linha = linha.strip()
        if not linha:
            continue
        try:
            return json.loads(linha)
        except Exception:
            print("  (ignorado no stdout: %r)" % linha[:120])
            continue
    return None


def enviar(proc, obj):
    proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
    proc.stdin.flush()


def main():
    import os

    # herda o ambiente (pydantic pode estar em site-packages do usuario)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    p = subprocess.Popen(
        [PY, SRV], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    try:
        enviar(p, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "probe", "version": "1.0"},
            },
        })
        r = ler_uma(p)
        print("initialize ->", json.dumps(r, ensure_ascii=False)[:400])

        enviar(p, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        enviar(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        r = ler_uma(p, 40)
        if r and "result" in r:
            nomes = [t["name"] for t in r["result"].get("tools", [])]
            print("tools/list -> %d ferramentas" % len(nomes))
            print("   %s" % ", ".join(nomes))
        else:
            print("tools/list -> %s" % json.dumps(r, ensure_ascii=False)[:600])
    finally:
        try:
            p.terminate()
            p.wait(timeout=8)
        except Exception:
            p.kill()
        err = (p.stderr.read() or b"").decode("utf-8", "replace")
        if err.strip():
            print("\n--- STDERR do servidor ---")
            print(err[-2500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
