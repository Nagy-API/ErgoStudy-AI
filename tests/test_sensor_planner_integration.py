"""Integration tests between the Stage 6A planner and Stage 6B sensor adapter."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.daily_planner import DailyPlanner
from src.sensor_adapter import SensorPlanAdapter
from tests.planner_fakes import FakeRetrievalService


ROOT = Path(__file__).resolve().parents[1]


class SensorPlannerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = DailyPlanner(ROOT, retrieval_service=FakeRetrievalService())
        self.adapter = SensorPlanAdapter(ROOT)
        self.plan = self.planner.plan(
            {
                "total_available_minutes": 120,
                "preferred_start_time": "09:00",
                "subjects": [
                    {
                        "name": "Mathematics",
                        "topics": ["Equations"],
                        "difficulty": 5,
                        "priority": 5,
                        "workload": 4,
                        "current_understanding": 2,
                    },
                    {
                        "name": "Physics",
                        "topics": ["Forces"],
                        "difficulty": 4,
                        "priority": 4,
                        "workload": 3,
                        "current_understanding": 3,
                    },
                ],
            }
        )

    def test_planner_output_adapts_without_academic_changes(self) -> None:
        result = self.adapter.adapt(
            self.plan,
            {
                "sensor_enabled": True,
                "connection_status": "connected",
                "observation_status": "valid",
                "continuous_sitting_minutes": 65,
                "poor_posture_duration_minutes": 12,
                "posture_direction": "leaning_right",
                "pressure_imbalance_detected": True,
                "reading_age_seconds": 5,
            },
        )
        self.assertEqual(result.original_plan_id, self.plan.plan_id)
        self.assertLessEqual(result.total_planned_minutes, self.plan.total_available_minutes)
        original_studies = [item.to_dict() for item in self.plan.sessions if item.session_type == "study"]
        adapted_studies = [item for item in result.sessions if item["session_type"] == "study"]
        self.assertEqual(len(original_studies), len(adapted_studies))
        for original, adapted in zip(original_studies, adapted_studies):
            for key in (
                "subject",
                "topic",
                "cognitive_demand",
                "recommended_methods",
                "retrieved_record_ids",
                "used_fallback",
                "reason",
            ):
                self.assertEqual(adapted[key], original[key])

    def test_non_sensor_fallback_preserves_complete_planner_output_timeline(self) -> None:
        result = self.adapter.adapt(
            self.plan,
            {
                "sensor_enabled": True,
                "connection_status": "disconnected",
                "observation_status": "missing",
            },
        )
        self.assertEqual(list(result.sessions), [item.to_dict() for item in self.plan.sessions])
        self.assertEqual(result.total_study_minutes, self.plan.total_study_minutes)
        self.assertEqual(result.total_break_minutes, self.plan.total_break_minutes)


if __name__ == "__main__":
    unittest.main()
