# -*- coding: utf-8 -*-
"""Tenta destravar o COM do AutoCAD: ESC na janela + retry paciente."""
from __future__ import annotations

import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import win32con
import win32gui
import win32process

VK_ESCAPE = 0x1B


def hwnds_acad(pid: int):
    out = []

    def cb(h, _):
        _, w = win32process.GetWindowThreadProcessId(h)
        if w == pid:
            out.append(h)
        return True

    win32gui.EnumWindows(cb, None)
    return out


def main(pid: int) -> None:
    principal = 15472308
    for h in hwnds_acad(pid):
        if win32gui.GetClassName(h).startswith("AfxMDIFrame"):
            principal = h
    mdi = win32gui.FindWindowEx(principal, 0, "MDIClient", None) or principal
    print("principal=%s mdi=%s" % (principal, mdi))
    for alvo, nome in ((principal, "frame"), (mdi, "mdi")):
        for i in range(3):
            win32gui.PostMessage(alvo, win32con.WM_KEYDOWN, VK_ESCAPE, 0)
            win32gui.PostMessage(alvo, win32con.WM_KEYUP, VK_ESCAPE, 0)
            time.sleep(0.25)
        print("  ESC x3 enviado para %s" % nome)

    import pythoncom
    import win32com.client as wc

    pythoncom.CoInitialize()
    t0 = time.time()
    while time.time() - t0 < 60:
        try:
            app = wc.GetActiveObject("AutoCAD.Application.25")
            nome = app.ActiveDocument.Name
            print("\n[OK] COM respondeu em %.1fs -> %s" % (time.time() - t0, nome))
            print("     entities = %s" % app.ActiveDocument.ModelSpace.Count)
            return
        except Exception as e:
            print("  [%.1fs] %s" % (time.time() - t0, str(e)[:110]))
            time.sleep(2.0)
    print("\n[FALHOU] COM continua rejeitando")


if __name__ == "__main__":
    main(int(sys.argv[1]))
