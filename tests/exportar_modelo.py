# -*- coding: utf-8 -*-
"""Exporta o MODELO de tests/planta_3q.py para JSON (template do modelo de planta)."""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent / "src"))

import planta_3q  # noqa: E402

destino = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "modelo-3-quartos.json"
destino.parent.mkdir(parents=True, exist_ok=True)
txt = json.dumps(planta_3q.MODELO, ensure_ascii=False, indent=2)
destino.write_text(txt, encoding="utf-8")

print("gravado: %s (%d B)" % (destino, len(txt.encode("utf-8"))))
print("chaves : %s" % ", ".join(planta_3q.MODELO.keys()))
print("paredes: %d trechos | ambientes: %d | portas: %d | janelas: %d | moveis: %d"
      % (len(planta_3q.MODELO["paredes"]), len(planta_3q.MODELO["ambientes"]),
         len(planta_3q.MODELO["portas"]), len(planta_3q.MODELO["janelas"]),
         len(planta_3q.MODELO["moveis"])))
