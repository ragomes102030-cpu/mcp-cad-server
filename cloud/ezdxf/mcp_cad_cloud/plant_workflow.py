"""Preview authorization: one-time tokens bound to a particular MCP session."""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time

from mcp_cad_cloud.backend import session_key

_TTL_S = 15 * 60
_MAX_TOKENS = 256
_LOCK = threading.RLock()
_TOKENS: dict[str, tuple[str, str, float]] = {}


def fingerprint(modelo: dict, template: str) -> str:
    payload = json.dumps(
        {"template": template, "modelo": modelo},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _prune(now):
    for token, (_, _, expiry) in list(_TOKENS.items()):
        if expiry < now:
            del _TOKENS[token]


def issue(modelo: dict, template: str) -> str:
    token = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _LOCK:
        _prune(now)
        if len(_TOKENS) >= _MAX_TOKENS:
            raise ValueError("limite de prévias atingido; conclua as aprovações existentes")
        _TOKENS[token] = (session_key(), fingerprint(modelo, template), now + _TTL_S)
    return token


def consume(token: str | None, modelo: dict, template: str) -> bool:
    if not isinstance(token, str) or not token:
        return False
    with _LOCK:
        item = _TOKENS.pop(token, None)
    if item is None:
        return False
    session, expected, expires = item
    return (
        expires >= time.monotonic()
        and secrets.compare_digest(session, session_key())
        and secrets.compare_digest(expected, fingerprint(modelo, template))
    )
