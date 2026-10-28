"""Volatile DXF workspace isolated by validated FastMCP HTTP session.

Never persist CAD state to another MCP connection. Local test helpers are
explicitly confined to the Python process. Restarting the service discards
all drawings; clients must export DXF before disconnecting.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import threading
import time
import os
import secrets
import ezdxf

# In-memory, per-session quotas prevent unbounded workspaces on free Render.
_TTL = 3600
_MAX = 64
_LOCK = threading.RLock()
_TEST_SESSION: ContextVar[str | None] = ContextVar("cad_local_test_session", default=None)
# Newer MCP clients do not carry Mcp-Session-Id across requests.
# A random, explicit workspace token lets them address a private volatile DXF.
_ANON_TOKEN: ContextVar[str | None] = ContextVar("cad_anon_workspace_token", default=None)


@dataclass
class Workspace:
    doc: object
    name: str = "planta_sem_nome"
    last_seen: float = field(default_factory=time.monotonic)
    lock: object = field(default_factory=threading.RLock)


_WORKSPACES: dict[str, Workspace] = {}


def _new_document():
    doc = ezdxf.new("R2013", setup=True)
    doc.header["$INSUNITS"] = 6
    return doc


def auth_mode() -> str:
    """Authentication is OFF for the online trial; can be enabled by config."""
    value = os.environ.get("MCP_CAD_AUTH_MODE", "off").strip().lower()
    if value not in {"off", "required"}:
        raise ValueError("MCP_CAD_AUTH_MODE deve ser off ou required")
    return value


def session_key() -> str:
    """Use MCP's verified connection header, not user-controlled tool args.

    A stateless HTTP call with no stable session id MUST NOT access another
    client's drawing. In-process imports/tests use an explicit local scope.
    """
    current = _TEST_SESSION.get()
    if current is not None:
        return "local:" + current
    try:
        from fastmcp.server.dependencies import get_http_request
        request = get_http_request()
    except (RuntimeError, ImportError):
        # Direct Python calls used by tests and local offline tooling.
        return "local:default"
    # Public trial mode: no API key until the owner opts into authentication.
    # Session isolation, one-use preview tokens and quotas remain enforced.
    # Set MCP_CAD_AUTH_MODE=required to enable the existing Bearer-key guard.
    if auth_mode() == "required":
        configured = os.environ.get("MCP_CAD_API_KEY", "")
        if len(configured) < 32:
            raise PermissionError("MCP_CAD_API_KEY ausente ou fraca; acesso remoto bloqueado")
        authorization = request.headers.get("authorization", "")
        supplied = authorization[7:] if authorization.lower().startswith("bearer ") else ""
        if not supplied:
            supplied = request.headers.get("x-mcp-cad-api-key", "")
        if not secrets.compare_digest(supplied, configured):
            raise PermissionError("credenciais MCP CAD inválidas")
    sid = request.headers.get("mcp-session-id", "").strip()
    if sid:
        if len(sid) > 256:
            raise ValueError("identificador de sessão MCP inválido")
        return "mcp:" + sid
    token = _ANON_TOKEN.get()
    if token:
        return "anon:" + token
    raise RuntimeError(
        "chamada MCP sem sessão: utilize workspace_token retornado na primeira "
        "ferramenta ou inicie um novo desenho")


@contextmanager
def tool_workspace(workspace_token: str | None = None):
    """Bind a stateless HTTP tool call to a cryptographically random workspace.

    If the HTTP protocol supplies a stable MCP session, preserve it unchanged.
    On modern stateless HTTP, mint a new opaque token or require an existing one.
    No IP address, User-Agent, public constant, or other shared fallback is used.
    """
    if _TEST_SESSION.get() is not None:
        yield None
        return
    try:
        from fastmcp.server.dependencies import get_http_request
        request = get_http_request()
    except (RuntimeError, ImportError):
        # Direct Python calls from tests or offline tools keep local:default.
        yield None
        return
    if request.headers.get("mcp-session-id", "").strip():
        yield None
        return
    if workspace_token is None:
        token = secrets.token_urlsafe(32)
    else:
        if not isinstance(workspace_token, str) or len(workspace_token) != 43:
            raise ValueError("workspace_token inválido; utilize o token opaco recebido do MCP")
        with _LOCK:
            ws = _WORKSPACES.get("anon:" + workspace_token)
            if ws is None or time.monotonic() - ws.last_seen >= _TTL:
                raise ValueError("workspace_token desconhecido ou expirado; crie nova prévia")
        token = workspace_token
    ctx_token = _ANON_TOKEN.set(token)
    try:
        yield token
    finally:
        _ANON_TOKEN.reset(ctx_token)


def _workspace() -> Workspace:
    key = session_key()
    now = time.monotonic()
    with _LOCK:
        for id_, ws in list(_WORKSPACES.items()):
            if now - ws.last_seen >= _TTL and id_ != key:
                del _WORKSPACES[id_]
        ws = _WORKSPACES.get(key)
        if ws is None:
            if len(_WORKSPACES) >= _MAX:
                raise RuntimeError("limite de sessões CAD alcançado; exporte e encerre sessões antigas")
            ws = Workspace(doc=_new_document())
            _WORKSPACES[key] = ws
        ws.last_seen = now
        return ws


@contextmanager
def session_lock():
    """Serialize operations targeting the same drawing across requests."""
    ws = _workspace()
    with ws.lock:
        yield


@contextmanager
def test_session(identifier: str):
    """Explicit, non-HTTP test-only context; no effect on other sessions."""
    if not identifier or len(identifier) > 128:
        raise ValueError("session identifier inválido")
    token = _TEST_SESSION.set(identifier)
    try:
        yield
    finally:
        _TEST_SESSION.reset(token)


def initialize() -> None:
    _workspace()


def reset_drawing() -> None:
    ws = _workspace()
    with ws.lock:
        ws.doc = _new_document()


def _ensure():
    return _workspace().doc


def drawing_name() -> str:
    return _workspace().name


def set_drawing_name(name: str) -> None:
    ws = _workspace()
    with ws.lock:
        ws.name = name


def ezx_version() -> str:
    return ezdxf.__version__


def state_summary() -> dict:
    doc = _ensure()
    return {
        "ok": True, "backend": "ezdxf",
        "entity_count": len(doc.modelspace()),
        "layers": len(doc.layers), "units": doc.header.get("$INSUNITS"),
        "temporary": True, "single_user": True,
        "isolation": "mcp_session_or_workspace_token", "session_ttl_seconds": _TTL,
    }


def _ent_count(doc) -> dict[str, int]:
    return dict(Counter(ent.dxftype() for ent in doc.modelspace()))
