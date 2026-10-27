"""Guarda de workflow para impedir desenho sem preview aprovado."""
from __future__ import annotations

import hashlib
import json
import secrets
import time

_TTL_S = 15 * 60
_TOKENS: dict[str, tuple[str, float]] = {}


def fingerprint(modelo: dict, template: str) -> str:
    payload = json.dumps(
        {"template": template, "modelo": modelo},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def issue(modelo: dict, template: str) -> str:
    token = secrets.token_urlsafe(24)
    _TOKENS[token] = (fingerprint(modelo, template), time.monotonic() + _TTL_S)
    return token


def consume(token: str | None, modelo: dict, template: str) -> bool:
    if not isinstance(token, str) or not token:
        return False
    item = _TOKENS.pop(token, None)
    if item is None:
        return False
    expected, expires = item
    return expires >= time.monotonic() and secrets.compare_digest(
        expected, fingerprint(modelo, template)
    )
