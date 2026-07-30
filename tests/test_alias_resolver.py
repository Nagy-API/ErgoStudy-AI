"""Tests for exact controlled alias resolution and ambiguity preservation."""

from __future__ import annotations

import unittest

from src.alias_resolver import AliasResolver


RECORDS = [
    {
        "record_id": "subject-mathematics",
        "document_family": "subject_profile",
        "subject_name": "Mathematics",
        "aliases": ["Maths"],
    },
    {
        "record_id": "subject-computer-science",
        "document_family": "subject_profile",
        "subject_name": "Computer Science",
        "aliases": ["CS"],
    },
    {
        "record_id": "alias-computer-science-cs",
        "document_family": "subject_alias",
        "aliases": ["CS"],
        "canonical_subject_record_id": "subject-computer-science",
        "related_subject_record_ids": ["subject-computer-science"],
        "ambiguous": True,
    },
]


class AliasResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = AliasResolver(RECORDS)

    def test_exact_subject_name_inside_plain_query(self) -> None:
        result = self.resolver.resolve("Help me revise Computer Science today")
        self.assertIn("subject-computer-science", result.resolved_subject_record_ids)
        self.assertTrue(any(match.match_kind == "subject_name" for match in result.matches))

    def test_exact_alias_matching_is_case_and_punctuation_safe(self) -> None:
        result = self.resolver.resolve("MATHS: revision")
        self.assertEqual(result.resolved_subject_record_ids, ("subject-mathematics",))

    def test_ambiguous_alias_is_not_silently_resolved(self) -> None:
        result = self.resolver.resolve("Tell me about CS")
        self.assertTrue(result.has_ambiguity)
        self.assertNotIn("subject-computer-science", result.resolved_subject_record_ids)

    def test_ambiguous_alias_can_use_explicit_education_context(self) -> None:
        result = self.resolver.resolve("CS course revision")
        self.assertFalse(result.has_ambiguity)
        self.assertIn("subject-computer-science", result.resolved_subject_record_ids)

    def test_no_substring_false_positive(self) -> None:
        self.assertFalse(self.resolver.resolve("mathematical reasoning").matches)


if __name__ == "__main__":
    unittest.main()
