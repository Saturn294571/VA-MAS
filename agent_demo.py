import time
from env.env import VillagerBench, env_type, Agent
from pipeline.agent import BaseAgent
from pipeline.controller import GlobalController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
from model.init_model import init_language_model
from model.role_models import configure_actor_model, standalone_model_config

if __name__ == "__main__":


    llm_config = standalone_model_config()
    llm = init_language_model(llm_config)
    configure_actor_model(Agent, llm_config)

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
