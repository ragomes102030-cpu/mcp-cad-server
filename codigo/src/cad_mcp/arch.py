# -*- coding: utf-8 -*-
"""Paredes com aberturas hospedadas -- porta e janela que nao podem "descolar".

De onde veio: lido do `autocad-mcp-pro` 1.6.0 (`engineering/arch/model.py` e
`walls.py`, MIT). A ideia deles e melhor que a nossa:

    a abertura NAO e um furo desenhado por cima da parede; ela e um dado
    HOSPEDADO na parede (parede + offset + largura). O vao nao existe no modelo:
    ele e o que sobra quando a parede e cortada pelas aberturas.

Com isso, "arco de porta sobre parede fechada" deixa de ser um erro possivel --
nao ha parede inteira para desenhar. E mover a porta e mudar `offset`, nao
recalcular quatro trechos na mao.

Este modulo e puro (sem COM, sem AutoCAD) e devolve quatro coisas:
    trechos()      -- os pedacos de eixo que sobram entre as aberturas
    primitivas()   -- folha + arco da porta, ou as 4 linhas da janela
    validar()      -- recusa abertura fora da parede, sobreposta, id repetido
    expandir()     -- ponte para o modelo do `planta.py` (paredes + portas)

Diferenca para o original: eles constroem a rede de paredes com juncao L/T/X e
miter; aqui ainda nao ha juncao -- cada parede e um eixo independente. O que
faltar fica registrado em `historico/`.

Unidades: metros, angulos em GRAUS na saida (o `planta.py` converte para radiano).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = [
    "Pt", "Parede", "Abertura", "segmentos_eixo", "comprimento",
    "ponto_no_eixo", "validar", "trechos", "primitivas", "expandir",
]

Pt = tuple[float, float]
EPS = 1e-9
TIPOS = ("porta", "janela", "vao")


@dataclass(frozen=True)
class Parede:
    """Eixo poligonal com espessura. `fechada=True` levanta o ultimo trecho."""
    id: str
    eixo: tuple[Pt, ...]
    espessura: float = 0.15
    fechada: bool = False
    altura: float = 2.70

    def __post_init__(self):
        if len(self.eixo) < 2:
            raise ValueError("parede %r: eixo precisa de 2 pontos" % self.id)
        if self.espessura <= 0:
            raise ValueError("parede %r: espessura deve ser > 0" % self.id)


@dataclass(frozen=True)
class Abertura:
    """Vao hospedado numa parede.

    offset  -- do INICIO do eixo ate o batente inicial
    largura -- do batente inicial ao final (offset + largura = batente final)
    dobradica -- "inicio" | "fim": de que lado fica o pivo da porta
    gira  -- "esquerda" | "direita": para que lado a folha abre (90 graus)
    """
    id: str
    parede: str
    tipo: str
    offset: float
    largura: float
    altura: float = 2.10
    peitoril: float = 0.0
    dobradica: str = "inicio"
    gira: str = "esquerda"

    def __post_init__(self):
        if self.tipo not in TIPOS:
            raise ValueError("abertura %r: tipo deve ser um de %s" % (self.id, TIPOS))
        if self.largura <= 0:
            raise ValueError("abertura %r: largura deve ser > 0" % self.id)
        if self.offset < -EPS:
            raise ValueError("abertura %r: offset negativo" % self.id)
        if self.dobradica not in ("inicio", "fim"):
            raise ValueError("abertura %r: dobradica deve ser inicio|fim" % self.id)
        if self.gira not in ("esquerda", "direita"):
            raise ValueError("abertura %r: gira deve ser esquerda|direita" % self.id)

    @property
    def fim(self) -> float:
        return self.offset + self.largura


# ------------------------------------------------------------------ geometria
def segmentos_eixo(p: Parede) -> list[tuple[Pt, Pt]]:
    """Trechos do eixo, na ordem; o de fechamento por ultimo quando `fechada`."""
    pts = list(p.eixo)
    segs = list(zip(pts, pts[1:]))
    if p.fechada:
        segs.append((pts[-1], pts[0]))
    return segs


def comprimento(p: Parede) -> float:
    return sum(math.dist(a, b) for a, b in segmentos_eixo(p))


def _unit(a: Pt, b: Pt) -> Pt:
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy)
    if d < EPS:
        raise ValueError("trecho de comprimento zero")
    return (dx / d, dy / d)


def ponto_no_eixo(p: Parede, offset: float) -> tuple[Pt, Pt, int]:
    """(ponto, direcao unitaria do trecho, indice do trecho) a `offset` do inicio.

    Distancia que cai exatamente num vertice pertence ao trecho que COMECA ali
    (mesma regra do `segment_of` deles); o fim do eixo pertence ao ultimo trecho.
    """
    total = comprimento(p)
    if offset < -1e-6 or offset > total + 1e-6:
        raise ValueError("offset %.3f fora da parede %r (comprimento %.3f)"
                         % (offset, p.id, total))
    corrido = 0.0
    segs = segmentos_eixo(p)
    for i, (a, b) in enumerate(segs):
        d = math.dist(a, b)
        ultimo = i == len(segs) - 1
        if offset < corrido + d - 1e-9 or ultimo:
            t = min(max(offset - corrido, 0.0), d)
            u = _unit(a, b)
            return ((a[0] + u[0] * t, a[1] + u[1] * t), u, i)
        corrido += d
    raise AssertionError("inalcancavel")


# ------------------------------------------------------------------ validacao
def validar(paredes: list[Parede], aberturas: list[Abertura]) -> None:
    """Recusa o que a parede nao pode hospedar. Mensagem diz qual e por que."""
    por_id = {}
    for p in paredes:
        if p.id in por_id:
            raise ValueError("parede %r repetida" % p.id)
        por_id[p.id] = p

    vistos: set[str] = set()
    ordem = {p.id: i for i, p in enumerate(paredes)}
    for ab in aberturas:
        if ab.id in vistos:
            raise ValueError("abertura %r repetida" % ab.id)
        vistos.add(ab.id)
        if ab.parede not in por_id:
            raise ValueError("abertura %r cita parede inexistente %r" % (ab.id, ab.parede))

    for p in paredes:
        total = comprimento(p)
        minhas = sorted([a for a in aberturas if a.parede == p.id], key=lambda a: a.offset)
        corrido = 0.0
        for ab in minhas:
            if ab.fim > total + 1e-6:
                raise ValueError("abertura %r termina em %.3f, parede %r tem %.3f"
                                 % (ab.id, ab.fim, p.id, total))
            if ab.offset < corrido - 1e-6:
                raise ValueError("aberturas de %r se sobrepoem (%.3f < %.3f)"
                                 % (p.id, ab.offset, corrido))
            corrido = ab.fim
            # a abertura tem de caber inteira num unico trecho do eixo
            _, _, i0 = ponto_no_eixo(p, ab.offset)
            _, _, i1 = ponto_no_eixo(p, ab.fim - 1e-9)
            if i0 != i1:
                raise ValueError("abertura %r atravessa o vertice do eixo da parede %r"
                                 % (ab.id, p.id))
    _ = ordem  # mantido para futura resolucao de juncao


# -------------------------------------------------------------------- trechos
def trechos(p: Parede, aberturas: list[Abertura]) -> list[tuple[Pt, Pt]]:
    """Os pedacos de eixo que sobram depois de cortar as aberturas.

    Nao desenhamos parede sob a abertura: o vao e o que sobra. Para uma parede
    de 6 m com uma porta de 0,80 em 2,00, saem (0..2) e (2,80..6).
    """
    minhas = sorted([a for a in aberturas if a.parede == p.id], key=lambda a: a.offset)
    saida: list[tuple[Pt, Pt]] = []
    for ini, fim in segmentos_eixo(p):
        d = math.dist(ini, fim)
        u = _unit(ini, fim)
        # recorte em coordenada local do trecho (0..d)
        base = _offset_do_trecho(p, ini)
        cortes = [(a.offset - base, a.fim - base) for a in minhas]
        cortes = [(max(0.0, a), min(d, b)) for a, b in cortes if b > 0 and a < d]
        cortes.sort()
        pos = 0.0
        for a, b in cortes:
            if a > pos + 1e-9:
                saida.append((_pt(ini, u, pos), _pt(ini, u, a)))
            pos = max(pos, b)
        if pos < d - 1e-9:
            saida.append((_pt(ini, u, pos), _pt(ini, u, d)))
    return saida


def _pt(a: Pt, u: Pt, t: float) -> Pt:
    return (a[0] + u[0] * t, a[1] + u[1] * t)


def _offset_do_trecho(p: Parede, ini: Pt) -> float:
    """Distancia do inicio do eixo ate `ini` (que e um vertice do eixo)."""
    corrido = 0.0
    for a, b in segmentos_eixo(p):
        if math.dist(a, ini) < 1e-7:
            return corrido
        corrido += math.dist(a, b)
    raise ValueError("vertice nao pertence ao eixo da parede %r" % p.id)


# ---------------------------------------------------------------- primitivas
def primitivas(p: Parede, ab: Abertura) -> dict:
    """O que desenhar da abertura, em coordenadas do mundo.

    porta -> {"porta": (x, y, angulo, largura), "arco": (cx, cy, r, a1, a2)}
        (x, y) e o pivo; `angulo` e a direcao da FOLHA aberta (90 graus da parede).
    janela -> {"linhas": [((x1,y1),(x2,y2)), ...]} -- 4 linhas (2 de vidro + 2 batentes).
    """
    total = comprimento(p)
    if ab.fim > total + 1e-6:
        raise ValueError("abertura %r passa do fim da parede %r" % (ab.id, p.id))

    ini, u0, _ = ponto_no_eixo(p, ab.offset)     # batente inicial
    fim = _pt(ini, u0, ab.largura)               # batente final
    base = {"id": ab.id, "tipo": ab.tipo, "parede": p.id,
            "pivo": (ini[0], ini[1]), "largura": ab.largura,
            "altura": ab.altura, "peitoril": ab.peitoril}

    if ab.tipo == "vao":
        return base                                # vao puro: so o furo, nada a desenhar

    if ab.tipo == "porta":
        inicio = ab.dobradica == "inicio"
        ponto = ini if inicio else fim
        u = u0 if inicio else (-u0[0], -u0[1])     # do pivo para o outro batente
        n = (-u[1], u[0])
        lado = 1.0 if ab.gira == "esquerda" else -1.0
        folha = (n[0] * lado, n[1] * lado)

        ang_u = math.degrees(math.atan2(u[1], u[0])) % 360.0
        ang_f = math.degrees(math.atan2(folha[1], folha[0])) % 360.0
        # AutoCAD desenha arco no sentido anti-horario de a1 ate a2
        if lado > 0:
            a1, a2 = ang_u, (ang_u + 90.0) % 360.0
        else:
            a1, a2 = (ang_u - 90.0) % 360.0, ang_u

        base["pivo"] = (ponto[0], ponto[1])
        base["porta"] = (ponto[0], ponto[1], ang_f, ab.largura)
        base["arco"] = (ponto[0], ponto[1], ab.largura, a1, a2)
        base["folha_fim"] = (ponto[0] + folha[0] * ab.largura,
                             ponto[1] + folha[1] * ab.largura)
        return base

    # janela: 4 linhas atravessando o vao
    mt = p.espessura / 2.0
    n = (-u0[1], u0[0])
    linhas = []
    for fra in (-1.0 / 3.0, 1.0 / 3.0):          # 2 linhas de vidro
        desloc = (n[0] * mt * fra, n[1] * mt * fra)
        linhas.append(((ini[0] + desloc[0], ini[1] + desloc[1]),
                       (fim[0] + desloc[0], fim[1] + desloc[1])))
    for q in (ini, fim):                          # 2 batentes no sentido da espessura
        linhas.append(((q[0] - n[0] * mt, q[1] - n[1] * mt),
                       (q[0] + n[0] * mt, q[1] + n[1] * mt)))
    base["linhas"] = linhas
    return base


# ------------------------------------------------------------------- ponte
def expandir(modelo: dict) -> dict:
    """Modelo com `paredes_arquitetonicas` -> modelo no schema do `planta.py`.

    Adiciona/replaceia:
        paredes -- trechos de eixo ja cortados pelos vaos
        portas  -- (x, y, angulo_da_folha, largura)
        janelas -- (x1, y1, x2, y2) da caixa da esquadria (schema do renderer)

    Se o modelo nao tem `paredes_arquitetonicas`, volta intacto (retrocompativel).
    """
    cruas = modelo.get("paredes_arquitetonicas")
    if not cruas:
        return modelo

    paredes = []
    for i, d in enumerate(cruas):
        eixo = tuple((float(x), float(y)) for x, y in d["eixo"])
        paredes.append(Parede(
            id=str(d.get("id", "P%d" % (i + 1))), eixo=eixo,
            espessura=float(d.get("espessura", modelo.get("espessura_parede", 0.15))),
            fechada=bool(d.get("fechada", False)),
            altura=float(d.get("altura", 2.70)),
        ))
    aberturas = []
    for i, d in enumerate(modelo.get("aberturas", []) or []):
        aberturas.append(Abertura(
            id=str(d.get("id", "A%d" % (i + 1))), parede=str(d["parede"]),
            tipo=str(d.get("tipo", "porta")), offset=float(d["offset"]),
            largura=float(d["largura"]), altura=float(d.get("altura", 2.10)),
            peitoril=float(d.get("peitoril", 0.0)),
            dobradica=str(d.get("dobradica", "inicio")),
            gira=str(d.get("gira", "esquerda")),
        ))
    validar(paredes, aberturas)

    saida = dict(modelo)
    saida["paredes"] = [tuple(x for pt in seg for x in pt)
                        for p in paredes for seg in trechos(p, aberturas)]
    portas, janelas = [], []
    for ab in aberturas:
        p = next(x for x in paredes if x.id == ab.parede)
        pr = primitivas(p, ab)
        if pr["tipo"] == "janela":
            xs = [q[0] for par in pr["linhas"] for q in par]
            ys = [q[1] for par in pr["linhas"] for q in par]
            janelas.append((min(xs), min(ys), max(xs), max(ys)))
        elif "porta" in pr:
            portas.append(pr["porta"])
    if portas:
        saida["portas"] = portas
    if janelas:
        saida["janelas"] = janelas
    saida["_arquitetura"] = {
        "paredes": len(paredes), "aberturas": len(aberturas),
        "trechos": len(saida["paredes"]),
    }
    return saida
