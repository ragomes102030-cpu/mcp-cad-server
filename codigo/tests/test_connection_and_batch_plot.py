"""Regressoes para diagnostico COM e publicacao de layouts."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cad_mcp.backend_manager import BackendManager
import cad_mcp.tools_ext as ext
from autocad_mcp.backends.base import CommandResult


class FailingManager(BackendManager):
    def _resolve(self):
        raise RuntimeError("AutoCAD nao exposto via COM")


class PlotBackend:
    name = "autocad_com"

    async def drawing_plot_pdf(self, path, media=None, escala=None):
        return CommandResult(ok=True, payload={"pdf": path})


class ConnectionAndBatchPlotTests(unittest.TestCase):
    def test_status_returns_actionable_diagnostic_when_com_is_unavailable(self):
        result = asyncio.run(FailingManager(mode="com").status())

        self.assertFalse(result["ok"])
        self.assertEqual(result["backend"], None)
        self.assertEqual(result["modo_configurado"], "com")
        self.assertIn("AutoCAD nao exposto", result["erro"])

    def test_batch_plot_restores_the_original_layout(self):
        original_b = ext._b
        original_list = ext.layout_list
        original_current = ext.layout_current
        original_set = ext.layout_set_current
        switched = []

        async def fake_b():
            return PlotBackend()

        async def fake_list():
            return {"ok": True, "payload": ["Model", "PRANCHA 01", "PRANCHA 02"]}

        async def fake_current():
            return {"ok": True, "payload": "Model"}

        async def fake_set(name):
            switched.append(name)
            return {"ok": True}

        ext._b = fake_b
        ext.layout_list = fake_list
        ext.layout_current = fake_current
        ext.layout_set_current = fake_set
        try:
            result = asyncio.run(ext.batch_plot(out_dir=str(ROOT / "work")))
        finally:
            ext._b = original_b
            ext.layout_list = original_list
            ext.layout_current = original_current
            ext.layout_set_current = original_set

        self.assertTrue(result["ok"])
        self.assertEqual(result["plotados"], 2)
        self.assertEqual(switched, ["PRANCHA 01", "PRANCHA 02", "Model"])


if __name__ == "__main__":
    unittest.main()
