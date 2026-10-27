from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "codigo" / "src"), str(ROOT / "cloud" / "ezdxf")]

from cad_mcp import __version__ as local_version
from cad_mcp import tools as local_tools
from cad_mcp.server import build_info as local_build_info
from mcp_cad_cloud import __version__ as cloud_version
from mcp_cad_cloud import tools_verified as cloud_tools
from mcp_cad_cloud.server import build_info as cloud_build_info


def test_local_and_cloud_expose_same_build_identity():
    local = local_build_info()
    cloud = cloud_build_info()
    assert local["version"] == local_version == cloud_version == cloud["version"]
    assert local["revision"] == cloud["revision"]
    assert local["transport"] == "stdio"
    assert cloud["transport"] == "http"
    assert local["backend"] == "autocad-or-headless"
    assert cloud["backend"] == "ezdxf"


def test_cloud_tools_are_a_real_subset_of_local_contract():
    assert set(cloud_tools.TOOLS).issubset({fn.__name__ for fn in local_tools.TOOLS})
