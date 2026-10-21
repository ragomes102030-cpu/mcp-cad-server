# -*- coding: utf-8 -*-
"""Renderiza uma planta baixa a partir de um MODELO em JSON.

O JSON tem o mesmo schema do dict "modelo" de `cad_mcp/planta.py`
(ver references/modelo-planta.md).

Uso:
    python render_planta.py modelo.json
    python render_planta.py modelo.json --nome planta_sobrado --media A3
    python render_planta.py modelo.json --entrega "C:/caminho/da/conversa"
    python render_planta.py modelo.json --sem-pdf --sem-entrega

Fluxo interno (a ordem importa):
    conecta no AutoCAD vivo (COM) -> desenho novo -> desenha o modelo
    -> SALVA o DWG -> exporta DXF (accoreconsole lê o arquivo no disco!)
    -> plota PDF -> screenshot -> copia para as pastas de entrega -> confere.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ------------------------------------------------------------------ localização
PROJETO = Path(os.environ.get("MCP_CAD_SERVER", r"C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad"))
if not (PROJETO / "src" / "cad_mcp" / "planta.py").exists():
    raise SystemExit("mcp-cad-server nao encontrado em %s (defina MCP_CAD_SERVER)" % PROJETO)
sys.path.insert(0, str(PROJETO / "src"))

from cad_mcp.com_backend import ComBackend            # noqa: E402
from cad_mcp.planta import desenhar_modelo, num_br    # noqa: E402

# Todos os caminhos de trabalho ficam SEM ESPACO: SendCommand trata espaco como ENTER.
TMP = Path(os.environ.get("MCP_CAD_TEMP", r"C:/temp/mcp_cad_com"))
DESKTOP = Path(os.environ.get("USERPROFILE", r"C:\Users")) / "Desktop"

VERDE, AMARELO, VERMELHO, FIM = "\033[92m", "\033[93m", "\033[91m", "\033[0m"


def diga(*partes) -> None:
    print("   " + " ".join(str(p) for p in partes), flush=True)


def _marca(ok: bool) -> str:
    return (VERDE + "OK" + FIM) if ok else (VERMELHO + "FALHA" + FIM)


# ------------------------------------------------------------------ verificação
def conferir_dxf(dxf: Path) -> dict:
    """Confere o DXF gerado: unidades, contagens, extensão e abertura dos arcos.

    A abertura dos arcos é a checagem que pega o erro clássico do AutoCAD:
    `entmake`/`entget` no AutoLISP usam RADIANOS nos grupos 50/51, então um
    arco de porta "nasce" com 116,62° em vez de 90° — e o desenho continua
    sem erro nenhum. Só medindo a abertura o problema aparece.
    """
    saida = {"arquivo": str(dxf), "existe": dxf.exists()}
    if not dxf.exists():
        return saida
    try:
        import ezdxf
        from ezdxf import bbox
    except ImportError:
        saida["aviso"] = "ezdxf nao instalado: conferencia parcial"
        return saida

    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    saida["insunits"] = doc.header.get("$INSUNITS")
    saida["unidades_ok"] = saida["insunits"] == 6  # 6 = metros

    tipos, camadas = {}, {}
    for e in msp:
        tipos[e.dxftype()] = tipos.get(e.dxftype(), 0) + 1
        camadas[e.dxf.layer] = camadas.get(e.dxf.layer, 0) + 1
    saida["entidades"] = len(msp)
    saida["tipos"] = tipos
    saida["camadas"] = camadas

    ext = bbox.extents(msp)
    saida["extensao"] = {"x": round(ext.size.x, 2), "y": round(ext.size.y, 2)}

    aberturas = []
    for e in msp:
        if e.dxftype() == "ARC":
            aberturas.append(round((e.dxf.end_angle - e.dxf.start_angle) % 360.0, 3))
    saida["aberturas_arco"] = aberturas
    saida["arcos_90"] = all(abs(a - 90.0) < 0.01 for a in aberturas) if aberturas else None

    areas = {}
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.closed and e.dxf.layer in ("TERRENO", "PAREDES"):
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            soma = 0.0
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                soma += x1 * y2 - x2 * y1
            areas[e.dxf.layer] = round(float(areas.get(e.dxf.layer, 0.0)) + abs(soma) / 2.0, 2)
    saida["areas"] = areas
    return saida


def conferir_pdf(pdf: Path) -> dict:
    saida = {"arquivo": str(pdf), "existe": pdf.exists()}
    if not pdf.exists():
        return saida
    saida["bytes"] = pdf.stat().st_size
    saida["assinatura_ok"] = pdf.read_bytes()[:5] == b"%PDF-"
    try:
        import fitz
        import numpy as np

        doc = fitz.open(pdf)
        saida["paginas"] = len(doc)
        pg = doc[0]
        saida["folha_mm"] = [round(pg.rect.width * 25.4 / 72), round(pg.rect.height * 25.4 / 72)]
        pix = pg.get_pixmap(dpi=150)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
        escuro = a.mean(axis=2) < 200
        saida["tinta_pct"] = round(float(escuro.mean()) * 100, 2)
        if escuro.any():
            ys, xs = np.where(escuro)
            mm = 25.4 / 150
            saida["margens_mm"] = [round(float(xs.min()) * mm, 1),
                                   round(float(pix.width - xs.max()) * mm, 1),
                                   round(float(ys.min()) * mm, 1),
                                   round(float(pix.height - ys.max()) * mm, 1)]
        previa = pdf.with_name(pdf.stem + "_preview.png")
        pix.save(previa)
        saida["preview"] = str(previa)
    except ImportError:
        saida["aviso"] = "pymupdf/numpy nao instalados: conferencia parcial"
    return saida


# ------------------------------------------------------------------ render
async def renderizar(modelo: dict, nome: str, media: str | None = None,
                     destino: list[Path] | None = None,
                     fazer_pdf: bool = True, fazer_dxf: bool = True) -> dict:
    TMP.mkdir(parents=True, exist_ok=True)
    resultado: dict = {"nome": nome, "erros": [], "entregues": []}

    print("1) conectando no AutoCAD (COM)...", flush=True)
    b = ComBackend()
    r = await b.initialize()
    if not r.ok:
        raise SystemExit("AutoCAD nao respondeu: %s" % r.error)
    diga("conectado:", (r.payload or {}).get("versao") or (r.payload or {}).get("aplicacao") or "ok")

    print("2) desenho novo...")
    r = await b.drawing_create()
    if not r.ok:
        raise SystemExit("nao consegui criar o desenho: %s" % r.error)

    print("3) desenhando o modelo...")
    t0 = time.time()
    res = await desenhar_modelo(b, modelo, log=diga)
    if res.get("valido") is False:
        # validacao reprovou: nem chegamos a desenhar (nao gastamos um ciclo COM->DXF->PDF)
        for p in res.get("erros_validacao", []):
            print("  ERRO %-22s %-26s %s" % (p["chave"], p["onde"], p["detalhe"]))
        raise SystemExit("modelo reprovado na validacao -- nada foi desenhado")
    resultado.update({k: res[k] for k in ("entidades_criadas", "erros", "areas", "area_util")})
    diga("%.1f s | entidades=%d | erros=%d" % (time.time() - t0, res["entidades_criadas"], len(res["erros"])))
    diga("area util: %s m2" % num_br(res["area_util"]))
    for e in res["erros"][:6]:
        diga("!", e)

    arquivos: list[Path] = []

    # o DWG sempre sai: é a base do DXF e do PDF
    # ARMADILHA CONHECIDA: sobrescrever um DWG que já existe (ou que está aberto)
    # devolve "Error saving the document". Apagar antes resolve.
    print("4) salvando DWG...")
    for sufixo in ("", "_2", "_3"):
        dwg = TMP / ("%s%s.dwg" % (nome, sufixo))
        try:
            if dwg.exists():
                dwg.unlink()
        except OSError as exc:
            diga("nao consegui apagar %s (%s); tento outro nome" % (dwg.name, exc))
            continue
        r = await b.drawing_save(str(dwg))
        if r.ok and dwg.exists():
            arquivos.append(dwg)
            break
        diga("falhou salvar %s: %s" % (dwg.name, r.error))
    else:
        raise SystemExit("nao consegui salvar o DWG em nenhum nome")

    nome = dwg.stem  # se caiu no fallback, DXF/PDF acompanham o nome real
    resultado["nome"] = nome

    if fazer_dxf:
        print("5) exportando DXF (accoreconsole)...")
        dxf = TMP / ("%s.dxf" % nome)
        if dxf.exists():
            dxf.unlink()
        r = await b.drawing_save_as_dxf(str(dxf))
        if r.ok and dxf.exists() and dxf.stat().st_size > 1000:
            arquivos.append(dxf)
        else:
            diga("DXF nao saiu:", r.error if not r.ok else "arquivo vazio")

    if fazer_pdf:
        print("6) plotando PDF...")
        pdf = TMP / ("%s.pdf" % nome)
        if pdf.exists():
            pdf.unlink()
        r = await b.drawing_plot_pdf(str(pdf), media=media)
        if r.ok and pdf.exists() and pdf.stat().st_size > 500:
            arquivos.append(pdf)
        else:
            diga("PDF nao saiu:", r.error if not r.ok else "arquivo vazio")

    print("7) screenshot...")
    try:
        r = await b.get_screenshot()
        if r.ok:
            origem = (r.payload or {}).get("arquivo") or (r.payload or {}).get("png")
            if origem and Path(origem).exists():
                png = TMP / ("%s.png" % nome)
                shutil.copy2(origem, png)
                arquivos.append(png)
    except Exception as exc:
        diga("screenshot falhou:", exc)

    print("8) conferindo o que foi gerado...")
    dxf_final = TMP / ("%s.dxf" % nome)
    pdf_final = TMP / ("%s.pdf" % nome)
    resultado["conferencia_dxf"] = conferir_dxf(dxf_final) if fazer_dxf else {}
    resultado["conferencia_pdf"] = conferir_pdf(pdf_final) if fazer_pdf else {}

    pastas = list(destino or [PROJETO / "saida", DESKTOP])
    print("9) entregando em %d pasta(s)..." % len(pastas))
    for pasta in pastas:
        try:
            if not pasta or not str(pasta).strip():
                continue
            pasta = Path(pasta)
            pasta.mkdir(parents=True, exist_ok=True)
            for f in arquivos:
                shutil.copy2(f, pasta / f.name)
                resultado["entregues"].append(str(pasta / f.name))
        except Exception as exc:
            resultado["erros"].append("entrega em %s: %s" % (pasta, exc))

    return resultado


# ------------------------------------------------------------------ CLI
def relatar(res: dict) -> None:
    dxf = res.get("conferencia_dxf") or {}
    pdf = res.get("conferencia_pdf") or {}
    print("\n================ CONFERENCIA ================")
    if dxf.get("existe"):
        print(" DXF: %d entidades | camadas: %s" % (dxf.get("entidades", 0), ", ".join(sorted(dxf.get("camadas", {})))))
        print("      unidades : %s (%s)" % (dxf.get("insunits"), _marca(bool(dxf.get("unidades_ok")))))
        print("      extensao : %s x %s m" % (dxf["extensao"]["x"], dxf["extensao"]["y"]))
        print("      areas    : %s m2" % dxf.get("areas"))
        if dxf.get("aberturas_arco"):
            ruins = [a for a in dxf["aberturas_arco"] if abs(a - 90.0) >= 0.01]
            print("      portas   : %d arcos | abertura 90 graus: %s"
                  % (len(dxf["aberturas_arco"]), _marca(bool(dxf.get("arcos_90")))))
            if ruins:
                print(VERMELHO + "      !! arco(s) fora de 90 graus: %s" % ruins[:8] + FIM)
                print("      !! sintoma classico de graus passados onde entmake espera RADIANOS")
    else:
        print(" DXF: nao gerado")
    if pdf.get("existe"):
        print(" PDF: %s paginas | folha %s mm | tinta %s%% | margens L/D/T/B %s mm"
              % (pdf.get("paginas"), pdf.get("folha_mm"), pdf.get("tinta_pct"), pdf.get("margens_mm")))
        print("      assinatura %s" % _marca(bool(pdf.get("assinatura_ok"))))
    else:
        print(" PDF: nao gerado")
    print(" area util : %s m2" % res.get("area_util"))
    print(" entregues : %d arquivo(s)" % len(res.get("entregues", [])))
    if res.get("erros"):
        print(AMARELO + " erros     : %s" % res["erros"][:6] + FIM)
    print("=============================================")


def main() -> int:
    ap = argparse.ArgumentParser(description="Renderiza uma planta baixa (modelo JSON) no AutoCAD vivo.")
    ap.add_argument("modelo", help="arquivo .json com o dict 'modelo'")
    ap.add_argument("--nome", help="nome base dos arquivos (padrao: nome do json)")
    ap.add_argument("--media", help="folha do plot, ex. A3 (padrao: A4 preferido)")
    ap.add_argument("--entrega", action="append", default=None,
                    help="pasta extra de entrega (pode repetir). Padrao: saida/ + Desktop")
    ap.add_argument("--sem-pdf", action="store_true")
    ap.add_argument("--sem-dxf", action="store_true")
    ap.add_argument("--sem-entrega", action="store_true")
    args = ap.parse_args()

    origem = Path(args.modelo)
    if not origem.exists():
        raise SystemExit("modelo nao encontrado: %s" % origem)
    modelo = json.loads(origem.read_text(encoding="utf-8"))
    nome = args.nome or origem.stem

    destino = None if args.sem_entrega else args.entrega
    res = asyncio.run(renderizar(modelo, nome, media=args.media, destino=destino,
                                 fazer_pdf=not args.sem_pdf, fazer_dxf=not args.sem_dxf))
    relatar(res)

    dxf = res.get("conferencia_dxf") or {}
    ok = (not dxf.get("existe")) or (dxf.get("unidades_ok") and dxf.get("arcos_90") is not False)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
