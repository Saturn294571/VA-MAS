from pipeline.controller_execution import ControllerExecution
import sys
import os
import time
import traceback
from concurrent.futures import as_completed

from model.init_model import init_language_model

sys.path.append(os.getcwd())
from type_define.graph import Task
from pipeline.task_manager import TaskManager
from pipeline.data_manager import DataManager
from pipeline.agent import BaseAgent
from pipeline.utils import *
from pipeline.controller_prompt import *
from env.env import VillagerBench
import logging
from tracer import current_tracer, safe_emit, traced
from pipeline.assignment_policy import graph_error, revalidate_controller_assignments, validate_controller_proposal


class GlobalController(ControllerExecution):
    '''
    Global Controller for Minecraft game agents. The task is to assign tasks to agents. Create a plan that assigns tasks to suitable agents and return a list of task-assignment JSON objects.
    
    This is a tiny version of the GlobalController, which is used for faster task assignment and execution. It is designed for the purpose of testing and debugging.
    
    Args:
    - llm_config (dict): Configuration for the language model.
    - task_manager (TaskManager): TaskManager object.
    - data_manager (DataManager): DataManager object.
    - env (VillagerBench): VillagerBench object.
    - silent (bool): Whether to suppress the log output. Default is False.
    - max_workers (int): The maximum number of workers in the thread pool. Default is 4.
    '''
    def __init__(self, llm_config: dict, task_manager: TaskManager, data_manager: DataManager, env: VillagerBench,
                 silent: bool = False, max_workers=4, tm_llm_config: dict = None, dm_llm_config: dict = None, base_agent_config: dict = None, all_tools=[], ac_llm_config: dict = None):

        self.task_manager = task_manager
        tm_llm_config = llm_config.copy() if tm_llm_config is None else tm_llm_config.copy()
        tm_llm_config["role_name"] = "TaskManager"
        self.task_manager.llm = init_language_model(tm_llm_config)

        self.task_manager.dm = data_manager
        self.data_manager = data_manager
        dm_llm_config = llm_config.copy() if dm_llm_config is None else dm_llm_config.copy()
        dm_llm_config["role_name"] = "DataManager"
        self.data_manager.llm = init_language_model(dm_llm_config)

        llm = init_language_model(ac_llm_config or llm_config)
        base_agent_config = llm_config.copy() if base_agent_config is None else base_agent_config
        base_llm = init_language_model(base_agent_config)
        self.agent_list = [BaseAgent(base_llm, env, data_manager, name=a.name, silent=False, all_tools=all_tools) for a in env.agent_pool]
        self.task_manager.agent_list = self.agent_list
        self.assignment = {}
        self._traced_ready = set()
        self.feedback = {}

        self.logger = init_logger("GlobalController", level=logging.DEBUG, dump=True, silent=silent)
        self.env = env
        self.llm = llm
        self.llm.role_name = "GlobalController"

        self._initialize_execution(max_workers)


    def validate_assignments(self, result: [dict]):
        return validate_controller_proposal(self, result, allow_multi_agent=False)

    @traced("AC", "assignment")
    def execute_assignments(self, validated_assignments):
        validated_assignments = revalidate_controller_assignments(
            self, validated_assignments, source="direct", allow_multi_agent=False)
        for assignment in validated_assignments:
            task_instance = assignment["task_instance"]
            agent_instances = assignment["agent_instances"]
            for agent in agent_instances:
                self.assignment[agent.name] = task_instance.id
                task_instance._agent.append(agent.name)
                safe_emit(current_tracer(), "AC", "task.assigned", task_id=task_instance.id,
                          agent_id=agent.name, assignment_mode="direct",
                          decision_id=assignment.get("decision_id"),
                          candidate_count=len(task_instance.candidate_list),
                          required_agents=task_instance.number)

            with self.task_list_lock:
                task_instance.status = Task.running
                self.task_queue.append((agent_instances[0], task_instance))
        
            name_list = ", ".join([agent.name for agent in agent_instances])
            self.logger.info(f"Agent(s) {name_list} assigned to do task {task_instance.description}")

            # agent_env_dict = self.env.get_init_state()
            # for env_dict in agent_env_dict:
            #     self.logger.warning(str(env_dict))

            task_instance.status = Task.running


    
    def update_feedback(self, task, agent, detail):
        if isinstance(detail, dict) and detail.get("policy_abort"):
            self.logger.warning("Decision BA stopped: %s", detail["policy_abort"])
            self.set_task_status(task.id, Task.failure, detail)
            self.shutdown = True
            return
        task.status = Task.success if agent.reflect(task, detail) else Task.failure
        # task.status = Task.success
        self.set_task_status(task.id, task.status, detail)

        for agent in self.agent_list:
            if self.assignment.get(agent.name) == task.id:
                self.assignment.pop(agent.name)
        self.logger.info(
            f"task {task.description} has been executed, the result is {task.status}")
        self.task_manager.feedback_task(self.get_task_by_id(task.id))

        return

    @traced("AC", "task.feedback")
    def update_task_status(self, task, status, detail): 
        task.status = status
        self.set_task_status(task.id, status, detail)

        for agent in self.agent_list:
            if self.assignment.get(agent.name) == task.id:
                self.assignment.pop(agent.name)

        self.logger.info(
            f"task {task.description} has been executed, the result is {task.status}")
        self.task_manager.feedback_task(self.get_task_by_id(task.id))

        return
        

    def process_completed_tasks(self):
        while True:
            if self.shutdown:
                break

            # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
            if self.env.agents_ping()["status"] == False:
                self.logger.info("Some agents are offline!")
                self.shutdown = True
                break

            with self.result_list_lock:
                result_list_copy = []
                for future, agent, task, start_time in self.result_queue:

                    if self.shutdown:
                        break
                    # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
                    if future.done():
                        try:
                            self.logger.info(f"Task {task.description} finished!")
                            _, detail = future.result()
                            self.update_feedback(task, agent, detail)

                        except Exception as e: # No handling for collab; this code is incorrect
                            traceback.print_exception(type(e), e, e.__traceback__)
                            self.logger.error(f"Task {task.description} failed with exception: {e}\n{e.__traceback__}")
                            self.logger.exception(e)
                            self.update_task_status(task, Task.failure, f"Task {task.description} failed with exception: {e}\n{e.__traceback__}")                            
                    
                    elif time.time() - start_time > self.max_task_time: # No handling for collab; this code is incorrect
                        self.logger.warning(f"Task {task.description} timeout!")
                        self.update_task_status(task, Task.failure, f"Task {task.description} timeout!")
                    
                    else:
                        result_list_copy.append((future, agent, task, start_time))
                    time.sleep(self.query_interval)
                self.result_queue = result_list_copy

                
    def check_task_list_available(self):
        available_task_list = []
        for task in self.task_list:
            task.available = True
            if len(task.candidate_list) == 0:
                task.candidate_list = [agent.name for agent in self.agent_list]
            if len(task.predecessor_task_list) > 0 or task.status != Task.unknown:
                task.available = False
                continue
            free_candidate = 0
            for agent in self.agent_list:
                if agent.name in task.candidate_list and self.assignment.get(agent.name) is None:
                    free_candidate += 1
            if free_candidate < task.number:
                task.available = False
        
        for task in self.task_list:
            if task.available:
                available_task_list.append(task)
                tracer = current_tracer()
                if tracer is not None and not hasattr(self, "_traced_ready"):
                    self._traced_ready = set()
                if tracer is not None and task.id not in self._traced_ready:
                    self._traced_ready.add(task.id)
                    safe_emit(tracer, "AC", "task.ready", task_id=task.id,
                              candidate_count=len(task.candidate_list), required_agents=task.number)
        
        return available_task_list
    # Producer
    def execute_tasks(self):
        try:
            while True:
                if self.shutdown:
                    break

                # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
                if self.env.agents_ping()["status"] == False:
                    self.logger.info("Some agents are offline!")
                    self.shutdown = True
                    break

                invalid_graph = graph_error(self.task_manager.graph)
                if invalid_graph:
                    self.logger.error("Cannot schedule task graph: %s", invalid_graph)
                    safe_emit(current_tracer(), "AC", "assignment.rejected", reason=invalid_graph)
                    self.shutdown = True
                    break
                self.task_list = self.task_manager.query_subtask_list()
                if self.task_list == []:
                    self.logger.info("all assigned tasks are finished ...")
                    self.shutdown = True
                    break
                # Write to logs/task_list.json
                agent_states = []
                for agent in self.agent_list:
                    if self.assignment.get(agent.name) is None:
                        agent_states.append({"name": agent.name, "state": "free", "task": None})
                    else:
                        tmp_description = ""
                        for task in self.task_list:
                            if task.id == self.assignment.get(agent.name):
                                tmp_description = task.description
                                break
                        agent_states.append({"name": agent.name, "state": "busy", "task": tmp_description})

                with open("logs/task_list.json", "w") as f:
                    json.dump({
                        "agent_states": agent_states,
                        "task_list": [task.assign_json(idx) for idx, task in enumerate(self.task_list)],
                    }, f, indent=4)
                    
                if self.check_task_list_available() == []:
                    # self.logger.info("no available task ...")
                    # sleep
                    time.sleep(self.query_interval)
                    continue

                if len(self.assignment) == 0:
                    # If number == length of candidate_list, assign tasks directly
                    for task in self.task_list:
                        if task.number == len(task.candidate_list) and task.available and \
                            all([self.assignment.get(agent.name) is None for agent in self.agent_list if agent.name in task.candidate_list]):

                            self.logger.info(f"Task {task.description} is assigned to {task.candidate_list}")
                            self.execute_assignments([{
                                "task_instance": task,
                                "agent_instances": [agent for agent in self.agent_list if agent.name in task.candidate_list]
                            }])

        except KeyboardInterrupt:
            self.shutdown = True
            self.task_manager = None
            self.data_manager = None
            self.executor.shutdown(wait=False)
            raise Exception("Interrupted by user")
