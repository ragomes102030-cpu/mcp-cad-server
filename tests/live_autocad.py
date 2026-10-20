# -*- coding: utf-8 -*-
"""Teste AO VIVO da ponte com o AutoCAD — passo a passo, com prova em arquivo.

Etapas (cada uma só roda se a anterior passar):
 1. ACHAR      -> acha a janela do AutoCAD (classe AfxMDIFrame*), mostra titulo
 2. PROBE      -> injeta um LISP que escreve C:/temp/mcp_probe.txt  (prova o PostMessage)
 3. CARGA      -> (load "...mcp_dispatch.lsp") + attribute_tools.lsp
 4. IPC        -> escreve comando JSON, dispara (c:mcp-dispatch), espera resposta
 5. BACKEND    -> usa o backend Python vendorizado (que agora usa NOSSO detector)
 6. PDF        -> exporta o desenho atual para PDF pelo proprio AutoCAD

Uso:
    python tests/live_autocad.py            # tudo
    python tests/live_autocad.py --ate 3    # para na etapa 3
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

try:  # console do Windows costuma ser cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp import win32_bridge as wb  # noqa: E402

PROBE = Path(r"C:/temp/mcp_probe.txt")
DXF = RAIZ / "data" / "smoke" / "smoke_planta.dxf"
PDF_SAIDA = Path(r"C:/temp/smoke_planta.pdf")


def titulo(txt: str) -> None:
    print("\n" + "=" * 68)
    print(txt)
    print("=" * 68)


# ---------------------------------------------------------------- 1. ACHAR
def etapa1_achar() -> int:
    titulo("1. ACHAR janela do AutoCAD")
    js = wb.janelas_autocad()
    for j in js:
        print("  hwnd=%-9s classe=%-18s titulo=%r" % (j["hwnd"], j["classe"], j["titulo"]))
    if not js:
        raise SystemExit("  NENHUMA janela de AutoCAD encontrada.")
    hwnd = js[0]["hwnd"]
    print("  -> usando hwnd=%s" % hwnd)
    return hwnd


# ---------------------------------------------------------------- 2. PROBE
def etapa2_probe(hwnd: int) -> bool:
    titulo("2. PROBE — provar que o PostMessage chega na linha de comando")
    alvo = wb.mdi_client(hwnd)
    print("  alvo = %s (MDIClient=%s)" % (alvo, alvo != hwnd))
    if PROBE.exists():
        PROBE.unlink()

    lisp = (
        '(progn (setq f (open "C:/temp/mcp_probe.txt" "w"))'
        ' (write-line "mcp-cad-server: injecao OK" f) (close f) (princ))'
    )
    # AutoLISP não gosta de ':' em nome de função própria; usamos apenas built-ins.
    wb.enviar_esc(hwnd)
    time.sleep(0.5)
    print("  injetando probe...")
    wb.post_texto(alvo, lisp)
    for i in range(20):
        time.sleep(0.5)
        if PROBE.exists():
            print("  [OK] PROBE em %.1fs -> %s" % ((i + 1) * 0.5, PROBE.read_text(errors="replace").strip()))
            return True
    print("  [FALHOU] probe NAO apareceu em 10s")
    return False


# ---------------------------------------------------------------- 3. CARGA
def etapa3_carga(hwnd: int) -> bool:
    titulo("3. CARGA do dispatcher LISP")
    r = wb.carregar_ponte(hwnd, espera=3.0)
    print("  %s" % json.dumps(r, ensure_ascii=False))
    return bool(r.get("ok"))


# ---------------------------------------------------------------- 4. IPC
def etapa4_ipc(hwnd: int) -> dict:
    titulo("4. IPC — (c:mcp-dispatch) de verdade")
    ipc = wb.ipc_dir()
    ipc.mkdir(parents=True, exist_ok=True)
    alvo = wb.mdi_client(hwnd)

    rid = uuid.uuid4().hex[:12]
    cmd = ipc / f"autocad_mcp_cmd_{rid}.json"
    res = ipc / f"autocad_mcp_result_{rid}.json"
    payload = {"request_id": rid, "command": "ping", "params": {}, "ts": time.time()}
    cmd.write_text(json.dumps(payload), encoding="utf-8")
    print("  comando: %s" % cmd.name)

    wb.post_texto(alvo, "(c:mcp-dispatch)")
    for i in range(30):
        time.sleep(0.5)
        if res.exists():
            raws = res.read_text(encoding="utf-8", errors="replace")
            print("  [OK] resposta em %.1fs: %s" % ((i + 1) * 0.5, raws[:400]))
            try:
                return json.loads(raws)
            except Exception:
                return {"raw": raws}
    print("  [FALHOU] sem resposta em 15s")
    return {}


# ---------------------------------------------------------------- 5. BACKEND
def etapa5_backend() -> bool:
    titulo("5. BACKEND Python (vendorizado, com NOSSO detector)")
    import asyncio

    from autocad_mcp.backends.file_ipc import FileIPCBackend

    async def run():
        b = FileIPCBackend()
        st = await b.initialize()
        print("  initialize.ok = %s" % st.ok)
        if not st.ok:
            print("  erro: %s" % st.error)
            return False
        info = await b.drawing_info()
        print("  drawing_info: %s" % json.dumps(info.to_dict(), ensure_ascii=False)[:400])
        ec = await b.entity_count()
        print("  entity_count: %s" % json.dumps(ec.to_dict(), ensure_ascii=False)[:200])
        return True

    return asyncio.run(run())


# ---------------------------------------------------------------- 6. PDF
def etapa6_pdf() -> Path | None:
    titulo("6. PDF — plotando pelo proprio AutoCAD")
    import asyncio

    from autocad_mcp.backends.file_ipc import FileIPCBackend

    async def run():
        b = FileIPCBackend()
        r = await b.initialize()
        if not r.ok:
            print("  initialize falhou: %s" % r.error)
            return False
        if PDF_SAIDA.exists():
            PDF_SAIDA.unlink()
        print("  pedindo drawing-plot-pdf -> %s" % PDF_SAIDA)
        out = await b.drawing_plot_pdf(str(PDF_SAIDA).replace("\\", "/"))
        print("  ok=%s erro=%s payload=%s" % (out.ok, out.error, json.dumps(out.payload, ensure_ascii=False)[:300]))
        return out.ok and PDF_SAIDA.exists()

    return PDF_SAIDA if asyncio.run(run()) else None


if __name__ == "__main__":
    ate = 99
    if len(sys.argv) > 2 and sys.argv[1] == "--ate":
        ate = int(sys.argv[2])

    hwnd = etapa1_achar()
    ok = True
    if ate >= 2:
        ok = etapa2_probe(hwnd)
    if ok and ate >= 3:
        ok = etapa3_carga(hwnd)
    if ok and ate >= 4:
        etapa4_ipc(hwnd)
    if ok and ate >= 5:
        etapa5_backend()
    if ok and ate >= 6:
        p = etapa6_pdf()
        print("\nPDF: %s" % (p if p else "NAO gerado"))
