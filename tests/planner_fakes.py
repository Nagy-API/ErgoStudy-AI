"""Small retrieval fake shared by planner unit tests."""

from __future__ import annotations

from src.alias_resolver import AliasResolver
from src.query_analyzer import QueryAnalyzer
from src.retrieval_models import RetrievalResult


RECORDS = [
    {
        "record_id": "subject-mathematics-test-v1",
        "document_family": "subject_profile",
        "subject_family": "mathematics",
        "subject_name": "Mathematics",
        "aliases": ["Maths"],
        "title": "Mathematics profile",
    },
    {
        "record_id": "subject-computer-science-test-v1",
        "document_family": "subject_profile",
        "subject_family": "computing",
        "subject_name": "Computer Science",
        "aliases": ["CS"],
        "title": "Computer Science profile",
    },
    {
        "record_id": "alias-computer-science-cs-test-v1",
        "document_family": "subject_alias",
        "subject_family": "computing",
        "subject_name": "Computer Science",
        "aliases": ["CS"],
        "canonical_subject_record_id": "subject-computer-science-test-v1",
        "related_subject_record_ids": ["subject-computer-science-test-v1"],
        "ambiguous": True,
        "title": "CS alias",
    },
    {
        "record_id": "topic-equations-test-v1",
        "document_family": "topic_profile",
        "subject_family": "mathematics",
        "subject_name": "Mathematics",
        "topic": "Equations",
        "recommended_methods": ["worked_examples", "independent_practice"],
        "title": "Equations topic",
    },
    {
        "record_id": "strategy-retrieval-test-v1",
        "document_family": "study_strategy",
        "subject_family": "general",
        "recommended_methods": ["retrieval_practice", "feedback"],
        "title": "Retrieval practice",
    },
    {
        "record_id": "session-practice-test-v1",
        "document_family": "session_template",
        "subject_family": "general",
        "recommended_methods": ["guided_practice", "self_check"],
        "title": "Practice session",
    },
]


class FakeRetrievalService:
    def __init__(self) -> None:
        self.analyzer = QueryAnalyzer(AliasResolver(RECORDS))

    def analyze_query(self, query: str):
        return self.analyzer.analyze(query)

    def retrieve(self, query: str, *, top_k: int, metadata_filters: dict) -> list[RetrievalResult]:
        family = metadata_filters["document_family"]
        lowered = query.casefold()
        candidates = [record for record in RECORDS if record["document_family"] == family]
        if family == "subject_profile":
            if "computer science" in lowered or " cs" in f" {lowered}":
                candidates = [record for record in candidates if record["subject_family"] == "computing"]
            elif "math" in lowered:
                candidates = [record for record in candidates if record["subject_family"] == "mathematics"]
        if family == "topic_profile" and "equations" not in lowered:
            candidates = []
        return [
            RetrievalResult(
                record_id=record["record_id"],
                title=record["title"],
                retrieval_text=record["title"],
                document_family=record["document_family"],
                subject_family=record["subject_family"],
                score=0.9,
                metadata={key: value for key, value in record.items() if key not in {"record_id", "title", "document_family", "subject_family"}},
            )
            for record in candidates[:top_k]
        ]
