"""Release identity shared by the local and cloud MCP packages.

The root VERSION file is the release authority. Package ``__version__``
values remain importable when a package is installed from its own subtree;
this module verifies that those derived values were updated together.
"""
from __future__ import annotations

import re
from pathlib import Path


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def read_release_version(root: Path) -> str:
    """Read and validate the canonical release version from ``root/VERSION``."""
    path = Path(root) / "VERSION"
    version = path.read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(f"invalid release version in {path}: {version!r}")
    return version


def assert_release_alignment(root: Path) -> None:
    """Fail if local/cloud package metadata does not match the root release."""
    root = Path(root).resolve()
    expected = read_release_version(root)
    checks = {
        "codigo/pyproject.toml": (root / "codigo/pyproject.toml").read_text(encoding="utf-8"),
        "cloud/ezdxf/pyproject.toml": (root / "cloud/ezdxf/pyproject.toml").read_text(encoding="utf-8"),
        "codigo/src/cad_mcp/__init__.py": (root / "codigo/src/cad_mcp/__init__.py").read_text(encoding="utf-8"),
        "cloud/ezdxf/mcp_cad_cloud/__init__.py": (root / "cloud/ezdxf/mcp_cad_cloud/__init__.py").read_text(encoding="utf-8"),
    }
    for relative, content in checks.items():
        if f'version = "{expected}"' not in content and f'__version__ = "{expected}"' not in content:
            raise ValueError(f"{relative} is not aligned with release {expected}")


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    assert_release_alignment(repository)
    print(read_release_version(repository))
