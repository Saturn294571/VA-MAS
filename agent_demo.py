import time
from env.env import VillagerBench, env_type, Agent
from pipeline.agent import BaseAgent
from pipeline.controller import GlobalController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
from model.google_model import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_THINKING_LEVEL,
    GOOGLE_OPENAI_BASE_URL,
    GoogleLanguageModel,
    load_google_api_keys,
)

if __name__ == "__main__":


    api_key_list = load_google_api_keys()
    llm = GoogleLanguageModel(
        api_model=DEFAULT_GEMINI_MODEL,
        api_base=GOOGLE_OPENAI_BASE_URL,
        thinking_level=DEFAULT_GEMINI_THINKING_LEVEL,
        api_key_list=api_key_list,
    )
    Agent.model = DEFAULT_GEMINI_MODEL
    Agent.base_url = GOOGLE_OPENAI_BASE_URL
    Agent.thinking_level = DEFAULT_GEMINI_THINKING_LEVEL
    Agent.api_key_list = api_key_list

    # llm = OpenAILanguageModel(api_model="gpt-3.5-turbo-1106")

    env = VillagerBench(env_type.none, 1, _virtual_debug=False, host = "10.21.31.18", port=25565, dig_needed=True)

    agent_tool = [Agent.scanNearbyEntities, Agent.navigateTo, Agent.attackTarget,
            Agent.UseItemOnEntity, Agent.sleep, Agent.wake,
            Agent.MineBlock, Agent.placeBlock, Agent.equipItem,
            Agent.handoverBlock, Agent.SmeltingCooking,
            Agent.withdrawItem, Agent.storeItem, Agent.craftBlock,
            Agent.enchantItem, Agent.trade, Agent.repairItem, Agent.eat,
            Agent.fetchContainerContents, Agent.ToggleAction]

    env.agent_register(agent_tool=agent_tool, agent_number=2, name_list=["Amy","Andrew"])
    
    with env.run(fast_api=False): # Added a new parameter to control whether to use the fastapi server

        start_time = time.time()
        dm = DataManager()
        dm.update_database_init(env.get_init_state())
        while True:
            feedback, detail = env.step("Andrew", '''You are a powerful ai act as minecraft agent. Try to cook the raw rabbit to get the cooked rabbit. You can use the furnace''')
