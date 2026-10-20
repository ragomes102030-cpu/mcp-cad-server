# -*- coding: utf-8 -*-
"""Captura de janela do Windows (PrintWindow) sem roubar foco.

Usado pelo backend COM para "ver" o AutoCAD. Requer Pillow.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _capturar_hwnd(hwnd: int):
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    largura = rect.right - rect.left
    altura = rect.bottom - rect.top
    if largura <= 0 or altura <= 0:
        raise RuntimeError("janela sem area util")

    hdc = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc)
    hbmp = gdi32.CreateCompatibleBitmap(hdc, largura, altura)
    gdi32.SelectObject(hdc_mem, hbmp)

    ok = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
    if not ok:
        gdi32.BitBlt(hdc_mem, 0, 0, largura, altura, hdc, 0, 0, SRCCOPY)

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = largura
    info.bmiHeader.biHeight = -altura  # top-down
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0

    buf = ctypes.create_string_buffer(largura * altura * 4)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, altura, buf, ctypes.byref(info), DIB_RGB_COLORS)

    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc)
    return largura, altura, buf.raw


def _preparar(hwnd: int) -> tuple[int, int]:
    """Garante que a janela tem area util; restaura se estiver minimizada.

    PrintWindow numa janela minimizada devolve um bitmap minusculo (ex.: 160x28),
    que era a causa do PNG inutil que o agente recebia.
    """
    SW_RESTORE = 9
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.6)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    largura = rect.right - rect.left
    altura = rect.bottom - rect.top
    if largura < 320 or altura < 240:
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.6)
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        largura = rect.right - rect.left
        altura = rect.bottom - rect.top
    if largura < 320 or altura < 240:
        raise RuntimeError(
            "janela do AutoCAD com area util de %dx%d px (minimizada ou escondida). "
            "Restaure/maximize a janela e chame de novo." % (largura, altura))
    return largura, altura


def capturar(hwnd: int, pasta: Path):
    """Salva um PNG da janela indicada e devolve (caminho, largura, altura)."""
    from PIL import Image  # import tardio: so' falha se o Pillow nao estiver instalado

    _preparar(hwnd)
    largura, altura, bruto = _capturar_hwnd(hwnd)
    img = Image.frombuffer("RGBA", (largura, altura), bruto, "raw", "BGRA", 0, 1).convert("RGB")
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = "autocad_screenshot_%s.png" % time.strftime("%Y%m%d_%H%M%S")
    saida = pasta / nome
    img.save(saida)
    return saida, largura, altura
