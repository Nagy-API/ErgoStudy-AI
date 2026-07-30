"""Tests for the configurable planning heuristic."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.planner_config import default_planner_config
from src.planner_models import SubjectInput
from src.subject_scoring import score_subject


ROOT = Path(__file__).resolve().parents[1]


class SubjectScoringTests(unittest.TestCase):
    def test_weighted_score_and_gap_are_exact(self) -> None:
        subject = SubjectInput("Calculus", 5, 5, 4, 1)
        result = score_subject(subject, default_planner_config(ROOT))
        self.assertEqual(result.knowledge_gap, 5)
        self.assertAlmostEqual(result.score, 4.75)
        self.assertEqual(result.cognitive_demand, "high")
        self.assertIn("high priority", result.reason)
        self.assertIn("large knowledge gap", result.reason)

    def test_lower_inputs_produce_lower_score(self) -> None:
        config = default_planner_config(ROOT)
        lower = score_subject(SubjectInput("Art", 1, 1, 1, 5), config)
        higher = score_subject(SubjectInput("Art", 3, 4, 3, 2), config)
        self.assertLess(lower.score, higher.score)
        self.assertEqual(lower.cognitive_demand, "low")


if __name__ == "__main__":
    unittest.main()
