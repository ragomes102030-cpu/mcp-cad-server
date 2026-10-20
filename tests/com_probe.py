# -*- coding: utf-8 -*-
"""Testa a rota COM/ActiveX no AutoCAD aberto (sem roubar foco)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROBE = Path(r"C:/temp/mcp_probe_com.txt")


def passo(t):
    print("\n--- " + t)


def main():
    passo("1. importar pywin32")
    try:
        import win32com.client as wc
        from win32com.client import gencache  # noqa
    except Exception as e:
        print("  pywin32 ausente: %s" % e)
        return 1
    import pythoncom

    passo("2. achar a instancia aberta (GetActiveObject)")
    app = None
    for progid in ("AutoCAD.Application.25", "AutoCAD.Application.24", "AutoCAD.Application"):
        try:
            app = wc.GetActiveObject(progid)
            print("  ligado em %s" % progid)
            break
        except Exception as e:
            print("  %-26s -> %s" % (progid, e))
    if app is None:
        print("  Nenhuma instancia COM. (AutoCAD rodando como outro usuario? VBA/ActiveX desligado?)")
        return 2

    passo("3. propriedades da aplicacao")
    try:
        print("  Name      = %s" % app.Name)
        print("  Version   = %s" % app.Version)
        print("  Visible   = %s" % app.Visible)
        print("  Documents = %s" % app.Documents.Count)
        doc = app.ActiveDocument
        print("  ActiveDocument = %s" % doc.Name)
        print("  FullName       = %s" % doc.FullName)
        print("  Saved          = %s" % doc.Saved)
    except Exception as e:
        print("  ERRO: %s" % e)
        return 3

    passo("4. SendCommand -> escrever arquivo de prova")
    if PROBE.exists():
        PROBE.unlink()
    lisp = '(progn (setq f (open "C:/temp/mcp_probe_com.txt" "w")) (write-line "COM SendCommand OK" f) (close f) (princ))'
    try:
        t0 = time.time()
        doc.SendCommand(lisp + "\n")
        print("  SendCommand retornou em %.2fs" % (time.time() - t0))
    except Exception as e:
        print("  ERRO no SendCommand: %s" % e)
        return 4
    for i in range(20):
        time.sleep(0.25)
        if PROBE.exists():
            print("  [OK] prova em %.1fs -> %r" % ((i + 1) * 0.25, PROBE.read_text(errors="replace").strip()))
            return 0
    print("  [FALHOU] arquivo de prova nao apareceu")
    return 5


if __name__ == "__main__":
    sys.exit(main())
