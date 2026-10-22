# -*- coding: utf-8 -*-
"""Audita a cobertura REAL: para cada ferramenta publica, quais metodos de
backend ela alcanca (transitivamente) e se o backend COM (AutoCAD de verdade)
os implementa."""
import ast, json, os, sys
from pathlib import Path

RAIZ = Path(os.environ.get("CAD_RAIZ", Path(__file__).resolve().parent.parent))
SRC = RAIZ / "src"
sys.path.insert(0, str(SRC))
import cad_mcp.tools as T  # noqa

def nomes_metodos(caminho):
    tree = ast.parse(Path(caminho).read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

BASE_NS = nomes_metodos(SRC / "autocad_mcp/backends/base.py")
COM_IMPL = nomes_metodos(SRC / "cad_mcp/com_backend.py")
EZ_IMPL = nomes_metodos(SRC / "autocad_mcp/backends/ezdxf_backend.py")
IPC_IMPL = nomes_metodos(SRC / "autocad_mcp/backends/file_ipc.py")
UNIVERSO = BASE_NS | COM_IMPL | EZ_IMPL | IPC_IMPL

# grafo de chamada: funcao -> {funcoes que ela chama} (mesmo arquivo)
MODULOS = ["tools.py", "tools_ext.py", "tools_plot.py", "tools_geo.py",
           "arch.py", "planta.py", "layers.py", "quantitativo.py", "sexp.py"]
GRAFOS = {}
for mod in MODULOS:
    caminho = SRC / "cad_mcp" / mod
    if not caminho.exists():
        continue
    tree = ast.parse(caminho.read_text(encoding="utf-8"))
    grafo = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        chamadas = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name):
                    chamadas.add(f.id)
                elif isinstance(f, ast.Attribute):
                    chamadas.add(f.attr)
        grafo[node.name] = chamadas
    GRAFOS[mod] = grafo

def alcancaveis(inicio, profundidade=6):
    """Funcoes de modulo alcancaveis a partir de `inicio`."""
    vistos, fila, prof = set(), [(inicio, 0)], {inicio: 0}
    while fila:
        nome, p = fila.pop(0)
        if p > profundidade:
            continue
        for mod, grafo in GRAFOS.items():
            if nome not in grafo:
                continue
            for alvo in grafo[nome]:
                if alvo in UNIVERSO and alvo not in vistos:
                    vistos.add(alvo)
                if alvo in grafo and alvo not in prof:
                    prof[alvo] = p + 1
                    fila.append((alvo, p + 1))
    return vistos

# arquivo onde cada ferramenta esta definida
ARQ_DA_FUNCAO = {}
for mod in MODULOS:
    caminho = SRC / "cad_mcp" / mod
    if not caminho.exists():
        continue
    for node in ast.parse(caminho.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ARQ_DA_FUNCAO[node.name] = mod

linhas, resumo = [], {"com_ok": [], "so_ezdxf": [], "so_file_ipc": [],
                      "so_headless": [], "sem_backend": []}
for fn in T.TOOLS:
    pub = T.nome_publico(fn)
    metodos = alcancaveis(fn.__name__)
    com_ok = sorted(m for m in metodos if m in COM_IMPL)
    so_ez = sorted(m for m in metodos if m not in COM_IMPL and m in EZ_IMPL)
    so_ipc = sorted(m for m in metodos if m not in COM_IMPL and m in IPC_IMPL)
    linhas.append({"publico": pub, "func": fn.__name__, "arq": ARQ_DA_FUNCAO.get(fn.__name__),
                   "metodos": sorted(metodos), "com": com_ok,
                   "so_ezdxf": so_ez, "so_file_ipc": so_ipc})
    if not metodos:
        resumo["sem_backend"].append(pub)
    elif not com_ok and so_ez:
        resumo["so_ezdxf"].append(pub)
    elif not com_ok and so_ipc:
        resumo["so_file_ipc"].append(pub)
    elif com_ok:
        resumo["com_ok"].append(pub)
    else:
        resumo["so_headless"].append(pub)

out = {"total": len(T.TOOLS), "base": len(BASE_NS), "com": len(COM_IMPL),
       "ezdxf": len(EZ_IMPL), "file_ipc": len(IPC_IMPL),
       "resumo": {k: sorted(v) for k, v in resumo.items()}, "detalhe": linhas}
p = Path(os.environ.get("TMPDIR", ".")) / "auditoria_backend.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("TOTAL FERRAMENTAS:", len(T.TOOLS))
print("metodos: base=%d com=%d ezdxf=%d file_ipc=%d" % (len(BASE_NS), len(COM_IMPL), len(EZ_IMPL), len(IPC_IMPL)))
for k in ("com_ok", "so_ezdxf", "so_file_ipc", "so_headless", "sem_backend"):
    print("\n[%s] %d" % (k, len(resumo[k])))
    for x in sorted(resumo[k]):
        print("   -", x)
print("\njson:", p)
