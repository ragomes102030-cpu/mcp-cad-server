# -*- coding: utf-8 -*-
"""Prova que o validador ve o que deveria ver -- e nao inventa problema.

1) O modelo REAL entregue (3 quartos, 119,56 m2) tem de passar limpo.
2) Cada erro conhecido tem de ser pego pela chave certa:
   - porta sem vao (arco cortando parede fechada)
   - rotulo maior que o ambiente (o caso do selo de 130 caracteres)
   - ambiente invertido / sobreposto
   - soma de areas longe do pedido
   - selo passando do terreno
3) Rodar duas vezes seguidas da o mesmo resultado (sem estado escondido).

Sem AutoCAD, sem COM: e matematica pura. Roda em ~1 ms.
"""
from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

from cad_mcp.validar_modelo import validar, relatar  # noqa: E402

ASSET = Path(r"C:\Users\Correta Engenharia\AppData\Roaming\AionUi\aionui\skills"
             r"\users\system_default_user\cad-planta-autocad\assets"
             r"\modelo-3-quartos.json")


def modelo_base() -> dict:
    if ASSET.exists():
        return json.loads(ASSET.read_text(encoding="utf-8"))
    import planta_3q                      # fallback: o modelo do teste original
    return copy.deepcopy(planta_3q.MODELO)


def chaves(r: dict) -> set[str]:
    return {p["chave"] for p in r["problemas"]}


falhas = []


def checar(nome: str, cond: bool, extra: str = "") -> None:
    print("  %s  %s%s" % ("ok  " if cond else "FALHA", nome, (" -- " + extra) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)


def caso(nome: str, mutacao, chave_esperada: str) -> None:
    m = modelo_base()
    mutacao(m)
    r = validar(m)
    achei = chave_esperada in chaves(r)
    checar("%s -> %s" % (nome, chave_esperada), achei,
           relatar(r) if not achei else "")


def main() -> int:
    m = modelo_base()
    print("1) modelo real entregue (area util esperada 119,56 m2)")
    t0 = time.perf_counter()
    r = validar(m)
    dt = (time.perf_counter() - t0) * 1000.0
    print(relatar(r))
    print("   %.2f ms" % dt)
    checar("passa limpo", r["ok"], "erros: %s" % [p["chave"] for p in r["erros"]])
    checar("area util 119,56", abs(r["area_util"] - 119.56) < 0.05, "deu %.2f" % r["area_util"])
    checar("10 portas contadas", r["resumo"]["portas"] == 10)
    checar("rapido (< 20 ms)", dt < 20.0, "%.2f ms" % dt)

    print("\n2) erros conhecidos")
    caso("porta sobre parede fechada",
         lambda x: x["portas"].append((2.0, 6.275, 90.0, 0.80)), "porta-sem-vao")
    caso("porta no meio do nada",
         lambda x: x["portas"].append((5.0, 3.0, 0.0, 0.80)), "porta-sem-parede")
    caso("rotulo gigante no quarto",
         lambda x: x["ambientes"][0].update({"nome": "QUARTO 1 DE CASAL COM CLOSET E BANHEIRO"}),
         "texto-transborda")
    caso("ambiente invertido",
         lambda x: x["ambientes"][0].update({"x1": 3.0, "x2": 0.5}), "ambiente-invertido")
    caso("dois ambientes no mesmo lugar",
         lambda x: x["ambientes"][1].update({"x1": 0.5, "x2": 3.0}), "ambientes-sobrepostos")
    caso("area pedida diferente", lambda x: x.update({"area_pedida": 95.0}), "area-total-diverge")
    caso("parede fora do terreno",
         lambda x: x["paredes"].append((20.0, 0.0, 21.0, 0.0)), "parede-fora-terreno")
    caso("parede duplicada",
         lambda x: x["paredes"].append(tuple(x["paredes"][0])), "parede-duplicada")
    caso("selo maior que o terreno",
         lambda x: x["selo"].append((0.0, -7.0, "X" * 120, 0.22)), "selo-transborda")
    caso("linhas do selo colidindo",
         lambda x: x["selo"][1].__setitem__(1, x["selo"][0][1] - 0.24), "selo-linhas-colidem")

    print("\n3) selo antigo (o que estourou o A3 na pratica: 130 chars a 0,22 m)")
    m2 = modelo_base()
    m2["selo"] = [(0.0, -3.30,
                   "PLANTA BAIXA - RESIDENCIA UNIFAMILIAR - 3 QUARTOS SENDO 1 SUITE - AREA UTIL 119,56 m2 - " * 2,
                   0.22)]
    r2 = validar(m2)
    print("   " + (relatar(r2).splitlines()[0]))
    checar("selo de 130 chars reprovado", "selo-transborda" in chaves(r2))

    print("\n4) determinismo")
    a = validar(modelo_base())
    b = validar(modelo_base())
    checar("duas rodadas iguais", a == b)

    print("\n5) o portao segura o desenho (sem COM, backend falso)")

    class _R:
        def __init__(self, payload=None, ok=True, error=None):
            self.payload, self.ok, self.error = payload, ok, error

    class FakeBackend:
        """Conta chamadas em vez de falar com o AutoCAD."""

        def __init__(self):
            self.chamadas = 0
            self.entes = 0

        async def entmakex(self, corpo):
            self.chamadas += 1
            self.entes += 1
            return _R("H%d" % self.chamadas)

        async def create_dimension_linear(self, *a):
            self.chamadas += 1
            self.entes += 1
            return _R("D%d" % self.chamadas)

        def __getattr__(self, nome):
            # qualquer outro metodo do backend (layer_create, setvar...) vira no-op
            async def _qualquer(*a, **k):
                self.chamadas += 1
                return _R("X%d" % self.chamadas)
            return _qualquer

    import asyncio
    from cad_mcp.planta import desenhar_modelo

    fb = FakeBackend()
    rv = asyncio.run(desenhar_modelo(fb, modelo_base()))
    checar("modelo bom desenha", rv.get("valido") is True and fb.entes > 50,
           "valido=%s entidades=%d" % (rv.get("valido"), fb.entes))
    checar("contagem de entidades bate", rv["entidades_criadas"] == fb.entes,
           "%s x %d" % (rv["entidades_criadas"], fb.entes))

    ruim = modelo_base()
    ruim["portas"].append((2.0, 6.275, 90.0, 0.80))     # pivo dentro da parede
    fb2 = FakeBackend()
    rv2 = asyncio.run(desenhar_modelo(fb2, ruim))
    checar("modelo ruim NAO desenha", rv2.get("valido") is False and fb2.chamadas == 0,
           "valido=%s chamadas=%d" % (rv2.get("valido"), fb2.chamadas))
    checar("devolve o motivo",
           any(p["chave"] == "porta-sem-vao" for p in rv2.get("erros_validacao", [])))

    print()
    if falhas:
        print("FALHOU: %d caso(s): %s" % (len(falhas), ", ".join(falhas)))
        return 1
    print("TUDO OK -- o validador barra o que ja nos custou uma rodada inteira.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
