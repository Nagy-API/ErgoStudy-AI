"""Fast unit tests for RetrievalService behavior and schema."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import numpy as np

import src.alias_resolver
import src.query_analyzer
import src.retriever
from src.retriever import RetrievalService, cosine_distance_to_similarity, intent_configuration
from src.retrieval_models import RetrievalResult


def _record(record_id: str, family: str, subject: str, title: str, **extra: object) -> dict:
    return {
        "record_id": record_id,
        "title": title,
        "retrieval_text": title,
        "document_family": family,
        "subject_family": subject,
        "subject_name": extra.pop("subject_name", None),
        "aliases": extra.pop("aliases", []),
        "source_ids": ["source-test"],
        **extra,
    }


RECORDS = [
    _record("a-topic", "topic_profile", "general", "General study topic"),
    _record("b-strategy", "study_strategy", "not_applicable", "Active recall guidance"),
    _record("c-math", "subject_profile", "mathematics", "Mathematics profile", subject_name="Mathematics", aliases=["Maths"]),
]


class FakeModel:
    def encode(self, texts: list[str], **_: object) -> np.ndarray:
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)


class FakeCollection:
    def count(self) -> int:
        return 3

    def query(self, *, where=None, **_: object) -> dict:
        ids = ["a-topic", "b-strategy", "c-math"]
        distances = [0.10, 0.11, 0.30]
        if where:
            clauses = where.get("$and", [where])
            expected_family = next((clause["document_family"] for clause in clauses if "document_family" in clause), None)
            if expected_family:
                kept = [index for index, record_id in enumerate(ids) if next(r for r in RECORDS if r["record_id"] == record_id)["document_family"] == expected_family]
                ids = [ids[index] for index in kept]
                distances = [distances[index] for index in kept]
        return {"ids": [ids], "distances": [distances], "documents": [[]], "metadatas": [[]]}

    def get(self, *, ids: list[str], **_: object) -> dict:
        embeddings = [[0.7, 0.7141428] for _ in ids]
        return {"ids": ids, "embeddings": embeddings}


class RetrievalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RetrievalService(
            Path(__file__).resolve().parents[1],
            configuration=intent_configuration(),
            model=FakeModel(),
            collection=FakeCollection(),
            records=RECORDS,
        )

    def test_empty_and_invalid_queries_are_safe(self) -> None:
        self.assertEqual(self.service.retrieve(""), [])
        self.assertEqual(self.service.retrieve(None), [])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.service.retrieve("valid", top_k=0)

    def test_cosine_distance_conversion(self) -> None:
        self.assertAlmostEqual(cosine_distance_to_similarity(0.25), 0.75)
        result = self.service.retrieve("plain semantic lookup", top_k=1)[0]
        self.assertAlmostEqual(result.score, 0.90)

    def test_intent_blending_and_deterministic_ordering(self) -> None:
        first = self.service.retrieve("active recall study method", top_k=3)
        second = self.service.retrieve("active recall study method", top_k=3)
        self.assertEqual([item.record_id for item in first], [item.record_id for item in second])
        self.assertEqual(first[0].record_id, "b-strategy")

    def test_metadata_filter_and_structured_schema(self) -> None:
        results = self.service.retrieve("study", top_k=3, metadata_filters={"document_family": "study_strategy"})
        self.assertEqual([item.record_id for item in results], ["b-strategy"])
        self.assertIsInstance(results[0], RetrievalResult)
        self.assertEqual(
            set(results[0].to_dict()),
            {"record_id", "title", "retrieval_text", "document_family", "subject_family", "score", "metadata"},
        )
        self.assertEqual(results[0].metadata["source_ids"], ["source-test"])
        with self.assertRaises(ValueError):
            self.service.retrieve("study", metadata_filters={"not_indexed": "value"})

    def test_retrieval_modules_do_not_contain_evaluation_labels(self) -> None:
        sources = "\n".join(inspect.getsource(module) for module in (src.alias_resolver, src.query_analyzer, src.retriever))
        self.assertNotIn("expected_relevant", sources)
        self.assertNotIn("expected_document", sources)
        self.assertNotIn("difficulty_type", sources)
        self.assertNotIn("rq-", sources)


if __name__ == "__main__":
    unittest.main()
