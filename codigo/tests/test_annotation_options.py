"""Regressao para anotacoes posicionaveis sem alterar o estilo global."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cad_mcp.com_backend import ComBackend, CommandResult
from autocad_mcp.backends.ezdxf_backend import EzdxfBackend


class CapturingComBackend(ComBackend):
    def __init__(self) -> None:
        pass

    def _aval(self, expression: str) -> CommandResult:
        self.expression = expression
        return CommandResult(ok=True, payload="TEST")


class AnnotationOptionsTests(unittest.TestCase):
    def test_centered_text_uses_anchor_as_alignment_point(self) -> None:
        backend = CapturingComBackend()
        result = asyncio.run(
            backend.create_text(5, 4, "SALA", height=0.16, justification="center")
        )

        self.assertTrue(result.ok)
        self.assertIn('(cons 72 1)', backend.expression)
        self.assertIn('(cons 11 (list 5 4 0.0))', backend.expression)

    def test_dimension_options_are_entity_overrides(self) -> None:
        backend = CapturingComBackend()
        result = asyncio.run(
            backend.create_dimension_linear(
                0, 0, 4, 0, 2, -0.6,
                layer="COTA", text_height=0.15, arrow_size=0.06, scale=0.06,
            )
        )

        self.assertTrue(result.ok)
        self.assertIn('vla-put-Layer __o "COTA"', backend.expression)
        self.assertIn('vla-put-TextHeight __o 0.15', backend.expression)
        self.assertIn('vla-put-ArrowheadSize __o 0.06', backend.expression)
        self.assertIn('vla-put-ScaleFactor __o 0.06', backend.expression)

    def test_dimension_provisions_its_target_layer(self) -> None:
        backend = CapturingComBackend()
        asyncio.run(
            backend.create_dimension_linear(0, 0, 4, 0, 2, -0.6, layer="COTA")
        )

        self.assertIn('(vla-Add (vla-get-Layers __d) "COTA")', backend.expression)

    def test_bulk_property_change_requires_a_filter_and_updates_matches(self) -> None:
        backend = CapturingComBackend()
        missing_filter = asyncio.run(
            backend.entity_set_properties_filter(target_layer="COTA")
        )
        self.assertFalse(missing_filter.ok)

        result = asyncio.run(
            backend.entity_set_properties_filter(
                filter_layer="TEXTO", tipo="TEXT", target_layer="ANOTACAO", color=7,
            )
        )
        self.assertTrue(result.ok)
        self.assertIn('(strcase "TEXTO")', backend.expression)
        self.assertIn('"TEXT"', backend.expression)
        self.assertIn('(vla-put-Layer __e "ANOTACAO")', backend.expression)
        self.assertIn('(vla-put-Color __e 7)', backend.expression)

    def test_headless_text_accepts_center_justification(self) -> None:
        backend = EzdxfBackend()
        asyncio.run(backend.initialize())
        result = asyncio.run(
            backend.create_text(5, 4, "SALA", height=0.16, justification="center")
        )

        self.assertTrue(result.ok)
        entity = backend._doc.entitydb[result.payload["handle"]]
        self.assertEqual(entity.dxf.halign, 1)
        self.assertEqual(tuple(entity.dxf.align_point)[:2], (5.0, 4.0))


if __name__ == "__main__":
    unittest.main()
