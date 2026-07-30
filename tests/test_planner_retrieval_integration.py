"""Planner checks against fake and persistent source-traceable retrieval."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import src.daily_planner
import src.knowledge_adapter
from src.daily_planner import DailyPlanner
from src.dataset_io import read_jsonl
from src.knowledge_adapter import KnowledgeAdapter
from src.planner_config import default_planner_config
from src.planner_models import SubjectInput
from src.retriever import RetrievalService
from src.retrieval_models import AliasMatch, AliasResolution, QueryAnalysis
from tests.planner_fakes import FakeRetrievalService


ROOT = Path(__file__).resolve().parents[1]


class PlannerRetrievalUnitTests(unittest.TestCase):
    def test_planned_record_ids_are_from_retrieval_results(self) -> None:
        planner = DailyPlanner(ROOT, retrieval_service=FakeRetrievalService())
        plan = planner.plan({
            "total_available_minutes": 90,
            "subjects": [{
                "name": "Mathematics",
                "topics": ["Equations"],
                "difficulty": 4,
                "priority": 5,
                "workload": 4,
                "current_understanding": 2,
            }],
        })
        record_ids = plan.sessions[0].retrieved_record_ids
        self.assertIn("subject-mathematics-test-v1", record_ids)
        self.assertIn("topic-equations-test-v1", record_ids)

    def test_planner_does_not_use_sealed_evaluation_fields(self) -> None:
        source = inspect.getsource(src.daily_planner) + inspect.getsource(src.knowledge_adapter)
        self.assertNotIn("expected_relevant", source)
        self.assertNotIn("retrieval_evaluation_queries", source)
        self.assertNotIn("final_test", source)

    def test_multi_subject_alias_uses_explicit_fallback(self) -> None:
        class AmbiguousService:
            def analyze_query(self, query: str) -> QueryAnalysis:
                resolution = AliasResolution(
                    "science",
                    (AliasMatch("science", "alias", ("subject-a", "subject-b"), ambiguous=True),),
                )
                return QueryAnalysis("study subject science", "alias_lookup", ("alias_lookup",), (), resolution)

            def retrieve(self, *args, **kwargs):
                raise AssertionError("ambiguous aliases must not be densely collapsed")

        adapter = KnowledgeAdapter(AmbiguousService(), default_planner_config(ROOT))
        result = adapter.retrieve(SubjectInput("Science", 3, 3, 3, 3))
        self.assertTrue(result.used_fallback)
        self.assertIn("ambiguous", result.warnings[0])


class PersistentPlannerRetrievalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = RetrievalService.from_frozen_config(ROOT, device="cpu")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.service.close()

    def test_existing_chroma_collection_produces_traceable_plan(self) -> None:
        planner = DailyPlanner(ROOT, retrieval_service=self.service)
        plan = planner.plan({
            "total_available_minutes": 120,
            "preferred_start_time": "14:00",
            "subjects": [{
                "name": "Stats",
                "topics": ["Probability"],
                "difficulty": 4,
                "priority": 5,
                "workload": 4,
                "current_understanding": 2,
            }],
        })
        corpus_ids = {row["record_id"] for row in read_jsonl(ROOT / "data" / "processed" / "knowledge_corpus.jsonl")}
        returned_ids = {record_id for session in plan.sessions for record_id in session.retrieved_record_ids}
        self.assertTrue(returned_ids)
        self.assertTrue(returned_ids.issubset(corpus_ids))
        self.assertEqual(plan.scheduled_subjects[0].canonical_subject, "Statistics")
        self.assertFalse(plan.scheduled_subjects[0].used_fallback)


if __name__ == "__main__":
    unittest.main()
