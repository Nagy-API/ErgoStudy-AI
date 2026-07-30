"""Tests for deterministic ordering, breaks, and clock calculations."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.knowledge_adapter import SubjectKnowledge
from src.planner_config import default_planner_config
from src.planner_models import SubjectInput
from src.session_scheduler import schedule_sessions
from src.subject_scoring import SubjectScore
from src.time_allocator import SubjectAllocation


ROOT = Path(__file__).resolve().parents[1]


class SessionSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_planner_config(ROOT)
        self.high = SubjectScore(SubjectInput("Calculus", 5, 5, 5, 1, ("Integration",)), 5.0, 5, "high", "High need.")
        self.low = SubjectScore(SubjectInput("Art", 1, 2, 2, 4), 2.0, 2, "low", "Balanced need.")
        self.knowledge = {
            "Calculus": SubjectKnowledge("Calculus", ("worked examples",), ("subject-calculus",), (), False),
            "Art": SubjectKnowledge("Art", ("guided practice",), ("subject-art",), (), False),
        }

    def test_lower_demand_interrupts_high_demand_when_possible(self) -> None:
        allocations = (
            SubjectAllocation(self.high, 80, (40, 40)),
            SubjectAllocation(self.low, 40, (40,)),
        )
        timeline = schedule_sessions(allocations, self.knowledge, "16:00", self.config)
        study = [item for item in timeline.sessions if item.session_type == "study"]
        self.assertEqual([item.subject for item in study], ["Calculus", "Art", "Calculus"])
        self.assertEqual(timeline.sessions[0].start_time, "16:00")
        self.assertEqual(timeline.sessions[1].duration_minutes, 10)

    def test_missing_start_time_keeps_all_times_null(self) -> None:
        timeline = schedule_sessions(
            (SubjectAllocation(self.low, 40, (40,)),), self.knowledge, None, self.config
        )
        self.assertTrue(all(item.start_time is None for item in timeline.sessions))

    def test_invalid_clock_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            schedule_sessions((SubjectAllocation(self.low, 40, (40,)),), self.knowledge, "25:10", self.config)


if __name__ == "__main__":
    unittest.main()
