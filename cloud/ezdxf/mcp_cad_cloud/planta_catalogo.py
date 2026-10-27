"""Catalogo explicito de templates de planta para agentes pequenos."""
from __future__ import annotations

from copy import deepcopy

TEMPLATE_PADRAO = "residencia_unifamiliar_12x11"

_TEMPLATES = (
    {
        "id": TEMPLATE_PADRAO,
        "nome": "Residencia unifamiliar 12 x 11 m",
        "status": "disponivel",
        "dimensoes_externas": {"largura": 12.0, "profundidade": 11.0},
        "parede": 0.15,
        "pe_direito_padrao": 2.8,
        "ambientes": 10,
        "modo_desenho": "ezdxf",
    },
    {
        "id": "tiny_house_10m2",
        "nome": "Tiny House de 10 m2",
        "status": "em_desenvolvimento",
        "dimensoes_externas": {"area": 10.0},
        "observacao": "Ainda nao deve ser desenhada pelo template residencial.",
    },
)


def listar_templates() -> list[dict]:
    return deepcopy(list(_TEMPLATES))
