# -*- coding: utf-8 -*-
"""Ponte headless com o `accoreconsole.exe` do AutoCAD.

O accoreconsole e' o AutoCAD sem interface: abre um DWG, roda um script .scr e
sai. E' a rota ideal para converter/plotar em lote porque
  - nao abre dialogo nenhum (nao travа o COM da sessao aberta do usuario);
  - nao depende de janela nem de foco;
  - e' rapido (~3s para um desenho simples).

Usamos para: DWG -> DXF (alimentar o quantitativo/ezdxf) e DWG -> PDF
(quando nao ha uma sessao interativa do AutoCAD).
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import time
from pathlib import Path

__all__ = ["achar_accore", "dwg_para_dxf", "dwg_para_pdf", "disponivel"]


def _candidatos() -> list[str]:
    padroes = []
    for raiz in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        padroes += glob.glob(os.path.join(raiz, "Autodesk", "AutoCAD*", "accoreconsole.exe"))
        padroes += glob.glob(os.path.join(raiz, "Autodesk", "AutoCAD*", "*", "accoreconsole.exe"))
    extra = os.environ.get("MCP_CAD_ACCORE")
    if extra:
        padroes.insert(0, extra)
    vistos, saida = set(), []
    for p in padroes:
        if p not in vistos and Path(p).exists():
            vistos.add(p)
            saida.append(p)
    return saida


def achar_accore() -> str | None:
    """Acha o accoreconsole.exe (a versao mais nova primeiro)."""
    c = _candidatos()
    if not c:
        return None
    return sorted(c, reverse=True)[0]


def disponivel() -> bool:
    return achar_accore() is not None


def _pasta_temp() -> Path:
    p = Path(os.environ.get("MCP_CAD_TEMP") or "C:/temp/mcp_cad_com")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rodar(dwg: str, linhas_scr: list[str], timeout: float = 240.0) -> dict:
    exe = achar_accore()
    if not exe:
        return {"ok": False, "erro": "accoreconsole.exe nao encontrado (defina MCP_CAD_ACCORE)"}
    scr = _pasta_temp() / ("script_%d.scr" % int(time.time() * 1000 % 10_000_000))
    scr.write_text("\n".join(linhas_scr) + "\n", encoding="ascii", errors="replace")
    t0 = time.time()
    try:
        p = subprocess.run(
            [exe, "/i", str(dwg), "/s", str(scr), "/l", "pt-BR"],
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "erro": "accoreconsole estourou %.0fs" % timeout}
    except Exception as e:
        return {"ok": False, "erro": str(e)}
    saida = (p.stdout or b"").decode("utf-16-le", errors="replace")
    return {
        "ok": p.returncode == 0,
        "exit": p.returncode,
        "segundos": round(time.time() - t0, 1),
        "saida": saida[-1200:],
        "script": str(scr),
    }


def dwg_para_dxf(dwg: str | Path, dxf: str | Path, versao: str = "2018", timeout: float = 240.0) -> dict:
    """Converte um DWG em DXF ASCII via accoreconsole (headless).

    ATENCAO: num script .scr o ESPACO termina o token, entao o arquivo e' sempre
    gerado primeiro numa pasta sem espacos (MCP_CAD_TEMP) e depois movido.
    """
    dwg, dxf = Path(dwg), Path(dxf)
    if not dwg.exists():
        return {"ok": False, "erro": "DWG inexistente: %s" % dwg}
    dxf.parent.mkdir(parents=True, exist_ok=True)
    if dxf.exists():
        try:
            dxf.unlink()
        except Exception:
            pass
    estagio = _pasta_temp() / ("conv_%d.dxf" % int(time.time() * 1000 % 10_000_000))
    if estagio.exists():
        estagio.unlink()
    r = _rodar(
        str(dwg),
        ["FILEDIA", "0", "CMDDIA", "0", "_.DXFOUT", str(estagio).replace("\\", "/"), "_V", versao, "16"],
        timeout,
    )
    if estagio.exists() and estagio.stat().st_size > 200:
        import shutil

        shutil.copy2(estagio, dxf)
        cabeca = dxf.read_bytes()[:32]
        r.update(
            {
                "dxf": str(dxf),
                "bytes": dxf.stat().st_size,
                "ascii": not cabeca.startswith(b"AutoCAD Binary DXF"),
                "ok": True,
            }
        )
        return r
    r["ok"] = False
    r.setdefault("erro", "DXFOUT nao gerou o arquivo")
    return r


def dwg_para_pdf(dwg: str | Path, pdf: str | Path, plotter: str = "DWG To PDF.pc3", timeout: float = 300.0) -> dict:
    """Plota um DWG direto para PDF via accoreconsole (headless)."""
    dwg, pdf = Path(dwg), Path(pdf)
    if not dwg.exists():
        return {"ok": False, "erro": "DWG inexistente: %s" % dwg}
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if pdf.exists():
        try:
            pdf.unlink()
        except Exception:
            pass
    estagio = _pasta_temp() / ("conv_%d.pdf" % int(time.time() * 1000 % 10_000_000))
    if estagio.exists():
        estagio.unlink()
    r = _rodar(
        str(dwg),
        [
            "FILEDIA", "0", "CMDDIA", "0", "BACKGROUNDPLOT", "0",
            "_.-PLOT", "_Y", "Model", plotter, "A4",
            "_M", "Landscape", "_N", "_E", "_F", "_C", "_Y",
            plotter, "_Y", str(estagio).replace("\\", "/"), "_N", "_Y",
        ],
        timeout,
    )
    if estagio.exists() and estagio.stat().st_size > 500:
        import shutil

        shutil.copy2(estagio, pdf)
        r.update({"pdf": str(pdf), "bytes": pdf.stat().st_size, "ok": True})
        return r
    r["ok"] = False
    r.setdefault("erro", "-PLOT nao gerou o PDF")
    return r


if __name__ == "__main__":
    print("accoreconsole:", achar_accore())
    if len(sys.argv) > 2:
        print(dwg_para_dxf(sys.argv[1], sys.argv[2]))
