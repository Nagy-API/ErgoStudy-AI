"""Command-line entry point for Stage 3 dataset validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_validator import validate_dataset  # noqa: E402


def main() -> int:
    report = validate_dataset(PROJECT_ROOT)
    print(json.dumps({
        "passed": report["passed"],
        "error_count": report["error_count"],
        "warning_count": report["warning_count"],
        "summary": report.get("summary", {}),
        "errors": report["errors"],
        "warnings": report["warnings"],
    }, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
