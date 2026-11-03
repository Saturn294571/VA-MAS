"""Offline checks for lifecycle tracing; no Minecraft server or API calls."""

import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tracer import TRACE_ENV, Tracer, safe_emit, summarize, trace_scope


def write_events(directory, worker):
    tracer = Tracer(directory)
    for index in range(40):
        tracer.emit("BA", "fixture", agent_id=f"worker-{worker}", request_id=str(index))


class TracerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name) / "run"
        self.directory = self.run / "trace"
        self.tracer = Tracer(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def read_events(self):
        return [json.loads(line) for line in (self.directory / "events.jsonl").read_text().splitlines()]

    def test_process_writes_are_not_lost_or_interleaved(self):
        processes = [multiprocessing.Process(target=write_events, args=(str(self.directory), i))
                     for i in range(4)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(10)
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(len(self.read_events()), 160)

    def test_scope_summary_and_interrupted_line(self):
        with self.tracer.span("BA", "task.execute", task_id="t1", agent_id="Alice"):
            with trace_scope(decision_id="d1"):
                safe_emit(self.tracer, "BA", "llm.request.end", result_status="ok",
                          prompt_tokens=3, completion_tokens=0, cost_usd=0.1,
                          request_id="r1", prompt="secret", api_key="secret")
        with (self.directory / "events.jsonl").open("a") as output:
            output.write('{"partial":')
        summary = summarize(self.directory, "recovered")
        self.assertEqual(summary["invalid_lines"], 1)
        self.assertEqual(summary["llm_usage_by_component"]["BA"]["completion_tokens"], 0)
        raw = (self.directory / "events.jsonl").read_text()
        self.assertNotIn("secret", raw)
        self.assertIn('"decision_id": "d1"', raw)
        self.assertTrue((self.run / "summary.json").exists())

    def test_google_request_and_tool_guard_use_common_context(self):
        from env.action_policy import guarded_tools, make_action_context
        from langchain_core.tools import StructuredTool
        from model.google_model import GoogleLanguageModel, DEFAULT_GEMINI_MODEL

        calls = []
        def fixture_tool(player_name: str, x: int) -> dict:
            """Move fixture agent."""
            calls.append(x)
            return {"status": True}
        tool = StructuredTool.from_function(func=fixture_tool)
        context = make_action_context("Alice", {"id": "t1"}, {}, [tool], 1)
        events = []
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"), finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=4, completion_tokens=0, total_tokens=4,
                                  completion_tokens_details=None),
        )
        with patch.dict(os.environ, {TRACE_ENV: str(self.directory)}):
            with tempfile.TemporaryDirectory() as runtime:
                original_cwd = os.getcwd()
                try:
                    os.chdir(runtime)
                    model = GoogleLanguageModel(api_key="offline", api_model=DEFAULT_GEMINI_MODEL)
                    model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
                        create=lambda **kwargs: response)))
                    with self.tracer.span("BA", "task.execute", task_id="t1", agent_id="Alice"):
                        with trace_scope(decision_id="actor1"):
                            self.assertEqual(model.few_shot_generate_thoughts("system", "prompt", cache_enabled=False), "ok")
                            guarded = guarded_tools(context, [tool], events)[0]
                            self.assertTrue(guarded.run({"player_name": "Alice", "x": 3})["status"])
                            self.assertFalse(guarded.run({"player_name": "Bob", "x": 4})["status"])
                finally:
                    os.chdir(original_cwd)
        self.assertEqual(calls, [3])
        records = self.read_events()
        model_event = next(event for event in records if event["event"] == "llm.request.end")
        self.assertEqual((model_event["task_id"], model_event["decision_id"]), ("t1", "actor1"))
        self.assertEqual(model_event["completion_tokens"], 0)
        self.assertEqual(sum(e["event"] == "action.execute.end" for e in records), 1)
        self.assertNotIn("offline", (self.directory / "events.jsonl").read_text())

    def test_actor_callback_records_success_and_error(self):
        from model.google_model import create_google_chat_model, DEFAULT_GEMINI_MODEL

        with patch.dict(os.environ, {TRACE_ENV: str(self.directory)}):
            with tempfile.TemporaryDirectory() as runtime:
                original_cwd = os.getcwd()
                try:
                    os.chdir(runtime)
                    actor = create_google_chat_model(api_key="offline", api_model=DEFAULT_GEMINI_MODEL,
                                                     actor_name="Alice")
                    callback = actor.callbacks[0]
                    response = SimpleNamespace(generations=[], llm_output={
                        "token_usage": {"prompt_tokens": 5, "completion_tokens": 2},
                        "finish_reason": "stop"})
                    with self.tracer.span("BA", "task.execute", task_id="t1", agent_id="Alice"):
                        with trace_scope(decision_id="d1"):
                            callback.on_chat_model_start({}, [], run_id="success")
                            callback.on_llm_end(response, run_id="success")
                            callback.on_chat_model_start({}, [], run_id="failure")
                            callback.on_llm_error(TimeoutError(), run_id="failure")
                finally:
                    os.chdir(original_cwd)
        ended = [event for event in self.read_events() if event["event"] == "llm.request.end"]
        self.assertEqual([e["result_status"] for e in ended], ["ok", "error"])
        self.assertEqual(ended[0]["decision_id"], "d1")
        self.assertEqual(ended[1]["error_type"], "TimeoutError")


if __name__ == "__main__":
    unittest.main()
