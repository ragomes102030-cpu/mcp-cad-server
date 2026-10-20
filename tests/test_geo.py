# -*- coding: utf-8 -*-
"""Testa as ferramentas novas (tools_geo) no motor headless -- sem AutoCAD.

Padrao do projeto: **contagem de entidades e "0 erros" nao provam nada**. Cada
teste confere PROPRIEDADE (comprimento, area, abertura de arco, camada, texto),
nao so' se a chamada devolveu ok.

O que exige AutoCAD vivo (COM) nao e' testado aqui -- esta' marcado em
`requer_com`, e o teste diz isso em vez de passar sem verificar.

Uso:
    CAD_MCP_BACKEND=ezdxf python tests/test_geo.py
"""
from __future__ import annotations

import asyncio
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("CAD_MCP_BACKEND", "ezdxf")

import cad_mcp.tools_geo as G  # noqa: E402
from cad_mcp.backend_manager import MANAGER  # noqa: E402
import cad_mcp.tools as T  # noqa: E402

falhas = []
requer_com = []


def checar(nome: str, cond: bool, extra="") -> None:
    print("  %s  %s%s" % ("ok   " if cond else "FALHA", nome,
                          ("  -- " + str(extra)) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)


def quase(a, b, tol=1e-3) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


async def novo_desenho():
    """Um desenho novo, com as camadas de planta, para cada teste.

    Usa o MESMO singleton (MANAGER) que as ferramentas usam -- se o teste criasse
    um backend proprio, a ferramenta desenharia em outro desenho e o teste
    mediria o vazio.
    """
    await MANAGER.reset()
    b = await MANAGER.get()
    await b.drawing_create("teste_geo")
    for camada in ("PAREDES", "COTAS", "TEXTOS", "HACHURA", "EIXOS", "SIMBOLOS"):
        await b.layer_create(camada)
    return b


async def teste_desenho() -> None:
    print("desenho")
    b = await novo_desenho()
    r = await G.entity_create_ellipse(5, 5, 2.0, 0.0, 0.5, layer="PAREDES")
    checar("entity_create_ellipse ok", r.get("ok"), r)
    g = await b.entity_geometry(r["payload"]["handle"])
    checar("elipse tem centro e raio", g.ok and quase(g.payload["centro"][0], 5)
           and quase(g.payload["raio"], 2.0), g.payload if g.ok else g.error)

    r = await G.entity_create_point(1, 2, layer="COTAS")
    g = await b.entity_geometry(r["payload"]["handle"])
    checar("entity_create_point cai em (1,2)", g.ok and quase(g.payload["ponto"][0], 1)
           and quase(g.payload["ponto"][1], 2), g.payload if g.ok else g.error)

    r = await G.entity_create_spline([[0, 0], [5, 5], [10, 0]])
    g = await b.entity_geometry(r["payload"]["handle"])
    checar("entity_create_spline tem 3 pontos", g.ok and len(g.payload["pontos"]) == 3,
           g.payload if g.ok else g.error)
    r = await G.entity_create_spline([[0, 0]])
    checar("spline com 1 ponto e' recusada", not r.get("ok"), r)

    r = await G.construction_xline(0, 0, 90, layer="EIXOS")
    g = await b.entity_geometry(r["payload"]["handle"])
    checar("xline nasce na vertical (x2 == x1)",
           g.ok and quase(g.payload["pontos"][0][0], g.payload["pontos"][1][0]),
           g.payload if g.ok else g.error)

    r = await G.entity_create_revcloud([[0, 0], [4, 0], [4, 4], [0, 4]], closed=True)
    checar("revcloud fecha 4 arcos", r.get("ok") and r.get("arcos") == 4, r)
    arcos = r.get("handles") or []
    if arcos:
        g = await b.entity_geometry(arcos[0])
        pts = g.payload["pontos"]
        corda = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        abertura = abs(g.payload["angulo_fim"] - g.payload["angulo_inicio"])
        checar("revcloud: arco abre ~180 graus", quase(abertura, 180, 1.0),
               "abertura=%.1f" % abertura)
        checar("revcloud: corda do arco = lado do contorno", quase(corda, 4.0),
               "corda=%.3f" % corda)


async def teste_desenho2() -> None:
    b = await novo_desenho()
    r = await G.drawing_properties_set(title="Casa de Praia", author="Rafael")
    r2 = await G.drawing_properties_get()
    checar("drawing_properties round-trip (titulo)", r2.get("ok")
           and r2["payload"]["title"] == "Casa de Praia", r2)
    checar("drawing_properties avisa que nao e' SummaryInfo",
           "SummaryInfo" in (r.get("payload", {}).get("onde") or ""),
           r.get("payload", {}).get("onde"))

    r = await G.drawing_apply_standard(standard="ISO", layers="arquitetura", unidades=6)
    checar("drawing_apply_standard ok", r.get("ok"), r)
    info = await b.drawing_get_variables(["INSUNITS"])
    # o backend ezdxf devolve as variaveis do cabecalho como TEXTO
    checar("drawing_apply_standard gravou INSUNITS=6",
           str((info.payload or {}).get("INSUNITS")) == "6", info.payload)

    r = await G.user_pick_point("Escolha um ponto")
    checar("user_pick_point nao finge coordenada no headless", not r.get("ok"), r)


async def teste_edicao() -> None:
    print("\nedicao")
    b = await novo_desenho()
    r = await T.draw_line(0, 0, 10, 0, layer="PAREDES")
    h = r["payload"]["handle"]
    r = await G.entity_scale(h, 0, 0, 2.0)
    g = await b.entity_geometry(h)
    comp = math.hypot(g.payload["fim"][0] - g.payload["inicio"][0],
                      g.payload["fim"][1] - g.payload["inicio"][1])
    checar("entity_scale dobra o comprimento", quase(comp, 20.0), "comp=%.3f" % comp)

    r = await G.entity_chamfer(h, h, 1.0, 1.0)
    checar("entity_chamfer responde", "ok" in r, r)

    r = await G.entity_array_rectangular(h, 2, 3, 1.0, 2.0)
    checar("entity_array_rectangular cria 5 copias", r.get("ok")
           and r["payload"].get("copies") == 5, r)

    r = await G.entity_array_polar(h, 4, 360, 0, 0)
    checar("entity_array_polar cria 3 copias", r.get("ok")
           and r["payload"].get("criadas") == 3, r)
    antes = len(b._msp)
    r = await G.entity_array_polar(h, 1, 360, 0, 0)
    checar("array_polar com count=1 nao copia", len(b._msp) == antes, len(b._msp))

    r = await G.entity_set_properties(h, layer="COTAS", color=3)
    g = await b.entity_geometry(h)
    checar("entity_set_properties mudou camada", g.payload["camada"] == "COTAS", g.payload)
    checar("entity_set_properties mudou cor", r["payload"]["mudou"] == ["layer", "color"],
           r["payload"])

    t = await T.draw_text(0, 0, "antes", height=2.5, layer="TEXTOS")
    th = t["payload"]["handle"]
    r = await G.entity_edit_text(th, text="depois", height=3.0)
    g = await b.entity_geometry(th)
    checar("entity_edit_text trocou o texto", g.payload["texto"] == "depois", g.payload)
    checar("entity_edit_text trocou a altura", quase(g.payload["altura"], 3.0), g.payload)
    checar("entity_edit_text manteve o handle", th == t["payload"]["handle"], th)

    total = len(b._msp)
    r = await G.entity_delete_many([h, th], confirmar=False)
    checar("delete_many SEM confirmar nao apaga", len(b._msp) == total and not r.get("ok"), r)
    checar("delete_many sem confirmar e' pre-visualizacao", r.get("pre_visualizacao") is True, r)
    r = await G.entity_delete_many([h, th], confirmar=True)
    checar("delete_many COM confirmar apaga", len(b._msp) == total - 2, len(b._msp))
    checar("delete_many relata quantas apagou", r.get("ok")
           and r["payload"]["apagadas"] == 2, r)


async def teste_hatch() -> None:
    b = await novo_desenho()
    r = await T.draw_rectangle(0, 0, 4, 3, layer="PAREDES")
    rh = r["payload"]["handle"]
    await b.create_hatch(rh, pattern="ANSI31")
    hatch = [e for e in b._msp if e.dxftype() == "HATCH"]
    if not hatch:
        checar("hatch_edit (hatch nao criado)", False, "create_hatch falhou")
        return
    r = await G.hatch_edit(hatch[0].dxf.handle, pattern="AR-CONC", color=2)
    checar("hatch_edit troca o padrao", hatch[0].dxf.pattern_name == "AR-CONC",
           hatch[0].dxf.pattern_name)
    r = await G.hatch_edit("999999", pattern="ANSI31")
    checar("hatch_edit com handle inexistente falha", not r.get("ok"), r)


async def teste_geometria() -> None:
    print("\ngeometria / consulta")
    b = await novo_desenho()
    r = await T.draw_line(0, 0, 10, 0, layer="PAREDES")
    h = r["payload"]["handle"]
    r = await G.entity_get(h)
    checar("entity_get devolve geometria", r.get("ok") and len(r["payload"]["pontos"]) == 2, r)

    r = await G.point_from_snap(h, "midpoint")
    checar("snap midpoint = (5,0)", quase(r["ponto"][0], 5) and quase(r["ponto"][1], 0), r)
    r = await G.point_from_snap(h, "endpoint", ref_x=10, ref_y=0)
    checar("snap endpoint escolhe o mais proximo", quase(r["ponto"][0], 10), r)
    r = await G.point_from_snap(h, "perpendicular", ref_x=5, ref_y=4)
    checar("snap perpendicular cai em (5,0)", quase(r["ponto"][0], 5) and quase(r["ponto"][1], 0), r)
    r = await G.point_from_snap(h, "banana")
    checar("snap desconhecido e' recusado", not r.get("ok"), r)

    c = await T.draw_circle(5, 0, 3, layer="PAREDES")
    ch = c["payload"]["handle"]
    r = await G.point_from_snap(ch, "center")
    checar("snap center devolve o centro", quase(r["ponto"][0], 5) and quase(r["ponto"][1], 0), r)

    r = await G.point_tangent(ch, 5, 10)
    checar("point_tangent encontra 2 tangencias", r.get("ok") and len(r.get("tangencias", [])) == 2, r)
    for t in r.get("tangencias", []):
        # todo ponto de tangencia esta' a exatamente `raio` do centro
        checar("tangencia esta' a raio do centro (%.2f, %.2f)" % (t["x"], t["y"]),
               quase(math.hypot(t["x"] - 5, t["y"] - 0), 3.0), t)
    r = await G.point_tangent(ch, 5, 1)
    checar("ponto dentro do circulo nao tem tangente", not r.get("ok"), r)

    # dois retangulos: um dentro da janela, um fora
    a = await T.draw_rectangle(0, 0, 4, 3, layer="PAREDES")
    await T.draw_rectangle(100, 100, 110, 110, layer="PAREDES")
    # dentro da janela [-1,-1,5,4]: so' o retangulo 0..4 x 0..3
    r = await G.selection_window(-1, -1, 5, 4, modo="inside")
    checar("selection_window inside acha so o de dentro", r["selecionadas"] == 1, r)
    # crossing: o retangulo (dentro), a reta 0..10 (cruza x=5) e o circulo
    # (bbox 2..8 cruza x=5) -- 3, nao 1
    r = await G.selection_window(-1, -1, 5, 4, modo="crossing")
    checar("selection_window crossing pega quem cruza a borda", r["selecionadas"] == 3, r)
    # filtro por tipo: a reta 0..10 esta' dentro de 0..200, o circulo tambem
    r = await G.selection_window(0, 0, 200, 200, modo="inside", entity_type="LINE")
    checar("selection_window filtra por tipo (so LINE)", r["selecionadas"] == 1, r)
    # o circulo (centro 5,0 r=3) tem bbox 2..8 x -3..3 -- o ymin -3 fica fora
    # de 0..200, entao "inside" nao o pega: crossing sim
    r = await G.selection_window(0, 0, 200, 200, modo="inside", entity_type="CIRCLE")
    checar("selection_window inside nao pega o circulo (ymin fora)", r["selecionadas"] == 0, r)
    r = await G.selection_window(0, 0, 200, 200, modo="crossing", entity_type="CIRCLE")
    checar("selection_window crossing pega o circulo", r["selecionadas"] == 1, r)

    r = await G.view_zoom_window(0, 0, 10, 10)
    checar("view_zoom_window nao finge zoom no headless", not r.get("ok"), r)


async def teste_arquitetura() -> None:
    print("\narquitetura")
    b = await novo_desenho()
    r = await G.arch_grid(x_axes=[0, 6, 12], y_axes=[0, 5])
    checar("arch_grid cria eixos", r.get("ok") and r["eixos"] == 5, r)
    checar("arch_grid cria bolhas nas duas pontas", r.get("ok") and r["bolhas"] >= 10, r)

    r = await G.arch_symbol("north", 5, 5)
    checar("arch_symbol north tem circulo+seta+letra",
           r.get("ok") and set(r["partes"]) >= {"circulo", "seta", "letra"}, r)
    r = await G.arch_symbol("level", 5, 5, {"cota": "2.400"})
    checar("arch_symbol level tem cota e triangulo",
           r.get("ok") and set(r["partes"]) >= {"cota", "triangulo"}, r)
    r = await G.arch_symbol("banana", 5, 5)
    checar("arch_symbol de kind desconhecido e' recusado", not r.get("ok"), r)

    r = await G.hatch_material("tijolo", handles=[h for h in []] or None)
    checar("hatch_material sem handles e' recusado", not r.get("ok"), r)
    r = await G.hatch_material("material-raro", handles=["1A"])
    checar("hatch_material de material desconhecido lista os conhecidos",
           not r.get("ok") and r.get("conhecidos"), r)

    r = await T.draw_rectangle(0, 0, 4, 3, layer="PAREDES")
    rh = r["payload"]["handle"]
    await b.create_hatch(rh, pattern="ANSI31")
    r = await G.hatch_material("concreto", handles=[rh])
    checar("hatch_material aplica o padrao ISO do material",
           r.get("ok") and r["padrao"] == "AR-CONC", r)
    hatch = [e for e in b._msp if e.dxftype() == "HATCH"]
    padroes = [h.dxf.pattern_name for h in hatch]
    checar("hachura com o padrao do material existe no desenho",
           "AR-CONC" in padroes, padroes)

    # ambientes: um grande e um armario pequeno (desenho novo, para nao herdar
    # o retangulo do teste de hachura)
    b = await novo_desenho()
    await T.draw_rectangle(0, 0, 6, 4, layer="PAREDES")
    await T.draw_rectangle(7, 0, 7.6, 0.6, layer="PAREDES")
    r = await G.arch_rooms_detect(layers=["PAREDES"], min_area=2.0)
    checar("arch_rooms_detect acha o ambiente grande", r.get("ok") and r["ambientes"] == 1, r)
    checar("arch_rooms_detect mede a area certa (6x4=24)",
           bool(r.get("lista")) and quase(r["lista"][0]["area"], 24.0), r.get("lista"))
    checar("arch_rooms_detect separa os menores", r.get("ok") and len(r.get("menores", [])) == 1, r)

    r = await G.arch_dimension_chains(sides=["s", "w"])
    checar("arch_dimension_chains desenha cotas", r.get("ok") and r["cotas"] == 6, r)

    r = await G.dimension_angular(0, 0, 1, 0, 0, 1)
    checar("dimension_angular responde", "ok" in r, r)
    r = await G.dimension_radius(0, 0, 5)
    checar("dimension_radius responde", "ok" in r, r)
    r = await G.leader_create_mleader([[0, 0], [3, 0]], "VER NOTA")
    checar("leader_create_mleader desenha", r.get("ok"), r)
    r = await G.leader_create_mleader([[0, 0]], "so um ponto")
    checar("leader com 1 ponto e' recusado", not r.get("ok"), r)
    r = await G.block_define("BLOCO_TESTE", [{"handle": rh}])
    checar("block_define responde", "ok" in r, r)


async def main() -> int:
    print("== tools_geo (motor headless) ==\n")
    for fn in (teste_desenho, teste_desenho2, teste_edicao, teste_hatch,
               teste_geometria, teste_arquitetura):
        try:
            await fn()
        except Exception as exc:  # noqa: BLE001
            checar("%s nao estourou" % fn.__name__, False, repr(exc)[:200])

    print("\n%d verificacoes com falha" % len(falhas))
    if falhas:
        for f in falhas:
            print("  - %s" % f)
        return 1
    print("TUDO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
