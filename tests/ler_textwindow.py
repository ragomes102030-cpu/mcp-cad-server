# -*- coding: utf-8 -*-
"""Le o texto da janela F2 do AutoCAD -> mostra o estado real da linha de comando."""
from __future__ import annotations

import ctypes
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import win32gui
import win32process

WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E


def achar_textwindow(pid: int) -> int | None:
    alvo = []

    def cb(h, _):
        _, w = win32process.GetWindowThreadProcessId(h)
        t = win32gui.GetWindowText(h)
        if w == pid and "AutoCAD Text Window" in t:
            alvo.append(h)
        return True

    win32gui.EnumWindows(cb, None)
    return alvo[0] if alvo else None


def ler(hwnd: int) -> str:
    pedacos = []

    def cb(h, _):
        c = win32gui.GetClassName(h)
        if c in ("RichEdit20W", "RichEdit20A", "Edit", "RICHEDIT60W", "RichEdit50W"):
            tam = ctypes.windll.user32.SendMessageW(h, WM_GETTEXTLENGTH, 0, 0)
            if tam > 0:
                buf = ctypes.create_unicode_buffer(tam + 2)
                ctypes.windll.user32.SendMessageW(h, WM_GETTEXT, tam + 1, buf)
                pedacos.append((c, buf.value))
        return True

    win32gui.EnumChildWindows(hwnd, cb, None)
    if not pedacos:
        # tenta no proprio
        tam = ctypes.windll.user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
        buf = ctypes.create_unicode_buffer(tam + 2)
        ctypes.windll.user32.SendMessageW(hwnd, WM_GETTEXT, tam + 1, buf)
        pedacos.append(("<self>", buf.value))
    return "\n".join("--- %s ---\n%s" % (c, t) for c, t in pedacos)


if __name__ == "__main__":
    pid = int(sys.argv[1])
    h = achar_textwindow(pid)
    if not h:
        print("Text Window nao encontrada")
        sys.exit(1)
    print("text window hwnd=%s" % h)
    txt = ler(h)
    print("TAMANHO TOTAL = %d" % len(txt))
    print("=" * 70)
    print(txt[-4000:])
