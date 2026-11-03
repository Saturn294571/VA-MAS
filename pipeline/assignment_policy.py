"""Common assignment contract for the existing VA Controller policies.

It preserves TD candidate restrictions and validates proposed assignments
before dispatch, enabling later comparison of worker-selection policies.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Protocol, TypedDict
from uuid import uuid4


class TaskSnapshot(TypedDict):
    task_id: str
    legacy_index: int
    status: str
    available: bool
    predecessor_ids: list[str]
    predecessors_successful: bool
    candidate_ids: list[str]
    required_agents: int


class AgentSnapshot(TypedDict):
    agent_id: str
    free: bool


class AssignmentContext(TypedDict):
    decision_id: str
    graph_valid: bool
    graph_error: str | None
    tasks: list[TaskSnapshot]
    agents: list[AgentSnapshot]
    observation: dict[str, Any]


class Assignment(TypedDict):
    task_id: str
    agent_ids: list[str]


class AssignmentDecision(TypedDict):
    kind: str
    assignments: list[Assignment]
    source: str


class AssignmentPolicy(Protocol):
    def select(self, context: AssignmentContext) -> AssignmentDecision:
        """Return proposed assignments or defer; validation is a separate step."""


class Rejection(TypedDict):
    index: int | None
    reason: str


def _graph_ancestors(graph: Any) -> tuple[dict[str, set[str]], str | None]:
    if graph is None or not hasattr(graph, "vertex") or not hasattr(graph, "edge"):
        return {}, "graph_unavailable"
    nodes = graph.vertex
    ids = [getattr(node, "id", None) for node in nodes]
    if any(not isinstance(node_id, str) or not node_id for node_id in ids) or len(ids) != len(set(ids)):
        return {}, "invalid_graph_nodes"
    node_by_id = dict(zip(ids, nodes))
    successors = {node_id: set() for node_id in ids}
    indegree = {node_id: 0 for node_id in ids}
    for edge in graph.edge:
        if not isinstance(edge, (tuple, list)) or len(edge) != 2:
            return {}, "invalid_graph_edge"
        src, dst = edge
        src_id, dst_id = getattr(src, "id", None), getattr(dst, "id", None)
        if (src_id not in node_by_id or dst_id not in node_by_id
                or node_by_id[src_id] is not src or node_by_id[dst_id] is not dst):
            return {}, "invalid_graph_edge"
        if dst_id not in successors[src_id]:
            successors[src_id].add(dst_id)
            indegree[dst_id] += 1
    ready = deque(node_id for node_id in ids if indegree[node_id] == 0)
    ancestors = {node_id: set() for node_id in ids}
    visited = 0
    while ready:
        src = ready.popleft()
        visited += 1
        for dst in successors[src]:
            ancestors[dst].update(ancestors[src])
            ancestors[dst].add(src)
            indegree[dst] -= 1
            if indegree[dst] == 0:
                ready.append(dst)
    if visited != len(ids):
        return {}, "graph_cycle"
    return ancestors, None


def graph_error(graph: Any) -> str | None:
    """Return a graph structural error before any predecessor traversal."""
    return _graph_ancestors(graph)[1]


def make_assignment_context(
    tasks: list[Any], agents: list[Any], assignment: dict[str, Any], graph: Any,
    observation: dict[str, Any] | None = None,
) -> AssignmentContext:
    """Snapshot current task/agent constraints; an invalid graph fails closed."""
    ancestors, error = _graph_ancestors(graph)
    names = [agent.name for agent in agents]
    graph_nodes = {node.id: node for node in graph.vertex} if error is None else {}
    snapshots: list[TaskSnapshot] = []
    for index, task in enumerate(tasks):
        if error is None and (task.id not in graph_nodes or graph_nodes[task.id] is not task):
            error = "task_not_in_graph"
        predecessors = ancestors.get(task.id, set())
        snapshots.append({
            "task_id": task.id, "legacy_index": index, "status": task.status,
            "available": bool(task.available), "predecessor_ids": sorted(predecessors),
            "predecessors_successful": all(graph_nodes[p].status == "success" for p in predecessors),
            "candidate_ids": list(task.candidate_list) if task.candidate_list else list(names),
            "required_agents": task.number,
        })
    return {"decision_id": uuid4().hex, "graph_valid": error is None, "graph_error": error,
            "tasks": snapshots, "agents": [{"agent_id": name, "free": assignment.get(name) is None}
                                           for name in names], "observation": observation or {}}


def from_legacy_proposal(
    context: AssignmentContext, proposal: Any, source: str = "llm",
) -> tuple[AssignmentDecision, list[Rejection]]:
    """Convert legacy zero-based task indexes to UUIDs without correcting invalid output."""
    decision: AssignmentDecision = {"kind": "assign", "assignments": [], "source": source}
    rejected: list[Rejection] = []
    if not isinstance(proposal, list):
        return decision, [{"index": None, "reason": "invalid_response"}]
    for index, item in enumerate(proposal):
        if not isinstance(item, dict):
            rejected.append({"index": index, "reason": "invalid_item"})
            continue
        raw_index = item.get("task_id")
        if isinstance(raw_index, bool) or not (isinstance(raw_index, int) or
                                               isinstance(raw_index, str) and raw_index.isdigit()):
            rejected.append({"index": index, "reason": "invalid_task_index"})
            continue
        try:
            task_index = int(raw_index)
        except ValueError:
            rejected.append({"index": index, "reason": "invalid_task_index"})
            continue
        if task_index < 0 or task_index >= len(context["tasks"]):
            rejected.append({"index": index, "reason": "unknown_task"})
            continue
        raw_agents = item.get("agent")
        raw_agents = raw_agents if isinstance(raw_agents, list) else [raw_agents]
        agent_ids = [getattr(agent, "name", agent) for agent in raw_agents]
        if not all(isinstance(agent, str) for agent in agent_ids):
            rejected.append({"index": index, "reason": "invalid_agents"})
            continue
        decision["assignments"].append({"task_id": context["tasks"][task_index]["task_id"],
                                        "agent_ids": agent_ids})
    return decision, rejected


class LegacyAssignmentPolicy:
    """Adapt one existing Controller LLM response to the shared policy output.

    The model call remains in the existing Controller; malformed legacy items
    are exposed in ``rejections`` rather than silently repaired.
    """

    def __init__(self, proposal: Any):
        self.proposal = proposal
        self.rejections: list[Rejection] = []

    def select(self, context: AssignmentContext) -> AssignmentDecision:
        decision, self.rejections = from_legacy_proposal(context, self.proposal)
        return decision


def validate_assignment(
    context: AssignmentContext, decision: AssignmentDecision, *, allow_multi_agent: bool = True,
) -> tuple[list[Assignment], list[Rejection]]:
    """Validate an ordered batch; independent valid items survive invalid proposals."""
    if not context["graph_valid"]:
        return [], [{"index": None, "reason": context["graph_error"] or "invalid_graph"}]
    if decision.get("kind") == "defer" and decision.get("assignments") == []:
        return [], []
    if decision.get("kind") != "assign" or not isinstance(decision.get("assignments"), list):
        return [], [{"index": None, "reason": "invalid_decision"}]
    tasks = {task["task_id"]: task for task in context["tasks"]}
    agents = {agent["agent_id"]: agent for agent in context["agents"]}
    reserved_tasks: set[str] = set()
    reserved_agents: set[str] = set()
    accepted: list[Assignment] = []
    rejected: list[Rejection] = []
    for index, item in enumerate(decision["assignments"]):
        if not isinstance(item, dict) or not isinstance(item.get("task_id"), str):
            rejected.append({"index": index, "reason": "invalid_item"})
            continue
        task_id, selected = item["task_id"], item.get("agent_ids")
        task = tasks.get(task_id)
        reason = None
        if task is None:
            reason = "unknown_task"
        elif task_id in reserved_tasks:
            reason = "duplicate_task"
        elif task["status"] != "unknown" or not task["available"]:
            reason = "task_unavailable"
        elif not task["predecessors_successful"]:
            reason = "predecessor_not_successful"
        elif not isinstance(selected, list) or not all(isinstance(a, str) for a in selected):
            reason = "invalid_agents"
        elif not isinstance(task["required_agents"], int) or isinstance(task["required_agents"], bool) or task["required_agents"] < 1:
            reason = "invalid_required_agents"
        elif not allow_multi_agent and task["required_agents"] != 1:
            reason = "unsupported_multi_agent"
        elif len(selected) != task["required_agents"] or len(set(selected)) != len(selected):
            reason = "agent_count_or_duplicate"
        elif any(name not in agents for name in selected):
            reason = "unknown_agent"
        elif any(name not in task["candidate_ids"] for name in selected):
            reason = "ineligible_agent"
        elif any(not agents[name]["free"] or name in reserved_agents for name in selected):
            reason = "agent_busy_or_reserved"
        if reason:
            rejected.append({"index": index, "reason": reason})
            continue
        accepted.append(item)
        reserved_tasks.add(task_id)
        reserved_agents.update(selected)
    return accepted, rejected


def controller_context(controller: Any) -> AssignmentContext:
    """Snapshot a Controller; missing TaskManager/graph is an invalid context."""
    manager = getattr(controller, "task_manager", None)
    return make_assignment_context(controller.task_list, controller.agent_list,
                                   controller.assignment, getattr(manager, "graph", None))


def _report_rejections(controller: Any, context: AssignmentContext, source: str,
                       rejected: list[Rejection], *, stage: str = "validation") -> None:
    from tracer import current_tracer, safe_emit
    for rejection in rejected:
        controller.logger.warning("Assignment rejected at %s: %s (item %s)", stage,
                                  rejection["reason"], rejection["index"])
        safe_emit(current_tracer(), "AC", "assignment.rejected", decision_id=context["decision_id"],
                  assignment_mode=source, reason=rejection["reason"])


def _to_controller_assignments(controller: Any, accepted: list[Assignment],
                               decision_id: str) -> list[dict[str, Any]]:
    tasks = {task.id: task for task in controller.task_list}
    agents = {agent.name: agent for agent in controller.agent_list}
    return [{"task_instance": tasks[item["task_id"]], "decision_id": decision_id,
             "agent_instances": [agents[name] for name in item["agent_ids"]]} for item in accepted]


def validate_controller_proposal(
    controller: Any, proposal: Any, *, allow_multi_agent: bool = True,
) -> list[dict[str, Any]]:
    """Adapt and validate a legacy LLM batch; rejected items are logged."""
    context = controller_context(controller)
    policy = LegacyAssignmentPolicy(proposal)
    decision = policy.select(context)
    accepted, invalid = validate_assignment(context, decision, allow_multi_agent=allow_multi_agent)
    _report_rejections(controller, context, "llm", policy.rejections, stage="legacy_format")
    _report_rejections(controller, context, "llm", invalid)
    return _to_controller_assignments(controller, accepted, context["decision_id"])


def revalidate_controller_assignments(
    controller: Any, assignments: list[dict[str, Any]], *, source: str,
    allow_multi_agent: bool = True,
) -> list[dict[str, Any]]:
    """Recheck live state just before dispatch; invalid items are not executed."""
    context = controller_context(controller)
    proposed: list[Assignment] = []
    malformed: list[Rejection] = []
    for index, item in enumerate(assignments):
        try:
            task_id = item["task_instance"].id
            agents = [agent.name for agent in item["agent_instances"]]
        except (KeyError, TypeError, AttributeError):
            malformed.append({"index": index, "reason": "invalid_item"})
            continue
        proposed.append({"task_id": task_id, "agent_ids": agents})
    decision: AssignmentDecision = {"kind": "assign", "assignments": proposed, "source": source}
    accepted, rejected = validate_assignment(context, decision, allow_multi_agent=allow_multi_agent)
    _report_rejections(controller, context, source, malformed + rejected)
    return _to_controller_assignments(controller, accepted, context["decision_id"])
