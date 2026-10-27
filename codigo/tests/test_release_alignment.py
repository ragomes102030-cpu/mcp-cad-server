from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "codigo" / "src"),
    str(ROOT / "cloud" / "ezdxf"),
    str(ROOT / "tools"),
]

from cad_mcp import __version__ as local_version
from mcp_cad_cloud import __version__ as cloud_version
from release_version import assert_release_alignment, read_release_version


def test_local_and_cloud_report_root_release_version():
    release_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert local_version == release_version
    assert cloud_version == release_version


def test_release_helper_validates_the_whole_repository():
    assert read_release_version(ROOT) == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert_release_alignment(ROOT)
