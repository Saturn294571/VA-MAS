import sys
import os
sys.path.append(os.getcwd())
import time
import logging
from env.env import VillagerBench
from type_define.graph import Task
from pipeline.data_manager import DataManager
from pipeline.utils import *
from model.abstract_language_model import AbstractLanguageModel
from random import random, randint, choice, sample
from pipeline.agent_prompt import *
from speaking_style import speaking_styles, speaking_styles_zh
import threading
import platform
from tracer import traced
from model.utils import extract_info

class AgentFeedback:
    def __init__(self, task:Task, detail, status):
        self.task = task
        self.detail = detail
        self.status = status

    def to_json(self) -> dict:
        return {
            "task": self.task.to_json(),
            "detail": self.detail,
            "status": self.status,
        }

        

class BaseAgent:
    '''
    ### BaseAgent is the single agent in the system, it can take action and reflect
    
    step: take an action and return the feedback and detail
    reflect: reflect on the task and return the result
    to_json: return the json format of the agent
    '''
    _virtual_debug = False
    def __init__(self, llm:AbstractLanguageModel , env:VillagerBench, data_manager:DataManager, name:str, logger:logging.Logger = None, silent = False,
    all_tools = [], **kwargs):
        if {"RL_mode", "rl_env", "rl_model"} & kwargs.keys():
            raise ValueError("RL actor settings are preserved on archive/full-features-20261104")
        self.env = env
        self.name = name
        self.data_manager = data_manager
        self.llm = llm
        self.history_action_list = ["No action yet"]
        self.reflect_info = {"prompt": [], "response": []}
        self.logger = logger
        self.all_tools = all_tools
        if not env.running:
            BaseAgent._virtual_debug = True

        if self.logger is None:
            self.logger = init_logger("BaseAgent", dump=True, silent=silent)
        
        self.instruction_history = []  # New: save history instructions
        self.state_history = []        # New: save history state

        self.IDLE = True  # Control whether in IDLE state
        self.stop_event = threading.Event()  # Used to control thread termination
        # self.start_idle_thread()  # Start IDLE thread

        system_type = platform.system().lower()
        if system_type == "linux":
            self.logger.info("Linux system detected.")
            self.logger.info("EMOJI is supported.")
            self.EMOJI = True
        else:
            self.logger.info("EMOJI is not supported.")
            self.EMOJI = False

    def update_reflect(self, system_prompt, user_prompt, response):
        if type(user_prompt) == str:
            user_prompt = [user_prompt]
        prompt = str(system_prompt) + "\n"
        for i in range(len(user_prompt)):
            prompt += user_prompt[i] + "\n"

        self.reflect_info["prompt"].append(prompt)
        self.reflect_info["response"].append(response)
        with open(".cache/meta_setting.json", "r") as f:
            config = json.load(f)
            task_name = config["task_name"]
        if not os.path.exists("result/" + task_name):
            os.mkdir(os.path.join("result/", task_name))
        root = os.path.join("result/", task_name)
        with open(os.path.join(root, f"{self.name}_reflect.json"), "w") as f:
            json.dump(self.reflect_info, f, indent=4)

    @traced("BA", "task.execute")
    def step(self, task:Task) -> (str, dict):
        '''
        take an action and return the feedback and detail
        return: final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}
        '''
        if BaseAgent._virtual_debug:
            return self.virtual_step(task)

        return self.normal_step(task)

    def start_idle_thread(self):
        '''
        Start the idle_step function in a separate thread.
        '''
        self.idle_thread = threading.Thread(target=self.idle_step, daemon=True)
        self.idle_thread.start()

    def stop_idle_thread(self):
        '''
        Stop the idle_step thread.
        '''
        self.stop_event.set()  # Set stop signal
        self.idle_thread.join()  # Wait for thread to finish

    def idle_step(self):
        '''
        idle_step is the step for the agent to wait for the task
        At this time, the agent will help other agents to do the task
        find what the agent can do or talk with other agents or just wait
        '''
        if random() < 0.5:
            speech_style = sample(list(speaking_styles.keys()), 1)[0]
            personality = speaking_styles[speech_style]['personality']
            traits = speaking_styles[speech_style]['traits']
            example = speaking_styles[speech_style]['example']
        else:
            speech_style = sample(list(speaking_styles_zh.keys()), 1)[0]
            personality = speaking_styles_zh[speech_style]['性格']
            traits = speaking_styles_zh[speech_style]['特征']
            example = speaking_styles_zh[speech_style]['示例']


        if platform.system().lower() != "linux":
            idle_prompt = idle_prompt_wo_emoji
        else:
            idle_prompt = idle_prompt_w_emoji

        task_str = format_string(idle_prompt, 
                                 {
                                "agent_name": self.name,
                                "agent_state": self.data_manager.query_history(self.name),
                                "personality": personality,
                                "example": example,
                                "traits": traits,
                                "other_agents": self.other_agents(),
                                "agent_action_list": self.history_action_list,
                                "minecraft_knowledge_card": minecraft_knowledge_card})

        actions = []
        observations = []
        basic_state = ""
        current_state = basic_state

        time.sleep(60) # Wait 30 seconds for startup
        while not self.stop_event.is_set():  # Main loop, until exit signal is received
            if not self.IDLE:
                # If not in IDLE state, enter wait
                time.sleep(1)
                continue

            # Build current status string
            current_context = f"{task_str}\n{current_state}"
            if actions and observations:
                action_history = "\n".join([f"Action: {a}\nObservation: {o}" for a, o in zip(actions, observations)])
                current_context += f"\nHistory:\n{action_history}"

            if self.env.agents_ping()["status"] == False:
                self.logger.info("Some agents are offline!")
                break 
            
            try:
                if self.env.agents_ping()["status"] == False:
                    self.logger.info("Some agents are offline!")
                    break 
                
                time.sleep(2)
                (act, obs), detail = self.env.iter_step(self.name, current_context, 
                                                    actions=actions, 
                                                    observations=observations, 
                                                    recommended_actions=[])
                if act is None:
                    continue
                    
                # Update state
                current_state = f"{basic_state}\nLast Action: {act}\nLast Observation: {obs}"

            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt")
                self.stop_event.set()  # Set stop signal
                raise KeyboardInterrupt
            except ConnectionError:
                self.logger.error("ConnectionError")
                self.stop_event.set()  # Set stop signal
                raise ConnectionError
            except ConnectionRefusedError:
                self.logger.error("ConnectionRefusedError")
                self.stop_event.set()  # Set stop signal
                raise ConnectionRefusedError
            except Exception as e:
                self.logger.error(f"Error: {e}")

            actions.append(act)
            observations.append(obs)

    
    def normal_step(self, task:Task) -> (str, dict):
        if random() < 0.5:
            speech_style = sample(list(speaking_styles.keys()), 1)[0]
            personality = speaking_styles[speech_style]['personality']
            traits = speaking_styles[speech_style]['traits']
            example = speaking_styles[speech_style]['example']
        else:
            speech_style = sample(list(speaking_styles_zh.keys()), 1)[0]
            personality = speaking_styles_zh[speech_style]['性格']
            traits = speaking_styles_zh[speech_style]['特征']
            example = speaking_styles_zh[speech_style]['示例']

        if platform.system().lower() != "linux":
            agent_prompt = agent_prompt_wo_emoji
        else:
            agent_prompt = agent_prompt_w_emoji

        env_snapshot = self.data_manager.query_env_with_task(task.description, agent_query=True)
        agent_state = self.data_manager.query_history(self.name)
        other_agents = self.other_agents()
        relevant_data = smart_truncate(task.content, max_length=4096)
        action_context = {
            "task": {"id": task.id, "description": task.description,
                     "milestones": task.milestones},
            "observation": {"environment": env_snapshot, "agent_state": agent_state,
                            "other_agents": other_agents, "relevant_data": relevant_data},
        }

        if len(task._agent) == 1:
            task_str = format_string(agent_prompt, {"task_description": task.description, "milestone_description": task.milestones, 
                                    "env": env_snapshot,
                                    "relevant_data": relevant_data, # TODO: change to "relevant_data": task.content
                                    "agent_name": self.name,
                                    "agent_state": agent_state,
                                    "personality": personality,
                                    "example": example,
                                    "traits": traits,
                                    "other_agents": other_agents,
                                    "agent_action_list": self.history_action_list,
                                    "minecraft_knowledge_card": minecraft_knowledge_card})
        else:
            task_str = format_string(agent_cooper_prompt, {"task_description": task.description, "milestone_description": task.milestones, 
                                    "env": env_snapshot,
                                    "relevant_data": relevant_data, # TODO: change to "relevant_data": task.content
                                    "agent_name": self.name,
                                    "agent_state": agent_state,
                                    "other_agents": other_agents,
                                    "agent_action_list": self.history_action_list,
                                    "team_members": ", ".join(task._agent),
                                    "minecraft_knowledge_card": minecraft_knowledge_card})
            
        self.logger.debug("="*20 + " Agent Step " + "="*20)
        self.logger.info(f"{self.name} try task:\n {task.description}")
        self.logger.info(f"{self.history_action_list}")
        self.logger.info(f"other agents: {other_agents}")
        self.logger.info(f"{self.name} status:\n {agent_state}")
        max_retry = 3
        
        instruction = format_string(task_prompt, {
            "task_description": task.description,
            "milestone_description": task.milestones,
        })
        state = format_string(state_prompt, {
            "other_agents": self.other_agents(),
            "agent_name": self.name,
            "env": self.data_manager.query_env_with_task(task.description, agent_query=True),
            "relevant_data": smart_truncate(task.content, max_length=4096), 
            "agent_state": self.data_manager.query_history(self.name),
        })
        self.IDLE = False
        while max_retry > 0:
            try:
                feedback, detail = self.env.step(self.name, task_str, action_context=action_context)
                break
            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt")
                raise KeyboardInterrupt
            except ConnectionError:
                self.logger.error("ConnectionError")
                raise ConnectionError
            except ConnectionRefusedError:
                self.logger.error("ConnectionRefusedError")
                raise ConnectionRefusedError
            except Exception as e:
                self.logger.error(f"Error: {e}")
                max_retry -= 1
                time.sleep(3)
        
        self.IDLE = True

        # Time-consuming operation
        status = self.env.agent_status(self.name)
        self.data_manager.update_database(AgentFeedback(task, detail, status).to_json())

        # self.data_manager.save()
        return feedback, detail
    
    def other_agents(self) -> [str]:
        '''
        return the feedback of other agent's pretask
        '''
        return self.data_manager.query_other_agent_state(self.name)
    

    def action_format(self, action:dict) -> str:
        action_str = '''{{message}}'''
        feedback = action.get("feedback", {})
        # If feedback is a string, convert it to {"message": feedback}
        if isinstance(feedback, str):
            feedback = {"message": feedback}
        # Otherwise, ensure feedback is a dictionary and set a default message
        elif not isinstance(feedback, dict):
            feedback = {"message": ""}
        
        # If message does not exist, set a default empty string
        if "message" not in feedback:
            feedback["message"] = ""

        return format_string(action_str, feedback)


    def filter_emoji(self, text: str) -> str:
        ret_str = []
        for c in text:
            try:
                c.encode('gbk')
                ret_str.append(c)
            except UnicodeEncodeError:
                continue
        return ''.join(ret_str)

    @traced("BA", "reflection")
    def reflect(self, task: Task, detail) -> bool:
        '''
        Reflect on the task and return the result
        '''
        # print("in reflect")
        task_description = task.description
        milestone_description = task.milestones
        action_history = detail["action_list"]
        global reflect_system_prompt, reflect_user_prompt
        # print("before llm")
        prompt = format_string(reflect_user_prompt,
                               {
                                   "task_description": task_description,
                                   "milestone_description": milestone_description,
                                   "state": self.data_manager.query_history(self.name),
                                   "action_history": action_history
                               })
        prompt = self.filter_emoji(prompt)
        # print("before response")
        response = self.llm.few_shot_generate_thoughts(reflect_system_prompt, prompt, cache_enabled=False, max_tokens=512, json_check=True)
        # print(response)
        # print("before filter emoji")
        response = self.filter_emoji(response)
        self.update_reflect(reflect_system_prompt, prompt, response)
        result = extract_info(response)[0]
        task.reflect = result
        if "summary" in result.keys():
            task._summary.append(result["summary"])
        else:
            task._summary.append(str(result))

        # add the action to the history
        self.history_action_list = [self.action_format(action) for action in action_history]
        # print("before return ")
        return result.get("task_status", False)
        # return result["task_status"]
    
    def to_json(self) -> dict:
        return {
            "name": self.name
        }
    
    def virtual_env(name:str):
        '''
        ### virtual_env is the virtual environment for the agent to test the agent
        return the virtual environment
        '''
        env = {
            "I_held_item": {
                "spruce_planks": 1
            },
            "sign": "text",
            "blocks": [
                {
                    "spruce_planks": [
                        -3,
                        -60,
                        0
                    ]
                }
            ],
            "equipment": "hidden",
            "food": 20,
            "health": 20,
            "my_name": name,
            "my_position": [
                -1,
                -59,
                1
            ],
            "nearby_entities": [
                
            ],
            "oxygen": 20,
            "saturation": 2,
            "timeOfDay": "sunrise"
        }
        
        env = {
            "message": env,
            "status": True
        }
        return env

    def virtual_step(self, task:Task) -> (str, dict):
        '''
        ### virtual_step is the virtual step for the agent to test the agent
        take an action and return the feedback and detail
        return: final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}
        '''
        # random action
        action = choice(["place", "dig", "find", "open"])
        input = smart_truncate(task.to_json(), max_length=4096)
        random_action_num = randint(1, 10)
        action_list = []
        for i in range(random_action_num):
            action_dict = {
                "tool" : action,
                "tool_input" : {
                    "player_name": self.name,
                    "x": randint(-100, 100),
                    "y": randint(-100, 100),
                    "z": randint(-100, 100),
                },
                "log": "random action"
            }
            feedback = {
                "message": f"execute {action_dict['tool']} at {action_dict['tool_input']['x']} {action_dict['tool_input']['y']} {action_dict['tool_input']['z']}",
                "status": True
            }
            action_list.append({"action": action_dict, "feedback": feedback})
        score = random()
        if score > 0.3:
            final_answer = f"successfully done {task.description}."
            task.status = Task.success
        else:
            final_answer = f"failed to do {task.description}."
            task.status = Task.failure
        detail = {
            "input": input,
            "action_list": action_list,
            "final_answer": final_answer,
        }
        
        self.data_manager.update_database(AgentFeedback(task, detail, VillagerBench.virtual_env(self.name)).to_json())
        # self.data_manager.save()
        return final_answer, {"input": input, "action_list": action_list, "final_answer": final_answer}
