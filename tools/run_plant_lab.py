"""Run the reproducible MCP CAD plant lab and preserve all evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.plant_lab.runner import run_lab


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "plant-lab",
                        help="directory for JSON/Markdown reports, DXFs and visual evidence")
    args = parser.parse_args(argv)
    report = run_lab(args.output)
    summary = report["summary"]
    print(f"Plant lab {'PASS' if report['ok'] else 'FAIL'}: "
          f"valid {summary['valid_passed']}/{summary['valid_total']}, "
          f"adversarial {summary['adversarial_passed']}/{summary['adversarial_total']}, "
          f"tool handlers {summary['mcp_passed']}/{summary['mcp_total']}")
    print(f"Evidence: {report['output_dir']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
