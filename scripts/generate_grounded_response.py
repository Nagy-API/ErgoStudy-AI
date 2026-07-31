"""Generate current-scope local explanation demonstration artifacts."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generation_validator import validate_generated_response
from src.grounded_generator import GroundedResponseGenerator
from src.grounding_context import build_grounding_context


PROCESSED = PROJECT_ROOT / "data" / "processed"


def _read_json(name: str) -> Any:
    return json.loads((PROCESSED / name).read_text(encoding="utf-8"))


def _records_by_id() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with (PROCESSED / "knowledge_corpus.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record["record_id"]] = record
    return records


def _relevant_records(plan: dict[str, Any], records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    record_ids: set[str] = set()
    for subject in plan["scheduled_subjects"]:
        record_ids.update(subject["retrieved_record_ids"])
    for session in plan["sessions"]:
        record_ids.update(session["retrieved_record_ids"])
    summaries: list[dict[str, Any]] = []
    for record_id in sorted(record_ids):
        if record_id not in records:
            continue
        text = records[record_id]["retrieval_text"].strip()
        if len(text) > 220:
            text = text[:217].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."
        summaries.append(
            {
                "record_id": records[record_id]["record_id"],
                "title": records[record_id]["title"],
                "document_family": records[record_id]["document_family"],
                "summary": text,
                "source_ids": records[record_id].get("source_ids", []),
                "evidence_level": records[record_id].get("evidence_level", ""),
                "reviewed": bool(records[record_id].get("reviewed", False)),
            }
        )
    return summaries


def build_demo_inputs() -> list[dict[str, Any]]:
    requests = {item["example_id"]: item["request"] for item in _read_json("planner_demo_inputs.json")}
    plans = {item["example_id"]: item["plan"] for item in _read_json("planner_demo_outputs.json")}
    records = _records_by_id()
    definitions = [
        ("school_plan", "school_evening"),
        ("university_aliases", "university_afternoon"),
        ("unscheduled_subject", "short_window"),
        ("unknown_subject_fallback", "unknown_subject_fallback"),
    ]
    result: list[dict[str, Any]] = []
    for case_id, plan_id in definitions:
        plan = plans[plan_id]
        result.append(
            {
                "case_id": case_id,
                "original_user_input": requests[plan_id],
                "plan": plan,
                "retrieved_record_summaries": _relevant_records(plan, records),
            }
        )
    return result


def main() -> int:
    inputs = build_demo_inputs()
    (PROCESSED / "generation_demo_inputs.json").write_text(
        json.dumps(inputs, indent=2) + "\n", encoding="utf-8"
    )
    generator = GroundedResponseGenerator(PROJECT_ROOT)
    outputs: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    latencies: list[float] = []
    for item in inputs:
        result = generator.generate(
            item["original_user_input"],
            item["plan"],
            retrieved_record_summaries=item["retrieved_record_summaries"],
        )
        context = build_grounding_context(
            item["original_user_input"],
            item["plan"],
            retrieved_record_summaries=item["retrieved_record_summaries"],
        )
        validation = validate_generated_response(result.response.to_dict(), context)
        latencies.append(result.latency_seconds)
        outputs.append({"case_id": item["case_id"], **result.to_dict()})
        validations.append(
            {
                "case_id": item["case_id"],
                "valid": validation.valid,
                "errors": list(validation.errors),
                "numeric_preservation": validation.valid
                and not any("changed" in error for error in validation.errors),
            }
        )
        print(f"{item['case_id']}: {result.generation_mode} ({result.latency_seconds:.2f}s)")
    summary = {
        "case_count": len(outputs),
        "first_attempt_json_success_count": sum(
            item["generation_mode"] == "local_llm" for item in outputs
        ),
        "corrected_response_count": sum(
            item["generation_mode"] == "local_llm_corrected" for item in outputs
        ),
        "deterministic_fallback_count": sum(
            item["generation_mode"] == "deterministic_fallback" for item in outputs
        ),
        "average_latency_seconds": round(statistics.mean(latencies), 4),
        "median_latency_seconds": round(statistics.median(latencies), 4),
        "maximum_latency_seconds": round(max(latencies), 4),
        "numeric_preservation_result": all(item["numeric_preservation"] for item in validations),
        "grounding_validation_result": all(item["valid"] for item in validations),
        "cases": validations,
    }
    (PROCESSED / "generation_demo_outputs.json").write_text(
        json.dumps(outputs, indent=2) + "\n", encoding="utf-8"
    )
    (PROCESSED / "generation_validation_results.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["grounding_validation_result"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
