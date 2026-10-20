# -*- coding: utf-8 -*-
"""Probe: como o entmakex grava os angulos de um ARC no AutoCAD vivo."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.com_backend import ComBackend  # noqa: E402

CORPO = ('(list (cons 0 "ARC") (cons 100 "AcDbEntity") (cons 8 "0")'
         ' (cons 100 "AcDbCircle") (cons 10 (list 0.0 0.0 0.0)) (cons 40 1.0)'
         ' (cons 100 "AcDbArc") (cons 50 %s) (cons 51 %s))')


async def main():
    b = ComBackend()
    r = await b.initialize()
    if not r.ok:
        print("init falhou:", r.error)
        return 2
    print("OK conectado\n")

    criados = []
    for a1, a2 in ((90.0, 180.0), (0.0, 90.0), (30.0, 120.0), (116.620156177409, 233.240312354818)):
        res = await b.entmakex(CORPO % (repr(a1), repr(a2)))
        if not res.ok:
            print("a1=%-22s a2=%-22s -> ERRO %s" % (a1, a2, res.error))
            continue
        h = res.payload
        h = h.get("resultado") if isinstance(h, dict) else h
        criados.append(h)
        leitura = await b.execute_lisp(
            '(progn (setq e (entget (handent "%s")))'
            ' (list (cdr (assoc 50 e)) (cdr (assoc 51 e)) (cdr (assoc 40 e))))' % h)
        lido = leitura.payload
        lido = lido.get("resultado") if isinstance(lido, dict) else lido
        print("pedido a1=%-22s a2=%-22s | gravado %s" % (a1, a2, json.dumps(lido)))

    # limpa apenas o que este teste criou
    for h in criados:
        await b.execute_lisp('(progn (entdel (handent "%s")) (princ))' % h)
    print("\narcos de teste apagados: %d" % len(criados))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
