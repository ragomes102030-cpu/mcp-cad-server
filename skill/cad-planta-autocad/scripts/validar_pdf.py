# -*- coding: utf-8 -*-
"""Valida um PDF de plotagem (sem abrir leitor de PDF).

    python validar_pdf.py planta.pdf

Responde: o arquivo e PDF mesmo? quantas paginas? que folha? quanto do papel
foi usado? sobrou margem demais (plot "esticado" por extents errados)? gera um
PNG de previa ao lado do PDF.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def validar(arq: Path) -> int:
    print("arquivo   : %s (%.1f KB)" % (arq, arq.stat().st_size / 1024.0))
    assinatura = arq.read_bytes()[:5]
    ok_assinatura = assinatura == b"%PDF-"
    print("assinatura: %r %s" % (assinatura, "OK" if ok_assinatura else "INVALIDO"))
    if not ok_assinatura:
        return 1

    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf

    try:
        import numpy as np
    except ImportError:
        np = None

    doc = pymupdf.open(arq)
    print("paginas   : %d" % len(doc))
    pg = doc[0]
    print("folha     : %.0f x %.0f mm"
          % (pg.rect.width * 25.4 / 72, pg.rect.height * 25.4 / 72))

    pix = pg.get_pixmap(dpi=150)
    previa = arq.with_name(arq.stem + "_preview.png")
    pix.save(previa)
    print("previa    : %s (%d x %d px)" % (previa.name, pix.width, pix.height))

    if np is None:
        return 0

    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    escuro = a.mean(axis=2) < 200
    tinta = float(escuro.mean()) * 100
    print("tinta     : %.2f%%" % tinta)
    if escuro.any():
        ys, xs = np.where(escuro)
        mm = 25.4 / 150
        esq = xs.min() * mm
        topo = ys.min() * mm
        dir_ = (pix.width - xs.max()) * mm
        base = (pix.height - ys.max()) * mm
        print("margens   : esq %.1f | dir %.1f | topo %.1f | base %.1f mm" % (esq, dir_, topo, base))
        print("desenho   : %.0f x %.0f mm" % ((xs.max() - xs.min()) * mm, (ys.max() - ys.min()) * mm))

    print("textos    : %d caracteres extraiveis (SHX vira vetor: 0 e normal)"
          % len(pg.get_text().strip()))

    if tinta < 0.3:
        print("!! tinta quase nula: o plot pegou a area errada (extents vazios?)")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Valida um PDF de plotagem gerado pelo AutoCAD.")
    ap.add_argument("pdf")
    args = ap.parse_args()
    arq = Path(args.pdf)
    if not arq.exists():
        raise SystemExit("nao encontrado: %s" % arq)
    return validar(arq)


if __name__ == "__main__":
    sys.exit(main())
