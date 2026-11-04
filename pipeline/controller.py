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
    Global Controller is the main controller of the system, it is responsible for assigning tasks to agents and monitoring the progress of the tasks.

    Args:
    - llm_config: dict, language model configuration
    - task_manager: TaskManager, task manager
    - data_manager: DataManager, data manager
    - env: VillagerBench, environment
    - silent: bool, whether to print logs
    - max_workers: int, the maximum number of threads to use

    '''
    def __init__(self, llm_config: dict, task_manager: TaskManager, data_manager: DataManager, env: VillagerBench,
                 silent: bool = False, max_workers=4,
                 ac_llm_config=None, base_agent_config=None, tm_llm_config=None, dm_llm_config=None):
        self.task_manager = task_manager

        tm_llm_config = (tm_llm_config or llm_config).copy()
        tm_llm_config["role_name"] = "TaskManager"

        self.task_manager.llm = init_language_model(tm_llm_config)
        self.task_manager.dm = data_manager

        self.data_manager = data_manager

        dm_llm_config = (dm_llm_config or llm_config).copy()
        dm_llm_config["role_name"] = "DataManager"

        self.data_manager.llm = init_language_model(dm_llm_config)

        llm = init_language_model(ac_llm_config or llm_config)
        base_llm = (llm if ac_llm_config is None and base_agent_config is None
                    else init_language_model({**(base_agent_config or llm_config), "role_name": "BaseAgent"}))
        self.agent_list = [BaseAgent(base_llm, env, data_manager, name=a.name, silent=False) for a in env.agent_pool]
        self.task_manager.agent_list = self.agent_list
        self.task_manager.agent_describe = env.get_all_agent_description_tiny()
        self.assignment = {}
        self._traced_ready = set()
        self.name_list = []
        self.collab_list = []
        for agent in self.agent_list:
            self.name_list.append(agent.name)
        self.feedback = {}
        self.env = env

        self.logger = init_logger("GlobalController", logging.DEBUG, dump=True, silent=silent)
        self.llm = llm
        self.llm.role_name = "GlobalController"

        self._initialize_execution(max_workers)


        self.max_execution_time = 60 * 20  # 20 minutes
        self.stop_after_fail_times = 3  # stop after 3 times of failure
        self.stop_after_success_times = 10  # stop after 10 times of success

        # task done signal
        self.one_task_done = True


        # start time
        self.start_time = time.time()


    def set_stop_condition(self, max_execution_time: int, stop_after_fail_times: int, stop_after_success_times: int):
        self.max_execution_time = max_execution_time
        self.stop_after_fail_times = stop_after_fail_times
        self.stop_after_success_times = stop_after_success_times

    # worker
    def _worker_should_stop(self) -> bool:
        if (self.shutdown or time.time() - self.start_time > self.max_execution_time
                or self.stop_after_fail_times <= 0 or self.stop_after_success_times <= 0):
            self.logger.info("Worker thread is shutting down ...")
            return True
        return False

    def _worker_offline(self) -> None:
        super()._worker_offline()
        self.max_execution_time = 0

    def _stop_before_submit(self) -> bool:
        return self._worker_should_stop()

    def _task_submitted(self, agent) -> None:
        pass

    def _after_submit(self) -> None:
        time.sleep(self.query_interval)

    # Organizational namespaces only: methods bind to GlobalController via aliases below.
    class Scheduling:
        """Determine ready tasks and schedule assignments. Do not instantiate; state belongs to GlobalController."""

        def check_task_list_available(self):
            available_task_list = []
            for task in self.task_list:
                task.available = True
                if len(task.candidate_list) == 0:
                    task.candidate_list = self.name_list
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


        def execute_tasks(self):
            try:
                while True:
                    if self.shutdown or time.time() - self.start_time > self.max_execution_time or self.stop_after_fail_times <= 0 or self.stop_after_success_times <= 0:
                        self.logger.info("Task execution thread is shutting down ...")
                        break

                    if self.env.agents_ping()["status"] == False:
                        self.logger.info("Some agents are offline!")
                        self.shutdown = True
                        self.max_execution_time = 0
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
                    # write task list to file
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

                    if self.one_task_done:
                        for task in self.task_list:
                            if task.number == len(task.candidate_list) and task.available and \
                                all([self.assignment.get(agent.name) is None for agent in self.agent_list if agent.name in task.candidate_list]):

                                self.logger.info(f"Task {task.description} is assigned to all agents!")
                                self.execute_assignments([{
                                    "task_instance": task,
                                    "agent_instances": [agent for agent in self.agent_list if agent.name in task.candidate_list]
                                }])

                        if self.check_task_list_available() != []:
                            env = self.data_manager.query_env()
                            agent_state = self.data_manager.query_agent_list(self.name_list)
                            experience = self.data_manager.query_task_list_experience(self.task_list)

                            result = self.generate_prompt_and_get_response(env, experience, agent_state)
                            self.assign_tasks_to_agents(result)

            except KeyboardInterrupt:
                self.shutdown = True
                self.task_manager = None
                self.data_manager = None
                self.executor.shutdown(wait=False)
                raise Exception("Interrupted by user")


    class Assignment:
        """Select, validate and enqueue agent assignments. Do not instantiate; state belongs to GlobalController."""

        def validate_assignments(self, result: [dict]):
            return validate_controller_proposal(self, result, allow_multi_agent=True)


        @traced("AC", "assignment.select")
        def generate_prompt_and_get_response(self, env, experience, agent_state):
            controller_system_prompt = CONTROLLER_SYSTEM_PROMPT
            controller_user_prompt = format_string(CONTROLLER_USER_PROMPT, {
                "env": env[0],
                "experience": experience,
                "agent state": agent_state,
                "free agent": smart_truncate([agent.to_json() for agent in self.agent_list if self.assignment.get(agent.name) is None], 2048),
                "tasks": smart_truncate([task.assign_json(idx) for idx, task in enumerate(self.task_list) if task.available], 2048)
            })

            # self.logger.debug("-"*10 + "assign prompt in controller" + "-"*10)
            # print(controller_user_prompt)
            # self.logger.debug("-"*15 + "assign prompt end" + "-"*15)

            response = self.llm.few_shot_generate_thoughts(controller_system_prompt, controller_user_prompt, cache_enabled=True, json_check=True)
            # self.logger.debug("-"*10 + "response in controller" + "-"*10)
            # print(response)
            # self.logger.debug("-"*15 + "response end" + "-"*15)

            return extract_info(response)


        def generate_decompose_prompt_and_get_response(self, agent_state, name_list, task_description, task_milestones):
            controller_system_prompt = CONTROLLER_DECOMPOSE_SYSTEM_PROMPT
            controller_user_prompt = format_string(CONTROLLER_DECOMPOSE_USER_PROMPT, {
                "agent state": agent_state,
                "task description": task_description,
                "task milestones": task_milestones,
                "agent name": name_list
            })

            # self.logger.debug("-"*10 + "decompose prompt in controller" + "-"*10)
            # print(controller_user_prompt)
            # self.logger.debug("-"*15 + "decompose prompt end" + "-"*15)

            response = self.llm.few_shot_generate_thoughts(controller_system_prompt, controller_user_prompt, cache_enabled=True, json_check=True)
            self.logger.debug("-"*10 + "response in controller" + "-"*10)
            # print(response)
            self.logger.debug("-"*15 + "response end" + "-"*15)

            return extract_info(response)


        def assign_tasks_to_agents(self, result: [dict]):
            # self.logger.info("Start to assign tasks!")
            self.logger.info(f"Controller LLM proposed assignments: {result}")
            validated_assignments = self.validate_assignments(result)
            self.logger.info(f"Controller LLM accepted assignments: {[(item['task_instance'].id, [agent.name for agent in item['agent_instances']]) for item in validated_assignments]}")
            self.execute_assignments(validated_assignments, assignment_mode="llm")


        @traced("AC", "assignment")
        def execute_assignments(self, validated_assignments, assignment_mode="direct"):
            validated_assignments = revalidate_controller_assignments(
                self, validated_assignments, source=assignment_mode)
            for assignment in validated_assignments:
                task_instance = assignment["task_instance"]
                agent_instances = assignment["agent_instances"]
                result = ""
                if len(agent_instances) > 1:
                    assign_name_list = []
                    for agent in agent_instances:
                        assign_name_list.append(agent.name)
                    agent_state = self.data_manager.query_agent_list(assign_name_list)
                    result = self.generate_decompose_prompt_and_get_response(agent_state, assign_name_list, task_instance.description, task_instance.milestones)

                    self.logger.debug("-"*10 + "decompose feedback in controller" + "-"*10)
                    self.logger.debug("-"*40)
                    for assign in result:
                        self.logger.debug("|" + assign["agent"] + ": " + assign["description"])
                    self.logger.debug("-"*40)
                    self.logger.debug("-"*15 + "decompose feedback end" + "-"*15)

                    if len(result) != len(agent_instances):
                        self.logger.warning("decompose error!")
                        continue
                    if not revalidate_controller_assignments(self, [assignment], source=assignment_mode):
                        continue
                tmp_collab = {"task": task_instance.id, "assign agent": 0, "complete agent": 0}
                for agent in agent_instances:
                    self.assignment[agent.name] = task_instance.id
                    task_instance._agent.append(agent.name)
                    safe_emit(current_tracer(), "AC", "task.assigned", task_id=task_instance.id,
                              agent_id=agent.name, assignment_mode=assignment_mode,
                              decision_id=assignment.get("decision_id"),
                              candidate_count=len(task_instance.candidate_list),
                              required_agents=task_instance.number)
                    # add task to agent's task list
                    if len(agent_instances) > 1:
                        tmp_task = task_instance.copy()
                        safe_emit(current_tracer(), "AC", "task.child_created", task_id=tmp_task.id,
                                  parent_task_id=task_instance.id, agent_id=agent.name)
                        for assign in result:
                            if assign["agent"] == agent.name:
                                tmp_task.description = assign["description"]
                                tmp_task.milestones = assign["milestones"]
                                tmp_task.status = Task.running
                                break
                        with self.task_list_lock:
                            self.task_queue.append((agent, tmp_task))
                            time.sleep(1)
                    else:
                        with self.task_list_lock:
                            task_instance.status = Task.running
                            self.task_queue.append((agent, task_instance))
                            time.sleep(1)
                    self.one_task_done = False
                    tmp_collab["assign agent"] += 1

                name_list = ", ".join([agent.name for agent in agent_instances])
                self.logger.info(f"Agent(s) {name_list} are assigned to do task {task_instance.description}")

                self.collab_list.append(tmp_collab)
                task_instance.status = Task.running


    class Feedback:
        """Collect execution results and propagate task feedback. Do not instantiate; state belongs to GlobalController."""

        def process_completed_tasks(self):
            while True:
                if self.shutdown or time.time() - self.start_time > self.max_execution_time or self.stop_after_fail_times <= 0 or self.stop_after_success_times <= 0:
                    self.logger.info("Task processing thread is shutting down ...")
                    break

                if self.env.agents_ping()["status"] == False:
                    self.logger.info("Some agents are offline!")
                    self.shutdown = True
                    self.max_execution_time = 0
                    break

                with self.result_list_lock:
                    result_list_copy = []
                    for future, agent, task, start_time in self.result_queue:
                        # if future.done() and task.id in [t.id for t in self.task_list] and task.status == Task.running:
                        if self.env.agents_ping()["status"] == False:
                            self.logger.info("Some agents are offline!")
                            self.shutdown = True
                            self.max_execution_time = 0
                            break

                        if future.done():
                            try:
                                self.logger.info(f"Task {task.description} finished!")
                                _, detail = future.result()
                                self.update_feedback(task, agent, detail)
                            except KeyboardInterrupt:
                                self.shutdown = True
                                self.max_execution_time = 0
                                self.task_manager = None
                                self.data_manager = None
                                self.executor.shutdown(wait=False)
                                raise Exception("Interrupted by user")
                            except ConnectionError as e:
                                self.shutdown = True
                                self.max_execution_time = 0
                                self.task_manager = None
                                self.data_manager = None
                                self.executor.shutdown(wait=False)
                                raise Exception("ConnectionError")
                            except ConnectionRefusedError as e:
                                self.shutdown = True
                                self.max_execution_time = 0
                                self.task_manager = None
                                self.data_manager = None
                                self.executor.shutdown(wait=False)
                                raise Exception("ConnectionRefusedError")
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


        def update_feedback(self, task, agent, detail):
            if isinstance(detail, dict) and detail.get("policy_abort"):
                self.logger.warning("Decision BA stopped: %s", detail["policy_abort"])
                self.set_task_status(task.id, Task.failure, detail)
                self.shutdown = True
                return

            collab = next((c for c in self.collab_list if c["task"] == task.id), None)
            if collab == None:
                tag = agent.reflect(task, detail)
                task.status = Task.success if tag else Task.failure
                self.set_task_status(task.id, task.status, detail)

                for agent in self.agent_list:
                    if self.assignment.get(agent.name) == task.id:
                        self.assignment.pop(agent.name)

                self.logger.info(
                    f"task {task.description} has been executed, the result is {task.status}")
                self.task_manager.feedback_task(self.get_task_by_id(task.id))
                self.one_task_done = True

                return
            else:
                collab["complete agent"] += 1
                tag = agent.reflect(task, detail)
                task.status = Task.success if tag else Task.failure
                self.set_task_status(task.id, Task.success if tag else Task.failure, task.reflect)

                if collab["complete agent"] == collab["assign agent"]:
                    for agent in self.agent_list:
                        if self.assignment.get(agent.name) == task.id:
                            self.assignment.pop(agent.name)

                    self.logger.info(
                        f"task {task.description} has been executed, the result is {task.status}")

                    if task.status == Task.failure:
                        self.stop_after_fail_times -= 1
                    if task.status == Task.success:
                        self.stop_after_success_times -= 1

                    self.task_manager.feedback_task(self.get_task_by_id(task.id))
                    self.one_task_done = True

                    self.collab_list.remove(collab)


        @traced("AC", "task.feedback")
        def update_task_status(self, task, status, detail):
            collab = next((c for c in self.collab_list if c["task"] == task.id), None)
            if collab == None:
                task.status = status
                self.set_task_status(task.id, status, detail)

                for agent in self.agent_list:
                    if self.assignment.get(agent.name) == task.id:
                        self.assignment.pop(agent.name)

                self.logger.info(
                    f"task {task.description} has been executed, the result is {task.status}")

                if task.status == Task.failure:
                    self.stop_after_fail_times -= 1
                if task.status == Task.success:
                    self.stop_after_success_times -= 1

                self.task_manager.feedback_task(self.get_task_by_id(task.id))
                self.one_task_done = True

                return

            else:
                collab["complete agent"] += 1
                task.status = status
                self.set_task_status(task.id, status, detail)

                if collab["complete agent"] == collab["assign agent"]:
                    for agent in self.agent_list:
                        if self.assignment.get(agent.name) == task.id:
                            self.assignment.pop(agent.name)

                    self.logger.info(
                        f"task {task.description} has been executed, the result is {task.status}")
                    self.task_manager.feedback_task(self.get_task_by_id(task.id))
                    self.one_task_done = True

                    self.collab_list.remove(collab)


    # Preserve existing callers, overrides and ControllerExecution thread entry points.
    check_task_list_available = Scheduling.check_task_list_available
    execute_tasks = Scheduling.execute_tasks
    validate_assignments = Assignment.validate_assignments
    generate_prompt_and_get_response = Assignment.generate_prompt_and_get_response
    generate_decompose_prompt_and_get_response = Assignment.generate_decompose_prompt_and_get_response
    assign_tasks_to_agents = Assignment.assign_tasks_to_agents
    execute_assignments = Assignment.execute_assignments
    process_completed_tasks = Feedback.process_completed_tasks
    update_feedback = Feedback.update_feedback
    update_task_status = Feedback.update_task_status
