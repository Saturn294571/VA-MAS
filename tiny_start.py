### This is a simple example of how to run the pipeline.
### You can modify the code to fit your own environment and task.
### You can also refer to the doc/api_library.md to add more agent tools.

from env.env import VillagerBench, env_type, Agent
from pipeline.controller import GlobalController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
import json
import os
from model.google_model import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_THINKING_LEVEL,
    GOOGLE_OPENAI_BASE_URL,
    load_google_api_keys,
)

LLM_API_BASE = GOOGLE_OPENAI_BASE_URL
LLM_API_MODEL = DEFAULT_GEMINI_MODEL
LLM_THINKING_LEVEL = DEFAULT_GEMINI_THINKING_LEVEL
MINECRAFT_HOST = "localhost"
MINECRAFT_PORT = 25565
TASK_NAME = "tiny_start_single_task"
TASK_DESCRIPTION = "Alice talk with yubo"

if __name__ == "__main__":
    api_key_list = load_google_api_keys()
    os.makedirs(".cache", exist_ok=True)
    with open(".cache/meta_setting.json", "w", encoding="utf-8") as config_file:
        json.dump({"task_name": TASK_NAME}, config_file, indent=4)

    # Set Environment
    env = VillagerBench(env_type.none, task_id=0, _virtual_debug=False, dig_needed=False, host=MINECRAFT_HOST, port=MINECRAFT_PORT)

    # Set Agent
    llm_config = {
        "api_model": LLM_API_MODEL,
        "api_base": LLM_API_BASE,
        "thinking_level": LLM_THINKING_LEVEL,
        "api_key_list": api_key_list
    }

    Agent.model = LLM_API_MODEL
    Agent.base_url = LLM_API_BASE
    Agent.thinking_level = LLM_THINKING_LEVEL
    Agent.api_key_list = api_key_list

    # more agent tools can be added here you can refer to the agent_tool in doc/api_library.md
    agent_tool = [Agent.talkTo, Agent.read, Agent.scanNearbyEntities, Agent.equipItem, Agent.SmeltingCooking,
                      Agent.navigateTo, Agent.withdrawItem, Agent.craftBlock, Agent.waitForFeedback, Agent.useItemOnEntity,
                      Agent.handoverBlock]

    # Register Agent
    env.agent_register(agent_tool=agent_tool, agent_number=1, name_list=["Alice"]) # Attention that the agent number should be consistent with the agent_tool
    # Attention you should use /op to give the agent the permission to use the command in minecraft server for example /op Agent1

    # Run Environment
    with env.run():
        
        # Set Data Manager
        dm = DataManager(silent=False)
        dm.update_database_init(env.get_init_state())

        # Set Task Manager
        tm = TaskManager(silent=False)

        # Set Controller
        ctrl = GlobalController(llm_config, tm, dm, env)
        ctrl.set_stop_condition(
            max_execution_time=5 * 60,
            stop_after_fail_times=1,
            stop_after_success_times=1,
        )

        # Set Task
        tm.init_task(TASK_DESCRIPTION, {})

        # Run Controller
        ctrl.run()
