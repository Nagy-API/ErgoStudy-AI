"""Tests for non-oracle deterministic query analysis."""

from __future__ import annotations

import unittest

from src.alias_resolver import AliasResolver, normalize_query
from src.query_analyzer import QueryAnalyzer


RECORDS = [
    {
        "record_id": "subject-mathematics",
        "document_family": "subject_profile",
        "subject_name": "Mathematics",
        "aliases": ["Maths"],
    }
]


class QueryAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = QueryAnalyzer(AliasResolver(RECORDS))

    def test_query_normalization(self) -> None:
        self.assertEqual(normalize_query("  A&P---Revision!  "), "a and p revision")
        self.assertEqual(normalize_query("MATHS\t equations"), "maths equations")

    def test_detects_subject_alias_and_strategy_signals(self) -> None:
        analysis = self.analyzer.analyze("What is a useful way to study Maths equations?")
        self.assertIn("alias_lookup", analysis.intents)
        self.assertIn("subject_lookup", analysis.intents)
        self.assertIn("topic_lookup", analysis.intents)
        self.assertEqual(analysis.alias_resolution.resolved_subject_record_ids, ("subject-mathematics",))

    def test_detects_session_intent(self) -> None:
        session = self.analyzer.analyze("Give me a study session with a short break")
        self.assertEqual(session.primary_intent, "session_template")
        self.assertIn("session_template", session.suggested_document_families)

    def test_empty_query_is_invalid(self) -> None:
        analysis = self.analyzer.analyze(" \n ")
        self.assertEqual(analysis.primary_intent, "invalid")
        self.assertFalse(analysis.intents)


if __name__ == "__main__":
    unittest.main()
