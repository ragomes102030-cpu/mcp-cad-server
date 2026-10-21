# -*- coding: utf-8 -*-
"""Mede o limite pratico de uma expressao LISP enviada INLINE via SendCommand."""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pythoncom
import win32com.client as wc

pythoncom.CoInitialize()
app = wc.GetActiveObject("AutoCAD.Application.25")
doc = app.ActiveDocument
print("doc:", doc.Name)


def inline(expr: str, res: Path, timeout=20.0):
    if res.exists():
        res.unlink()
    rp = str(res).replace("\\", "/")
    codigo = (
        '(progn (setq r (vl-catch-all-apply (quote (lambda () ' + expr + '))))'
        ' (setq f (open "' + rp + '" "w"))'
        ' (if (vl-catch-all-error-p r)'
        '  (progn (write-line "ERR" f) (write-line (vl-catch-all-error-message r) f))'
        '  (write-line (vl-prin1-to-string r) f))'
        ' (close f) (princ))'
    )
    t0 = time.time()
    doc.SendCommand(codigo + "\n")
    while time.time() - t0 < timeout:
        if res.exists():
            time.sleep(0.05)
            try:
                return True, res.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                return False, ["(arquivo ilegivel)"]
        time.sleep(0.05)
    return False, ["timeout"]


RES = Path(r"C:/temp/mcp_cad_com/inline_res.txt")
RES.parent.mkdir(parents=True, exist_ok=True)
for tamanho in (400, 700, 1000, 1500, 2000, 3000):
    # monta uma expressao que devolve o comprimento da string -> mede se chegou inteira
    alvo = "(strlen \"" + ("A" * tamanho) + "\")"
    ok, linhas = inline(alvo, RES)
    esperado = tamanho
    print("A x %-4d  expr=%-5d total=%-5d ok=%-5s esperado=%-4d -> %s"
          % (tamanho, len(alvo), len(alvo) + 235, ok, esperado, linhas))
