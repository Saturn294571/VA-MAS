"""Offline request and pricing checks for the Gemini 3.1 Flash-Lite smoke model."""
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from model.google_model import GoogleLanguageModel, create_google_chat_model, _validate_model_settings

MODEL = "gemini-3.1-flash-lite"


class FlashLiteChecks(unittest.TestCase):
    def test_default_thinking_level_and_actor_request_settings(self):
        self.assertEqual(_validate_model_settings(MODEL, None), "minimal")
        actor = create_google_chat_model(api_model=MODEL, api_key="offline-fixture",
                                         thinking_level="minimal", max_tokens=1024)
        self.assertEqual(actor.model_name, MODEL)
        self.assertEqual(actor.model_kwargs["extra_body"]["reasoning_effort"], "minimal")

    def test_control_request_model_and_pricing_metadata(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                model = GoogleLanguageModel(api_model=MODEL, api_key="offline-fixture")
                create = Mock(return_value=SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="OK"), finish_reason="stop")],
                    usage=SimpleNamespace(prompt_tokens=4, completion_tokens=2, total_tokens=6,
                                          completion_tokens_details=None)))
                model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
                self.assertEqual(model.few_shot_generate_thoughts("fixture", "reply", cache_enabled=False), "OK")
                self.assertEqual(create.call_args.kwargs["model"], MODEL)
                self.assertEqual(create.call_args.kwargs["extra_body"], {"reasoning_effort": "minimal"})
                tokens = json.loads(Path("data/tokens.json").read_text())
                usage = tokens["model_usage"][MODEL]
                self.assertAlmostEqual(usage["cost_usd"], (4 * .25 + 2 * 1.5) / 1_000_000)
                self.assertEqual(usage["pricing_as_of"], "2026-11-04")
                self.assertEqual(usage["requests"], 1)
            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main()
