"""Execute notebook code cells in order without rewriting notebook artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_notebook(path: Path) -> int:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    scope = {"__name__": "__main__"}
    code_cell_count = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        exec(compile(source, str(path), "exec"), scope)
        code_cell_count += 1
    return code_cell_count


def main() -> int:
    names = sys.argv[1:] or [
        "03_embedding_model_evaluation.ipynb",
        "04_chromadb_index.ipynb",
    ]
    for name in names:
        path = PROJECT_ROOT / "notebooks" / name
        count = run_notebook(path)
        print(f"{name}: executed {count} code cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
