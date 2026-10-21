# -*- coding: utf-8 -*-
"""Lista e fecha dialogos modais do AutoCAD (ex.: 'Security - Unsigned Executable File')."""
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

BM_CLICK = 0x00F5


def janelas_do_pid(pid: int):
    out = []

    def cb(hwnd, _):
        _, wpid = win32process.GetWindowThreadProcessId(hwnd)
        if wpid == pid:
            out.append(hwnd)
        return True

    win32gui.EnumWindows(cb, None)
    return out


def botoes(hwnd: int):
    out = []

    def cb(h, _):
        if win32gui.GetParent(h) == hwnd and win32gui.GetClassName(h) in ("Button", "AfxWnd140u"):
            out.append(h)
        return True

    win32gui.EnumChildWindows(hwnd, cb, None)
    return out


def fechar(hwnd: int, preferir: tuple[str, ...] = ("don't load", "don't", "cancel", "no")) -> bool:
    print("  dialogo hwnd=%s titulo=%r" % (hwnd, win32gui.GetWindowText(hwnd)))
    bs = botoes(hwnd)
    escolhido = None
    for b in bs:
        t = win32gui.GetWindowText(b).strip()
        print("    botao hwnd=%s classe=%s texto=%r" % (b, win32gui.GetClassName(b), t))
        if escolhido is None and t.lower() in preferir:
            escolhido = b
    if escolhido:
        print("    -> clicando %r" % win32gui.GetWindowText(escolhido))
        win32gui.PostMessage(escolhido, BM_CLICK, 0, 0)
        time.sleep(0.4)
        return True
    print("    -> nenhum botao preferido; mandando WM_CLOSE")
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    time.sleep(0.4)
    return True


def main(pid: int) -> None:
    for _ in range(3):
        modais = []
        for h in janelas_do_pid(pid):
            if not win32gui.IsWindowVisible(h):
                continue
            c = win32gui.GetClassName(h)
            t = win32gui.GetWindowText(h)
            if c == "#32770":
                modais.append(h)
        if not modais:
            print("sem dialogos modais visiveis")
            return
        for h in modais:
            fechar(h)
    print("restantes:", [h for h in janelas_do_pid(pid) if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "#32770"])


if __name__ == "__main__":
    main(int(sys.argv[1]))
