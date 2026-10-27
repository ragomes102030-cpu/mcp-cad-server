"""Build identity shared by local MCP status responses."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def revision() -> str:
    """Return an explicit deployment revision, Git revision, or ``unknown``."""
    explicit = os.getenv("MCP_CAD_REVISION") or os.getenv("RENDER_GIT_COMMIT")
    if explicit:
        return explicit[:80]
    repository = Path(__file__).resolve().parents[3]
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--short=12", "HEAD"],
            check=True, capture_output=True, text=True, timeout=2,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"
