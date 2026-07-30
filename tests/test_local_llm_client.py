"""Tests for the standard-library local Ollama HTTP client."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib import error

from src.local_llm_client import LocalLLMClient, OllamaUnavailableError


class FakeHTTPResponse:
    def __init__(self, values: dict) -> None:
        self.payload = json.dumps(values).encode("utf-8")

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class LocalLLMClientTests(unittest.TestCase):
    def test_rejects_non_local_base_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be local"):
            LocalLLMClient(base_url="https://example.com", model_name="qwen3:4b-instruct")

    @patch("src.local_llm_client.request.urlopen")
    def test_generate_sends_required_deterministic_structured_options(self, mocked) -> None:
        mocked.return_value = FakeHTTPResponse(
            {"model": "qwen3:4b-instruct", "message": {"content": "{}"}, "eval_count": 1}
        )
        client = LocalLLMClient(
            base_url="http://127.0.0.1:11434",
            model_name="qwen3:4b-instruct",
            temperature=0,
            context_size=4096,
        )
        schema = {"type": "object", "additionalProperties": False}
        response = client.generate(system_instruction="system", user_prompt="user", output_schema=schema)
        sent = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(sent["stream"])
        self.assertEqual(sent["format"], schema)
        self.assertEqual(sent["options"], {"temperature": 0, "num_ctx": 4096})
        self.assertEqual(sent["model"], "qwen3:4b-instruct")
        self.assertEqual(response.content, "{}")

    @patch("src.local_llm_client.request.urlopen")
    def test_unavailable_api_raises_specific_error(self, mocked) -> None:
        mocked.side_effect = error.URLError("offline")
        client = LocalLLMClient(
            base_url="http://localhost:11434", model_name="qwen3:4b-instruct"
        )
        with self.assertRaises(OllamaUnavailableError):
            client.api_version()

    @patch("src.local_llm_client.request.urlopen")
    def test_api_version_parsing(self, mocked) -> None:
        mocked.return_value = FakeHTTPResponse({"version": "1.2.3"})
        client = LocalLLMClient(
            base_url="http://localhost:11434", model_name="qwen3:4b-instruct"
        )
        self.assertEqual(client.api_version(), "1.2.3")


if __name__ == "__main__":
    unittest.main()
