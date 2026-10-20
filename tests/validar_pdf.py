# -*- coding: utf-8 -*-
"""Valida o PDF gerado: assinatura, paginas e 'tinta' (nao pode estar em branco)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PDF = Path(r"C:\Users\Correta Engenharia\mcp-cad-server\saida\planta_mcp.pdf")
ENTREGA_DIRS = [
    Path(r"C:\Users\Correta Engenharia\AppData\Roaming\Arquimedes\arquimedes\conversations\users\system_default_user\2026\10\16\aionrs-temp-65d9ff37"),
    Path(r"C:\Users\Correta Engenharia\Desktop"),
]

bruto = PDF.read_bytes()
print("arquivo : %s" % PDF)
print("tamanho : %d bytes" % len(bruto))
print("cabeca  : %r" % bruto[:8])
print("rodape  : %r" % bruto[-30:])
print("paginas : obj /Type /Page -> %d" % bruto.count(b"/Type /Page"))
print("media   : %s" % (b"/MediaBox" in bruto))

try:
    import fitz  # PyMuPDF

    doc = fitz.open(str(PDF))
    print("PyMuPDF : %d pagina(s)" % doc.page_count)
    pag = doc[0]
    print("  rect  : %s" % (pag.rect,))
    pix = pag.get_pixmap(dpi=150)
    png = PDF.with_suffix(".png")
    pix.save(str(png))
    print("  preview: %s (%dx%d px)" % (png, pix.width, pix.height))
    # tinta: conta pixels escuros
    amostra = pix.samples
    n = pix.width * pix.height
    escuros = 0
    for i in range(0, len(amostra), pix.n * 7):
        if amostra[i] < 200:
            escuros += 1
    pct = 100.0 * escuros / max(1, n // 7)
    print("  tinta  : ~%.2f%% dos pixels amostrados estao escuros" % pct)
    print("  TEXTO extraivel: %r" % (pag.get_text()[:200].replace("\n", " | "),))
except ImportError:
    print("PyMuPDF nao instalado (validacao visual limitada)")

print()
for d in ENTREGA_DIRS:
    if d.exists():
        alvo = d / PDF.name
        shutil.copy2(PDF, alvo)
        print("copiado -> %s (%d bytes)" % (alvo, alvo.stat().st_size))
        if (PDF.with_suffix(".png")).exists():
            alvo_png = d / PDF.with_suffix(".png").name
            shutil.copy2(PDF.with_suffix(".png"), alvo_png)
            print("copiado -> %s" % alvo_png)
    else:
        print("(nao existe) %s" % d)
