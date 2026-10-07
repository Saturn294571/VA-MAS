"""One-round Construction Task Decomposer / Agent Controller probe.

No Minecraft connection, actor creation, task execution, or benchmark scoring.
The environment is an explicit synthetic snapshot, not a live server observation.

Examples:
    .venv/bin/python td_ac_probe.py --self-test
    .venv/bin/python td_ac_probe.py --live --task-idx 25
    .venv/bin/python td_ac_probe.py --replay result/previous/probe.json
"""

import argparse
import json
import logging
import os
from pathlib import Path
import re
import tempfile
from dataclasses import dataclass

import networkx as nx
from openai import OpenAI

from model.google_model import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_THINKING_LEVEL,
    GOOGLE_OPENAI_BASE_URL,
    GoogleLanguageModel,
)
from pipeline.controller import GlobalController
from pipeline.task_manager import TaskManager
from type_define.graph import Graph


REPO = Path(__file__).resolve().parent
GOAL = (
    "Using the provided blueprint, collaborate to place the required blocks in "
    "Minecraft. You can use materials from your inventory or the supply chest. "
    "The task is complete once the blueprint is fully built."
)


@dataclass
class ProbeAgent:
    name: str

    def to_json(self):
        return {"name": self.name, "state": "free", "tools": "same Construction tools"}


class SnapshotDataManager:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def query_env_with_task(self, _task):
        return self.snapshot


class NoRetryGoogleModel(GoogleLanguageModel):
    """Use the existing adapter/accounting with one attempt per probe call."""

    def _new_client(self):
        return OpenAI(api_key=self.api_key, base_url=self.api_base,
                      max_retries=0, timeout=30.0)

    def few_shot_generate_thoughts(self, *args, **kwargs):
        return GoogleLanguageModel.few_shot_generate_thoughts.__wrapped__(
            self, *args, **kwargs
        )


class FixtureModel:
    def __init__(self, responses):
        self.responses = iter(responses)

    def few_shot_generate_thoughts(self, *args, **kwargs):
        return next(self.responses)


def snapshot_for(task_idx, blueprint, names):
    materials = sorted({block["name"] for block in blueprint["blocks"]})
    return (
        "Synthetic pre-execution snapshot for a planning-only probe; no live "
        "Minecraft observation. Flat peaceful world; the construction site is "
        "clear and unchanged. "
        + "; ".join(f"{name} is free at [-4, -59, 1]" for name in names)
        + ". Each agent has the same Construction tools. The shared supply "
        "chest is at [-4, -60, 0] and has enough " + ", ".join(materials)
        + f". Sign info: {blueprint['name']} (Task{task_idx})."
    )


def make_fixture():
    td = [
        {"id": 1, "description": "Place the bottom stone-brick supports",
         "milestones": ["Bottom supports placed"], "retrieval paths": [],
         "required subtasks": [], "assigned agents": ["Alice", "Bob", "Cindy"]},
        {"id": 2, "description": "Place middle stone bricks after bottom supports",
         "milestones": ["Middle supports placed"], "retrieval paths": [],
         "required subtasks": [1], "assigned agents": ["Alice", "Bob", "Cindy"]},
    ]
    ac = [{"reason": "All agents are eligible", "task_id": "0", "agent": "Alice"}]
    return FixtureModel([json.dumps(td), json.dumps(ac)])


def run_probe(task_idx, model, output_dir):
    with (REPO / "data/building_blue_print.json").open(encoding="utf-8") as file:
        blueprints = json.load(file)
    if not 0 <= task_idx < len(blueprints):
        raise ValueError(f"Unknown Construction task index: {task_idx}")
    with (REPO / "data/blueprint_description_all.json").open(encoding="utf-8") as file:
        recipes = json.load(file)
    recipe = recipes.get(f"task_{task_idx}")
    if not recipe:
        raise ValueError(f"No precomputed recipe for Task{task_idx}")

    names = ["Alice", "Bob", "Cindy"]
    agents = [ProbeAgent(name) for name in names]
    snapshot = snapshot_for(task_idx, blueprints[task_idx], names)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    original_cwd = Path.cwd()
    original_graph_writer = Graph.write_graph_to_md

    with tempfile.TemporaryDirectory(prefix="villager-td-ac-") as scratch:
        try:
            os.chdir(scratch)
            for directory in ("img", "logs", "result", "data", ".cache"):
                Path(directory).mkdir()
            Path(".cache/meta_setting.json").write_text(
                json.dumps({"task_name": "td_ac_probe"}), encoding="utf-8"
            )
            # The production writer starts a background thread. Write synchronously
            # so the temporary directory can be removed only after it is complete.
            Graph.write_graph_to_md = Graph._write_graph_to_md

            tm = TaskManager(silent=True, cache_enabled=False,
                             assignment_policy="controller")
            tm.agent_list = agents
            tm.dm = SnapshotDataManager(snapshot)
            tm.llm = model if model is not None else NoRetryGoogleModel(
                api_model=DEFAULT_GEMINI_MODEL,
                api_base=GOOGLE_OPENAI_BASE_URL,
                thinking_level=DEFAULT_GEMINI_THINKING_LEVEL,
                role_name="TaskManager",
            )
            tm.init_task(GOAL, {"recipe": recipe})

            graph = tm.graph
            dag = nx.DiGraph()
            dag.add_nodes_from(graph.vertex)
            dag.add_edges_from(graph.edge)
            acyclic = nx.is_directed_acyclic_graph(dag)
            nodes = graph.vertex
            indices = {node: idx for idx, node in enumerate(nodes)}
            expected_positions = {
                tuple(block["position"]) for block in blueprints[task_idx]["blocks"]
                if block["name"] not in ("air", "water", "lava")
            }
            x_offset = (-blueprints[task_idx]["size"][0]) // 2 - 8
            expected_positions = {
                (x + x_offset, y - 60, z) for x, y, z in expected_positions
            }
            explicitly_planned = set()
            for node in nodes:
                for milestone in node.milestones:
                    if "plac" not in milestone.lower():
                        continue
                    for x, y, z in re.findall(
                        r"\[(-?\d+),\s*(-?\d+),\s*(-?\d+)\]", milestone
                    ):
                        explicitly_planned.add((int(x), int(y), int(z)))
            invalid_dependencies = [
                {"task_id": idx, "predecessor_id": predecessor}
                for idx, node in enumerate(nodes)
                for predecessor in node._pre_idxs
                if predecessor < 1 or predecessor > len(nodes) or predecessor == idx + 1
            ]
            result = {
                "task_idx": task_idx,
                "environment_source": "synthetic snapshot; not a live Minecraft run",
                "actor_calls": 0,
                "minecraft_connections": 0,
                "blueprint": blueprints[task_idx]["name"],
                "recipe": recipe,
                "environment_snapshot": snapshot,
                "task_goal": GOAL,
                "td_response": tm.history["response"][0],
                "nodes": [
                    {"id": idx, "description": node.description,
                     "required_subtask_ids": node._pre_idxs,
                     "candidates": node.candidate_list,
                     "required_agents": node.number}
                    for idx, node in enumerate(nodes)
                ],
                "edges": [[indices[src], indices[dst]] for src, dst in graph.edge],
                "acyclic": acyclic,
                "invalid_dependencies": invalid_dependencies,
                "first_round_explicit_block_coverage": {
                    "covered": len(expected_positions & explicitly_planned),
                    "total": len(expected_positions),
                    "not_explicitly_planned": sorted(
                        expected_positions - explicitly_planned
                    ),
                    "interpretation": "Initial horizon only; missing blocks may be planned after feedback.",
                },
            }
            if not acyclic or invalid_dependencies:
                result["ac_skipped_reason"] = (
                    "invalid or cyclic graph; predecessor traversal/assignment is unsafe"
                )
            else:
                ctrl = GlobalController.__new__(GlobalController)
                ctrl.agent_list = agents
                ctrl.assignment = {}
                ctrl.name_list = names
                ctrl.task_list = tm.query_subtask_list()
                ctrl.logger = logging.getLogger("td_ac_probe")
                ctrl.llm = model if model is not None else NoRetryGoogleModel(
                    api_model=DEFAULT_GEMINI_MODEL,
                    api_base=GOOGLE_OPENAI_BASE_URL,
                    thinking_level=DEFAULT_GEMINI_THINKING_LEVEL,
                    role_name="GlobalController",
                )
                ready = ctrl.check_task_list_available()
                result["ready_task_ids"] = [indices[task] for task in ready]
                if ready:
                    # Mirror the full Controller's LLM selection path. Do not call
                    # execute_assignments(), run(), worker(), or BaseAgent.step().
                    proposal = ctrl.generate_prompt_and_get_response(
                        [snapshot], [], [agent.to_json() for agent in agents]
                    )
                    accepted = ctrl.validate_assignments(proposal)
                    result["ac_proposal"] = proposal
                    result["ac_accepted"] = [
                        {"task_id": indices[item["task_instance"]],
                         "agents": [agent.name for agent in item["agent_instances"]]}
                        for item in accepted
                    ]
                else:
                    result["ac_skipped_reason"] = "no ready task"

            token_file = Path("data/tokens.json")
            if token_file.exists():
                result["tokens"] = json.loads(token_file.read_text(encoding="utf-8"))
            (output_dir / "probe.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return result
        finally:
            Graph.write_graph_to_md = original_graph_writer
            os.chdir(original_cwd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true", help="No API calls")
    mode.add_argument("--live", action="store_true", help="Exactly one TD and at most one AC API call")
    mode.add_argument("--replay", type=Path, help="Recheck saved LLM responses without API calls")
    parser.add_argument("--task-idx", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    replay = None
    if args.replay:
        replay = json.loads(args.replay.read_text(encoding="utf-8"))
        args.task_idx = replay["task_idx"]
        responses = [replay["td_response"]]
        if replay.get("ac_proposal") is not None:
            responses.append(json.dumps(replay["ac_proposal"]))
        model = FixtureModel(responses)
    else:
        model = make_fixture() if args.self_test else None
    output = args.output or REPO / "result" / (
        f"td_ac_probe_task{args.task_idx}_"
        f"{'selftest' if args.self_test else 'replay' if args.replay else 'live'}"
    )
    result = run_probe(args.task_idx, model, output)
    if replay:
        result["replayed_from"] = str(args.replay)
        result["original_tokens"] = replay.get("tokens")
        (output / "probe.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    print(json.dumps({
        "output": str(output),
        "nodes": len(result["nodes"]),
        "edges": len(result["edges"]),
        "acyclic": result["acyclic"],
        "ready": result.get("ready_task_ids", []),
        "accepted": result.get("ac_accepted", []),
        "requests": result.get("tokens", {}).get("successful_requests", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
