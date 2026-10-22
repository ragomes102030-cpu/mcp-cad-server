"""Verifica a instalacao do mcp-cad-server sem desenhar nada.

Uso:
    python verificar_instalacao.py            # checagem completa (nao abre AutoCAD)
    python verificar_instalacao.py --esperado 76

Sai com codigo 0 se tudo passou, 1 se algo falhou.
Feito para ser rodado por um agente: cada linha comeca com [OK] ou [FALHA].
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import time

FALHAS = []


def ok(msg):
    print("[OK]    " + msg)


def falha(msg):
    print("[FALHA] " + msg)
    FALHAS.append(msg)


def checar_python():
    v = sys.version_info
    if v >= (3, 10):
        ok("Python %d.%d.%d (%s)" % (v.major, v.minor, v.micro, platform.architecture()[0]))
    else:
        falha("Python %d.%d.%d: precisa de 3.10 ou mais novo" % (v.major, v.minor, v.micro))
    if platform.architecture()[0] != "64bit":
        falha("Python nao e 64 bits; o AutoCAD exige 64")


def checar_imports():
    for mod in ("cad_mcp", "autocad_mcp", "ezdxf", "fastmcp"):
        try:
            __import__(mod)
            ok("import %s" % mod)
        except Exception as e:
            falha("import %s: %s" % (mod, e))
    try:
        import win32com.client  # noqa: F401
        ok("pywin32 presente (motor COM disponivel)")
    except Exception:
        print("[AVISO] pywin32 ausente: so o motor headless (ezdxf) vai funcionar")


def checar_autocad():
    try:
        import win32com.client
        app = win32com.client.GetActiveObject("AutoCAD.Application")
        ok("AutoCAD aberto: %s" % app.Version)
    except Exception:
        print("[AVISO] AutoCAD nao esta aberto (normal se for so headless)")


def listar_tools(timeout=45):
    cmd = [sys.executable, "-m", "cad_mcp.server"]
    env = dict(os.environ)
    env["MCP_CAD_BACKEND"] = "ezdxf"   # nao toca no AutoCAD aberto
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)
    linhas = []
    threading.Thread(target=lambda: [linhas.append(l) for l in p.stdout], daemon=True).start()

    def send(o):
        p.stdin.write((json.dumps(o) + "\n").encode("utf-8"))
        p.stdin.flush()

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                         "clientInfo": {"name": "verificar_instalacao", "version": "1"}}})
        time.sleep(3)
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        time.sleep(0.5)
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        t0 = time.time()
        while time.time() - t0 < timeout:
            for l in list(linhas):
                if isinstance(l, bytes):
                    l = l.decode("utf-8", "replace")
                l = l.strip()
                if not l.startswith("{"):
                    continue
                try:
                    d = json.loads(l)
                except Exception:
                    continue
                if d.get("id") == 2:
                    return [t["name"] for t in d["result"]["tools"]]
            time.sleep(0.3)
        return None
    finally:
        try:
            p.stdin.close()
        except Exception:
            pass
        time.sleep(0.3)
        p.terminate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esperado", type=int, default=76)
    a = ap.parse_args()

    print("== Python")
    checar_python()
    print("== Pacotes")
    checar_imports()
    print("== AutoCAD")
    checar_autocad()
    print("== Servidor MCP (stdio)")
    nomes = listar_tools()
    if nomes is None:
        falha("o servidor nao respondeu tools/list; rode de novo mostrando o erro: "
              "python -m cad_mcp.server")
    else:
        ok("respondeu tools/list com %d ferramentas" % len(nomes))
        if len(nomes) == a.esperado:
            ok("contagem esperada (%d)" % a.esperado)
        else:
            falha("esperava %d ferramentas, veio %d" % (a.esperado, len(nomes)))
        for nova in ("entity_erase", "entity_erase_filter", "entity_move", "drawing_setup",
                     "entity_copy", "entity_copy_filter", "entity_rotate", "entity_mirror",
                     "entity_offset", "layer_linetype_load", "entity_mirror_filter",
                     "entity_rotate_filter"):
            if nova in nomes:
                ok("ferramenta presente: %s" % nova)
            else:
                falha("ferramenta ausente: %s" % nova)

    print()
    if FALHAS:
        print("RESULTADO: FALHOU (%d)" % len(FALHAS))
        return 1
    print("RESULTADO: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
