# -*- coding: utf-8 -*-
"""Backend ezdxf headless: desenho sem AutoCAD, sem licença, sem Windows.

Estado:
- Cada MCP session tem um desenho em memória (Pizza/PE) mantido pelo backend.
- As ferramentas só operam sobre este contexto (átomo `MANAGER`).
- `render()` gera PNG (via matplotlib) a partir do DXF.

Uso:
    from mcp_cad_cloud.backend import MANAGER, ezdxf
    await MANAGER.initialize()
    await MANAGER.new_drawing("P&Q")
"""

from __future__ import annotations

import os
from pathlib import Path

import ezdxf

# ---------------------------------------------------------------- instância
app = ezdxf.new_document()
app.set_screen_size(1200, 800)
MANAGER = None  # será setada na inicialização


def _ensure() -> ezdxf.document.Document:
    """Garante que o documento está pronto (inicialização idempotente)."""
    global MANAGER
    if MANAGER is None:
        raise RuntimeError("backend não inicializado: execute initialize()")
    return MANAGER


def initialize() -> None:
    global MANAGER
    MANAGER = app


def reset_drawing() -> None:
    """Sola o estado do desenho (clear + novo Document)."""
    global MANAGER
    import ezdxf

    MANAGER = ezdxf.new_document()
    MANAGER.set_screen_size(1200, 800)


def ezx_version() -> str:
    return ezdxf.__version__


# ------------------------------------------------------------------ helpers
def _ent_count(doc) -> dict:
    from collections import Counter

    c = Counter()
    for block in doc.blocks:
        for ent in block.query():
            c[ent.dxftype()] += 1
    return dict(c)
