"""Offline behavior checks for dependency boundaries and legacy execution compatibility."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import Mock, patch

from model.utils import extract_info as model_extract
from pipeline.utils import extract_info as pipeline_extract
from pipeline.controller import GlobalController as Full
from pipeline.controller_tiny import GlobalController as Tiny
from type_define.graph import Graph, Task


class StructureChecks(unittest.TestCase):
    def test_parser_compatibility_and_redacted_errors(self):
        fixtures = [
            ('prefix {"description": "a", "ok": True} suffix', [{"description": "a", "ok": True}]),
            ('{"wrapper": {"description": "a"}}', [{"description": "a"}]),
            ('{"description": "a" "n": 2}', [{"description": "a", "n": 2}]),
            ("{description: yaml}", [{"description": "yaml"}]),
            ('{"x": 1}', []),
            ('no object', []),
        ]
        for text, expected in fixtures:
            for parser in [model_extract, pipeline_extract]:
                with self.subTest(parser=parser.__module__, text=text):
                    self.assertEqual(parser(text, ["description"]), expected)
        secret = '{"description": "secret-token", broken: [}'
        with self.assertLogs(level="WARNING") as logs:
            self.assertEqual(model_extract(secret, ["description"]), [])
            with self.assertRaises(AttributeError):
                pipeline_extract(secret, ["description"])
        self.assertNotIn("secret-token", "\n".join(logs.output))
        # Pipeline recovers from bad YAML and can continue; model aborts the batch.
        with self.assertLogs(level="WARNING"):
            self.assertEqual(pipeline_extract('{x: [} {"description": "later"}'), [{"description": "later"}])
            self.assertEqual(model_extract('{x: [} {"description": "later"}'), [])

    def test_default_imports_without_optional_sdks_or_runtime_files(self):
        script = '''import importlib.abc, sys
from pathlib import Path
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        blocked = {"torch", "transformers", "FlagEmbedding", "chromadb", "zhipuai", "gymnasium", "fastapi", "uvicorn", "optimum", "auto_gptq", "mistralai", "dashscope"}
        if fullname.split(".")[0] in blocked or fullname in {"model.huggingface_model", "model.vllm_model", "model.zhipu_model"}:
            raise ModuleNotFoundError("blocked optional package", name=fullname)
sys.meta_path.insert(0, Block())
import model.init_model, start_with_config, env.utils, rl_env
assert not any(Path(p).exists() for p in ["data", ".cache", "logs", "result"])
try:
    env.utils.split_structure([])
except ImportError as exc:
    assert "requirements/construction.txt" in str(exc)
else:
    raise AssertionError("missing Construction dependency was not reported")
try:
    rl_env.PPO
except ImportError as exc:
    assert "requirements/rl.txt" in str(exc)
else:
    raise AssertionError("missing RL dependency was not reported")
try:
    model.init_model.init_language_model({"api_model": "unsupported-hf"})
except ImportError as exc:
    assert "requirements/huggingface.txt" in str(exc)
else:
    raise AssertionError("missing HF dependency was not reported")
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", "-c", script], cwd=directory,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_judger_utils_direct_script_import(self):
        repo = Path(__file__).resolve().parents[1]
        script = """import sys
from pathlib import Path
repo = Path.cwd()
sys.path = [str(repo / 'env')] + [p for p in sys.path if p and Path(p).resolve() != repo]
import utils
assert utils.init_logger.__module__ == 'common.logging'
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=repo,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_data_manager_document_conversion_keeps_metadata(self):
        from pipeline.data_manager import DataManager
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "documents.json"
            source.write_text(json.dumps([{"content": "fixture", "tag": "task"}]))
            docs = DataManager.json2documents(str(source))
            self.assertEqual(docs[0].page_content, "fixture")
            self.assertEqual(docs[0].metadata, {"tag": "task"})
            self.assertEqual(DataManager.json2documents(str(source.with_name("missing.json"))), [])

    def test_factory_dispatch_does_not_load_other_adapters(self):
        from model.init_model import init_language_model
        adapters = {"google_model": "GoogleLanguageModel", "openai_models": "OpenAILanguageModel",
                    "zhipu_model": "ZhipuLanguageModel", "huggingface_model": "HFLanguageModel",
                    "vllm_model": "VLLMLanguageModel", "ollama_model": "OllamaLanguageModel"}
        modules = {}
        for module, name in adapters.items():
            fake = ModuleType("model." + module)
            setattr(fake, name, lambda _module=module, **args: (_module, args))
            modules["model." + module] = fake
        cases = [("gemini-x", "google_model"), ("qwen-x", "openai_models"),
                 ("glm-x", "zhipu_model"), ("llama-x", "vllm_model"),
                 ("local-hf", "huggingface_model"), ("qwen3.8:27b", "ollama_model")]
        with patch.dict(sys.modules, modules):
            for model, expected in cases:
                args = {"api_model": model, "role_name": "fixture"}
                original = dict(args)
                self.assertEqual(init_language_model(args)[0], expected)
                self.assertEqual(args, original)

    def controller(self, cls):
        ctrl = cls.__new__(cls)
        ctrl._initialize_execution(1)
        ctrl.executor.shutdown()
        ctrl.logger = logging.getLogger("controller-fixture")
        ctrl.env = SimpleNamespace(agents_ping=lambda: {"status": True})
        ctrl.start_time = 0
        ctrl.max_execution_time = 100
        ctrl.stop_after_fail_times = 3
        ctrl.stop_after_success_times = 10
        return ctrl

    def test_full_and_tiny_keep_distinct_queue_shutdown_behavior(self):
        for cls, expected in [(Full, 1), (Tiny, 2)]:
            ctrl = self.controller(cls)
            agent = SimpleNamespace(name="Alice", step=lambda task: None)
            tasks = [Task("first", {}), Task("second", {})]
            ctrl.task_queue = [(agent, task) for task in tasks]
            def submit(*args):
                ctrl.shutdown = True
                return "future"
            ctrl.executor = SimpleNamespace(submit=Mock(side_effect=submit))
            with patch("time.time", return_value=1), patch("time.sleep") as sleep:
                ctrl.worker()
            self.assertEqual(len(ctrl.result_queue), expected)
            self.assertEqual(ctrl.executor.submit.call_count, expected)
            self.assertEqual(sleep.call_count, 1 if cls is Full else 0)
            self.assertEqual([entry[2] for entry in ctrl.result_queue], tasks[:expected])

    def test_full_time_and_failure_limits_and_offline_effects(self):
        for field, value in [("max_execution_time", 0), ("stop_after_fail_times", 0),
                             ("stop_after_success_times", 0)]:
            ctrl = self.controller(Full)
            setattr(ctrl, field, value)
            ctrl.env.agents_ping = Mock(side_effect=AssertionError("should stop before ping"))
            with patch("time.time", return_value=1):
                ctrl.worker()
        for cls in [Full, Tiny]:
            ctrl = self.controller(cls)
            ctrl.env.agents_ping = lambda: {"status": False}
            with patch("time.time", return_value=1):
                ctrl.worker()
            self.assertTrue(ctrl.shutdown)
            self.assertEqual(ctrl.max_execution_time, 0 if cls is Full else 100)

    def test_task_status_and_interrupt_cleanup(self):
        for cls in [Full, Tiny]:
            ctrl = self.controller(cls)
            task = Task("fixture", {})
            graph = Graph()
            graph.add_node(task)
            ctrl.task_manager = SimpleNamespace(graph=graph)
            ctrl.data_manager = object()
            ctrl.set_task_status(task.id, Task.running, "first")
            self.assertIs(ctrl.get_task_by_id(task.id), task)
            ctrl.set_task_status(task.id, Task.success, "second")
            self.assertEqual(task.reflect, ["first", "second"])
            ctrl.set_task_status(task.id, Task.failure, "last")
            self.assertEqual(task.status, Task.failure)
            self.assertEqual(task.reflect, ["first", "second", "last"])
            ctrl.executor = Mock()
            ctrl.execute_tasks = Mock()
            ctrl.process_completed_tasks = Mock()
            thread = Mock()
            thread.start.side_effect = KeyboardInterrupt
            with patch("pipeline.controller_execution.threading.Thread", return_value=thread):
                with self.assertRaisesRegex(Exception, "Interrupted by user"):
                    ctrl.run()
            self.assertTrue(ctrl.shutdown)
            self.assertIsNone(ctrl.task_manager)
            self.assertIsNone(ctrl.data_manager)
            ctrl.executor.shutdown.assert_called_once_with(wait=False)

    def test_google_and_ollama_share_accounting_without_changing_schema(self):
        import os
        from model.google_model import _TOKEN_FILE_LOCK, _record_token_usage
        from model.ollama_model import _TOKEN_FILE_LOCK as local_lock, _record_local_usage
        self.assertIs(_TOKEN_FILE_LOCK, local_lock)
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                _record_token_usage({"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
                                    "gemini-3.8-flash", "low")
                _record_local_usage("fixture", 3, 1)
                _record_local_usage("fixture", None, None)
                data = json.loads(Path("data/tokens.json").read_text())
                self.assertEqual((data["tokens_used"], data["successful_requests"]), (10, 3))
                self.assertEqual(data["total_cost"], (4 * .75 + 2 * 3.75) / 1_000_000)
                self.assertIsNone(data["model_usage"]["ollama/fixture"]["cost_usd"])
                self.assertEqual(data["model_usage"]["ollama/fixture"]["missing_usage"], 1)
            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main()
