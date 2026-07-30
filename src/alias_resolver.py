"""Exact normalized subject-name and controlled-alias resolution."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from src.retrieval_models import AliasMatch, AliasResolution


_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w]+", flags=re.UNICODE)
_EDUCATIONAL_CONTEXT = {
    "assignment",
    "class",
    "course",
    "exam",
    "homework",
    "learn",
    "lesson",
    "plan",
    "practice",
    "revision",
    "revise",
    "school",
    "study",
    "subject",
    "topic",
    "university",
}


def normalize_query(text: str) -> str:
    """Normalize case, whitespace, and punctuation without fuzzy matching.

    Ampersands are converted to the word ``and`` so controlled variants such
    as ``A&P`` and ``A and P`` share one exact normalized representation.
    Other punctuation becomes a word boundary; underscores are boundaries too.
    """
    if not isinstance(text, str):
        return ""
    value = unicodedata.normalize("NFKC", text).casefold().replace("&", " and ").replace("_", " ")
    value = _NON_WORD.sub(" ", value)
    return _WHITESPACE.sub(" ", value).strip()


def _contains_phrase(normalized_query: str, normalized_phrase: str) -> bool:
    query_tokens = normalized_query.split()
    phrase_tokens = normalized_phrase.split()
    if not phrase_tokens or len(phrase_tokens) > len(query_tokens):
        return False
    width = len(phrase_tokens)
    return any(query_tokens[index : index + width] == phrase_tokens for index in range(len(query_tokens) - width + 1))


@dataclass(frozen=True)
class _AliasEntry:
    text: str
    kind: str
    subject_record_ids: tuple[str, ...]
    alias_record_ids: tuple[str, ...]
    explicitly_ambiguous: bool


class AliasResolver:
    """Resolve controlled names exactly while preserving ambiguous aliases."""

    def __init__(self, records: Iterable[dict[str, Any]]) -> None:
        subject_names: dict[str, set[str]] = defaultdict(set)
        aliases: dict[str, dict[str, set[str] | bool]] = {}

        for record in records:
            family = record.get("document_family")
            if family == "subject_profile":
                subject_id = str(record["record_id"])
                name = normalize_query(str(record.get("subject_name", "")))
                if name:
                    subject_names[name].add(subject_id)
                for raw_alias in record.get("aliases", []):
                    self._add_alias(aliases, raw_alias, subject_id, None, False)
            elif family == "subject_alias":
                related = record.get("related_subject_record_ids") or []
                canonical = record.get("canonical_subject_record_id")
                subject_ids = [str(value) for value in related]
                if canonical and str(canonical) not in subject_ids:
                    subject_ids.append(str(canonical))
                for raw_alias in record.get("aliases", []):
                    for subject_id in subject_ids:
                        self._add_alias(
                            aliases,
                            raw_alias,
                            subject_id,
                            str(record["record_id"]),
                            bool(record.get("ambiguous")),
                        )

        entries: list[_AliasEntry] = []
        for text, subject_ids in subject_names.items():
            entries.append(_AliasEntry(text, "subject_name", tuple(sorted(subject_ids)), (), len(subject_ids) > 1))
        for text, values in aliases.items():
            alias_subject_ids = tuple(sorted(values["subjects"]))  # type: ignore[arg-type]
            alias_record_ids = tuple(sorted(values["records"]))  # type: ignore[arg-type]
            ambiguous = bool(values["ambiguous"]) or len(alias_subject_ids) != 1
            entries.append(_AliasEntry(text, "alias", alias_subject_ids, alias_record_ids, ambiguous))
        self._entries = tuple(sorted(entries, key=lambda item: (-len(item.text.split()), item.text, item.kind)))

    @staticmethod
    def _add_alias(
        aliases: dict[str, dict[str, set[str] | bool]],
        raw_alias: Any,
        subject_id: str,
        alias_record_id: str | None,
        ambiguous: bool,
    ) -> None:
        text = normalize_query(str(raw_alias))
        if not text:
            return
        values = aliases.setdefault(text, {"subjects": set(), "records": set(), "ambiguous": False})
        subjects = values["subjects"]
        records = values["records"]
        assert isinstance(subjects, set) and isinstance(records, set)
        subjects.add(subject_id)
        if alias_record_id:
            records.add(alias_record_id)
        values["ambiguous"] = bool(values["ambiguous"]) or ambiguous

    def resolve(self, query: str) -> AliasResolution:
        """Find exact token-phrase matches and resolve only safe meanings."""
        normalized = normalize_query(query)
        if not normalized:
            return AliasResolution(normalized_query="")
        query_tokens = set(normalized.split())
        has_educational_context = bool(query_tokens.intersection(_EDUCATIONAL_CONTEXT))
        matches: list[AliasMatch] = []
        covered_subject_ids: set[str] = set()
        for entry in self._entries:
            if not _contains_phrase(normalized, entry.text):
                continue
            if entry.kind == "alias" and set(entry.subject_record_ids).issubset(covered_subject_ids):
                continue
            ambiguous = entry.explicitly_ambiguous
            resolved = not ambiguous or entry.kind == "subject_name" or has_educational_context
            matches.append(
                AliasMatch(
                    matched_text=entry.text,
                    match_kind=entry.kind,
                    subject_record_ids=entry.subject_record_ids,
                    alias_record_ids=entry.alias_record_ids,
                    ambiguous=ambiguous,
                    resolved=resolved,
                )
            )
            if entry.kind == "subject_name":
                covered_subject_ids.update(entry.subject_record_ids)
        return AliasResolution(normalized_query=normalized, matches=tuple(matches))
