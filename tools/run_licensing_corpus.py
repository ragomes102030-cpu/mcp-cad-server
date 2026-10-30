"""Run the architecture-package regression corpus and save auditable evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.plant_lab.licensing_corpus import run_corpus


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "licensing-corpus")
    args = parser.parse_args()
    report = run_corpus(args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if report["summary"]["total_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
