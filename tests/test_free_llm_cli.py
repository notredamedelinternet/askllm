import os
import unittest
from unittest import mock

from src import free_llm_cli


class ProviderTests(unittest.TestCase):
    def test_available_providers_uses_environment(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "test"}, clear=True):
            self.assertEqual(free_llm_cli.available_providers(), ["groq"])

    def test_choose_provider_requires_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                free_llm_cli.choose_provider("openai")

    def test_parse_openai_compatible_response(self):
        payload = {"choices": [{"message": {"content": " hello "}}]}
        self.assertEqual(free_llm_cli._parse_chat_completions(payload), "hello")

    def test_parse_anthropic_response(self):
        payload = {"content": [{"type": "text", "text": "hi"}, {"type": "tool_use"}]}
        self.assertEqual(free_llm_cli._parse_anthropic(payload), "hi")

    def test_parse_gemini_response(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]}
        self.assertEqual(free_llm_cli._parse_gemini(payload), "a\nb")


if __name__ == "__main__":
    unittest.main()
