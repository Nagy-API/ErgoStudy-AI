"""Generate and validate the current FastAPI OpenAPI artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app  # noqa: E402


EXPECTED_PATHS = {
    "/api/v1/health",
    "/api/v1/readiness",
    "/api/v1/plans",
    "/api/v1/plans/full",
    "/api/v1/explanations",
    "/api/v1/plans/full-with-explanation",
}


def main() -> int:
    schema = app.openapi()
    if set(schema["paths"]) != EXPECTED_PATHS:
        raise AssertionError(f"Unexpected OpenAPI paths: {sorted(schema['paths'])}")
    if "sensor" in json.dumps(schema, ensure_ascii=True).casefold():
        raise AssertionError("OpenAPI contains an obsolete sensor field or schema")
    output = PROJECT_ROOT / "data" / "processed" / "openapi.json"
    output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"openapi_version": schema["openapi"], "path_count": len(schema["paths"]), "output": str(output.relative_to(PROJECT_ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
