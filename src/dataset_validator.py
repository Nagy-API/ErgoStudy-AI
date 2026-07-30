"""Automatic validation for the ErgoStudy Stage 3 dataset."""

from __future__ import annotations

import json
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from src.dataset_builder import DATASET_VERSION, FAMILY_FILES, build_dataset
from src.dataset_io import file_sha256, read_json, read_jsonl, read_source_catalog, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORD_ID_PATTERN = re.compile(r"^(subject|topic|strategy|session|sensor|alias|eval)-[a-z0-9]+(?:-[a-z0-9]+)*-v[0-9]+$")
DOCUMENT_FAMILIES = set(FAMILY_FILES) | {"retrieval_evaluation_query"}
SUBJECT_FAMILIES = {
    "mathematics", "natural_sciences", "language_and_literature", "social_sciences", "computing",
    "engineering", "health_sciences", "business_and_economics", "arts_and_design", "law", "general",
}
EDUCATIONAL_LEVELS = {"school", "university", "cross_level"}
LEARNING_TASKS = {
    "theory_learning", "memorization", "reading_comprehension", "writing", "problem_solving", "coding",
    "debugging", "laboratory", "design", "case_analysis", "mixed", None,
}
COGNITIVE_DEMANDS = {"remember", "understand", "apply", "analyze", "evaluate", "create", "mixed", None}
EVIDENCE_LEVELS = {"high", "moderate", "emerging", "expert_consensus", "source_descriptive", "design_proposal", "not_applicable"}
SAFETY_SCOPES = {"none", "non_medical_wellbeing", "stop_and_seek_help"}
REVIEW_TIERS = {"tier_a", "tier_b", "tier_c"}
SOURCE_ROLES = {"learning_evidence", "subject_framework", "ergonomics_guidance", "public_health_guidance", "planner_design_support"}

SHARED_REQUIRED = {
    "record_id", "document_family", "title", "retrieval_text", "evidence_level", "source_ids",
    "safety_scope", "synthetic", "reviewed", "review_tier", "dataset_version",
}
FAMILY_REQUIRED = {
    "subject_profile": {"subject_name", "aliases", "subject_family", "educational_level", "typical_learning_activities", "characteristics"},
    "topic_profile": {"topic", "subject_family", "educational_level", "learning_task", "cognitive_demand", "recommended_methods"},
    "study_strategy": {"recommended_methods", "suitable_learning_tasks", "implementation_guidance", "unsuitable_use_cases", "limitations"},
    "session_template": {"session_duration_min", "session_duration_max", "break_duration_min", "break_duration_max", "phases", "suitable_learning_tasks", "unsuitable_use_cases", "duration_status"},
    "sensor_intervention": {"sensor_condition", "intervention", "missing_data_behavior", "hardware_confirmation_required", "contraindications", "sensor_mode"},
    "subject_alias": {"subject_name", "aliases", "subject_family", "educational_level", "matching_notes", "ambiguous", "ambiguity_notes"},
}
EVALUATION_REQUIRED = {
    "record_id", "document_family", "dataset_version", "query_id", "query_text", "expected_document_families",
    "expected_subject_family", "difficulty_type", "notes",
}


def normalize_text(value: str) -> str:
    """Normalize text for duplicate and leakage checks."""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def validate_record(record: dict[str, Any]) -> list[str]:
    """Validate one retrievable record's required and conditional fields."""
    errors: list[str] = []
    _validate_record_shape(record, errors)
    return errors


def find_duplicate_retrieval_texts(records: list[dict[str, Any]]) -> list[list[str]]:
    """Return groups with exactly duplicated normalized retrieval text."""
    normalized_texts: defaultdict[str, list[str]] = defaultdict(list)
    for record in records:
        normalized_texts[normalize_text(record["retrieval_text"])].append(record["record_id"])
    return [record_ids for record_ids in normalized_texts.values() if len(record_ids) > 1]


def find_broken_source_references(records: list[dict[str, Any]], catalog_ids: set[str]) -> list[str]:
    """Return source IDs that are not in the catalog."""
    return sorted({source_id for record in records for source_id in record.get("source_ids", []) if source_id not in catalog_ids})


def find_source_role_errors(records: list[dict[str, Any]], source_roles: dict[str, str]) -> list[str]:
    """Return records that use a source outside its documented evidence role."""
    invalid: list[str] = []
    for record in records:
        roles = {source_roles.get(source_id) for source_id in record.get("source_ids", [])}
        if "subject_framework" in roles:
            if record.get("evidence_level") not in {"source_descriptive", "design_proposal"}:
                invalid.append(f"{record['record_id']}: framework used as effectiveness evidence")
            if record.get("document_family") == "sensor_intervention":
                invalid.append(f"{record['record_id']}: framework used for sensor intervention")
            if record.get("document_family") == "session_template" and (
                record.get("evidence_level") != "design_proposal"
                or record.get("duration_status") != "design_proposal_requires_evaluation"
            ):
                invalid.append(f"{record['record_id']}: framework-linked session is not a design proposal")
        if roles & {"ergonomics_guidance", "public_health_guidance"}:
            if record.get("document_family") != "sensor_intervention":
                invalid.append(f"{record['record_id']}: health or ergonomics source used outside sensor safety scope")
            if record.get("safety_scope") not in {"non_medical_wellbeing", "stop_and_seek_help"}:
                invalid.append(f"{record['record_id']}: health or ergonomics source lacks safe scope")
    return sorted(set(invalid))


def find_broken_parent_references(records: list[dict[str, Any]]) -> list[str]:
    """Return invalid derivation and record-relationship links."""
    record_ids = {record["record_id"] for record in records}
    invalid: list[str] = []
    for record in records:
        references = list(record.get("derived_from_record_ids", []))
        if record.get("derived_from_record_id"):
            references.append(record["derived_from_record_id"])
        references.extend(record.get("related_subject_record_ids", []))
        if record.get("canonical_subject_record_id"):
            references.append(record["canonical_subject_record_id"])
        for reference in references:
            if reference not in record_ids:
                invalid.append(f"{record['record_id']} -> {reference}")
    return invalid


def find_evaluation_leaks(records: list[dict[str, Any]], evaluations: list[dict[str, Any]]) -> list[str]:
    """Return evaluation IDs whose query text exactly duplicates retrieval text."""
    retrieval_norms = {normalize_text(record["retrieval_text"]) for record in records}
    return [record["record_id"] for record in evaluations if normalize_text(record["query_text"]) in retrieval_norms]


def find_sensor_safety_errors(records: list[dict[str, Any]]) -> list[str]:
    """Return sensor records that violate conservative language and metadata rules."""
    invalid: list[str] = []
    unsafe_patterns = [
        r"sensor (?:proves|confirms) (?:injury|disease)", r"diagnose the user", r"treat the user's",
        r"scientifically confirmed posture threshold", r"pressure threshold of \d", r"sampling rate of \d",
    ]
    for record in records:
        if record.get("document_family") != "sensor_intervention":
            continue
        text = record.get("retrieval_text", "").casefold()
        if not record.get("hardware_confirmation_required") or not record.get("reviewed"):
            invalid.append(record["record_id"])
        if record.get("safety_scope") not in {"non_medical_wellbeing", "stop_and_seek_help"}:
            invalid.append(record["record_id"])
        if "non-medical" not in text or "does not diagnose" not in text:
            invalid.append(record["record_id"])
        if any(re.search(pattern, text) for pattern in unsafe_patterns):
            invalid.append(record["record_id"])
    return sorted(set(invalid))


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _validate_record_shape(record: dict[str, Any], errors: list[str]) -> None:
    record_id = record.get("record_id", "<missing-id>")
    missing = sorted((SHARED_REQUIRED | FAMILY_REQUIRED.get(record.get("document_family"), set())) - record.keys())
    if missing:
        errors.append(f"{record_id}: missing required fields {missing}")
    if not RECORD_ID_PATTERN.fullmatch(str(record.get("record_id", ""))):
        errors.append(f"{record_id}: invalid record_id format")
    if record.get("document_family") not in FAMILY_FILES:
        errors.append(f"{record_id}: invalid retrievable document_family")
    if record.get("dataset_version") != DATASET_VERSION:
        errors.append(f"{record_id}: wrong dataset_version")
    if record.get("evidence_level") not in EVIDENCE_LEVELS:
        errors.append(f"{record_id}: invalid evidence_level")
    if record.get("safety_scope") not in SAFETY_SCOPES:
        errors.append(f"{record_id}: invalid safety_scope")
    if record.get("review_tier") not in REVIEW_TIERS:
        errors.append(f"{record_id}: invalid review_tier")
    if not isinstance(record.get("source_ids"), list) or not record.get("source_ids"):
        errors.append(f"{record_id}: source_ids must be a non-empty list")
    if len(str(record.get("retrieval_text", ""))) < 40:
        errors.append(f"{record_id}: retrieval_text is too short")
    levels = record.get("educational_level")
    if levels is not None and (not isinstance(levels, list) or not levels or not set(levels) <= EDUCATIONAL_LEVELS):
        errors.append(f"{record_id}: invalid educational_level")
    if "subject_family" in record and record["subject_family"] not in SUBJECT_FAMILIES | {None}:
        errors.append(f"{record_id}: invalid subject_family")
    if "learning_task" in record and record["learning_task"] not in LEARNING_TASKS:
        errors.append(f"{record_id}: invalid learning_task")
    if "cognitive_demand" in record and record["cognitive_demand"] not in COGNITIVE_DEMANDS:
        errors.append(f"{record_id}: invalid cognitive_demand")


def _validate_evaluation_record(record: dict[str, Any], errors: list[str]) -> None:
    record_id = record.get("record_id", "<missing-id>")
    missing = sorted(EVALUATION_REQUIRED - record.keys())
    if missing:
        errors.append(f"{record_id}: missing evaluation fields {missing}")
    if record.get("document_family") != "retrieval_evaluation_query":
        errors.append(f"{record_id}: evaluation file contains a retrievable family")
    if not (record.get("expected_relevant_record_ids") or record.get("relevance_criteria")):
        errors.append(f"{record_id}: evaluation query needs expected IDs or relevance criteria")
    if record.get("dataset_version") != DATASET_VERSION:
        errors.append(f"{record_id}: wrong evaluation dataset_version")


def detect_near_duplicates(records: list[dict[str, Any]], threshold: float = 0.985) -> list[dict[str, Any]]:
    """Find unusually similar records with token-set Jaccard similarity."""
    token_sets = [set(normalize_text(record["retrieval_text"]).split()) for record in records]
    matches: list[dict[str, Any]] = []
    for left_index, left in enumerate(records):
        for right_index in range(left_index + 1, len(records)):
            right = records[right_index]
            if left["document_family"] != right["document_family"]:
                continue
            union = token_sets[left_index] | token_sets[right_index]
            if not union:
                continue
            score = len(token_sets[left_index] & token_sets[right_index]) / len(union)
            if score >= threshold:
                matches.append({"left": left["record_id"], "right": right["record_id"], "score": round(score, 4)})
    return matches


def _validate_determinism(project_root: Path) -> tuple[bool, dict[str, str]]:
    with tempfile.TemporaryDirectory() as first_name, tempfile.TemporaryDirectory() as second_name:
        first = Path(first_name)
        second = Path(second_name)
        build_dataset(project_root, first)
        build_dataset(project_root, second)
        filenames = list(FAMILY_FILES.values()) + [
            "knowledge_corpus.jsonl", "retrieval_evaluation_queries.jsonl", "dataset_statistics.json"
        ]
        first_hashes = {name: file_sha256(first / name) for name in filenames}
        second_hashes = {name: file_sha256(second / name) for name in filenames}
        return first_hashes == second_hashes, first_hashes


def validate_dataset(project_root: Path = PROJECT_ROOT, *, check_determinism: bool = True,
                     write_report: bool = True) -> dict[str, Any]:
    """Run all Stage 3 validations and optionally write validation_report.json."""
    processed_dir = project_root / "data" / "processed"
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, dict[str, Any]] = {}

    required_paths = [processed_dir / "knowledge_corpus.jsonl", processed_dir / "retrieval_evaluation_queries.jsonl"]
    required_paths.extend(processed_dir / filename for filename in FAMILY_FILES.values())
    missing_paths = [str(path.relative_to(project_root)) for path in required_paths if not path.exists()]
    if missing_paths:
        errors.append(f"Missing processed files: {missing_paths}")
        report = {"passed": False, "error_count": len(errors), "warning_count": 0, "errors": errors, "warnings": [], "checks": {}}
        if write_report:
            write_json(processed_dir / "validation_report.json", report)
        return report

    try:
        corpus = read_jsonl(processed_dir / "knowledge_corpus.jsonl")
        evaluations = read_jsonl(processed_dir / "retrieval_evaluation_queries.jsonl")
        schema = read_json(project_root / "data" / "interim" / "dataset_schema.json")
        checks["json_and_jsonl_syntax"] = {"passed": True, "details": "All seed, schema, corpus, family, and evaluation files parsed."}
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"JSON parsing failed: {exc}")
        corpus, evaluations, schema = [], [], {}
        checks["json_and_jsonl_syntax"] = {"passed": False, "details": str(exc)}

    schema_properties = set(schema.get("properties", {}))
    unknown_fields = sorted({field for record in corpus + evaluations for field in record if field not in schema_properties})
    if unknown_fields:
        errors.append(f"Fields missing from dataset schema: {unknown_fields}")
    checks["schema_compatibility"] = {"passed": not unknown_fields, "unknown_fields": unknown_fields}

    shape_errors_start = len(errors)
    for record in corpus:
        _validate_record_shape(record, errors)
    for record in evaluations:
        _validate_evaluation_record(record, errors)
    checks["required_and_conditional_fields"] = {"passed": len(errors) == shape_errors_start}
    checks["valid_enumerations"] = {"passed": len(errors) == shape_errors_start}

    ids = [record.get("record_id") for record in corpus]
    duplicate_ids = sorted(record_id for record_id, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"Duplicate record IDs: {duplicate_ids}")
    checks["stable_unique_record_ids"] = {"passed": not duplicate_ids, "duplicates": duplicate_ids}

    duplicate_texts = find_duplicate_retrieval_texts(corpus)
    if duplicate_texts:
        errors.append(f"Duplicate retrieval texts: {duplicate_texts[:10]}")
    checks["duplicate_records_and_retrieval_texts"] = {"passed": not duplicate_texts, "groups": duplicate_texts}

    near_duplicates = detect_near_duplicates(corpus)
    if near_duplicates:
        warnings.append(f"Near-duplicate review candidates: {len(near_duplicates)}")
    checks["near_duplicate_retrieval_texts"] = {"passed": True, "review_candidates": near_duplicates[:100], "candidate_count": len(near_duplicates)}

    source_rows = read_source_catalog(project_root / "data" / "sources" / "source_catalog.csv")
    catalog_ids = {row["source_id"] for row in source_rows}
    broken_sources = find_broken_source_references(corpus, catalog_ids)
    if broken_sources:
        errors.append(f"Broken source references: {broken_sources}")
    checks["source_reference_validation"] = {"passed": not broken_sources, "broken_source_ids": broken_sources}

    invalid_catalog_roles = sorted(
        row["source_id"] for row in source_rows if row.get("source_role") not in SOURCE_ROLES
    )
    source_roles = {row["source_id"]: row.get("source_role", "") for row in source_rows}
    source_role_errors = find_source_role_errors(corpus, source_roles)
    if invalid_catalog_roles:
        errors.append(f"Missing or invalid source roles: {invalid_catalog_roles}")
    if source_role_errors:
        errors.append(f"Source-role violations: {source_role_errors[:20]}")
    checks["source_role_correctness"] = {
        "passed": not invalid_catalog_roles and not source_role_errors,
        "invalid_catalog_roles": invalid_catalog_roles,
        "invalid_record_uses": source_role_errors,
        "role_counts": dict(sorted(Counter(source_roles.values()).items())),
    }

    corpus_by_id = {record["record_id"]: record for record in corpus}
    parent_errors = find_broken_parent_references(corpus)
    if parent_errors:
        errors.append(f"Invalid parent or relationship references: {parent_errors[:20]}")
    checks["parent_reference_validation"] = {"passed": not parent_errors, "invalid_references": parent_errors}

    trace_errors: list[str] = []
    evidence_errors: list[str] = []
    for record in corpus:
        if not record.get("synthetic"):
            continue
        parents = record.get("derived_from_record_ids", [])
        if not record.get("generation_method") or not record.get("derived_from_record_id") or not parents:
            trace_errors.append(record["record_id"])
            continue
        parent = corpus_by_id.get(parents[0])
        if parent and (record["source_ids"] != parent["source_ids"] or record["evidence_level"] != parent["evidence_level"]):
            evidence_errors.append(record["record_id"])
    if trace_errors:
        errors.append(f"Untraceable synthetic records: {trace_errors[:20]}")
    if evidence_errors:
        errors.append(f"Synthetic evidence/source inconsistency: {evidence_errors[:20]}")
    checks["synthetic_traceability"] = {"passed": not trace_errors, "invalid_records": trace_errors}
    checks["evidence_level_consistency"] = {"passed": not evidence_errors, "invalid_records": evidence_errors}

    tier_errors: list[str] = []
    for record in corpus:
        family = record["document_family"]
        if family in {"study_strategy", "sensor_intervention"} and (record["review_tier"] != "tier_a" or not record["reviewed"]):
            tier_errors.append(record["record_id"])
        if family in {"subject_profile", "topic_profile", "session_template"} and record["review_tier"] != "tier_b":
            tier_errors.append(record["record_id"])
        if family == "subject_alias" and record["review_tier"] != "tier_c":
            tier_errors.append(record["record_id"])
    if tier_errors:
        errors.append(f"Review-tier violations: {tier_errors[:20]}")
    checks["review_tier_compliance"] = {"passed": not tier_errors, "invalid_records": tier_errors}

    sensor_errors = find_sensor_safety_errors(corpus)
    if sensor_errors:
        errors.append(f"Sensor safety-language violations: {sensor_errors}")
    checks["sensor_safety_and_medical_language"] = {"passed": not sensor_errors, "invalid_records": sensor_errors}

    range_errors: list[str] = []
    for record in corpus:
        if record["document_family"] != "session_template":
            continue
        if not (10 <= record["session_duration_min"] <= record["session_duration_max"] <= 120):
            range_errors.append(record["record_id"])
        if not (2 <= record["break_duration_min"] <= record["break_duration_max"] <= 30):
            range_errors.append(record["record_id"])
        if record.get("duration_status") != "design_proposal_requires_evaluation" or "not universal scientific facts" not in record["retrieval_text"]:
            range_errors.append(record["record_id"])
    if range_errors:
        errors.append(f"Session or break parameter violations: {sorted(set(range_errors))}")
    checks["session_and_break_bounds"] = {"passed": not range_errors, "invalid_records": sorted(set(range_errors))}

    non_english: list[str] = []
    forbidden_script = re.compile(r"[\u0370-\u03ff\u0400-\u052f\u0590-\u08ff\u3040-\u30ff\u3400-\u9fff]")
    for record in corpus + evaluations:
        if any(forbidden_script.search(text) for text in _strings(record)):
            non_english.append(record["record_id"])
    if non_english:
        errors.append(f"Non-English script detected: {non_english[:20]}")
    checks["english_only_content"] = {"passed": not non_english, "invalid_records": non_english}

    leaked = find_evaluation_leaks(corpus, evaluations)
    corpus_eval_families = [record["record_id"] for record in corpus if record["document_family"] == "retrieval_evaluation_query"]
    if leaked or corpus_eval_families:
        errors.append(f"Evaluation leakage: exact_text={leaked}, family_records={corpus_eval_families}")
    checks["evaluation_corpus_separation"] = {"passed": not leaked and not corpus_eval_families, "leaked_queries": leaked}

    bad_expected_ids = sorted({reference for query in evaluations for reference in query.get("expected_relevant_record_ids", []) if reference not in corpus_by_id})
    if bad_expected_ids:
        errors.append(f"Evaluation queries reference missing records: {bad_expected_ids}")
    checks["evaluation_reference_validation"] = {"passed": not bad_expected_ids, "missing_record_ids": bad_expected_ids}

    present_families = {record.get("subject_family") for record in corpus if record.get("subject_family")}
    missing_families = sorted(SUBJECT_FAMILIES - present_families)
    present_levels = {level for record in corpus for level in record.get("educational_level", [])}
    missing_levels = sorted({"school", "university"} - present_levels)
    if missing_families:
        errors.append(f"Missing subject-family coverage: {missing_families}")
    if missing_levels:
        errors.append(f"Missing educational-level coverage: {missing_levels}")
    checks["subject_family_coverage"] = {"passed": not missing_families, "missing": missing_families}
    checks["educational_level_coverage"] = {"passed": not missing_levels, "missing": missing_levels}

    used_sources = {source_id for record in corpus for source_id in record["source_ids"]}
    used_source_types = {row["source_type"] for row in source_rows if row["source_id"] in used_sources}
    source_coverage_ok = len(used_source_types) >= 6 and len(used_sources) >= 15
    if not source_coverage_ok:
        errors.append("Source-family coverage is too narrow")
    checks["source_family_coverage"] = {"passed": source_coverage_ok, "source_count": len(used_sources), "source_type_count": len(used_source_types), "source_types": sorted(used_source_types)}

    family_file_errors: list[str] = []
    for family, filename in FAMILY_FILES.items():
        family_records = read_jsonl(processed_dir / filename)
        expected = [record for record in corpus if record["document_family"] == family]
        if family_records != expected:
            family_file_errors.append(family)
    if family_file_errors:
        errors.append(f"Family files do not match corpus slices: {family_file_errors}")
    checks["family_file_consistency"] = {"passed": not family_file_errors, "invalid_families": family_file_errors}

    if check_determinism:
        deterministic, hashes = _validate_determinism(project_root)
        if not deterministic:
            errors.append("Repeated dataset builds produced different output")
        checks["reproducible_deterministic_build"] = {"passed": deterministic, "sha256": hashes}
    else:
        checks["reproducible_deterministic_build"] = {"passed": True, "details": "Skipped by caller; tested separately."}

    report = {
        "dataset_version": DATASET_VERSION,
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "summary": {
            "retrievable_record_count": len(corpus),
            "evaluation_query_count": len(evaluations),
            "document_family_counts": dict(sorted(Counter(record["document_family"] for record in corpus).items())),
            "canonical_record_count": sum(not record["synthetic"] for record in corpus),
            "synthetic_record_count": sum(record["synthetic"] for record in corpus),
            "reviewed_record_count": sum(record["reviewed"] for record in corpus),
            "unreviewed_record_count": sum(not record["reviewed"] for record in corpus),
            "source_count": len(source_rows),
            "sources_used_count": len(used_sources),
        },
    }
    if write_report:
        write_json(processed_dir / "validation_report.json", report)
    return report
