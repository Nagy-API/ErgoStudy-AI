"""Generate deterministic Stage 6B sensor-adaptation demo outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sensor_adapter import SensorPlanAdapter  # noqa: E402


def generate_adaptations(
    input_path: Path,
    output_path: Path,
    planner_output_path: Path,
) -> list[dict]:
    """Resolve named planner demos, adapt them, and write stable JSON."""
    raw_inputs = json.loads(input_path.read_text(encoding="utf-8"))
    raw_plans = json.loads(planner_output_path.read_text(encoding="utf-8"))
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError("sensor demo input must be a non-empty JSON list")
    plans = {item["example_id"]: item["plan"] for item in raw_plans}
    adapter = SensorPlanAdapter(PROJECT_ROOT)
    outputs: list[dict] = []
    for item in raw_inputs:
        example_id = item.get("example_id")
        plan_example_id = item.get("plan_example_id")
        if not isinstance(example_id, str) or not isinstance(plan_example_id, str):
            raise ValueError("each demo needs string example_id and plan_example_id")
        if plan_example_id not in plans:
            raise ValueError(f"unknown plan_example_id: {plan_example_id}")
        adapted = adapter.adapt(plans[plan_example_id], item.get("observation"))
        outputs.append(
            {
                "example_id": example_id,
                "plan_example_id": plan_example_id,
                "adapted_plan": adapted.to_dict(),
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "sensor_demo_inputs.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "sensor_demo_outputs.json",
    )
    parser.add_argument(
        "--plans",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "planner_demo_outputs.json",
    )
    arguments = parser.parse_args()
    outputs = generate_adaptations(arguments.input, arguments.output, arguments.plans)
    for item in outputs:
        plan = item["adapted_plan"]
        print(
            f"{item['example_id']}: mode={plan['mode']}, severity={plan['severity']}, "
            f"planned={plan['total_planned_minutes']}/{plan['total_available_minutes']}, "
            f"deferred={plan['deferred_study_minutes']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
