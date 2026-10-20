# -*- coding: utf-8 -*-
"""Planta baixa de 3 quartos (~120 m2) desenhada no AutoCAD vivo (COM) + PDF.

Aqui mora so a GEOMETRIA; o motor e o `cad_mcp.planta` (renderizador generico).
Fluxo: conecta no AutoCAD -> desenho novo -> modelo -> DWG -> DXF -> PDF -> PNG.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.com_backend import ComBackend          # noqa: E402
from cad_mcp.planta import desenhar_modelo, num_br  # noqa: E402

TMP = Path("C:/temp/mcp_cad_com")
TMP.mkdir(parents=True, exist_ok=True)
ENTREGA = RAIZ / "saida"
ENTREGA.mkdir(parents=True, exist_ok=True)

CONVERSA = Path(r"C:\Users\Correta Engenharia\AppData\Roaming\Arquimedes\arquimedes"
                r"\conversations\users\system_default_user\2026\10\16"
                r"\aionrs-temp-65d9ff37")
DESKTOP = Path(r"C:\Users\Correta Engenharia\Desktop")

NOME = "planta_3q"

# ---------------------------------------------------------------- geometria (m)
T = 0.15          # espessura da parede
FOOT = (13.00, 10.00)   # eixos externos 13,00 x 10,00 m

# terreno: 18,00 x 15,00 m com 2,50 m de recuo frontal/laterais
TERRENO = (-2.50, -2.50, 15.50, 12.50)

# ---- eixos das paredes (vaos das portas = trechos separados)
PAREDES = [
    # --- externas (cantos estendidos em 0,075 para fechar a espessura)
    (-0.075, 0.000, 8.600, 0.000),      # frente, trecho esquerdo
    (9.500, 0.000, 13.075, 0.000),      # frente, trecho direito (vao da entrada)
    (13.000, -0.075, 13.000, 8.600),    # direita, trecho baixo
    (13.000, 9.500, 13.000, 10.075),    # direita, trecho alto (vao da porta de servico)
    (13.075, 10.000, -0.075, 10.000),   # fundo
    (0.000, 10.075, 0.000, -0.075),     # esquerda
    # --- divisoria principal (sala | quartos) com o vao do corredor
    (7.000, 0.000, 7.000, 5.175),
    (7.000, 6.125, 7.000, 10.000),
    # --- corredor
    (0.000, 5.100, 2.300, 5.100),       # corredor/suite (vao da porta)
    (3.100, 5.100, 7.000, 5.100),
    (0.000, 6.200, 2.600, 6.200),       # corredor/quartos (vaos das portas)
    (3.400, 6.200, 4.100, 6.200),
    (4.900, 6.200, 7.000, 6.200),
    # --- quartos
    (3.500, 6.125, 3.500, 10.000),      # quarto 1 | quarto 2
    # --- suite / banheiro suite / closet
    (4.300, 0.000, 4.300, 1.200),       # (vao do closet)
    (4.300, 2.000, 4.300, 3.600),       # (vao do banheiro da suite)
    (4.300, 4.300, 4.300, 5.175),
    (4.300, 2.800, 7.000, 2.800),       # banheiro suite | closet
    # --- sala | cozinha / banheiro social / area de servico
    (7.000, 6.200, 8.300, 6.200),       # (vao porta sala->cozinha)
    (9.100, 6.200, 11.200, 6.200),      # (vao porta sala->banheiro social)
    (11.900, 6.200, 13.000, 6.200),
    (10.300, 6.125, 10.300, 8.600),     # cozinha | coluna direita (vao area de servico)
    (10.300, 9.300, 10.300, 10.000),
    (10.300, 8.300, 13.000, 8.300),     # banheiro social | area de servico
]

# ---- ambientes: medidas LIVRES (entre faces internas das paredes)
AMBIENTES = [
    {"nome": "QUARTO 1",        "x1": 0.075, "y1": 6.275, "x2": 3.425, "y2": 9.925},
    {"nome": "QUARTO 2",        "x1": 3.575, "y1": 6.275, "x2": 6.925, "y2": 9.925},
    {"nome": "CIRCULACAO",      "x1": 0.075, "y1": 5.175, "x2": 6.925, "y2": 6.125, "h": 0.18},
    {"nome": "SUITE",           "x1": 0.075, "y1": 0.075, "x2": 4.225, "y2": 5.025},
    {"nome": "BANHEIRO SUITE",  "x1": 4.375, "y1": 2.875, "x2": 6.925, "y2": 5.025, "h": 0.15},
    {"nome": "CLOSET",          "x1": 4.375, "y1": 0.075, "x2": 6.925, "y2": 2.725, "h": 0.17},
    {"nome": "SALA DE ESTAR/JANTAR", "x1": 7.075, "y1": 0.075, "x2": 12.925, "y2": 6.125, "h": 0.24},
    {"nome": "COZINHA",         "x1": 7.075, "y1": 6.275, "x2": 10.225, "y2": 9.925},
    {"nome": "BANHEIRO SOCIAL", "x1": 10.375, "y1": 6.275, "x2": 12.925, "y2": 8.225, "h": 0.15},
    {"nome": "AREA DE SERVICO", "x1": 10.375, "y1": 8.375, "x2": 12.925, "y2": 9.925, "h": 0.15},
]

# ---- portas: (x, y, angulo_graus, largura)  -> arco de 90 graus + folha
PORTAS = [
    (8.600, 0.075, 90.0, 0.90),    # entrada -> sala
    (8.300, 6.275, 90.0, 0.80),    # sala -> cozinha
    (11.200, 6.275, 90.0, 0.70),   # sala -> banheiro social
    (3.400, 6.275, 90.0, 0.80),    # circulacao -> quarto 1
    (4.900, 6.275, 90.0, 0.80),    # circulacao -> quarto 2
    (3.100, 5.025, 180.0, 0.80),   # circulacao -> suite
    (4.375, 3.600, 0.0, 0.70),     # suite -> banheiro suite
    (4.375, 1.200, 0.0, 0.80),     # suite -> closet
    (10.375, 8.600, 0.0, 0.70),    # cozinha -> area de servico
    (12.925, 9.500, 180.0, 0.80),  # area de servico -> externo
]

# ---- janelas: (x1, y1, x2, y2)
JANELAS = [
    (1.200, 0.000, 2.800, 0.000),      # suite - frente
    (0.000, 2.200, 0.000, 3.800),      # suite - esquerda
    (10.000, 0.000, 12.400, 0.000),    # sala - frente
    (1.000, 10.000, 2.600, 10.000),    # quarto 1 - fundo
    (0.000, 7.000, 0.000, 8.600),      # quarto 1 - esquerda
    (4.500, 10.000, 6.100, 10.000),    # quarto 2 - fundo
    (7.600, 10.000, 9.600, 10.000),    # cozinha - fundo
    (13.000, 6.900, 13.000, 7.700),    # banheiro social - direita
]

# ---- mobiliario: (x1, y1, x2, y2)
MOVEIS = [
    (0.450, 0.450, 2.050, 2.350),      # cama de casal (suite)
    (2.300, 0.450, 4.100, 0.850),      # guarda-roupa (suite)
    (0.600, 7.100, 1.500, 9.000),      # cama solteiro (quarto 1)
    (1.900, 9.200, 3.250, 9.800),      # guarda-roupa (quarto 1)
    (4.100, 7.100, 5.000, 9.000),      # cama solteiro (quarto 2)
    (5.400, 9.200, 6.700, 9.800),      # guarda-roupa (quarto 2)
    (7.400, 1.200, 9.900, 2.100),      # sofa (sala)
    (8.200, 3.400, 9.800, 4.600),      # mesa de jantar (sala)
    (11.900, 1.200, 12.800, 3.000),    # painel/rack (sala)
    (7.200, 9.200, 9.800, 9.850),      # bancada (cozinha)
    (10.550, 6.450, 11.150, 7.050),    # vaso (banheiro social)
    (12.250, 6.450, 12.850, 7.050),    # pia (banheiro social)
    (4.550, 4.300, 5.150, 4.900),      # vaso (banheiro suite)
    (6.150, 4.300, 6.850, 4.900),      # pia (banheiro suite)
    (4.600, 0.350, 6.700, 0.950),      # armario (closet)
    (10.550, 9.250, 11.350, 9.850),    # tanque (area de servico)
]

# ---- cotas
COTAS_H = [
    (0.00, 4.30, 0.0, -0.80),
    (4.30, 7.00, 0.0, -0.80),
    (7.00, 13.00, 0.0, -0.80),
    (0.00, 13.00, 0.0, -1.60),
]
COTAS_V = [
    (0.0, 0.00, 5.10, -0.80),
    (0.0, 5.10, 10.00, -0.80),
    (0.0, 0.00, 10.00, -1.60),
]

# ---- selo / legenda
SELO = [
    (0.00, -3.30, "PLANTA BAIXA - RESIDENCIA UNIFAMILIAR", 0.22),
    (0.00, -3.78, "3 QUARTOS (1 SUITE) - AREA UTIL 119,56 m2 - EIXOS 13,00 x 10,00 m", 0.20),
    (0.00, -4.22, "SUITE 20,54 | BANH. SUITE 5,48 | CLOSET 6,76 | QUARTO 1 12,23 | QUARTO 2 12,23", 0.17),
    (0.00, -4.58, "CIRCULACAO 6,51 | SALA DE ESTAR/JANTAR 35,39 | COZINHA 11,50 | BANH. SOCIAL 4,97", 0.17),
    (0.00, -4.94, "AREA DE SERVICO 3,95 | AREA CONSTRUIDA 130,00 m2", 0.17),
    (0.00, -5.30, "TERRENO 18,00 x 15,00 m (270,00 m2) | RECUOS 2,50 m | PAREDES 0,15 m | PE-DIREITO 2,80 m", 0.17),
    (0.00, -5.66, "COTAS EM METROS - 10 PORTAS - 8 JANELAS", 0.17),
    (0.00, -6.02, "GERADO POR mcp-cad-server (AutoCAD 2025 via COM) - 16/10/2026", 0.16),
]

MODELO = {
    "titulo": "Residencia unifamiliar 3 quartos",
    "espessura_parede": T,
    "terreno": TERRENO,
    "paredes": PAREDES,
    "ambientes": AMBIENTES,
    "portas": PORTAS,
    "janelas": JANELAS,
    "moveis": MOVEIS,
    "cotas_h": COTAS_H,
    "cotas_v": COTAS_V,
    "selo": SELO,
    "dim_txt": 0.22,
    "dim_asz": 0.18,
}


def diga(*a):
    print("   " + " ".join(str(x) for x in a), flush=True)


def espalhar(caminho: Path) -> list[str]:
    destinos = []
    for pasta in (CONVERSA, DESKTOP):
        try:
            if pasta.exists() and pasta.resolve() != caminho.parent.resolve():
                shutil.copy2(caminho, pasta / caminho.name)
                destinos.append(str(pasta / caminho.name))
        except Exception as e:
            destinos.append("falhou %s: %s" % (pasta, e))
    return destinos


async def main() -> int:
    print("1) conectando ao AutoCAD...", flush=True)
    b = ComBackend()
    r = await b.initialize()
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    if not r.ok:
        return 2

    print("2) desenho novo...", flush=True)
    r = await b.drawing_create()
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))

    print("3) desenhando o modelo...", flush=True)
    t0 = time.time()
    res = await desenhar_modelo(b, MODELO, log=diga)
    print("   %.1f s | entidades=%d | erros=%d"
          % (time.time() - t0, res["entidades_criadas"], len(res["erros"])))
    if res["erros"]:
        for e in res["erros"][:8]:
            print("   ! %s" % e)
    print("   area util: %s m2" % num_br(res["area_util"]))

    print("4) contagem/camadas...", flush=True)
    r = await b.entity_count()
    print("   entidades no ModelSpace: %s" % (r.payload if r.ok else r.error))
    r = await b.layer_list()
    if r.ok and r.payload:
        print("   camadas: %s" % ", ".join(c["nome"] for c in r.payload))

    print("5) salvando DWG...", flush=True)
    dwg = TMP / ("%s.dwg" % NOME)
    r = await b.drawing_save(str(dwg))
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    entregues = []
    if dwg.exists():
        alvo = ENTREGA / dwg.name
        shutil.copy2(dwg, alvo)
        entregues.append(alvo)
        print("   DWG %.1f KB -> %s" % (dwg.stat().st_size / 1024.0, alvo))

    print("6) exportando DXF (accoreconsole)...", flush=True)
    dxf = ENTREGA / ("%s.dxf" % NOME)
    r = await b.drawing_save_as_dxf(str(dxf))
    info = dict(r.payload) if r.ok else {"erro": r.error}
    info.pop("saida", None)
    print("   %s" % json.dumps(info, ensure_ascii=False))
    if dxf.exists():
        entregues.append(dxf)
        print("   DXF %.1f KB" % (dxf.stat().st_size / 1024.0))

    print("7) plotando PDF (A3)...", flush=True)
    pdf = ENTREGA / ("%s.pdf" % NOME)
    r = await b.drawing_plot_pdf(str(pdf), media="A3")
    print("   %s" % json.dumps(r.payload if r.ok else {"erro": r.error}, ensure_ascii=False))
    if pdf.exists() and pdf.stat().st_size > 500:
        entregues.append(pdf)
        print("   PDF %.1f KB -> %s" % (pdf.stat().st_size / 1024.0, pdf))

    print("8) screenshot...", flush=True)
    r = await b.get_screenshot()
    if r.ok:
        cam = (r.payload or {}).get("arquivo") or (r.payload or {}).get("png")
        print("   %s" % json.dumps(r.payload, ensure_ascii=False))
        if cam and Path(cam).exists():
            png = ENTREGA / ("%s.png" % NOME)
            shutil.copy2(cam, png)
            entregues.append(png)

    print("9) espalhando os arquivos...", flush=True)
    for f in list(entregues):
        for d in espalhar(f):
            print("   %s -> %s" % (f.name, d))
        time.sleep(0.05)

    print("\n== resumo ==")
    print(json.dumps({k: res[k] for k in ("entidades_criadas", "area_util", "areas")},
                     ensure_ascii=False, indent=2))
    print("arquivos: %s" % ", ".join(f.name for f in entregues))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
