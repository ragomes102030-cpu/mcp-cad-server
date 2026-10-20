# -*- coding: utf-8 -*-
"""Fecha os documentos de teste que ficaram abertos no AutoCAD (sem salvar).

So fecha documentos com nome que sabemos ser nossos (stage_*, planta_mcp*,
Drawing2..N). Usa Document.Close(False) -> descarta alteracoes e NAO abre
nenhum dialogo modal.
"""
from __future__ import annotations

import asyncio
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, r"C:\Users\Correta Engenharia\mcp-cad-server\src")

from cad_mcp.com_backend import ComBackend  # noqa: E402

NOSSOS = re.compile(r"^(stage_|planta_mcp|Drawing([2-9]|\d\d))", re.IGNORECASE)


async def main():
    b = ComBackend()
    r = await b.initialize()
    if not r.ok:
        print("init falhou:", r.error)
        return 1
    app = b._app
    docs = b._chamar(lambda: app.Documents)
    n = b._chamar(lambda: docs.Count)
    print("documentos abertos: %d" % n)
    fechados = []
    # varre de tras para frente para nao bagunçar indices
    for i in range(n - 1, -1, -1):
        d = b._chamar(docs.Item, i)
        nome = b._chamar(lambda: d.Name)
        marcar = bool(NOSSOS.match(nome))
        print("  [%d] %-46s %s" % (i, nome, "FECHANDO" if marcar else "mantido"))
        if marcar:
            try:
                b._chamar(d.Close, False)
                fechados.append(nome)
            except Exception as e:
                print("      erro ao fechar: %s" % str(e)[:90])
    print("\nfechados: %s" % (fechados or "nenhum"))
    r = await b.status()
    print("documento ativo agora: %s" % (r.payload or {}).get("documento"))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
