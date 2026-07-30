"""Deterministic builder for the ErgoStudy Stage 3 knowledge corpus.

Record IDs are human-readable slugs made from stable seed keys and a ``v1``
revision suffix. Wording changes do not regenerate an ID. A meaning change must
receive a new revision in the reviewed seed data.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.dataset_io import read_json, read_jsonl, read_source_catalog, write_json, write_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_VERSION = "1.0.0-prototype"
FAMILY_FILES = {
    "subject_profile": "subject_profiles.jsonl",
    "topic_profile": "topic_profiles.jsonl",
    "study_strategy": "study_strategies.jsonl",
    "session_template": "session_templates.jsonl",
    "sensor_intervention": "sensor_interventions.jsonl",
    "subject_alias": "subject_aliases.jsonl",
}

FAMILY_DEFAULTS = {
    "mathematics": {
        "activities": ["explain concepts and notation", "compare worked examples", "solve and check problems", "justify method choices"],
        "characteristics": ["theory", "practice", "problem_solving"],
    },
    "natural_sciences": {
        "activities": ["connect models with observations", "interpret representations and data", "solve or explain problems", "review evidence and limitations"],
        "characteristics": ["theory", "practice", "problem_solving", "laboratory"],
    },
    "language_and_literature": {
        "activities": ["read purposefully", "build and retrieve vocabulary", "analyze language or texts", "write and revise responses"],
        "characteristics": ["theory", "memorization", "reading", "writing"],
    },
    "social_sciences": {
        "activities": ["compare explanations", "analyze sources and evidence", "organize concepts and cases", "write supported arguments"],
        "characteristics": ["theory", "memorization", "reading", "writing"],
    },
    "computing": {
        "activities": ["trace and explain code", "write small working programs", "test and debug", "justify algorithms or designs"],
        "characteristics": ["theory", "practice", "problem_solving", "coding", "design"],
    },
    "engineering": {
        "activities": ["apply mathematics and science", "analyze constraints", "model or prototype solutions", "test and evaluate trade-offs"],
        "characteristics": ["theory", "practice", "problem_solving", "laboratory", "design"],
    },
    "health_sciences": {
        "activities": ["learn terminology and mechanisms", "interpret educational cases", "connect evidence to explanations", "practise safe professional reasoning"],
        "characteristics": ["theory", "memorization", "reading", "problem_solving"],
    },
    "business_and_economics": {
        "activities": ["interpret concepts and data", "solve quantitative examples", "analyze cases and decisions", "explain assumptions and trade-offs"],
        "characteristics": ["theory", "practice", "problem_solving", "reading", "writing"],
    },
    "arts_and_design": {
        "activities": ["research examples and context", "generate alternatives", "make or prototype work", "critique and revise against criteria"],
        "characteristics": ["theory", "practice", "reading", "writing", "design"],
    },
    "law": {
        "activities": ["identify relevant facts and issues", "read authorities carefully", "apply rules to a case", "write and evaluate reasoned arguments"],
        "characteristics": ["theory", "memorization", "reading", "writing", "problem_solving"],
    },
    "general": {
        "activities": ["set a specific learning goal", "practise the target performance", "check understanding", "record a next step"],
        "characteristics": ["theory", "practice"],
    },
}

TASK_METHODS = {
    "theory_learning": ["retrieval_practice", "self_explanation", "spaced_review"],
    "memorization": ["retrieval_practice", "spaced_review", "feedback"],
    "reading_comprehension": ["purposeful_reading", "section_summaries", "self_explanation"],
    "writing": ["model_practice_reflect", "drafting", "criteria_based_revision"],
    "problem_solving": ["worked_examples", "independent_practice", "error_checking"],
    "coding": ["code_tracing", "small_programs", "testing_and_feedback"],
    "debugging": ["reproduce_trace_hypothesize", "single_change_tests", "explain_the_fix"],
    "laboratory": ["pre_lab_questions", "procedure_and_safety_review", "data_interpretation"],
    "design": ["requirements_analysis", "alternative_generation", "prototype_test_revision"],
    "case_analysis": ["fact_issue_mapping", "rule_or_framework_application", "reasoned_conclusion"],
    "mixed": ["goal_decomposition", "active_practice", "feedback_and_reflection"],
}

TASK_DESCRIPTIONS = {
    "theory_learning": "build and explain connected concepts rather than only rereading",
    "memorization": "produce the target information from memory and correct errors",
    "reading_comprehension": "identify the reading purpose, main claims, evidence, and a concise summary",
    "writing": "produce text, compare it with criteria or feedback, and revise",
    "problem_solving": "select a method, carry out the steps, and check the result",
    "coding": "predict, write, run, test, and explain executable code",
    "debugging": "reproduce a fault, trace state, test a cause hypothesis, and explain the correction",
    "laboratory": "prepare the procedure, record observations, interpret data, and note limitations",
    "design": "define requirements, compare alternatives, create a prototype, and evaluate it",
    "case_analysis": "separate facts and issues, apply a relevant framework, and justify a conclusion",
    "mixed": "divide the topic into clear sub-tasks and practise each required performance",
}


def slugify(value: str) -> str:
    """Create a stable ASCII slug suitable for record IDs."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def stable_record_id(prefix: str, *parts: str, revision: int = 1) -> str:
    """Build a stable, readable ID from reviewed seed keys."""
    components = [slugify(part) for part in parts if slugify(part)]
    return f"{prefix}-{'-'.join(components)}-v{revision}"


def _level_key(levels: list[str]) -> str:
    return "cross-level" if len(levels) > 1 or levels == ["cross_level"] else levels[0]


def _base_record(family: str, record_id: str, title: str, source_ids: list[str], *,
                 evidence_level: str, review_tier: str, safety_scope: str = "none") -> dict[str, Any]:
    return {
        "record_id": record_id,
        "document_family": family,
        "title": title,
        "evidence_level": evidence_level,
        "source_ids": source_ids,
        "safety_scope": safety_scope,
        "synthetic": False,
        "reviewed": True,
        "review_tier": review_tier,
        "dataset_version": DATASET_VERSION,
    }


def _build_subjects(seed: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in seed["subject_groups"]:
        defaults = FAMILY_DEFAULTS[group["subject_family"]]
        for item in group["subjects"]:
            subject = {"name": item} if isinstance(item, str) else item
            levels = subject.get("educational_level", group["educational_level"])
            aliases = subject.get("aliases", [])
            activities = subject.get("activities", defaults["activities"])
            characteristics = subject.get("characteristics", defaults["characteristics"])
            name = subject["name"]
            alias_text = f" Common names include {', '.join(aliases)}." if aliases else ""
            focus_note = f" {subject['focus_note']}" if subject.get("focus_note") else ""
            activity_text = "; ".join(activities)
            retrieval_text = (
                f"Subject profile: {name} belongs to the curriculum-neutral {group['subject_family'].replace('_', ' ')} family."
                f"{alias_text} A useful study plan should match the learner's current topic and required task, because the subject name alone does not determine personal difficulty. "
                f"Typical learning activities are to {activity_text}.{focus_note} Methods should be chosen from the topic's real learning task and checked against course expectations. "
                "This profile describes common educational work without fixing a particular curriculum, course sequence, assessment, or study duration."
            )
            record = _base_record(
                "subject_profile",
                stable_record_id("subject", subject.get("key", name), _level_key(levels)),
                f"{name} subject profile",
                subject.get("source_ids", group["source_ids"]),
                evidence_level="source_descriptive",
                review_tier="tier_b",
            )
            record.update({
                "retrieval_text": retrieval_text,
                "educational_level": levels,
                "subject_family": group["subject_family"],
                "subject_name": name,
                "aliases": aliases,
                "typical_learning_activities": activities,
                "characteristics": characteristics,
            })
            records.append(record)
    return records


def _build_topics(seed: dict[str, Any], subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subject_by_name = {record["subject_name"].casefold(): record for record in subjects}
    records: list[dict[str, Any]] = []
    for group in seed["topic_groups"]:
        parent = subject_by_name[group["subject_name"].casefold()]
        for topic in group["topics"]:
            task = topic["learning_task"]
            methods = topic.get("recommended_methods", TASK_METHODS[task])
            focus_note = f" {topic['focus_note']}" if topic.get("focus_note") else ""
            task_description = topic.get("task_description", TASK_DESCRIPTIONS[task])
            retrieval_text = (
                f"Topic profile: {topic['name']} is studied within {group['subject_name']} and is classified here as a {task.replace('_', ' ')} task. "
                f"The practical goal is to {task_description}. Suitable methods include {', '.join(method.replace('_', ' ') for method in methods)}.{focus_note} "
                "The learner should finish by checking an answer, explanation, product, or decision against available feedback. Course notes, assignments, or teacher guidance remain the authority for required content and conventions. "
                "This curriculum-neutral mapping selects a learning task; it does not teach course-specific content or assign personal difficulty."
            )
            record = _base_record(
                "topic_profile",
                topic.get("record_id") or stable_record_id("topic", topic.get("key", topic["name"]), slugify(group["subject_name"])),
                f"{topic['name']} in {group['subject_name']}",
                topic.get("source_ids", group.get("source_ids", parent["source_ids"])),
                evidence_level=topic.get("evidence_level", "source_descriptive"),
                review_tier="tier_b",
            )
            record.update({
                "retrieval_text": retrieval_text,
                "educational_level": group.get("educational_level", parent["educational_level"]),
                "subject_family": parent["subject_family"],
                "subject_name": group["subject_name"],
                "topic": topic["name"],
                "learning_task": task,
                "cognitive_demand": topic["cognitive_demand"],
                "recommended_methods": methods,
                "related_subject_record_ids": [parent["record_id"]],
            })
            records.append(record)
    return records


def _build_strategies(seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in seed:
        guidance = "; ".join(item["implementation_guidance"])
        limitation = "; ".join(item["limitations"])
        retrieval_text = (
            f"Study strategy: {item['title']}. {item['summary']} Practical use: {guidance}. "
            f"Limits: {limitation}. Select this method only when it practises the target learning task, and use feedback where it is available."
        )
        record = _base_record(
            "study_strategy", stable_record_id("strategy", item["key"]), item["title"], item["source_ids"],
            evidence_level=item["evidence_level"], review_tier="tier_a",
        )
        record.update({key: value for key, value in item.items() if key not in {"key", "summary", "source_ids", "evidence_level", "title"}})
        record["retrieval_text"] = retrieval_text
        records.append(record)
    return records


def _build_sessions(seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in seed:
        phase_text = "; ".join(item["phases"])
        retrieval_text = (
            f"Session template proposal: {item['title']}. Use these phases: {phase_text}. The proposed focus range is "
            f"{item['session_duration_min']} to {item['session_duration_max']} minutes, followed by a {item['break_duration_min']} to {item['break_duration_max']} minute break. "
            "These bounded values are versioned planner design parameters for later user testing, not universal scientific facts. The learner may pause early when needed. "
            "A future planner may fit the phases to the time available without dropping the final check."
        )
        record = _base_record(
            "session_template", stable_record_id("session", item["key"]), item["title"], item["source_ids"],
            evidence_level="design_proposal", review_tier="tier_b",
        )
        record.update({key: value for key, value in item.items() if key not in {"key", "source_ids", "title"}})
        record["retrieval_text"] = retrieval_text
        record["duration_status"] = "design_proposal_requires_evaluation"
        record.setdefault("sensor_mode", "sensor_optional")
        records.append(record)
    return records


def _build_sensors(seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in seed:
        actions = "; ".join(item["intervention"])
        retrieval_text = (
            f"Non-medical sensor response: {item['title']}. Condition: {item['sensor_condition'].rstrip('.')}. Safe response: {actions}. "
            f"If data is unavailable or unreliable: {item['missing_data_behavior'].rstrip('.')}. This record does not diagnose posture, injury, or health. "
            "No hardware unit, sampling rate, calibration rule, or scientifically confirmed threshold is assumed; the hardware contract and deterministic trigger configuration must be confirmed before use."
        )
        record = _base_record(
            "sensor_intervention", stable_record_id("sensor", item["key"]), item["title"], item["source_ids"],
            evidence_level=item.get("evidence_level", "expert_consensus"), review_tier="tier_a",
            safety_scope=item.get("safety_scope", "non_medical_wellbeing"),
        )
        record.update({key: value for key, value in item.items() if key not in {"key", "source_ids", "title", "evidence_level", "safety_scope"}})
        record.update({"retrieval_text": retrieval_text, "hardware_confirmation_required": True, "sensor_mode": "sensor_optional"})
        records.append(record)
    return records


def _build_aliases(subjects: list[dict[str, Any]], seed: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[tuple[str, dict[str, Any], str]] = []
    globally_seen: set[str] = set()
    explicit = {item["alias"].casefold(): item for item in seed.get("explicit_aliases", [])}
    for subject in sorted(subjects, key=lambda record: record["record_id"]):
        reviewed_aliases = list(subject["aliases"])
        variants = reviewed_aliases + [f"{subject['subject_name']} course", f"{subject['subject_name']} studies"]
        for variant in variants:
            normalized = variant.casefold().strip()
            if normalized == subject["subject_name"].casefold() or normalized in globally_seen:
                continue
            if variant not in reviewed_aliases:
                variant_tokens = set(slugify(variant).split("-"))
                if any(len(variant_tokens ^ set(slugify(alias).split("-"))) <= 1 for alias in reviewed_aliases):
                    continue
            globally_seen.add(normalized)
            method = "reviewed_subject_alias" if variant in reviewed_aliases else "deterministic_course_name_variant"
            candidates.append((variant, subject, method))
    for item in seed.get("explicit_aliases", []):
        normalized = item["alias"].casefold().strip()
        if normalized in globally_seen:
            continue
        parent = next(record for record in subjects if record["subject_name"] == item["subject_name"])
        globally_seen.add(normalized)
        candidates.append((item["alias"], parent, item.get("generation_method", "reviewed_spelling_or_abbreviation_variant")))

    target = seed["target_count"]
    if len(candidates) < target:
        raise ValueError(f"Only {len(candidates)} unique alias candidates for target {target}")
    reviewed_variants = sorted(
        (candidate for candidate in candidates if candidate[2] != "deterministic_course_name_variant"),
        key=lambda value: (value[1]["subject_family"], value[1]["subject_name"], value[0].casefold()),
    )
    generated_by_family: defaultdict[str, list[tuple[str, dict[str, Any], str]]] = defaultdict(list)
    for candidate in candidates:
        if candidate[2] == "deterministic_course_name_variant":
            generated_by_family[candidate[1]["subject_family"]].append(candidate)
    for family in generated_by_family:
        generated_by_family[family].sort(key=lambda value: (value[1]["subject_name"], value[0].casefold()))
    selected = reviewed_variants[:target]
    while len(selected) < target:
        made_progress = False
        for family in sorted(generated_by_family):
            if generated_by_family[family] and len(selected) < target:
                selected.append(generated_by_family[family].pop(0))
                made_progress = True
        if not made_progress:
            break
    family_positions: defaultdict[str, int] = defaultdict(int)
    records: list[dict[str, Any]] = []
    for alias, parent, method in selected:
        family_positions[parent["subject_family"]] += 1
        explicit_item = explicit.get(alias.casefold(), {})
        ambiguous = bool(explicit_item.get("ambiguous", False))
        ambiguity_notes = explicit_item.get("ambiguity_notes") if ambiguous else None
        sample_reviewed = (
            (family_positions[parent["subject_family"]] - 1) % 10 == 0
            or ambiguous
            or method == "reviewed_common_misspelling"
        )
        retrieval_text = (
            f"Subject alias mapping: {alias} can refer to {parent['subject_name']} in the {parent['subject_family'].replace('_', ' ')} subject family. "
            f"Use this controlled name variant for exact or semantic matching, then retrieve the canonical subject profile and topic-specific guidance. "
            + (f"The alias is context-sensitive: {ambiguity_notes} " if ambiguous else "The mapping is unambiguous in ordinary educational subject-name context. ")
            + "This synthetic mapping inherits its reviewed parent's sources and introduces no new learning or safety claim."
        )
        record = {
            "record_id": stable_record_id("alias", parent["subject_name"], alias),
            "document_family": "subject_alias",
            "title": f"{alias} alias for {parent['subject_name']}",
            "retrieval_text": retrieval_text,
            "educational_level": parent["educational_level"],
            "subject_family": parent["subject_family"],
            "subject_name": parent["subject_name"],
            "aliases": [alias],
            "matching_notes": "Controlled exact and semantic subject-name variant; confirm topic context when ambiguity is flagged.",
            "ambiguous": ambiguous,
            "ambiguity_notes": ambiguity_notes,
            "canonical_subject_record_id": parent["record_id"],
            "related_subject_record_ids": [parent["record_id"]],
            "evidence_level": parent["evidence_level"],
            "source_ids": parent["source_ids"],
            "safety_scope": "none",
            "synthetic": True,
            "reviewed": sample_reviewed,
            "review_tier": "tier_c",
            "generation_method": method,
            "derived_from_record_id": parent["record_id"],
            "derived_from_record_ids": [parent["record_id"]],
            "dataset_version": DATASET_VERSION,
        }
        records.append(record)
    return records


def _build_evaluation_queries(seed_path: Path, subjects: list[dict[str, Any]], aliases: list[dict[str, Any]], target: int = 96) -> list[dict[str, Any]]:
    seed_queries = read_jsonl(seed_path)
    queries: list[dict[str, Any]] = []
    for seed in seed_queries:
        query_number = int(seed["query_id"].split("-")[1])
        record = dict(seed)
        record.update({
            "record_id": stable_record_id("eval", str(query_number)),
            "document_family": "retrieval_evaluation_query",
            "dataset_version": DATASET_VERSION,
        })
        queries.append(record)

    templates = [
        ("I am taking {subject}; what kind of learning work should I plan?", "exact_name", ["subject_profile"]),
        ("Help me choose active practice for my {subject} course.", "method_selection", ["subject_profile", "study_strategy"]),
        ("I have a university topic in {subject} and need task-specific guidance.", "university_level", ["subject_profile", "topic_profile"]),
        ("How should I structure one focused block for {subject} without assuming an ideal timer?", "session_structure", ["subject_profile", "session_template"]),
        ("This custom subject is called {subject}; map it before deciding how hard it is.", "unseen_wording", ["subject_profile", "subject_alias"]),
    ]
    next_number = max(int(query["query_id"].split("-")[1]) for query in queries) + 1
    alias_cases = [
        record for record in aliases
        if record["generation_method"] == "reviewed_common_misspelling" or record["ambiguous"]
    ]
    for alias_record in sorted(alias_cases, key=lambda record: record["record_id"]):
        alias_text = alias_record["aliases"][0]
        case_kind = "ambiguous" if alias_record["ambiguous"] else "alias"
        criteria = (
            f"Use context to map {alias_text} to {alias_record['subject_name']} without silently forcing an interpretation when the wording remains ambiguous."
            if alias_record["ambiguous"]
            else f"Resolve the controlled misspelling {alias_text} to {alias_record['subject_name']} and return its canonical subject profile."
        )
        queries.append({
            "record_id": stable_record_id("eval", str(next_number)),
            "document_family": "retrieval_evaluation_query",
            "dataset_version": DATASET_VERSION,
            "query_id": f"rq-{next_number:03d}",
            "query_text": f"I need to study {alias_text} this afternoon.",
            "expected_document_families": ["subject_alias", "subject_profile"],
            "expected_subject_family": alias_record["subject_family"],
            "expected_relevant_record_ids": [alias_record["record_id"], alias_record["canonical_subject_record_id"]],
            "relevance_criteria": criteria,
            "difficulty_type": case_kind,
            "notes": "Held-out ambiguous-alias case." if alias_record["ambiguous"] else "Held-out controlled misspelling case.",
        })
        next_number += 1

    school_subjects = [
        subject for subject in subjects
        if "school" in subject["educational_level"] and subject["subject_family"] in {
            "mathematics", "natural_sciences", "language_and_literature", "social_sciences"
        }
    ]
    used_school_families: set[str] = set()
    for subject in school_subjects:
        if subject["subject_family"] in used_school_families:
            continue
        used_school_families.add(subject["subject_family"])
        queries.append({
            "record_id": stable_record_id("eval", str(next_number)),
            "document_family": "retrieval_evaluation_query",
            "dataset_version": DATASET_VERSION,
            "query_id": f"rq-{next_number:03d}",
            "query_text": f"I am a secondary-school student revising {subject['subject_name']}; keep the guidance at school level.",
            "expected_document_families": ["subject_profile", "topic_profile"],
            "expected_subject_family": subject["subject_family"],
            "expected_relevant_record_ids": [subject["record_id"]],
            "relevance_criteria": "Retrieve school-compatible records and avoid assuming a university-only curriculum or assigning fixed personal difficulty.",
            "difficulty_type": "school_level",
            "notes": "Held-out school-level metadata-filtering case.",
        })
        next_number += 1

    subject_index = 0
    while len(queries) < target:
        subject = subjects[subject_index % len(subjects)]
        template, difficulty, families = templates[subject_index % len(templates)]
        query_text = template.format(subject=subject["subject_name"])
        queries.append({
            "record_id": stable_record_id("eval", str(next_number)),
            "document_family": "retrieval_evaluation_query",
            "dataset_version": DATASET_VERSION,
            "query_id": f"rq-{next_number:03d}",
            "query_text": query_text,
            "expected_document_families": families,
            "expected_subject_family": subject["subject_family"],
            "expected_relevant_record_ids": [subject["record_id"]],
            "relevance_criteria": "Resolve the curriculum-neutral subject and return task-appropriate records without assigning fixed personal difficulty or a universal session duration.",
            "difficulty_type": difficulty,
            "notes": "Held-out controlled query with wording that is not copied from retrieval text.",
        })
        next_number += 1
        subject_index += 1
    return queries


def build_dataset(project_root: Path = PROJECT_ROOT, output_dir: Path | None = None) -> dict[str, Any]:
    """Build all Stage 3 processed files and return dataset statistics."""
    raw_dir = project_root / "data" / "raw"
    processed_dir = output_dir or project_root / "data" / "processed"
    sources = read_source_catalog(project_root / "data" / "sources" / "source_catalog.csv")
    source_ids = {row["source_id"] for row in sources}

    subjects = _build_subjects(read_json(raw_dir / "subject_seed_data.json"))
    topics = _build_topics(read_json(raw_dir / "topic_seed_data.json"), subjects)
    strategies = _build_strategies(read_json(raw_dir / "study_strategy_seed.json"))
    sessions = _build_sessions(read_json(raw_dir / "session_template_seed.json"))
    sensors = _build_sensors(read_json(raw_dir / "sensor_intervention_seed.json"))
    aliases = _build_aliases(subjects, read_json(raw_dir / "alias_seed_data.json"))

    by_family = {
        "subject_profile": subjects,
        "topic_profile": topics,
        "study_strategy": strategies,
        "session_template": sessions,
        "sensor_intervention": sensors,
        "subject_alias": aliases,
    }
    corpus = [record for family in FAMILY_FILES for record in by_family[family]]
    corpus_ids = [record["record_id"] for record in corpus]
    if len(corpus_ids) != len(set(corpus_ids)):
        raise ValueError("Dataset builder produced duplicate record IDs")
    unknown_sources = sorted({source for record in corpus for source in record["source_ids"] if source not in source_ids})
    if unknown_sources:
        raise ValueError(f"Seed data references unknown sources: {unknown_sources}")

    for family, filename in FAMILY_FILES.items():
        write_jsonl(processed_dir / filename, by_family[family])
    write_jsonl(processed_dir / "knowledge_corpus.jsonl", corpus)
    evaluation_queries = _build_evaluation_queries(
        project_root / "data" / "interim" / "retrieval_evaluation_seed.jsonl", subjects, aliases
    )
    write_jsonl(processed_dir / "retrieval_evaluation_queries.jsonl", evaluation_queries)

    family_counts = {family: len(records) for family, records in by_family.items()}
    subject_family_counts = Counter(record.get("subject_family") or "not_applicable" for record in corpus)
    level_counts: Counter[str] = Counter()
    for record in corpus:
        level_counts.update(record.get("educational_level", []))
    statistics = {
        "dataset_version": DATASET_VERSION,
        "retrievable_record_count": len(corpus),
        "evaluation_query_count": len(evaluation_queries),
        "canonical_record_count": sum(not record["synthetic"] for record in corpus),
        "synthetic_record_count": sum(record["synthetic"] for record in corpus),
        "reviewed_record_count": sum(record["reviewed"] for record in corpus),
        "unreviewed_record_count": sum(not record["reviewed"] for record in corpus),
        "document_family_counts": family_counts,
        "subject_family_counts": dict(sorted(subject_family_counts.items(), key=lambda item: str(item[0]))),
        "educational_level_counts": dict(sorted(level_counts.items())),
        "source_catalog_count": len(sources),
        "sources_used_count": len({source for record in corpus for source in record["source_ids"]}),
        "source_role_counts": dict(sorted(Counter(row["source_role"] for row in sources).items())),
        "tier_c_record_count": sum(record["review_tier"] == "tier_c" for record in corpus),
        "tier_c_reviewed_sample_count": sum(record["review_tier"] == "tier_c" and record["reviewed"] for record in corpus),
    }
    write_json(processed_dir / "dataset_statistics.json", statistics)
    return statistics
