"""Optional Tev1 decisions for explicitly specified repeated construction blocks."""

from __future__ import annotations

import re
from typing import Any, Callable

from env.action_policy import guarded_tools
from model.ollama_decision import choose
from tracer import current_tracer, safe_emit


_BLOCK = re.compile(r"^\s*(?:place\s+)?([a-z][a-z0-9_ ]*?)\s+(?:placed\s+|placed successfully\s+)?at\s+\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]\s*[.!]?\s*$", re.I)
_OPTIONAL_ACQUIRE = re.compile(r"^\s*(?:obtain|retrieve)\s+.+?\s+from\s+(?:the\s+)?chest\s+at\s+\[\s*-?\d+\s*,\s*-?\d+\s*,\s*-?\d+\s*\]\s*[.!]?\s*$", re.I)
_MULTI = re.compile(r"^\s*place\s+([a-z][a-z0-9_ ]*?)\s+at\s+(.+)$", re.I)
_COORD = re.compile(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]")


def targets(task: dict[str, Any]) -> list[tuple[str, int, int, int]]:
    """Recognize only homogeneous, explicit placement milestones; reject ambiguity."""
    milestones = task.get("milestones")
    if not isinstance(milestones, list) or not 2 <= len(milestones) <= 33:
        return []
    if isinstance(milestones[0], str) and _OPTIONAL_ACQUIRE.fullmatch(milestones[0]):
        if "if necessary" not in str(task.get("description", "")).lower():
            return []
        milestones = milestones[1:]
    elif (isinstance(milestones[0], str) and
          re.fullmatch(r"\s*retrieve\s+[a-z0-9_ ]+\s+from inventory or nearby chests\s*[.!]?\s*", milestones[0], re.I)):
        milestones = milestones[1:]
    if len(milestones) == 1 and isinstance(milestones[0], str):
        match = _MULTI.fullmatch(milestones[0])
        if match:
            name, text = match.groups()
            coords = _COORD.findall(text)
            rest = _COORD.sub("", text)
            if 2 <= len(coords) <= 32 and not re.sub(r"\band\b|[,\s.]", "", rest, flags=re.I):
                return [(name.lower().replace(" ", "_"), *map(int, coord)) for coord in coords] if len(set(coords)) == len(coords) else []
    if len(milestones) < 2:
        return []
    result = []
    for milestone in milestones:
        match = _BLOCK.fullmatch(milestone) if isinstance(milestone, str) else None
        if not match:
            return []
        name, x, y, z = match.groups()
        result.append((name.lower().replace(" ", "_"), int(x), int(y), int(z)))
    if len({x[0] for x in result}) != 1 or len(set(result)) != len(result):
        return []
    return result


def run_segment(context: dict[str, Any], tools: list, events: list,
                select: Callable = choose) -> dict[str, Any] | None:
    """Run bounded decisions; return feedback for the generative actor to continue."""
    blocks = targets(context["task"])
    if not blocks or not any(t.name == "placeBlock" for t in tools):
        return None
    relevant = str(context.get("observation", {}).get("relevant_data", ""))
    facing = re.search(r"facing\s*:\s*([A-Za-z]+)", relevant)
    if not facing or facing.group(1) != "A":
        return None
    wrapped = {t.name: t for t in guarded_tools(context, tools, events, "tev1_repeated_placement")}
    decisions, completed = [], []
    feedback: Any = None
    reason = "completed_segment"
    for block, x, y, z in blocks[:context["budget"]["remaining_steps"]]:
        state = {"task": context["task"], "next": {"item": block, "position": [x, y, z]},
                 "completed": completed, "last_feedback": feedback,
                 "observation": context["observation"]}
        try:
            choice = select(state, {"place": "Place the next specified block at its target position.",
                                    "handoff": "Stop and ask the generative actor to inspect or recover."})
        except Exception as exc:
            reason = "decision_error:" + type(exc).__name__
            break
        decisions.append({"choice": choice, "target": [x, y, z], "item": block})
        safe_emit(current_tracer(), "BA", "decision.selected", policy="tev1_repeated_placement",
                  decision_id=context["decision_id"], agent_id=context["agent_name"], reason=choice)
        if choice != "place":
            reason = "model_handoff"
            break
        args = {"player_name": context["agent_name"], "item_name": block, "x": x, "y": y,
                "z": z, "facing": "A", "emotion": [], "murmur": ""}
        try:
            feedback = wrapped["placeBlock"].run(args)
        except Exception as exc:
            reason = "tool_error:" + type(exc).__name__
            break
        status = feedback.get("status") if isinstance(feedback, dict) else None
        if status is not True and status != "True":
            reason = "placement_unconfirmed"
            break
        completed.append({"item": block, "position": [x, y, z], "evidence": "tool_feedback"})
    if reason == "completed_segment" and len(completed) < len(blocks):
        reason = "step_budget"
    return {"policy": "tev1_repeated_placement", "decisions": decisions,
            "completed": completed, "last_feedback": feedback, "reason": reason}
