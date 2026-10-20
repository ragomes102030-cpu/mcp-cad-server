# -*- coding: utf-8 -*-
"""Despeja a arvore de janelas do AutoCAD para achar QUEM aceita PostMessage."""
from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import win32con
import win32gui


def texto(hwnd: int) -> str:
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""


def classe(hwnd: int) -> str:
    try:
        return win32gui.GetClassName(hwnd)
    except Exception:
        return ""


def visivel(hwnd: int) -> str:
    return "VIS" if win32gui.IsWindowVisible(hwnd) else "   "


def habilitado(hwnd: int) -> str:
    return "ENA" if win32gui.IsWindowEnabled(hwnd) else "DIS"


def dump(hwnd: int, nivel: int = 0, maxnivel: int = 6) -> None:
    pad = "  " * nivel
    print("%s%-9s %s %s %-28s %r" % (pad, hwnd, visivel(hwnd), habilitado(hwnd), classe(hwnd), texto(hwnd)[:70]))
    if nivel >= maxnivel:
        return
    filhos = []
    win32gui.EnumChildWindows(hwnd, lambda h, _: filhos.append(h) or True, None)
    for f in filhos:
        # EnumChildWindows e recursivo; evita duplicar mostrando so filhos diretos
        if win32gui.GetParent(f) == hwnd:
            dump(f, nivel + 1, maxnivel)


if __name__ == "__main__":
    alvo = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if alvo is None:
        tops = []
        win32gui.EnumWindows(lambda h, _: tops.append(h) or True, None)
        for h in tops:
            c = classe(h)
            t = texto(h)
            if c.startswith("AfxMDIFrame") or "autocad" in t.lower():
                alvo = h
                print("# TOP hwnd=%s classe=%s titulo=%r" % (h, c, t))
        if alvo is None:
            print("AutoCAD nao encontrado")
            sys.exit(1)
    print("# ---- arvore a partir de %s ----" % alvo)
    dump(alvo)
