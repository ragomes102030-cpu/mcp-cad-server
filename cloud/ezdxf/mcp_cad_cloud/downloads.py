"""Short-lived, unguessable download links for real DXF/ZIP exports.

This is an intentionally unauthenticated test server. The URL is a bearer
capability: never use for private project drawings. No disk persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import secrets
import threading
import time

_TTL_SECONDS = 15 * 60
_MAX_EXPORTS = 32
_MAX_TOTAL_BYTES = 24 * 1024 * 1024
_LOCK = threading.RLock()


@dataclass(frozen=True)
class Export:
    dxf: bytes
    archive: bytes
    expires_at: float


_EXPORTS: dict[str, Export] = {}


def _purge(now: float) -> None:
    for token, item in list(_EXPORTS.items()):
        if item.expires_at <= now:
            del _EXPORTS[token]


def publish(dxf: bytes, archive: bytes) -> dict:
    """Return links to the exact bytes of the exported in-memory drawing."""
    if not dxf or not archive:
        raise ValueError("exportação vazia")
    now = time.monotonic()
    with _LOCK:
        _purge(now)
        if len(_EXPORTS) >= _MAX_EXPORTS:
            raise ValueError("limite de downloads atingido; tente mais tarde")
        size = sum(len(x.dxf) + len(x.archive) for x in _EXPORTS.values())
        if size + len(dxf) + len(archive) > _MAX_TOTAL_BYTES:
            raise ValueError("limite de memória de downloads atingido")
        token = secrets.token_urlsafe(32)
        _EXPORTS[token] = Export(dxf, archive, now + _TTL_SECONDS)
    # A fixed Render URL avoids Host-header injection in download links.
    origin = os.getenv("MCP_CAD_PUBLIC_URL", "https://mcp-cad-cloud-clsq.onrender.com").rstrip("/")
    if not origin.startswith("https://") or "/" in origin[8:]:
        raise ValueError("MCP_CAD_PUBLIC_URL deve ser a origem https sem caminho")
    return {
        "download_url": f"{origin}/downloads/{token}/zip",
        "dxf_url": f"{origin}/downloads/{token}/dxf",
        "expires_in_seconds": _TTL_SECONDS,
    }


def retrieve(token: str, fmt: str) -> tuple[bytes, str, str] | None:
    if fmt not in {"zip", "dxf"} or not isinstance(token, str) or len(token) != 43:
        return None
    with _LOCK:
        _purge(time.monotonic())
        entry = _EXPORTS.get(token)
        if entry is None:
            return None
        if fmt == "zip":
            return entry.archive, "application/zip", "desenho.dxf.zip"
        return entry.dxf, "application/dxf", "desenho.dxf"
