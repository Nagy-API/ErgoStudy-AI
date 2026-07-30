"""Translate source-traceable retrieval results into planner knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.alias_resolver import normalize_query
from src.planner_config import PlannerConfig
from src.planner_models import SubjectInput
from src.retrieval_models import RetrievalResult


@dataclass(frozen=True)
class SubjectKnowledge:
    canonical_subject: str | None
    recommended_methods: tuple[str, ...]
    retrieved_record_ids: tuple[str, ...]
    topic_record_ids: tuple[tuple[str, str], ...]
    used_fallback: bool
    warnings: tuple[str, ...] = ()


def _method_name(value: str) -> str:
    return " ".join(value.replace("_", " ").split())


def _unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


class KnowledgeAdapter:
    """Retrieve planner-safe profiles, strategies, and templates per subject."""

    def __init__(self, retrieval_service: Any | None, config: PlannerConfig) -> None:
        self.service = retrieval_service
        self.config = config

    def fallback(self, subject: SubjectInput, warning: str) -> SubjectKnowledge:
        return SubjectKnowledge(
            canonical_subject=None,
            recommended_methods=self.config.fallback_methods,
            retrieved_record_ids=(),
            topic_record_ids=(),
            used_fallback=True,
            warnings=(f"{subject.name}: {warning}",),
        )

    def retrieve(self, subject: SubjectInput) -> SubjectKnowledge:
        if self.service is None:
            return self.fallback(subject, "retrieval was unavailable; a generic session was used")
        try:
            return self._retrieve(subject)
        except Exception as error:  # retrieval failure must not prevent a safe plan
            return self.fallback(
                subject,
                f"retrieval was unavailable ({type(error).__name__}); a generic session was used",
            )

    def _retrieve(self, subject: SubjectInput) -> SubjectKnowledge:
        rules = self.config.retrieval
        analysis = self.service.analyze_query(f"study subject {subject.name}")
        subject_ids = analysis.alias_resolution.resolved_subject_record_ids
        if len(subject_ids) > 1:
            return self.fallback(subject, "the subject alias was ambiguous; a generic session was used")

        profiles = self.service.retrieve(
            f"subject profile for {subject.name}",
            top_k=rules.subject_top_k,
            metadata_filters={"document_family": "subject_profile"},
        )
        profile: RetrievalResult | None = None
        if len(subject_ids) == 1:
            profile = next((item for item in profiles if item.record_id == subject_ids[0]), None)
        elif profiles:
            candidate = profiles[0]
            candidate_name = normalize_query(str(candidate.metadata.get("subject_name", "")))
            input_name = normalize_query(subject.name)
            if candidate.score >= rules.minimum_similarity and (
                candidate_name in input_name or input_name in candidate_name
            ):
                profile = candidate
        if profile is None:
            return self.fallback(subject, "no reliable subject profile was found; a generic session was used")

        canonical = str(profile.metadata.get("subject_name") or subject.name)
        record_ids = [profile.record_id]
        topic_pairs: list[tuple[str, str]] = []
        methods: list[str] = []
        for topic in subject.topics:
            topic_results = self.service.retrieve(
                f"{topic} in {canonical}",
                top_k=rules.topic_top_k,
                metadata_filters={"document_family": "topic_profile"},
            )
            normalized_topic_tokens = set(normalize_query(topic).split())
            accepted = next(
                (
                    item
                    for item in topic_results
                    if item.score >= rules.minimum_similarity
                    and (item.subject_family == profile.subject_family or item.subject_family == "general")
                    and normalized_topic_tokens.intersection(
                        normalize_query(str(item.metadata.get("topic", ""))).split()
                    )
                ),
                None,
            )
            if accepted:
                topic_pairs.append((topic, accepted.record_id))
                record_ids.append(accepted.record_id)
                methods.extend(_method_name(value) for value in accepted.metadata.get("recommended_methods", []))

        strategy_results = self.service.retrieve(
            f"study methods for {canonical} {' '.join(subject.topics)}",
            top_k=rules.strategy_top_k,
            metadata_filters={"document_family": "study_strategy"},
        )
        for result in strategy_results:
            if result.score < rules.minimum_similarity:
                continue
            record_ids.append(result.record_id)
            methods.extend(_method_name(value) for value in result.metadata.get("recommended_methods", []))

        template_results = self.service.retrieve(
            f"study session template for {canonical} {' '.join(subject.topics)}",
            top_k=rules.template_top_k,
            metadata_filters={"document_family": "session_template"},
        )
        if template_results and template_results[0].score >= rules.minimum_similarity:
            template = template_results[0]
            record_ids.append(template.record_id)
            methods.extend(_method_name(value) for value in template.metadata.get("recommended_methods", []))

        unique_methods = _unique(methods)[: rules.maximum_methods_per_session]
        used_fallback = not unique_methods
        if used_fallback:
            unique_methods = self.config.fallback_methods
        warnings: list[str] = []
        if used_fallback:
            warnings.append(f"{subject.name}: retrieved profiles did not provide usable methods; generic methods were used")
        missing_topics = [topic for topic in subject.topics if topic not in dict(topic_pairs)]
        if missing_topics:
            warnings.append(f"{subject.name}: no reliable topic profile was found for {', '.join(missing_topics)}")
        return SubjectKnowledge(
            canonical_subject=canonical,
            recommended_methods=unique_methods,
            retrieved_record_ids=_unique(record_ids),
            topic_record_ids=tuple(topic_pairs),
            used_fallback=used_fallback,
            warnings=tuple(warnings),
        )
