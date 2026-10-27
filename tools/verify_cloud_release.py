"""Verify a deployed MCP CAD Cloud release without credentials."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def _revision() -> str:
    explicit = os.getenv("MCP_CAD_REVISION") or os.getenv("RENDER_GIT_COMMIT")
    if explicit:
        return explicit[:12]
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short=12", "HEAD"],
            check=True, capture_output=True, text=True, timeout=2,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _get_json(url: str) -> dict:
    with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=20) as response:
        return json.load(response)


def verify(base_url: str) -> dict:
    base = base_url.rstrip("/")
    if base.endswith("/mcp"):
        base = base[:-4].rstrip("/")
    health = _get_json(f"{base}/healthz")
    expected_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    expected_revision = _revision()
    if health.get("version") != expected_version:
        raise RuntimeError(f"version mismatch: remote={health.get('version')!r} local={expected_version!r}")
    if health.get("revision", "")[:12] != expected_revision:
        raise RuntimeError(f"revision mismatch: remote={health.get('revision')!r} local={expected_revision!r}")
    if health.get("transport") != "http" or health.get("backend") != "ezdxf":
        raise RuntimeError(f"unexpected cloud identity: {health}")

    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "mcp-cad-release-check", "version": "1"},
        },
    }
    request = Request(
        f"{base}/mcp", data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"MCP initialize HTTP {exc.code}; public access check failed") from exc
    if status != 200 or '"jsonrpc":"2.0"' not in body:
        raise RuntimeError(f"MCP initialize failed: HTTP {status}, body={body[:300]!r}")
    return {"ok": True, "health": health, "initialize_status": status}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Render base URL or URL ending in /mcp")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.url), ensure_ascii=False, indent=2))
    except (HTTPError, URLError, OSError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
