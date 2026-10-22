"""regenerar_docs.py -- one generator for the whole AutoCAD mapping set.

Run this to refresh docs/ from the code (the canonical "keep the maps up to date"
command):

    python tools/regenerar_docs.py
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
DOCS = REPO / "docs"

PRODS = {
    "mapear_com": "C:/Users/Correta Engenharia/AppData/Local/Programs/Python/"
                  "Python310/python.exe",
}
GENS = [
    ("importar_acmpro", "docs/COBERTURA.md + docs/catalogo-acmpro.json"),
    ("mapear_com", "docs/MAPA-COM.md, docs/com-acad-2025.json, docs/ALIASES.md"),
    ("mapear_entidades", "docs/MAPA-ENTIDADES.md"),
    ("resumir_dotnet", "docs/MAPA-DOTNET.md"),
    # ATENCAO: MAPA-AUTOCAD.md e gerado sob demanda (abre o AutoCAD) por
    # sonda_autocad.py, nao a cada renovacao; mapear_comandos.py e' o gravador
    # de prompts (historico/prompts.jsonl), nao um mapeador de documentos.
]


def run(script, args):
    exe = PRODS.get(script, sys.executable)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO / "src"), str(REPO)])
    import inspect
    mod = importlib.import_module(script)
    old_argv = sys.argv
    sys.argv = [str(TOOLS / (script + ".py"))] + list(args)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(REPO / "src"))
        if inspect.signature(mod.main).parameters:
            rc = mod.main(args)
        else:
            rc = mod.main()
        return subprocess.CompletedProcess(
            args=[" ".join([str(TOOLS / (script + ".py"))] + list(args))],
            returncode=int(rc or 0), stdout="", stderr="",
        )
    finally:
        sys.path[:] = old_path
        sys.argv = old_argv
                       

def main():
    ok = True
    for script, saida in GENS:
        p = run(script, [])
        print("[" + ("OK" if p.returncode == 0 else "FALHA") + "] " + script)
        if p.stdout.strip():
            print("   " + p.stdout.strip().splitlines()[0])
        if p.stderr.strip():
            print("   stderr: " + p.stderr.strip().splitlines()[0])
        if p.returncode != 0:
            ok = False
            print("   escreve: " + saida)
        else:
            print("   escreve: " + saida)
    return 1 if not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
