"""Command-line entry point for the deterministic Stage 3 dataset build."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_builder import build_dataset  # noqa: E402


def main() -> int:
    statistics = build_dataset(PROJECT_ROOT)
    print(json.dumps(statistics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
