"""Generate deterministic Stage 6A demo plans from JSON inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.daily_planner import DailyPlanner  # noqa: E402
from src.retriever import RetrievalService  # noqa: E402


def generate_plans(input_path: Path, output_path: Path, *, device: str = "cpu") -> list[dict]:
    """Read named demo requests, retrieve knowledge, and write stable JSON."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("demo input must be a non-empty JSON list")
    outputs: list[dict] = []
    with RetrievalService.from_frozen_config(PROJECT_ROOT, device=device) as retrieval_service:
        planner = DailyPlanner(PROJECT_ROOT, retrieval_service=retrieval_service)
        for item in raw:
            if not isinstance(item, dict) or not isinstance(item.get("example_id"), str):
                raise ValueError("every demo must contain a string example_id")
            request = item.get("request")
            plan = planner.plan(request)
            outputs.append({"example_id": item["example_id"], "plan": plan.to_dict()})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "planner_demo_inputs.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "planner_demo_outputs.json",
    )
    parser.add_argument("--device", default="cpu")
    arguments = parser.parse_args()
    outputs = generate_plans(arguments.input, arguments.output, device=arguments.device)
    for item in outputs:
        plan = item["plan"]
        print(
            f"{item['example_id']}: {plan['total_study_minutes']} study + "
            f"{plan['total_break_minutes']} break = {plan['total_planned_minutes']} minutes; "
            f"{len(plan['unscheduled_subjects'])} unscheduled"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
