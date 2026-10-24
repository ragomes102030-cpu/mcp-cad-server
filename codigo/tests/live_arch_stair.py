# -*- coding: utf-8 -*-
"""Teste AO VIVO de arch_stair -- cria desenho temporario, desenha, confere, limpa.

Precisa do AutoCAD aberto e acessivel por COM. Se o COM nao responder, faz SKIP
(sai 0) em vez de falhar, para nao quebrar execucao offline.

O que prova:
  1. drawing_create (corrigido) cria e salva um desenho novo e isolado;
  2. entity_count devolve {"count": N} (contrato unico dos backends);
  3. a tool REAL arch_stair (via MANAGER/COM) desenha o tramo reto:
     2 talaias + (degraus-1) pisadas + seta (tronco + polilinea) + rotulo;
  4. o desenho e' conferido por handles/tipos e a regra de Blondel e' reportada;
  5. o desenho temporario e' fechado SEM salvar e o arquivo e' removido.

NUNCA toca em desenhos do usuario: so' no arquivo temporario unico criado aqui.

Uso:
    python3 tests/live_arch_stair.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

TEMP_DIR = Path(r"C:/temp/mcp_cad_smoke")
TEMP = TEMP_DIR / ("arch_stair_live_%d_%d.dwg" % (os.getpid(), int(time.time())))

falhas = []


def checar(nome: str, cond: bool, extra: str = "") -> None:
    print("  %s  %s%s" % ("ok  " if cond else "FALHA", nome,
                          (" -- " + str(extra)) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)


def perto(a, b, tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def _same(a, b) -> bool:
    return (os.path.normcase(os.path.abspath(str(a)))
            == os.path.normcase(os.path.abspath(str(b))))


async def _run(app):
    from collections import Counter
    from cad_mcp.com_backend import ComBackend
    from cad_mcp.backend_manager import MANAGER
    from cad_mcp.tools import arch_stair

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    if TEMP.exists():
        try:
            TEMP.unlink()
        except Exception:
            pass

    # 1) drawing_create (corrigido): cria e salva desenho novo
    b = ComBackend()
    r = await b.drawing_create(str(TEMP))
    checar("drawing_create cria e salva", r.ok and _same(r.payload.get("caminho", ""), TEMP),
           getattr(r, "error", None))
    if not r.ok:
        return

    # 2) doc ativo == TEMP
    ativo = app.ActiveDocument.FullName
    checar("documento ativo == temp", _same(ativo, TEMP), ativo)

    # 3) entity_count devolve {"count": N}
    ec = await b.entity_count()
    checar("entity_count devolve {'count': N}",
           isinstance(ec.payload, dict) and "count" in ec.payload, ec.payload)
    n0 = ec.payload.get("count", 0) if isinstance(ec.payload, dict) else 0
    ec_vazia = await b.entity_count(layer="CAMADA_VAZIA_XYZ")
    checar("entity_count(camada vazia) -> {'count': 0}",
           isinstance(ec_vazia.payload, dict) and ec_vazia.payload.get("count") == 0,
           ec_vazia.payload)

    # 4) tool REAL arch_stair via MANAGER/COM
    await MANAGER.reset()
    res = await arch_stair(x=0.0, y=0.0, largura=1.10, degraus=10, piso=0.28,
                           altura_total=1.80, angulo=0.0, seta=True, rotulo="SUBA",
                           camada="ESCADAS", lang="pt")
    checar("arch_stair ok", bool(res.get("ok")), res)
    p = res.get("payload", {}) if res.get("ok") else {}
    checar("14 entidades (11 linhas + seta(2) + rotulo)", p.get("count") == 14, p.get("count"))
    checar("14 handles", len(p.get("handles", [])) == 14, len(p.get("handles", [])))
    checar("comprimento = 10 x 0,28 = 2,80", perto(p.get("comprimento"), 2.80), p.get("comprimento"))
    checar("blondel default = 0,64 (conforme)",
           perto(p.get("blondel"), 0.64) and p.get("blondel_conforme") is True, p.get("blondel"))

    # 5) contagem final no doc
    mgr = await MANAGER.get()
    ec2 = await mgr.entity_count()
    n1 = ec2.payload.get("count", 0) if isinstance(ec2.payload, dict) else 0
    checar("delta de entidades no doc == 14", (n1 - n0) == 14, n1 - n0)

    # 6) tipos na camada ESCADAS
    ent = (await mgr.entity_list(layer="ESCADAS")).payload.get("entities", [])
    tipos = Counter(e["tipo"] for e in ent)
    checar("ESCADAS: 12 LINE", tipos.get("LINE") == 12, dict(tipos))
    checar("ESCADAS: 1 LWPOLYLINE (seta)", tipos.get("LWPOLYLINE") == 1, dict(tipos))
    checar("ESCADAS: 1 TEXT (rotulo)", tipos.get("TEXT") == 1, dict(tipos))


def main() -> int:
    print("=" * 68)
    print("TESTE AO VIVO: arch_stair (AutoCAD/COM)")
    print("=" * 68)
    try:
        import win32com.client as wc
    except Exception as e:
        print("SKIP: pywin32 indisponivel (%s)" % e)
        return 0
    try:
        app = wc.GetActiveObject("AutoCAD.Application")
        _ = app.ActiveDocument  # exige um desenho aberto
    except Exception as e:
        print("SKIP: AutoCAD/COM indisponivel (%s)" % e)
        return 0

    try:
        asyncio.run(_run(app))
    finally:
        # limpeza: fecha o temp SEM salvar e remove o arquivo (nunca toca outros docs)
        try:
            docs = app.Documents
            for i in range(docs.Count - 1, -1, -1):
                d = docs.Item(i)
                try:
                    fn = d.FullName
                except Exception:
                    fn = ""
                if fn and _same(fn, TEMP):
                    d.Close(False)
        except Exception:
            pass
        try:
            if TEMP.exists():
                TEMP.unlink()
        except Exception:
            pass

    print()
    if falhas:
        print("FALHOU: %d caso(s): %s" % (len(falhas), ", ".join(falhas)))
        return 1
    print("TUDO OK -- arch_stair desenhou e conferiu no AutoCAD ao vivo (temp limpo).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
