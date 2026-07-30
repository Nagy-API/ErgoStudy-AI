"""Unit tests for model-specific embedding formatting and normalization."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from src.embedding_models import load_embedding_configurations, normalize_rows


ROOT = Path(__file__).resolve().parents[1]


class EmbeddingPreprocessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, configurations = load_embedding_configurations(ROOT / "config" / "embedding_models.json")
        cls.by_id = {item.config_id: item for item in configurations}

    def test_plain_models_leave_text_unchanged(self) -> None:
        text = "Find debugging guidance."
        for config_id in ("minilm_plain", "bge_small_plain"):
            config = self.by_id[config_id]
            self.assertEqual(config.format_query(text), text)
            self.assertEqual(config.format_document(text), text)

    def test_bge_instruction_applies_only_to_query(self) -> None:
        config = self.by_id["bge_small_instruction"]
        self.assertEqual(
            config.format_query("debugging"),
            "Represent this sentence for searching relevant passages: debugging",
        )
        self.assertEqual(config.format_document("debugging"), "debugging")

    def test_e5_prefixes_queries_and_passages(self) -> None:
        config = self.by_id["e5_small_prefix"]
        self.assertEqual(config.format_query("debugging"), "query: debugging")
        self.assertEqual(config.format_document("debugging"), "passage: debugging")

    def test_normalize_rows_returns_float32_unit_vectors(self) -> None:
        result = normalize_rows(np.array([[3.0, 4.0], [0.0, 2.0]], dtype=np.float64))
        self.assertEqual(result.dtype, np.float32)
        np.testing.assert_allclose(np.linalg.norm(result, axis=1), np.ones(2), atol=1e-6)

    def test_normalize_rows_rejects_zero_vector(self) -> None:
        with self.assertRaises(ValueError):
            normalize_rows(np.zeros((1, 2), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
