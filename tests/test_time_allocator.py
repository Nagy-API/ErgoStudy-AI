"""Tests for selection, proportional allocation, and bounded splitting."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.planner_config import default_planner_config
from src.planner_models import SubjectInput
from src.subject_scoring import score_subjects
from src.time_allocator import allocate_study_minutes, select_schedulable_subjects, split_session_minutes


ROOT = Path(__file__).resolve().parents[1]


class TimeAllocatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_planner_config(ROOT)
        subjects = (
            SubjectInput("Mathematics", 5, 5, 5, 1),
            SubjectInput("History", 2, 2, 2, 4),
            SubjectInput("Art", 1, 1, 1, 5),
        )
        self.scored = score_subjects(subjects, self.config)

    def test_short_time_selects_only_highest_subject(self) -> None:
        selected, omitted = select_schedulable_subjects(self.scored, 45, self.config)
        self.assertEqual([item.subject.name for item in selected], ["Mathematics"])
        self.assertEqual(len(omitted), 2)

    def test_extra_minutes_follow_scores_and_sum_exactly(self) -> None:
        selected, _ = select_schedulable_subjects(self.scored, 180, self.config)
        allocations = allocate_study_minutes(selected, 160, 40, self.config)
        self.assertEqual(sum(item.study_minutes for item in allocations), 160)
        self.assertGreater(allocations[0].study_minutes, allocations[-1].study_minutes)

    def test_all_split_durations_respect_bounds(self) -> None:
        for total in range(20, 301):
            durations = split_session_minutes(total, 40, self.config)
            self.assertEqual(sum(durations), total)
            self.assertTrue(all(20 <= value <= 60 for value in durations))


if __name__ == "__main__":
    unittest.main()
