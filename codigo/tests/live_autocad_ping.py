# -*- coding: utf-8 -*-
"""Teste AO VIVO da ponte com o AutoCAD.

1. abre o AutoCAD com um DXF nosso (assim a linha de comando já está ativa)
2. injeta (load "...mcp_dispatch.lsp") na janela — sem roubar foco (PostMessage)
3. escreve um comando nosso no diretorio de IPC e injeta (c:mcp-dispatch)
4. espera o arquivo de resposta  ->  prova a PONTE LISP
5. chama o backend Python vendorizado ->  prova o LADO PYTHON
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
LISP = RAIZ / "vendor" / "puran-water" / "lisp"
IPC = Path(os.environ.get("AUTOCAD_MCP_IPC_DIR", "C:/temp")).resolve()
DXF = RAIZ / "data" / "smoke" / "smoke_planta.dxf"

WM_CHAR, VK_ESCAPE = 0x0102, 0x1B
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101


def hwnds_autocad() -> list[int]:
    from autocad_mcp.backends.file_ipc import find_autocad_window
    h = find_autocad_window()
    return [h] if h else []


def tipo_janela():
    user32 = ctypes.windll.user32
    return user32.GetForegroundWindow()


def post_text(hwnd: int, texto: str) -> int:
    """Envia texto + Enter para a janela (sem foco)."""
    user32 = ctypes.windll.user32
    n = 0
    for ch in texto:
        user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
        n += 1
        time.sleep(0.002)
    user32.PostMessageW(hwnd, WM_KEYDOWN, 0x0D, 0)
    user32.PostMessageW(hwnd, WM_KEYUP, 0x0D, 0)
    return n


def enviar_esc(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    user32.PostMessageW(hwnd, WM_KEYDOWN, VK_ESCAPE, 0)
    user32.PostMessageW(hwnd, WM_KEYUP, VK_ESCAPE, 0)


def abrir_autocad():
    import subprocess
    acad = Path(r"C:\Program Files\Autodesk\AutoCAD 2025\acad.exe")
    if not acad.exists():
        raise SystemExit("acad.exe não encontrado")
    subprocess.Popen([str(acad), "/nologo", str(DXF)], cwd=str(acad.parent))
    print("AutoCAD aberto com", DXF.name, "- aguardando janela...")
    for i in range(60):
        time.sleep(3)
        hs = hwnds_autocad()
        if hs:
            print("janela encontrada em %ds: hwnd=%s" % (i * 3, hs[0]))
            return hs[0]
    raise SystemExit("AutoCAD não abriu janela em 180s")


def carregar_ponte(hwnd: int):
    user32 = ctypes.windll.user32
    # MDIClient child é o alvo correto (mesma técnica do backend)
    alvo = hwnd
    filho = user32.FindWindowExW(hwnd, 0, "MDIClient", None)
    if filho:
        alvo = filho
    print("alvo do PostMessage: hwnd=%s (MDIClient=%s)" % (alvo, bool(filho)))
    enviar_esc(hwnd)
    time.sleep(0.4)
    for f in ("mcp_dispatch.lsp", "attribute_tools.lsp"):
        expr = '(load "%s")' % str(LISP / f).replace("\\", "/")
        print("carregando:", expr)
        post_text(alvo, expr)
        time.sleep(3)
    return alvo


def teste_ipc(alvo: int) -> dict:
    """Escreve um comando nosso e dispara (c:mcp-dispatch)."""
    IPC.mkdir(parents=True, exist_ok=True)
    cmd_id = uuid.uuid4().hex[:12]
    cmd = IPC / f"autocad_mcp_cmd_{cmd_id}.json"
    res = IPC / f"autocad_mcp_result_{cmd_id}.json"
    if res.exists():
        res.unlink()
    cmd.write_text(json.dumps({"id": cmd_id, "command": "echo", "params": {"texto": "ping mcp-cad-server"}}),
                   encoding="utf-8")
    print("comando escrito:", cmd.name)
    post_text(alvo, "(c:mcp-dispatch)")
    for i in range(30):
        time.sleep(1)
        if res.exists():
            try:
                data = json.loads(res.read_text(encoding="utf-8"))
            except Exception as exc:
                data = {"erro_leitura": str(exc), "raw": res.read_text(encoding="utf-8", errors="replace")[:400]}
            print("RESPOSTA da ponte LISP:", json.dumps(data, ensure_ascii=False)[:600])
            return data
    print("SEM resposta da ponte em 30s (o LISP carregou?)")
    return {}


def teste_backend():
    import asyncio
    from autocad_mcp.backends.file_ipc import FileIPCBackend

    async def run():
        b = FileIPCBackend()
        await b.initialize()
        st = await b.status()
        print("backend Python status:", json.dumps(st.to_dict(), ensure_ascii=False)[:500])
        info = await b.drawing_info()
        print("drawing_info:", json.dumps(info.to_dict(), ensure_ascii=False)[:500])
        ec = await b.entity_count()
        print("entity_count:", json.dumps(ec.to_dict(), ensure_ascii=False)[:300])

    asyncio.run(run())


if __name__ == "__main__":
    h = hwnds_autocad()
    if h:
        print("AutoCAD já estava aberto: hwnd=%s" % h[0])
        alvo = h[0]
    else:
        alvo = carregar_ponte(abrir_autocad())
    if len(sys.argv) > 1 and sys.argv[1] == "--so-carregar":
        print("ponte carregada; use o servidor MCP a partir de agora.")
        sys.exit(0)
    teste_ipc(alvo)
    try:
        teste_backend()
    except Exception as exc:
        print("backend Python falhou:", type(exc).__name__, exc)
