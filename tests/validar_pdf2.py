# -*- coding: utf-8 -*-
"""Valida um PDF: assinatura, paginas, tamanho da folha e area util aproveitada."""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import fitz
import numpy as np

arq = Path(sys.argv[1] if len(sys.argv) > 1 else r"saida\planta_3q.pdf")
print("arquivo : %s (%.1f KB)" % (arq, arq.stat().st_size / 1024.0))
print("assinatura: %r" % arq.read_bytes()[:8])

d = fitz.open(arq)
print("paginas : %d" % len(d))
pg = d[0]
print("folha   : %.1f x %.1f pt = %.0f x %.0f mm"
      % (pg.rect.width, pg.rect.height,
         pg.rect.width * 25.4 / 72, pg.rect.height * 25.4 / 72))

pix = pg.get_pixmap(dpi=150)
a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
escuro = a.mean(axis=2) < 200
print("tinta   : %.2f%%" % (escuro.mean() * 100))
if escuro.any():
    ys, xs = np.where(escuro)
    print("margem  : esq %.1f mm | dir %.1f mm | topo %.1f mm | base %.1f mm"
          % (xs.min() * 25.4 / 150, (pix.width - xs.max()) * 25.4 / 150,
             ys.min() * 25.4 / 150, (pix.height - ys.max()) * 25.4 / 150))
    print("desenho : %.0f x %.0f mm" % ((xs.max() - xs.min()) * 25.4 / 150,
                                        (ys.max() - ys.min()) * 25.4 / 150))

saida = arq.with_name(arq.stem + "_preview.png")
pix.save(saida)
print("preview : %s (%d x %d px)" % (saida, pix.width, pix.height))

# texto vetorial?
txt = pg.get_text().strip()
print("fontes  : %s" % {f[3] for f in pg.get_fonts()})
print("textos  : %d caracteres extraiveis" % len(txt))
