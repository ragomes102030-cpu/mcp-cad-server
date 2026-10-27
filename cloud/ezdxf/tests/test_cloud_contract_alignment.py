from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "codigo" / "src"), str(ROOT / "cloud" / "ezdxf")]

from mcp_cad_cloud.server import build_info


def test_cloud_build_info_is_complete():
    info = build_info()
    assert set(info) >= {"version", "revision", "transport", "backend"}
    assert info["transport"] == "http"
    assert info["backend"] == "ezdxf"
