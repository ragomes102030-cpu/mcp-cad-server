"""Independent byte-level acceptance of the downloaded CAD export."""
import asyncio
import hashlib
import io
import tempfile
import time
import zipfile
from urllib.parse import urlparse
from pathlib import Path

import ezdxf
from starlette.requests import Request

from mcp_cad_cloud import downloads, server
from mcp_cad_cloud import tools_verified as cad
from test_layout_compacto import CASA


def _request(token: str, fmt: str):
    scope = {
        "type": "http", "method": "GET", "path": f"/downloads/{token}/{fmt}",
        "path_params": {"token": token, "fmt": fmt}, "query_string": b"",
        "headers": [],
    }
    return Request(scope)


def test_real_dxf_https_download_and_independent_ezdxf_audit():
    preview = cad.planta_criar_validada(
        programa=CASA, template="programa_sob_medida", modo="preview")
    assert preview["ok"], preview
    result = cad.planta_criar_validada(
        programa=CASA, template="programa_sob_medida",
        modo="desenhar", preview_token=preview["preview_token"])
    assert result["ok"], result

    exported = cad.export_dxf()
    assert exported["ok"], exported
    assert exported["format"] == "direct_https_download"
    assert exported["expires_in_seconds"] == 900
    assert "data_base64" not in exported
    assert exported["download_url"].startswith("https://")
    assert exported["dxf_url"].startswith("https://")
    token = urlparse(exported["download_url"]).path.split("/")[-2]
    zip_response = asyncio.run(server.download_dxf(_request(token, "zip")))
    dxf_response = asyncio.run(server.download_dxf(_request(token, "dxf")))
    assert zip_response.status_code == dxf_response.status_code == 200
    assert zip_response.headers["cache-control"] == "no-store"
    assert dxf_response.headers["content-disposition"].endswith('"desenho.dxf"')
    assert hashlib.sha256(zip_response.body).hexdigest() == exported["sha256_zip"]
    assert hashlib.sha256(dxf_response.body).hexdigest() == exported["sha256_dxf"]

    with zipfile.ZipFile(io.BytesIO(zip_response.body)) as archive:
        assert archive.testzip() is None
        unzipped = archive.read("desenho.dxf")
    assert unzipped == dxf_response.body

    # Independent disk roundtrip: the DXF file returned by HTTP is read anew.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "downloaded.dxf"
        path.write_bytes(dxf_response.body)
        doc = ezdxf.readfile(path)
    assert len(doc.modelspace()) == 180
    assert len([e for e in doc.modelspace()
                if e.dxf.layer not in ("EIXOS-PAREDES", "PISOS", "PORTAS-DETALHE")]) == 146
    assert len(doc.modelspace().query('LINE[layer=="EIXOS-PAREDES"]')) == 22
    assert len(doc.modelspace().query('LWPOLYLINE[layer=="PISOS"]')) == 7
    assert len(list(doc.modelspace().query("DIMENSION"))) == 8
    assert doc.audit().has_errors is False


def test_invalid_and_expired_downloads_are_not_served():
    archive = cad.export_dxf()
    assert archive["ok"], archive
    token = urlparse(archive["dxf_url"]).path.split("/")[-2]
    assert asyncio.run(server.download_dxf(_request("X" * 43, "dxf"))).status_code == 404
    assert asyncio.run(server.download_dxf(_request(token, "bad"))).status_code == 404
    with downloads._LOCK:
        item = downloads._EXPORTS[token]
        downloads._EXPORTS[token] = downloads.Export(
            dxf=item.dxf, archive=item.archive, expires_at=time.monotonic()-1)
    assert asyncio.run(server.download_dxf(_request(token, "dxf"))).status_code == 404


def test_legacy_base64_remains_explicitly_available():
    import base64
    export = cad.export_dxf(incluir_base64=True)
    assert export["ok"] and "data_base64" in export
    token = urlparse(export["download_url"]).path.split("/")[-2]
    direct = asyncio.run(server.download_dxf(_request(token, "zip")))
    assert base64.b64decode(export["data_base64"]) == direct.body
