import multiprocessing
import os
import shutil
import random
import psutil
from pathlib import Path
from tracer import TRACE_ENV, Tracer, safe_emit, summarize, write_manifest

import time
from env.env import VillagerBench, env_type, Agent
from model.init_model import init_language_model
from model.role_models import configure_actor_model, resolve_role_models

start_time = time.time()
from pipeline.controller import GlobalController as FullController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
import json
from model.google_model import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_THINKING_LEVEL,
    GOOGLE_OPENAI_BASE_URL,
    load_google_api_keys,
)

LLM_API_BASE = GOOGLE_OPENAI_BASE_URL
LLM_API_MODEL = DEFAULT_GEMINI_MODEL
LLM_THINKING_LEVEL = DEFAULT_GEMINI_THINKING_LEVEL
CONFIG_PATH = os.environ.get("VILLAGER_BENCH_CONFIG_PATH", "base_agent_multi_test_config.json")

print(f"pipeline Time taken: {time.time() - start_time}")
start_time = time.time()

def validate_run_options(task_type: str, controller_mode: str = "full",
                         assignment_policy: str = "decomposer", role: str = "same") -> None:
    """Validate the retained run modes before I/O; unsupported choices raise ValueError."""
    archive = "archive/full-features-20261104"
    if controller_mode != "full":
        raise ValueError(f"Core uses Full Controller; other modes are on {archive}")
    if task_type not in {"construction", "farming", "puzzle"}:
        raise ValueError(f"Core supports Construction, Farming and Escape (puzzle); see {archive}")
    if assignment_policy not in {"decomposer", "controller"}:
        raise ValueError("assignment_policy must be decomposer or controller")
    if assignment_policy == "controller" and (task_type != "construction" or role != "same"):
        raise ValueError("Controller assignment currently requires homogeneous Construction agents")


def run(api_model: str, api_base: str, api_key_list: list, thinking_level: str, task_type: str, task_idx: int, agent_num: int, dig_needed: bool, max_task_num: int, task_goal: str, document_file: str, host: str, port: int, task_name: str, role: str = "same", document: dict = {}, controller_mode: str = "full", assignment_policy: str = "decomposer", model_roles=None):
    start_time = time.time()
    validate_run_options(task_type, controller_mode, assignment_policy, role)

    api_key_list = api_key_list or []
    llm_config = {"api_key": api_key_list[0] if api_key_list else "", "api_base": api_base, "api_model": api_model,
                  "thinking_level": thinking_level, "api_key_list": api_key_list}
    role_configs = resolve_role_models(model_roles, llm_config)
    if any(config["provider"] == "gemini" for config in role_configs.values()) and not api_key_list:
        raise ValueError("Gemini credentials are required by the selected model roles")
    all_local = all(config["provider"] == "ollama" for config in role_configs.values())
    ba_config = role_configs["ba"]
    configure_actor_model(Agent, ba_config)

    # Set env
    if task_type == "construction":
        env = VillagerBench(env_type=env_type.construction, task_id=task_idx, dig_needed=dig_needed, host=host, port=port, max_task_num=max_task_num, task_name=task_name, _virtual_debug=False)
    elif task_type == "farming":
        env = VillagerBench(env_type=env_type.farming, task_id=task_idx, dig_needed=False, host=host, port=port, max_task_num=max_task_num, task_name=task_name, _virtual_debug=False)
    elif task_type == "puzzle":
        env = VillagerBench(env_type=env_type.puzzle, task_id=task_idx, dig_needed=False, host=host, port=port, max_task_num=max_task_num, task_name=task_name, _virtual_debug=False)
    else:
        raise NotImplementedError

    env.local_generation_config = role_configs["td"] if all_local else None

    # Set agent_tool
    if task_type == "construction":
        agent_tool = [Agent.placeBlock, Agent.fetchContainerContents, Agent.MineBlock, Agent.scanNearbyEntities, Agent.equipItem,
                      Agent.navigateTo, Agent.withdrawItem, Agent.dismantleDirtLadder, Agent.erectDirtLadder, Agent.handoverBlock]
    elif task_type == "farming":
        agent_tool = [Agent.fetchContainerContents, Agent.MineBlock, Agent.scanNearbyEntities, Agent.equipItem, Agent.SmeltingCooking,
                      Agent.navigateTo, Agent.withdrawItem, Agent.craftBlock, Agent.attackTarget, Agent.useItemOnEntity,
                      Agent.handoverBlock]
    elif task_type == "puzzle":
        agent_tool = [Agent.placeBlock, Agent.fetchContainerContents, Agent.MineBlock, Agent.scanNearbyEntities, Agent.equipItem,
                      Agent.navigateTo, Agent.withdrawItem, Agent.ToggleAction, Agent.handoverBlock]
    else:
        raise NotImplementedError

    print(f"VillagerBench Time taken: {time.time() - start_time}")
    start_time = time.time()

    # Set agent_pool
    name_list = ["Alice", "Bob", "Cindy", "David", "Eve", "Frank", "Grace", "Helen", "Ivy", "Jack", "Kevin", "Lily",
                 "Mary", "Nancy", "Olivia", "Peter", "Queen", "Rose", "Sam", "Tom", "Umbrella", "Vivian", "Wendy",
                 "Xavier", "Yolanda", "Zoe"]
    if agent_num == 3 and task_type == "farming" and role == "different":
        agent_tool = [Agent.fetchContainerContents, Agent.scanNearbyEntities, Agent.equipItem,
                      Agent.navigateTo, Agent.withdrawItem, Agent.craftBlock, Agent.SmeltingCooking,
                      Agent.handoverBlock]
        env.agent_register(agent_tool=agent_tool, agent_number=1, name_list=[name_list[0]])
        agent_tool = [Agent.fetchContainerContents, Agent.scanNearbyEntities, Agent.equipItem,
                      Agent.navigateTo, Agent.withdrawItem, Agent.craftBlock, Agent.MineBlock,
                      Agent.handoverBlock]
        env.agent_register(agent_tool=agent_tool, agent_number=1, name_list=[name_list[1]])
        agent_tool = [Agent.fetchContainerContents, Agent.scanNearbyEntities, Agent.equipItem,
                      Agent.navigateTo, Agent.withdrawItem, Agent.craftBlock, Agent.attackTarget, 
                      Agent.handoverBlock]
        env.agent_register(agent_tool=agent_tool, agent_number=1, name_list=[name_list[2]])
    else:
        env.agent_register(agent_tool=agent_tool, agent_number=agent_num, name_list=name_list[:agent_num])

    with env.run(fast_api=False):  # Added a new parameter to control whether to use the fastapi server
        # Start DM
        dm = DataManager(silent=False)
        dm.update_database_init(env.get_init_state())

        print(f"DataManager Time taken: {time.time() - start_time}")
        start_time = time.time()

        # Start TM
        tm = TaskManager(silent=False, cache_enabled=False, assignment_policy=assignment_policy,
                         local_only=all_local)

        print(f"TaskManager Time taken: {time.time() - start_time}")
        start_time = time.time()

        # Set LLM
        tm_llm_config = role_configs["td"] if model_roles is not None else llm_config
        dm_llm_config = role_configs["sm"] if model_roles is not None else llm_config
        base_llm_config = ba_config if model_roles is not None else llm_config


        ctrl = FullController(llm_config, tm, dm, env,
                              ac_llm_config=role_configs["ac"] if model_roles is not None else None,
                              base_agent_config=base_llm_config if model_roles is not None else None,
                              tm_llm_config=tm_llm_config if model_roles is not None else None,
                              dm_llm_config=dm_llm_config if model_roles is not None else None)
        print(f"Controller mode: {controller_mode}; assignment policy: {assignment_policy}")


        if task_type == "farming": # Supplement prompt for supplementary materials
            with open("data/farm_setting.json", "r") as f:
                task_settings = json.load(f)
            task_data = task_settings[task_idx]
            task_goal += f"\nBelow is a detailed list of ingredients and their specific sources. Use this information to plan and coordinate your actions efficiently:\n"
            if "cake" in task_data["name"]:
                task_goal += f"egg: egg in chest\n"
                task_goal += f"milk: {task_data['milk']}\n"
                task_goal += f"wheat: {task_data['wheat']}\n"
                task_goal += f"sugar: {task_data['sugar']}\n"
            elif "rabbit_stew" in task_data["name"]:
                task_goal += f"cooked_rabbit: {task_data['cooked_rabbit']}\n"
                task_goal += f"baked_potato: {task_data['baked_potato']}\n"
                task_goal += f"carrot: {task_data['carrot']}\n"
                task_goal += f"brown_mushroom: {task_data['brown_mushroom']}\n"
                task_goal += f"bowl: {task_data['bowl']}\n"
                
        if os.path.exists(document_file):
            document["recipe"] = json.load((open(document_file)))
        tm.init_task(description=task_goal, document=document)

        ctrl.run()

        env.get_score()


if __name__ == "__main__":
    with open(CONFIG_PATH, "r") as f:
        launch_config = json.load(f)
    # shuffle 
    # launch_config = random.sample(launch_config, len(launch_config))
    for i, config in enumerate(launch_config):

        validate_run_options(config.get("task_type"), config.get("controller_mode", "full"),
                             config.get("assignment_policy", "decomposer"), config.get("role", "same"))

        policies = config.get("decision_policies")
        if not isinstance(policies, dict) or set(policies) != {"ba", "ac"}:
            raise ValueError("Set decision_policies with explicit ba and ac values")
        if policies["ba"] not in ("generative", "decision", "hybrid") or policies["ac"] not in ("generative", "decision"):
            raise ValueError("BA must be generative, decision or hybrid; AC must be generative or decision")
        if policies["ac"] == "decision":
            raise ValueError("Decision AC is not implemented; refusing to run a generative substitute")
        os.environ["VILLAGER_BA_POLICY"] = policies["ba"]
        os.environ.pop("VILLAGER_TEV1_REPEATED_PLACEMENT", None)

        role_configs = resolve_role_models(config.get("model_roles"),
                                          {"api_model": LLM_API_MODEL, "api_base": LLM_API_BASE})
        needs_gemini = any(role["provider"] == "gemini" for role in role_configs.values())
        api_key_list = load_google_api_keys() if needs_gemini else []
        if os.path.exists(f"result/{config['task_name']}"):
            print(f"task {config['task_name']} exists")
            continue
        result_dir = Path("result") / config["task_name"]
        result_dir.mkdir(parents=True, exist_ok=False)
        trace_dir = result_dir / "trace"
        tracer = Tracer(trace_dir, run_id=config["task_name"])
        all_local = all(role["provider"] == "ollama" for role in role_configs.values())
        uniform_models = {role["api_model"] for role in role_configs.values()}
        trace_settings = {**config, "controller_mode": "full", "model": next(iter(uniform_models)) if len(uniform_models) == 1 else "mixed",
                          "thinking_level": "disabled" if all_local else LLM_THINKING_LEVEL,
                          "td_provider": role_configs["td"]["provider"],
                          "td_model": role_configs["td"]["api_model"],
                          "td_num_ctx": role_configs["td"].get("num_ctx"),
                          "sm_provider": role_configs["sm"]["provider"],
                          "sm_model": role_configs["sm"]["api_model"],
                          "sm_num_ctx": role_configs["sm"].get("num_ctx"),
                          "ac_provider": role_configs["ac"]["provider"],
                          "ac_model": role_configs["ac"]["api_model"],
                          "ac_num_ctx": role_configs["ac"].get("num_ctx"),
                          "ba_provider": role_configs["ba"]["provider"],
                          "ba_model": role_configs["ba"]["api_model"],
                          "ba_num_ctx": role_configs["ba"].get("num_ctx")}
        write_manifest(trace_dir, trace_settings)
        previous_trace_dir = os.environ.get(TRACE_ENV)
        os.environ[TRACE_ENV] = str(trace_dir.resolve())
        run_started = time.monotonic()
        safe_emit(tracer, "RUN", "run.start")
        print(f"task {i+1}/{len(launch_config)} start")
        print("config:", config)
        with open(".cache/meta_setting.json", "w") as f:
            json.dump(config, f, indent=4)
        config.pop("evaluation_arg", None) # Scenario-specific scoring arguments are not actor input
        with open(".cache/load_status.cache", "w") as f:
            json.dump({"status": "start"}, f, indent=4)
        if os.path.exists(".cache/heart_beat.cache"):
            os.remove(".cache/heart_beat.cache")

        llm_config = {
            "api_key": api_key_list[0] if api_key_list else "",
            "api_base": LLM_API_BASE,
            "api_model": LLM_API_MODEL,
            "thinking_level": LLM_THINKING_LEVEL,
            "api_key_list": api_key_list
        }

        process = multiprocessing.Process(target=run,
                                            args=(llm_config["api_model"],
                                                llm_config["api_base"],
                                                llm_config["api_key_list"],
                                                llm_config["thinking_level"],
                                                config["task_type"],
                                                config["task_idx"],
                                                config["agent_num"],
                                                config.get("dig_needed", False),
                                                config.get("max_task_num", 0),
                                                config["task_goal"],
                                                config.get("document_file", ""),
                                                config["host"],
                                                config["port"],
                                                config["task_name"],
                                                config.get("role", "same"),
                                                config.get("evaluation_arg", {}),
                                                config.get("controller_mode", "full"),
                                                config.get("assignment_policy", "decomposer"),
                                                config.get("model_roles")
                                            )
                                          )
        process.start()

        parent = psutil.Process(process.pid)

        termination = "interrupted"
        try:
            while True:
                time.sleep(1)
                try:
                    with open(".cache/load_status.cache", "r") as f:
                        status = json.load(f)["status"]
                except (OSError, ValueError, KeyError):
                    status = None
                if status == "end":
                    termination = "judger_end"
                elif (trace_dir / "policy_abort.json").exists():
                    termination = "policy_abort"
                elif not process.is_alive():
                    termination = "process_exited"
                elif os.path.exists(".cache/heart_beat.cache"):
                    try:
                        with open(".cache/heart_beat.cache", "r") as f:
                            env_time = json.load(f)["time"]
                        if time.time() - env_time > 10:
                            termination = "heartbeat_timeout"
                    except (OSError, ValueError, KeyError):
                        pass
                if termination == "interrupted":
                    continue
                if process.is_alive():
                    try:
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()
                    except psutil.Error:
                        pass
                process.join(timeout=5)
                # A judger may already have moved these files. Never overwrite it.
                for name in ("action_log.json", "tokens.json"):
                    source, target = Path("data") / name, result_dir / name
                    if source.exists() and not target.exists():
                        shutil.copy2(source, target)
                break
        finally:
            safe_emit(tracer, "RUN", "run.end", result_status=termination,
                      duration_s=time.monotonic() - run_started)
            try:
                summarize(trace_dir, termination)
            except (OSError, ValueError, TypeError) as exc:
                print(f"Trace summary failed: {type(exc).__name__}")
            if previous_trace_dir is None:
                os.environ.pop(TRACE_ENV, None)
            else:
                os.environ[TRACE_ENV] = previous_trace_dir

        print(f"task {i+1} end")
