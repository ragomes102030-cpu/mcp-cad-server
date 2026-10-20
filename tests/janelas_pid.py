# -*- coding: utf-8 -*-
"""Lista TODAS as janelas top-level de um PID (acha dialogos modais escondidos)."""
from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import win32con
import win32gui
import win32process


def main(pid: int) -> None:
    achados = []

    def cb(hwnd, _):
        _, wpid = win32process.GetWindowThreadProcessId(hwnd)
        if wpid != pid:
            return True
        achados.append(
            (
                hwnd,
                win32gui.GetClassName(hwnd),
                win32gui.GetWindowText(hwnd),
                bool(win32gui.IsWindowVisible(hwnd)),
                bool(win32gui.IsWindowEnabled(hwnd)),
                hwnd in (win32gui.GetForegroundWindow(),),
            )
        )
        return True

    win32gui.EnumWindows(cb, None)
    print("PID=%s  janelas top-level=%d" % (pid, len(achados)))
    print("%-10s %-8s %-8s %-8s %-30s %s" % ("hwnd", "vis", "ena", "fg", "classe", "titulo"))
    for h, c, t, vis, ena, fg in achados:
        print("%-10s %-8s %-8s %-8s %-30s %r" % (h, vis, ena, fg, c, t[:60]))
        # dono
        try:
            o = win32gui.GetWindow(h, win32con.GW_OWNER)
            if o:
                print("%-10s   ^-- owner hwnd=%s classe=%s titulo=%r" % ("", o, win32gui.GetClassName(o), win32gui.GetWindowText(o)[:50]))
        except Exception:
            pass


if __name__ == "__main__":
    main(int(sys.argv[1]))
