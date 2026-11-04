"""Core-only benchmark wiring and removed-feature rejection, without actors or network."""
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import start_with_config as launcher
from env.env import VillagerBench, env_type
from env.minecraft_client import Agent
from model.init_model import init_language_model

REPO = Path(__file__).resolve().parents[1]


class CoreBoundaryChecks(unittest.TestCase):
    def setUp(self):
        self.original = Path.cwd()
        self.temp = tempfile.TemporaryDirectory()
        os.chdir(self.temp.name)

    def tearDown(self):
        os.chdir(self.original)
        self.temp.cleanup()

    def test_three_benchmark_launcher_wiring_and_role_models(self):
        Path('data').mkdir()
        Path('data/farm_setting.json').write_bytes((REPO/'data/farm_setting.json').read_bytes())
        for scenario, expected in [('construction', env_type.construction),
                                   ('farming', env_type.farming), ('puzzle', env_type.puzzle)]:
            received = {}
            class FixtureEnv:
                def __init__(self, **kwargs):
                    received['environment'] = kwargs
                def agent_register(self, **kwargs):
                    received['agents'] = kwargs
                @contextmanager
                def run(self, **kwargs):
                    received['transport'] = kwargs
                    yield
                def get_init_state(self): return []
                def get_score(self): return {}
            class FixtureDM:
                def __init__(self, **kwargs): pass
                def update_database_init(self, info): pass
            class FixtureTM:
                def __init__(self, **kwargs): received['task_manager'] = kwargs
                def init_task(self, **kwargs): received['task'] = kwargs
            class FixtureController:
                def __init__(self, config, *args, **kwargs): received['models'] = kwargs
                def run(self): received['ran'] = True
            with patch.object(launcher, 'VillagerBench', FixtureEnv), \
                 patch.object(launcher, 'DataManager', FixtureDM), \
                 patch.object(launcher, 'TaskManager', FixtureTM), \
                 patch.object(launcher, 'FullController', FixtureController), \
                 patch.object(launcher, 'configure_actor_model'):
                launcher.run('gemini-3.1-flash-lite', 'https://generativelanguage.googleapis.com/v1beta/openai/',
                             [], 'minimal', scenario, 0, 1, False, 1, 'fixture goal', '',
                             'localhost', 25565, f'fixture_{scenario}',
                             model_roles={'default': {'provider': 'ollama'}})
            self.assertEqual(received['environment']['env_type'], expected)
            self.assertTrue(received['ran'])
            self.assertEqual(received['agents']['agent_number'], 1)
            self.assertTrue(received['task_manager']['local_only'])
            for key in ['ac_llm_config', 'tm_llm_config', 'dm_llm_config', 'base_agent_config']:
                self.assertEqual(received['models'][key]['provider'], 'ollama')

    def test_retained_judger_subprocess_targets(self):
        Path('.cache').mkdir()
        for scenario, target in [(env_type.construction, 'build_judger.py'),
                                 (env_type.farming, 'farm_craft_judger.py'),
                                 (env_type.puzzle, 'escape_room_judger.py')]:
            env = VillagerBench.__new__(VillagerBench)
            env._virtual_debug = False
            env.env_type = scenario
            env.running = True
            env.agent_pool = [SimpleNamespace(name='Alice')]
            env.host, env.port, env.task_id = 'localhost', 25565, 0
            env.max_task_num, env.dig_needed = 1, False
            env.task_name, env.local_generation_config = 'fixture', None
            env.logger = logging.getLogger('fixture')
            def launch(*args, **kwargs):
                Path('.cache/load_status.cache').write_text(json.dumps({'status': 'loaded'}))
            with patch('env.env.subprocess.Popen', side_effect=launch) as popen, \
                 patch('env.env.time.sleep'):
                env.reset()
            args = popen.call_args.args[0]
            self.assertEqual(args[1], 'env/' + target)
            self.assertTrue((REPO / args[1]).is_file())
            self.assertEqual(args[args.index('--agent_names') + 1], 'Alice')

    def test_base_agent_reflection_preserves_action_history(self):
        from pipeline.agent import BaseAgent
        from type_define.graph import Task
        agent = BaseAgent.__new__(BaseAgent)
        agent.name = 'Alice'
        agent.data_manager = SimpleNamespace(query_history=lambda name: 'fixture history')
        agent.llm = SimpleNamespace(few_shot_generate_thoughts=Mock(
            return_value='{"task_status": true, "summary": "fixture complete"}'))
        agent.update_reflect = Mock()
        task = Task('fixture task', {})
        detail = {'action_list': [{'action': {'tool': 'placeBlock'},
                                  'feedback': {'message': 'placed', 'status': True}}]}
        self.assertTrue(agent.reflect(task, detail))
        self.assertEqual(agent.history_action_list, ['placed'])
        self.assertEqual(task._summary, ['running', 'fixture complete'])

    def test_existing_environment_error_can_return_normally(self):
        env = VillagerBench.__new__(VillagerBench)
        env._virtual_debug = True
        env.logger = Mock()
        env.stop = Mock()
        with env.run():
            raise RuntimeError('fixture legacy failure')
        env.logger.error.assert_called_once()
        self.assertTrue(env.stop.called)

    def test_removed_options_fail_before_credentials_or_environment_mutation(self):
        for scenario, controller in [('meta', 'full'), ('gen', 'full'), ('auto', 'full'),
                                     ('construction', 'tiny')]:
            with patch.object(launcher, 'VillagerBench', side_effect=AssertionError('environment touched')):
                with self.assertRaisesRegex(ValueError, 'archive/full-features-20261104'):
                    launcher.run('gemini-x', '', [], 'minimal', scenario, 0, 1, False, 1,
                                 'goal', '', 'localhost', 25565, 'fixture', controller_mode=controller)
        with patch('env.env.os.makedirs', side_effect=AssertionError('runtime files touched')):
            with self.assertRaises(ValueError):
                VillagerBench(10, 0, False)
        with patch('env.minecraft_client.subprocess.Popen', side_effect=AssertionError('bot launched')):
            with self.assertRaises(ValueError):
                Agent.launch(fast=True)
        empty = VillagerBench.__new__(VillagerBench)
        with self.assertRaises(ValueError):
            with empty.run(fast_api=True): pass
        for args in [{'provider': 'zhipu', 'api_model': 'glm-4'},
                     {'provider': 'huggingface', 'api_model': 'local'},
                     {'provider': 'openai', 'api_model': 'gemini-x'},
                     {'api_model': 'gpt-4o'}, {'api_model': 'llama'}, {'api_model': 'qwen-other'}]:
            with self.assertRaisesRegex(ValueError, 'archive/full-features-20261104'):
                init_language_model(args)


if __name__ == '__main__':
    unittest.main()
