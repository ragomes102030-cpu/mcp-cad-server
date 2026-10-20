# -*- coding: utf-8 -*-
"""Camada Win32 nossa: encontra o AutoCAD e injeta comandos sem roubar foco.

Por que existe: o detector do pacote vendorizado procura a janela por título
contendo "autocad" E ("drawing" ou ".dwg") — então falha com .dxf e com títulos
diferentes. Aqui detectamos pela CLASSE da janela (AfxMDIFrame*) + título, e
cobrimos AutoCAD 2024/2025 (AfxMDIFrame140u / 140s ...).
"""
from __future__ import annotations

import ctypes
import os
import time
from pathlib import Path

WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D

RAIZ = Path(__file__).resolve().parents[2]
LISP_DIR = RAIZ / "vendor" / "puran-water" / "lisp"


def janelas_autocad() -> list[dict]:
    """Todas as janelas principais do AutoCAD (classe AfxMDIFrame*)."""
    import win32gui

    achados: list[dict] = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        cls = win32gui.GetClassName(hwnd)
        txt = win32gui.GetWindowText(hwnd)
        if cls.startswith("AfxMDIFrame") or "autodesk autocad" in txt.lower():
            achados.append({"hwnd": hwnd, "classe": cls, "titulo": txt})

    win32gui.EnumWindows(cb, None)
    return achados


def find_autocad_window() -> int | None:
    """HWND da janela principal do AutoCAD (ou None)."""
    js = janelas_autocad()
    return js[0]["hwnd"] if js else None


def mdi_client(hwnd: int) -> int:
    """O MDIClient filho — é nele que a linha de comando recebe as mensagens."""
    import win32gui

    filho = win32gui.FindWindowEx(hwnd, 0, "MDIClient", None)
    return filho or hwnd


def post_texto(hwnd: int, texto: str, pausa: float = 0.003) -> int:
    """Envia texto + Enter por WM_CHAR (sem foco, sem teclado)."""
    user32 = ctypes.windll.user32
    n = 0
    for ch in texto:
        user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
        n += 1
        time.sleep(pausa)
    user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
    user32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)
    return n


def enviar_esc(hwnd: int, forcado: bool = False) -> None:
    """ESC: cancela o comando/prompt pendente na janela do desenho.

    PostMessage sozinho NAO resolve quando o AutoCAD esta' com um prompt ativo
    (as chamadas COM seguem sendo recusadas). No modo `forcado` a janela vai para
    o primeiro plano e o ESC e' enviado como teclado de verdade — antes de mandar,
    confere que o AutoCAD realmente esta' em foco para nao mandar ESC no app errado.
    """
    user32 = ctypes.windll.user32
    alvo = mdi_client(hwnd)
    if forcado:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.15)
        if user32.GetForegroundWindow() == hwnd:
            for _ in range(2):
                user32.keybd_event(VK_ESCAPE, 0, 0, 0)
                user32.keybd_event(VK_ESCAPE, 0, 2, 0)
                time.sleep(0.08)
            return
    for h in (alvo, hwnd):
        user32.PostMessageW(h, WM_KEYDOWN, VK_ESCAPE, 0)
        user32.PostMessageW(h, WM_KEYUP, VK_ESCAPE, 0)


def carregar_ponte(hwnd: int | None = None, espera: float = 3.0) -> dict:
    """Carrega mcp_dispatch.lsp + attribute_tools.lsp DENTRO do AutoCAD, em memória.

    Não altera APPLOAD, Startup Suite nem acaddoc.lsp — nada persiste no perfil.
    """
    hwnd = hwnd or find_autocad_window()
    if not hwnd:
        return {"ok": False, "erro": "AutoCAD não encontrado"}
    alvo = mdi_client(hwnd)
    enviar_esc(hwnd)
    time.sleep(0.4)
    carregados = []
    for nome in ("mcp_dispatch.lsp", "attribute_tools.lsp"):
        caminho = (LISP_DIR / nome)
        if not caminho.exists():
            continue
        expr = '(load "%s")' % str(caminho).replace("\\", "/")
        post_texto(alvo, expr)
        time.sleep(espera)
        carregados.append(nome)
    return {"ok": True, "hwnd": hwnd, "mdi_client": alvo, "carregados": carregados}


def patch_vendored() -> dict:
    """Faz o backend vendorizado usar o NOSSO detector de janela (sem editar o código deles)."""
    info = {}
    try:
        import autocad_mcp.backends.file_ipc as fi

        fi.find_autocad_window = find_autocad_window
        info["file_ipc"] = "patched"
    except Exception as exc:
        info["file_ipc"] = f"falhou: {exc}"
    return info


def ipc_dir() -> Path:
    return Path(os.environ.get("AUTOCAD_MCP_IPC_DIR", "C:/temp")).resolve()
