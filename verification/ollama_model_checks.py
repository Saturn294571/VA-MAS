"""Offline role-selection and local Ollama adapter checks."""

import json
import logging
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from langchain.agents import AgentType, initialize_agent
from langchain.tools import StructuredTool

from model.ollama_model import OllamaLanguageModel, _local_post, create_ollama_chat_model
from model.role_models import configure_actor_model, resolve_role_models, standalone_model_config
from tracer import TRACE_ENV, Tracer, summarize


class OllamaChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp.cleanup()

    @staticmethod
    def response(content):
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "done": True, "done_reason": "stop", "message": {"content": content},
            "prompt_eval_count": 12, "eval_count": 3, "load_duration": 1000000000,
            "prompt_eval_duration": 500000000, "eval_duration": 250000000,
        })

    def test_role_config_keeps_td_sm_and_rejects_remote(self):
        baseline = {"api_model": "gemini-3.8-flash", "api_key": "never-log"}
        roles = resolve_role_models({"ac": {"provider": "ollama"}, "ba": {"provider": "gemini"}}, baseline)
        self.assertEqual(roles["ac"]["api_model"], "qwen3.8:27b")
        self.assertEqual(roles["ba"]["api_model"], "gemini-3.8-flash")
        self.assertEqual(baseline["api_model"], "gemini-3.8-flash")
        self.assertNotIn("api_key", roles["ac"])
        reversed_roles = resolve_role_models({"ac": {"provider": "gemini"}, "ba": {"provider": "ollama"}}, baseline)
        self.assertEqual(reversed_roles["ac"]["api_model"], "gemini-3.8-flash")
        self.assertEqual(reversed_roles["ba"]["provider"], "ollama")
        with self.assertRaises(ValueError):
            resolve_role_models({"ba": {"provider": "ollama", "base_url": "http://example.com"}}, baseline)
        with self.assertRaises(ValueError):
            resolve_role_models({"unknown": {"provider": "ollama"}}, baseline)

    def test_shared_local_default_and_role_override(self):
        baseline = {"api_model": "gemini-3.8-flash"}
        all_api = resolve_role_models({"default": {"provider": "gemini"}}, baseline)
        self.assertTrue(all(role["provider"] == "gemini" and role["api_model"] == "gemini-3.8-flash"
                            for role in all_api.values()))
        all_local = resolve_role_models({"default": {"provider": "ollama"}}, baseline)
        self.assertEqual(set(all_local), {"td", "sm", "ac", "ba"})
        self.assertTrue(all(x["api_model"] == "qwen3.8:27b" and x["provider"] == "ollama"
                            for x in all_local.values()))
        mixed = resolve_role_models({"default": {"provider": "ollama"},
                                     "sm": {"provider": "gemini"}}, baseline)
        self.assertEqual(mixed["sm"]["provider"], "gemini")
        self.assertEqual(mixed["td"]["provider"], "ollama")

    def test_standalone_tools_default_to_gemini_with_explicit_local_override(self):
        import model.google_model as google
        from model.init_model import init_language_model
        with patch.dict(os.environ, {"VILLAGER_GENERATION_PROVIDER": "ollama"}, clear=True), \
             patch.object(google, "load_google_api_keys", side_effect=AssertionError("key access")):
            local = standalone_model_config()
            self.assertIsInstance(init_language_model({"api_model": "qwen3.8:27b"}), OllamaLanguageModel)
            actor = SimpleNamespace()
            configure_actor_model(actor, local)
            self.assertEqual((actor.model_provider, actor.model), ("ollama", "qwen3.8:27b"))
            self.assertEqual(actor.api_key_list, [])
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(google, "load_google_api_keys", return_value=["fixture"]):
            default = standalone_model_config()
            self.assertEqual(default["provider"], "gemini")
            self.assertEqual(default["api_model"], google.DEFAULT_GEMINI_MODEL)

    def test_construction_description_default_uses_gemini(self):
        import model.google_model as google
        from env.utils import describe_map
        fake = SimpleNamespace(few_shot_generate_thoughts=lambda *args, **kwargs: "[]")
        building = [[{"name": "stone", "facing": "A", "position": [0, 0, 0]},
                     {"name": "stone", "facing": "A", "position": [0, 1, 0]}]]
        with patch.dict(os.environ, {"VILLAGER_LOCAL_GENERATION_ONLY": "0"}, clear=True), \
             patch.object(google, "load_google_api_keys", return_value=["fixture"]), \
             patch("model.init_model.init_language_model", return_value=fake) as factory:
            self.assertEqual(describe_map(building), [[]])
        self.assertEqual(factory.call_args.args[0]["api_model"], google.DEFAULT_GEMINI_MODEL)

    def test_full_controller_all_roles_local(self):
        from pipeline.controller import GlobalController
        roles = resolve_role_models({"default": {"provider": "ollama"}},
                                    {"api_model": "gemini-3.8-flash"})
        def factory(config):
            return SimpleNamespace(role_name=config.get("role_name", ""), config=dict(config))
        class FakeAgent:
            def __init__(self, llm, env, data_manager, name, **kwargs):
                self.llm, self.name = llm, name
        env = SimpleNamespace(agent_pool=[SimpleNamespace(name="Alice")],
                              get_all_agent_description_tiny=lambda: {})
        with patch("pipeline.controller.init_language_model", side_effect=factory), \
             patch("pipeline.controller.BaseAgent", FakeAgent), \
             patch("pipeline.controller.init_logger", return_value=logging.getLogger("fixture")):
            tm, dm = SimpleNamespace(), SimpleNamespace()
            ctrl = GlobalController({"api_model": "gemini-3.8-flash"}, tm, dm, env,
                                    tm_llm_config=roles["td"], dm_llm_config=roles["sm"],
                                    ac_llm_config=roles["ac"], base_agent_config=roles["ba"])
            for model in (tm.llm, dm.llm, ctrl.llm, ctrl.agent_list[0].llm):
                self.assertEqual(model.config["api_model"], "qwen3.8:27b")
                self.assertEqual(model.config["provider"], "ollama")
            ctrl.executor.shutdown()

    def test_local_embedding_guard_blocks_remote_fallback(self):
        from pipeline.retriever import LocalOnlyEmbeddingGuard
        guard = LocalOnlyEmbeddingGuard()
        with self.assertRaisesRegex(RuntimeError, "not configured"):
            guard.embed_query("test")

    def test_construction_description_fallback_uses_local_model(self):
        from env.utils import describe_map
        fake = SimpleNamespace(few_shot_generate_thoughts=lambda *args, **kwargs: "[]")
        options = {"VILLAGER_LOCAL_GENERATION_ONLY": "1", "VILLAGER_LOCAL_MODEL": "qwen3.8:27b",
                   "VILLAGER_LOCAL_BASE_URL": "http://127.0.0.1:11434"}
        building = [[{"name": "stone", "facing": "A", "position": [0, 0, 0]},
                     {"name": "stone", "facing": "A", "position": [0, 1, 0]}]]
        with patch.dict(os.environ, options, clear=True), \
             patch("model.init_model.init_language_model", return_value=fake) as factory:
            self.assertEqual(describe_map(building), [[]])
        self.assertEqual(factory.call_args.args[0]["api_model"], "qwen3.8:27b")
        self.assertEqual(factory.call_args.args[0]["provider"], "ollama")

    def test_system_only_legacy_request_is_sent_as_user_message(self):
        model = OllamaLanguageModel()
        with patch("model.ollama_model._local_post", return_value=self.response("[]")) as post:
            self.assertEqual(model.few_shot_generate_thoughts("describe blueprint", cache_enabled=False), "[]")
        self.assertEqual(post.call_args.kwargs["payload"]["messages"],
                         [{"role": "user", "content": "describe blueprint"}])

    def test_local_http_ignores_environment_proxy(self):
        fake = SimpleNamespace(trust_env=True)
        fake.post = lambda url, **kwargs: fake.trust_env
        # Special methods are looked up on the class, not the instance.
        class Session:
            def __enter__(self): return fake
            def __exit__(self, *args): pass
        with patch("model.ollama_model.requests.Session", return_value=Session()):
            self.assertFalse(_local_post("http://127.0.0.1:11434/api/chat", payload={}, timeout=1))

    def test_launcher_main_does_not_load_keys_for_all_local(self):
        import model.google_model as google
        Path("result/existing").mkdir(parents=True)
        config = [{"task_name": "existing", "task_type": "construction", "controller_mode": "full",
                   "decision_policies": {"ba": "generative", "ac": "generative"},
                   "model_roles": {"default": {"provider": "ollama"}}}]
        Path("fixture.json").write_text(json.dumps(config))
        with patch.dict(os.environ, {"VILLAGER_BENCH_CONFIG_PATH": str(Path("fixture.json").resolve())}, clear=True), \
             patch.object(google, "load_google_api_keys", side_effect=AssertionError("key access")):
            runpy.run_path(str(Path(__file__).resolve().parents[1] / "start_with_config.py"), run_name="__main__")

    def test_control_model_native_options_usage_and_trace(self):
        tracer = Tracer(Path(self.temp.name) / "result" / "run" / "trace")
        model = OllamaLanguageModel(num_ctx=4096)
        with patch.dict(os.environ, {TRACE_ENV: str(tracer.directory)}), \
             patch("model.ollama_model._local_post", return_value=self.response('[{"task_id": 0, "agent": "Alice"}]')) as post:
            with tracer.span("AC", "assignment.select"):
                result = model.few_shot_generate_thoughts("system", "prompt", max_tokens=128,
                                                          json_check=True, cache_enabled=True)
                self.assertEqual(model.few_shot_generate_thoughts("system", "prompt", max_tokens=128,
                                                                  json_check=True, cache_enabled=True), result)
        self.assertEqual(post.call_count, 1)
        payload = post.call_args.kwargs["payload"]
        self.assertFalse(payload["think"])
        self.assertEqual(payload["options"]["num_ctx"], 4096)
        tokens = json.loads(Path("data/tokens.json").read_text())
        self.assertEqual(tokens["model_usage"]["ollama/qwen3.8:27b"]["requests"], 1)
        self.assertIsNone(tokens["model_usage"]["ollama/qwen3.8:27b"]["cost_usd"])
        summary = summarize(tracer.directory)
        self.assertEqual(summary["llm_usage_by_component"]["AC"]["unpriced_requests"], 1)

    def test_existing_react_executor_with_local_chat(self):
        calls = []
        def navigateTo(player_name: str, x: int) -> str:
            """Move an agent to x."""
            calls.append((player_name, x))
            return "arrived"
        tool = StructuredTool.from_function(func=navigateTo)
        responses = [self.response('```json\n{"action":"navigateTo","action_input":{"player_name":"Alice","x":1}}\n```'),
                     self.response('```json\n{"action":"Final Answer","action_input":"done"}\n```')]
        with patch("model.ollama_model._local_post", side_effect=responses):
            actor = create_ollama_chat_model(model="qwen3.8:27b", actor_name="Alice")
            executor = initialize_agent([tool], actor, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                                        max_iterations=2, return_intermediate_steps=True)
            result = executor({"input": "Move Alice to x=1."})
        self.assertEqual(calls, [("Alice", 1)])
        self.assertEqual(result["output"], "done")

    def test_minecraft_agent_uses_local_provider_and_contract(self):
        from env.minecraft_client import Agent
        calls = []
        def navigateTo(player_name: str, x: int) -> str:
            """Move an agent to x."""
            calls.append((player_name, x))
            return "arrived"
        actor = Agent.__new__(Agent)
        actor.name = "Alice"
        actor.model = "qwen3.8:27b"
        actor.tools = [StructuredTool.from_function(func=navigateTo)]
        actor.update_history = lambda detail: None
        Path("data/history").mkdir(parents=True)
        responses = [self.response('```json\n{"action":"navigateTo","action_input":{"player_name":"Alice","x":1}}\n```'),
                     self.response('```json\n{"action":"Final Answer","action_input":"done"}\n```')]
        with patch.object(Agent, "model_provider", "ollama"), patch.object(Agent, "api_key_list", []), \
             patch("model.ollama_model._local_post", side_effect=responses):
            answer, detail = actor.run("Move Alice to x=1.", max_iterations=2)
        self.assertEqual(answer, "done")
        self.assertEqual(calls, [("Alice", 1)])
        self.assertEqual(detail["action_contract"]["events"][0]["validation"], "valid")

    def test_default_minecraft_actor_provider_is_gemini(self):
        from env.minecraft_client import Agent
        from model.google_model import DEFAULT_GEMINI_MODEL
        self.assertEqual(Agent.model_provider, "gemini")
        self.assertEqual(Agent.model, DEFAULT_GEMINI_MODEL)

    def test_local_errors_do_not_fall_back_to_api(self):
        model = OllamaLanguageModel(timeout=1)
        with patch("model.ollama_model._local_post", side_effect=ConnectionError("unavailable")) as post:
            with self.assertRaises(ConnectionError):
                model.few_shot_generate_thoughts("system", "prompt", cache_enabled=False)
        self.assertEqual(post.call_count, 1)
        with patch("model.ollama_model._local_post", return_value=self.response("")):
            with self.assertRaisesRegex(ValueError, "empty response"):
                model.few_shot_generate_thoughts("system", "prompt", cache_enabled=False)

    def test_full_controller_injects_models_by_role(self):
        from pipeline.controller import GlobalController
        baseline = {"api_model": "gemini-3.8-flash"}
        roles = resolve_role_models({"ac": {"provider": "ollama"}, "ba": {"provider": "ollama"}}, baseline)
        configs = []
        def factory(config):
            configs.append(dict(config))
            return SimpleNamespace(role_name=config.get("role_name", ""), config=dict(config))
        class FakeAgent:
            def __init__(self, llm, env, data_manager, name, **kwargs):
                self.llm, self.name = llm, name
        env = SimpleNamespace(agent_pool=[SimpleNamespace(name="Alice")],
                              get_all_agent_description_tiny=lambda: {})
        with patch("pipeline.controller.init_language_model", side_effect=factory), \
             patch("pipeline.controller.BaseAgent", FakeAgent), \
             patch("pipeline.controller.init_logger", return_value=logging.getLogger("fixture")):
            tm, dm = SimpleNamespace(), SimpleNamespace()
            ctrl = GlobalController(baseline, tm, dm, env, ac_llm_config=roles["ac"],
                                    base_agent_config=roles["ba"])
            self.assertEqual(tm.llm.config["api_model"], "gemini-3.8-flash")
            self.assertEqual(dm.llm.config["api_model"], "gemini-3.8-flash")
            self.assertEqual(ctrl.llm.config["provider"], "ollama")
            self.assertEqual(ctrl.agent_list[0].llm.config["provider"], "ollama")
            self.assertIsNot(ctrl.llm, ctrl.agent_list[0].llm)
            ctrl.executor.shutdown()
            mixed = resolve_role_models({"ac": {"provider": "ollama"}}, baseline)
            tm, dm = SimpleNamespace(), SimpleNamespace()
            ctrl = GlobalController(baseline, tm, dm, env, ac_llm_config=mixed["ac"],
                                    base_agent_config=mixed["ba"])
            self.assertEqual(ctrl.llm.config["provider"], "ollama")
            self.assertEqual(ctrl.agent_list[0].llm.config["provider"], "gemini")
            ctrl.executor.shutdown()
            tm, dm = SimpleNamespace(), SimpleNamespace()
            ctrl = GlobalController(baseline, tm, dm, env)
            self.assertIs(ctrl.llm, ctrl.agent_list[0].llm)
            ctrl.executor.shutdown()

    def test_launcher_passes_local_roles_without_replacing_td_sm(self):
        from contextlib import contextmanager
        import start_with_config as launcher

        received = {}
        class FakeEnv:
            def __init__(self, **kwargs):
                pass
            def agent_register(self, **kwargs):
                pass
            @contextmanager
            def run(self, **kwargs):
                yield
            def get_init_state(self):
                return []
            def get_score(self):
                return {}
        class FakeDM:
            def __init__(self, **kwargs):
                pass
            def update_database_init(self, state):
                pass
        class FakeTM:
            def __init__(self, **kwargs):
                received["tm_init"] = kwargs
            def init_task(self, **kwargs):
                pass
        class FakeController:
            def __init__(self, config, tm, dm, env, **kwargs):
                received["baseline"] = config.copy()
                received["local_judger"] = env.local_generation_config
                received.update(kwargs)
            def run(self):
                pass

        roles = {"ac": {"provider": "ollama"}, "ba": {"provider": "ollama"}}
        with patch.object(launcher, "VillagerBench", FakeEnv), patch.object(launcher, "DataManager", FakeDM), \
             patch.object(launcher, "TaskManager", FakeTM), patch.object(launcher, "FullController", FakeController), \
             patch.object(launcher.Agent, "model_provider", "gemini"), \
             patch.object(launcher.Agent, "model", "gemini-3.8-flash"), \
             patch.object(launcher.Agent, "base_url", ""), patch.object(launcher.Agent, "api_key_list", []), \
             patch.object(launcher.Agent, "thinking_level", "low"), \
             patch.object(launcher.Agent, "ollama_base_url", ""), \
             patch.object(launcher.Agent, "ollama_num_ctx", None), \
             patch.object(launcher.Agent, "ollama_timeout", 300.0):
            launcher.run("gemini-3.8-flash", "https://generativelanguage.googleapis.com/v1beta/openai/",
                         ["offline"], "low", "construction", 0, 1, False, 1, "goal", "",
                         "localhost", 25565, "fixture", controller_mode="full",
                         assignment_policy="controller", model_roles=roles)
            self.assertEqual(launcher.Agent.model_provider, "ollama")
            self.assertEqual(launcher.Agent.model, "qwen3.8:27b")
        self.assertEqual(received["baseline"]["api_model"], "gemini-3.8-flash")
        self.assertEqual(received["ac_llm_config"]["provider"], "ollama")
        self.assertEqual(received["base_agent_config"]["provider"], "ollama")

        roles = {"default": {"provider": "ollama"}}
        with patch.object(launcher, "VillagerBench", FakeEnv), patch.object(launcher, "DataManager", FakeDM), \
             patch.object(launcher, "TaskManager", FakeTM), patch.object(launcher, "FullController", FakeController), \
             patch.object(launcher.Agent, "model_provider", "gemini"), \
             patch.object(launcher.Agent, "model", "gemini-3.8-flash"), \
             patch.object(launcher.Agent, "base_url", ""), patch.object(launcher.Agent, "api_key_list", []), \
             patch.object(launcher.Agent, "thinking_level", "low"), \
             patch.object(launcher.Agent, "ollama_base_url", ""), \
             patch.object(launcher.Agent, "ollama_num_ctx", None), \
             patch.object(launcher.Agent, "ollama_timeout", 300.0):
            launcher.run("gemini-3.8-flash", "https://generativelanguage.googleapis.com/v1beta/openai/",
                         [], "low", "construction", 0, 1, False, 1, "goal", "", "localhost", 25565,
                         "fixture", controller_mode="full", assignment_policy="controller", model_roles=roles)
            self.assertEqual(launcher.Agent.api_key_list, [])
            self.assertEqual(launcher.Agent.model_provider, "ollama")
        self.assertTrue(received["tm_init"]["local_only"])
        self.assertEqual(received["local_judger"]["api_model"], "qwen3.8:27b")
        for key in ("tm_llm_config", "dm_llm_config", "ac_llm_config", "base_agent_config"):
            self.assertEqual(received[key]["api_model"], "qwen3.8:27b")
            self.assertEqual(received[key]["provider"], "ollama")


if __name__ == "__main__":
    unittest.main()
