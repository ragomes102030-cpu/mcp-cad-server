# -*- coding: utf-8 -*-
"""Sonda do plugin PROPRIO do projeto: `CadMcpBridge` (ponte JSON-RPC local).

E' o par do `sonda_autocad.py`, mas para a superficie que existe de fato nesta
maquina. Os dois nao se confundem:

    sonda_autocad.py   -> o AutoCAD em si (comandos, variaveis de sistema)
    sonda_cadbridge.py -> o plugin .NET dentro do acad.exe (ping/exec/transaction)

O que este script mede (nada e' presumido):
    1. instalacao  -- o `.bundle` esta' no lugar? o PackageContents.xml declara o
                      que? a DLL existe? o TRUSTEDPATHS cobre o bundle?
    2. sessao      -- o AutoCAD esta' aberto? o `%TEMP%\cad_mcp_bridge.json` da
                      ponte existe (porta/token/pid)? a porta responde?
    3. ponte       -- `ping` (produto/versao) e `info` (desenho, INSUNITS) ao vivo
    4. veredito    -- o que isto prova e o que NAO prova

Limite que o proprio plugin declara (plugin/README.md): o `exec` **nao confirma**
se o comando cortou/apagou -- so' diz que foi enviado. Por isso a sonda roda
somente `ping`/`info` e um comando inofensivo (`_.ZOOM _E`), e mede latencia em
vez de afirmar resultado.

Nao mede -- e nao pode medir -- as 7 tools do MCP oficial da Autodesk: esse e' um
plugin do AutoCAD 2027 e esta maquina tem o 2025. Ver `docs/MAPA-OFICIAL-MCP.md`.

Uso:
    python tools/sonda_cadbridge.py [--json] [--sem-com]

Escreve `docs/catalogo-cadbridge.json` e `docs/MAPA-CADBRIDGE.md`.
Sem o AutoCAD aberto, reporta o plugin como nao carregado e sai com 0 (nao e'
erro: ausencia medida e' um resultado, nao uma falha).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

APPDATA = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
BUNDLE = APPDATA / "Autodesk" / "ApplicationPlugins" / "CadMcpBridge.bundle"
TEMP = Path(os.environ.get("TEMP") or "/tmp")
INFO_PONTE = TEMP / "cad_mcp_bridge.json"
LOG_PONTE = TEMP / "cad_mcp_bridge.log"

# onde o MCP oficial moraria (AutoCAD 2027) -- so' para dizer que NAO esta' aqui
OFICIAL = Path(r"C:\Program Files\Autodesk\ApplicationPlugins")


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ------------------------------------------------------------------ 1. bundle
def ler_package(bundle: Path) -> dict:
    """Le o PackageContents.xml: nome, versao, SeriesMin/Max, DLL, load."""
    xml = bundle / "PackageContents.xml"
    if not xml.exists():
        return {"existe": False, "caminho": str(xml)}
    try:
        raiz = ET.parse(xml).getroot()
    except ET.ParseError as exc:
        return {"existe": True, "ilegivel": str(exc), "caminho": str(xml)}

    comp = raiz.find(".//ComponentEntry")
    req = raiz.find(".//RuntimeRequirements")

    def _g(no, chave):
        return (no.get(chave) or "").strip() if no is not None else ""

    return {
        "existe": True,
        "caminho": str(xml),
        "nome": _g(raiz, "Name"),
        "versao_pacote": _g(raiz, "AppVersion"),
        "autor": _g(raiz, "Author"),
        "os": _g(req, "OS"),
        "series_min": _g(req, "SeriesMin"),
        "series_max": _g(req, "SeriesMax"),
        "plataforma": _g(req, "Platform"),
        "modulo": _g(comp, "ModuleName"),
        "versao_componente": _g(comp, "Version"),
        "load_no_startup": _g(comp, "LoadOnAutoCADStartup"),
        "load_no_comando": _g(comp, "LoadOnCommandInvocation"),
    }


def checar_trustedpaths() -> dict:
    """TRUSTEDPATHS decide se a DLL sem assinatura carrega sem dialogo.

    Sem isto o AutoCAD mostra "Security - Unsigned Executable File" e NAO termina
    de subir (relato de campo do proprio projeto, plugin/README.md). E' medicao de
    registro, nao de comportamento: dizer que cobre nao garante que carregou.
    """
    import winreg

    achado = None
    base = r"Software\Autodesk\AutoCAD"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as k:
            cur = winreg.QueryValueEx(k, "CurVer")[0]          # R25.0
            with winreg.OpenKey(k, cur) as k2:
                prod = winreg.QueryValueEx(k2, "CurVer")[0]      # ACAD-8101:409
                with winreg.OpenKey(k2, prod + r"\Profiles") as perfis:
                    i = 0
                    while True:
                        try:
                            nome = winreg.EnumKey(perfis, i)
                        except OSError:
                            break
                        try:
                            with winreg.OpenKey(perfis, nome + r"\Variables") as v:
                                val, _ = winreg.QueryValueEx(v, "TRUSTEDPATHS")
                                achado = {
                                    "perfil": nome,
                                    "chave": "%s\%s\Profiles\%s\Variables" % (base, cur, nome),
                                    "valor": val,
                                }
                        except OSError:
                            pass
                        i += 1
    except OSError as exc:
        return {"lido": False, "erro": str(exc)}
    if not achado:
        return {"lido": True, "presente": False}
    coberto = str(BUNDLE).lower() in achado["valor"].lower()
    return {"lido": True, "presente": True, **achado, "cobre_bundle": coberto}


# ------------------------------------------------------------------- 2. sessao
def checar_com() -> dict:
    """AutoCAD aberto? Le versao e ACADVER. Nao rouba foco."""
    try:
        import win32com.client as w

        app = w.GetActiveObject("AutoCAD.Application")
    except Exception as exc:  # noqa: BLE001
        return {"aberto": False, "erro": " ".join(str(exc).split())[:160]}

    saida = {"aberto": True, "versao": str(getattr(app, "Version", "?"))}
    try:
        doc = app.ActiveDocument
        saida["desenho"] = str(getattr(doc, "Name", "?"))
        saida["caminho"] = str(getattr(doc, "FullName", ""))
        saida["acadver"] = str(doc.GetVariable("ACADVER"))
        saida["entidades"] = int(doc.ModelSpace.Count)
    except Exception as exc:  # noqa: BLE001
        # AutoCAD aberto mas na tela inicial (sem desenho) -- COM responde assim
        saida["sem_desenho"] = " ".join(str(exc).split())[:160]
    return saida


def _porta_responde(porta: int, segundos: float = 2.0) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=segundos):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------- 3. ponte
def _metodo(info: dict, metodo: str, args: dict | None = None,
            timeout: float = 15.0) -> dict:
    """Uma linha JSON, uma linha de resposta (o protocolo do plugin)."""
    carga = {"token": info["token"], "metodo": metodo, "args": args or {}}
    try:
        with socket.create_connection(("127.0.0.1", int(info["porta"])), timeout=3.0) as s:
            s.settimeout(timeout)
            s.sendall((json.dumps(carga, ensure_ascii=False) + "\n").encode("utf-8"))
            pedacos, total = [], 0
            while True:
                p = s.recv(65536)
                if not p:
                    break
                pedacos.append(p)
                total += len(p)
                if p.endswith(b"\n") or total > 4 * 1024 * 1024:
                    break
    except OSError as exc:
        return {"ok": False, "erro": " ".join(str(exc).split())[:160]}

    bruto = b"".join(pedacos).decode("utf-8", errors="replace").strip()
    if not bruto:
        return {"ok": False, "erro": "ponte respondeu vazio"}
    try:
        return json.loads(bruto)
    except ValueError:
        return {"ok": False, "erro": "resposta nao e JSON: %r" % bruto[:160]}


def sondar_ponte(info: dict) -> dict:
    """ping + info + UM comando inofensivo, medindo latencia. Nao afirma resultado."""
    t0 = time.perf_counter()
    ping = _metodo(info, "ping")
    t_ping = round((time.perf_counter() - t0) * 1000, 1)

    t0 = time.perf_counter()
    inf = _metodo(info, "info")
    t_info = round((time.perf_counter() - t0) * 1000, 1)

    # `_.ZOOM _E` nao altera geometria: e' a unica forma de medir que o canal de
    # comando responde. Nao leio o resultado (o plugin nao confirma nada).
    t0 = time.perf_counter()
    exe = _metodo(info, "exec", {"comando": "_.ZOOM _E", "pontos": [], "confirmar": False})
    t_exec = round((time.perf_counter() - t0) * 1000, 1)

    return {
        "ping": ping,
        "ping_ms": t_ping,
        "info": inf,
        "info_ms": t_info,
        "exec": {"ok": bool(exe.get("ok")), "ms": t_exec,
                 "erro": exe.get("erro") or exe.get("error")},
        "exec_nao_confirma": ("o plugin devolve ok=True quando o comando foi ENVIADO; "
                              "nao diz se ele cortou/apagou/desenhou"),
    }


# ------------------------------------------------------------------- veredito
def veredito(dados: dict) -> list[str]:
    """O que a medicao prova -- e o que ela nao prova -- em frases curtas."""
    p, b, s, o = dados["ponte"], dados["bundle"], dados["sessao"], dados["oficial"]
    v = []

    if b["xml"].get("existe"):
        v.append("bundle instalado: %s (v%s, series %s-%s, load no startup=%s)"
                 % (b["xml"]["nome"] or "?", b["xml"]["versao_pacote"] or "?",
                    b["xml"]["series_min"] or "?", b["xml"]["series_max"] or "?",
                    b["xml"]["load_no_startup"] or "?"))
    else:
        v.append("bundle NAO instalado em %s" % BUNDLE)

    if p.get("carregado"):
        v.append("plugin CARREGADO nesta sessao: ping em %.1f ms, info em %.1f ms"
                 % (p["bruto"]["ping_ms"], p["bruto"]["info_ms"]))
        v.append("superficie exposta: ping / info / exec / transaction (JSON-RPC, "
                 "127.0.0.1, 1 linha por requisicao)")
    else:
        v.append("plugin NAO carregado nesta sessao (%s)" % p.get("motivo", "?"))

    if not o["existe"]:
        v.append("MCP oficial da Autodesk: AUSENTE (AutoCAD 2027; esta maquina tem %s)"
                 % (s["com"].get("versao") or "2025"))
    v.append("o que isto NAO prova: se um comando enviado realmente alterou o desenho "
             "(o plugin nao confirma) e a cobertura do MCP oficial")
    return v


# ------------------------------------------------------------------------ main
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Sonda o plugin CadMcpBridge (plugin proprio).")
    ap.add_argument("--json", action="store_true", help="imprime o JSON no fim")
    ap.add_argument("--sem-com", action="store_true", help="nao tenta falar com o AutoCAD")
    args = ap.parse_args(argv)

    print("1) bundle (PackageContents.xml)")
    xml = ler_package(BUNDLE)
    dll = BUNDLE / "Contents" / "Windows" / "CadMcpBridge.dll"
    dll_bytes = dll.stat().st_size if dll.exists() else 0
    print("   bundle: %s" % ("ok" if xml.get("existe") else "AUSENTE"))
    if xml.get("nome"):
        print("   nome=%s versao=%s series=%s..%s load_startup=%s"
              % (xml["nome"], xml["versao_pacote"], xml["series_min"],
                 xml["series_max"], xml["load_no_startup"]))
        print("   modulo: %s" % xml["modulo"])
    print("   dll: %s (%d bytes)" % (dll if dll_bytes else "AUSENTE", dll_bytes))

    print("\n2) TRUSTEDPATHS (registro)")
    tp = checar_trustedpaths()
    if tp.get("lido") and tp.get("presente"):
        print("   perfil %s: %s" % (tp["perfil"], "COBRE o bundle" if tp["cobre_bundle"]
                                    else "NAO cobre o bundle"))
        if not tp["cobre_bundle"]:
            print("   -> sem isto o AutoCAD mostra 'Security - Unsigned Executable File'")
    elif tp.get("lido"):
        print("   TRUSTEDPATHS ausente -> DLL sem assinatura nao carrega")
    else:
        print("   nao deu para ler o registro (%s)" % tp.get("erro"))

    print("\n3) sessao AutoCAD")
    com = {"aberto": False}
    if not args.sem_com:
        com = checar_com()
    if com.get("aberto"):
        print("   aberto: versao %s" % com.get("versao"))
        if com.get("sem_desenho"):
            print("   (sem desenho aberto: %s)" % com["sem_desenho"][:80])
        else:
            print("   desenho: %s | %s | %d entidades"
                  % (com.get("desenho"), com.get("acadver"), com.get("entidades") or 0))
    else:
        print("   fechado (%s)" % (com.get("erro") or "sem COM"))

    print("\n4) ponte")
    ponte = {"carregado": False}
    if INFO_PONTE.exists():
        try:
            info = json.loads(INFO_PONTE.read_text(encoding="utf-8"))
        except ValueError as exc:
            print("   %s ilegivel: %s" % (INFO_PONTE, exc))
            info = None
        if info:
            porta, pid = info.get("porta"), info.get("pid")
            print("   %s: porta=%s pid=%s token=%s"
                  % (INFO_PONTE.name, porta, pid,
                     "presente" if info.get("token") else "AUSENTE"))
            if _porta_responde(int(porta)):
                bruto = sondar_ponte(info)
                print("   ping: %s (%.1f ms)" % (bruto["ping"].get("produto") or bruto["ping"],
                                                  bruto["ping_ms"]))
                inf = bruto["info"]
                if inf.get("ok"):
                    print("   info: %s" % json.dumps(
                        {k: v for k, v in inf.items() if k != "token"}, ensure_ascii=False)[:200])
                else:
                    print("   info: %s" % (inf.get("erro") or inf))
                print("   exec _.ZOOM _E: ok=%s (%.1f ms) -- nao confirma resultado"
                      % (bruto["exec"]["ok"], bruto["exec"]["ms"]))
                ponte = {"carregado": True, "bruto": bruto,
                         "info": {k: v for k, v in info.items() if k != "token"}}
            else:
                print("   porta %s nao responde: a ponte escreve o arquivo ao carregar;"
                      " se o AutoCAD fechou, o arquivo e' de uma sessao antiga" % porta)
                ponte = {"carregado": False,
                         "motivo": "arquivo da ponte existe mas a porta nao responde",
                         "info": {k: v for k, v in info.items() if k != "token"}}
    else:
        print("   %s AUSENTE: o plugin so escreve este arquivo depois de carregar"
              " dentro do acad.exe" % INFO_PONTE.name)
        ponte = {"carregado": False, "motivo": "arquivo da ponte ausente"}

    print("\n5) MCP oficial (referencia, nao alvo)")
    oficial = {"existe": OFICIAL.exists(), "caminho": str(OFICIAL)}
    print("   %s: %s" % (OFICIAL, "existe" if OFICIAL.exists() else "AUSENTE (AutoCAD 2027)"))

    dados = {
        "gerado_em": agora(),
        "maquina": {"usuario": os.environ.get("USERNAME") or os.environ.get("USER"),
                    "appdata": str(APPDATA)},
        "bundle": {"caminho": str(BUNDLE), "xml": xml, "dll": str(dll),
                   "dll_bytes": dll_bytes, "installed": xml.get("existe", False)},
        "trustedpaths": tp,
        "sessao": {"com": com, "arquivo_ponte": str(INFO_PONTE),
                   "log_ponte": str(LOG_PONTE),
                   "log_ponte_existe": LOG_PONTE.exists()},
        "ponte": ponte,
        "oficial": oficial,
        "veredito": [],
    }
    dados["veredito"] = veredito(dados)

    (DOCS / "catalogo-cadbridge.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    linhas = [
        "# Mapa do CadMcpBridge — o plugin proprio, medido ao vivo",
        "",
        "Gerado em **%s** por `tools/sonda_cadbridge.py`." % dados["gerado_em"],
        "É o par do `sonda_autocad.py`: aquele mede o AutoCAD, este mede a **superfície**",
        "que o projeto expõe dentro dele.",
        "",
        "## 1. Instalação",
        "",
        "| item | valor |",
        "|---|---|",
        "| bundle | `%s` |" % dados["bundle"]["caminho"],
        "| PackageContents.xml | %s |" % ("ok" if xml.get("existe") else "**AUSENTE**"),
        "| nome / versão | %s / %s |" % (xml.get("nome") or "?", xml.get("versao_pacote") or "?"),
        "| série | `%s` .. `%s` |" % (xml.get("series_min") or "?", xml.get("series_max") or "?"),
        "| load no startup | `%s` |" % (xml.get("load_no_startup") or "?"),
        "| DLL | `%s` (%d bytes) |" % (dados["bundle"]["dll"], dll_bytes),
        "| TRUSTEDPATHS cobre o bundle | %s |" % (
            "sim" if tp.get("cobre_bundle")
            else ("**não**" if tp.get("presente") else "ausente")),
        "",
        "> Sem `TRUSTEDPATHS` o `SECURELOAD` bloqueia DLL não assinada e o AutoCAD",
        "> **não termina de subir** (relato de campo do projeto, `plugin/README.md`).",
        "",
        "## 2. Sessão",
        "",
        "- AutoCAD aberto: **%s**" % ("sim" if com.get("aberto") else "não")
        + ((" (versão %s)" % com.get("versao")) if com.get("aberto") else ""),
        "- desenho ativo: `%s`" % (com.get("desenho") or "—"),
        "- arquivo da ponte: `%s` — %s" % (INFO_PONTE, "presente" if INFO_PONTE.exists()
                                          else "**ausente**"),
        "- plugin carregado nesta sessão: **%s**" % ("sim" if ponte.get("carregado") else "não"),
        "",
        "## 3. Superfície medida",
        "",
    ]
    if ponte.get("carregado"):
        b = ponte["bruto"]
        linhas += [
            "| método | resposta | latência |",
            "|---|---|---|",
            "| `ping` | `%s` | %.1f ms |" % (json.dumps(b["ping"], ensure_ascii=False)[:120],
                                            b["ping_ms"]),
            "| `info` | `%s` | %.1f ms |" % (json.dumps(b["info"], ensure_ascii=False)[:160],
                                            b["info_ms"]),
            "| `exec _.ZOOM _E` | `ok=%s` | %.1f ms |" % (b["exec"]["ok"], b["exec"]["ms"]),
            "",
            "Protocolo: **uma linha JSON por requisição** em `127.0.0.1`, resposta em uma",
            "linha. Porta e token em `%TEMP%\cad_mcp_bridge.json`, escritos pelo plugin a",
            "cada carga. Métodos: `ping`, `info`, `exec`, `transaction`.",
            "",
            "> **`exec` não confirma resultado.** `ok: true` diz que o comando foi",
            "> *enviado*; não diz se cortou, apagou ou desenhou. Para decidir, meça a",
            "> geometria depois (contagem de entidades, `GetBoundingBox`).",
        ]
    else:
        linhas += [
            "Nada medido: o plugin não estava carregado nesta sessão.",
            "",
            "O `%TEMP%\cad_mcp_bridge.json` só existe depois que o Autoloader carrega o",
            "`.bundle` no início de uma sessão do AutoCAD — e o arquivo de uma sessão",
            "antiga não responde na porta. **Ausência medida, não presumida.**",
        ]

    linhas += [
        "",
        "## 4. O que isto não cobre",
        "",
        "- **As 7 tools do MCP oficial da Autodesk** não podem ser medidas aqui:",
        "  `%s` %s e a máquina tem %s (o MCP oficial é do 2027). Ver" % (
            OFICIAL, "não existe" if not oficial["existe"] else "existe",
            com.get("versao") or "AutoCAD 2025"),
        "  `MAPA-OFICIAL-MCP.md`.",
        "- **Se um comando enviado alterou o desenho** — o plugin não confirma.",
        "- **Cobertura do `.bundle` em outras versões** — o `PackageContents.xml` declara",
        "  `SeriesMin/SeriesMax`; isto não é medição de comportamento.",
        "",
        "## Lacunas deste mapa",
        "",
        "1. **`transaction` não foi exercitado ao vivo** — só o protocolo do cliente tem",
        "   teste (`tests/test_bridge.py`, com um servidor falso).",
        "2. **A carga real do `.bundle` não está provada por este script** — ele lê o",
        "   `PackageContents.xml` e o registro, não o processo do AutoCAD.",
        "3. **`MPCBRIDGE` (comando no AutoCAD) não é consultado** — é confirmação visual.",
        "",
    ]
    (DOCS / "MAPA-CADBRIDGE.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print("\n--- veredito ---")
    for v in dados["veredito"]:
        print("  * " + v)
    print("\nok: docs/MAPA-CADBRIDGE.md e docs/catalogo-cadbridge.json")
    if args.json:
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
