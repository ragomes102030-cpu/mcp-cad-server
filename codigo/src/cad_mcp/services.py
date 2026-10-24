# -*- coding: utf-8 -*-
"""Servicos de instalacao (fiacao/eletroduto/tubo) por tipo -- base do service_run.

Cada servico define camada e cor. Tudo 2D: o trecho e uma polilinha no plano.
"""
from __future__ import annotations

import math

__all__ = ["SERVICOS", "servico", "comprimento"]

SERVICOS = {
    "eletrica":    {"camada": "E-FIACAO",     "cor": 3},  # verde
    "agua_fria":   {"camada": "H-AGUA-FRIA",  "cor": 5},  # azul
    "agua_quente": {"camada": "H-AGUA-QUENTE","cor": 1},  # vermelho
    "esgoto":      {"camada": "H-ESGOTO",     "cor": 2},  # amarelo
    "gas":         {"camada": "G-GAS",        "cor": 6},  # magenta
}


def servico(nome: str) -> dict:
    if nome not in SERVICOS:
        raise ValueError("servico desconhecido: %r (use: %s)"
                         % (nome, ", ".join(sorted(SERVICOS))))
    return SERVICOS[nome]


def comprimento(points, closed: bool = False) -> float:
    """Comprimento da polilinha em metros (fecha o ultimo->primeiro se `closed`)."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    if closed and len(pts) > 1:
        pts = pts + [pts[0]]
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
