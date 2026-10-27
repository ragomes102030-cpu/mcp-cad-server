"""Private headless CAD backend. Process memory is ephemeral and single-user."""
from __future__ import annotations
from collections import Counter
import ezdxf

MANAGER = None

def _new_document():
    doc = ezdxf.new("R2013", setup=True)
    doc.header["$INSUNITS"] = 6
    return doc

def initialize() -> None:
    global MANAGER
    if MANAGER is None:
        MANAGER = _new_document()

def reset_drawing() -> None:
    global MANAGER
    MANAGER = _new_document()

def _ensure():
    initialize()
    return MANAGER

def ezx_version() -> str:
    return ezdxf.__version__

def state_summary() -> dict:
    doc = _ensure()
    return {"ok": True, "backend": "ezdxf", "entity_count": len(doc.modelspace()),
            "layers": len(doc.layers), "units": doc.header.get("$INSUNITS"),
            "temporary": True, "single_user": True}

def _ent_count(doc) -> dict[str, int]:
    return dict(Counter(ent.dxftype() for ent in doc.modelspace()))
