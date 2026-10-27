"""Shared action contract for Minecraft actor policies.

The current ReAct actor remains the generative baseline. Its tools pass through
the same validator that a future ActionPolicy implementation will use.
"""

from __future__ import annotations

import time
from typing import Any, Protocol, TypedDict
from uuid import uuid4

from langchain_core.tools import StructuredTool


class ActionContext(TypedDict):
    decision_id: str
    agent_name: str
    task: dict[str, Any]
    observation: dict[str, Any]
    history: list[dict[str, Any]]
    allowed_tools: list[dict[str, Any]]
    budget: dict[str, Any]


class ActionDecision(TypedDict):
    kind: str  # invoke | finish | defer
    tool_name: str | None
    tool_args: dict[str, Any] | None
    message: str | None


class ActionPolicy(Protocol):
    def select(self, context: ActionContext) -> ActionDecision:
        """Choose one action; invalid output is rejected by the common validator."""


def tool_spec(tool: StructuredTool) -> dict[str, Any]:
    """Expose the executable tool's argument schema, not a prompt-only list."""
    return {
        "name": tool.name,
        "description": tool.description,
        "args_schema": tool.args_schema.schema(),
    }


def make_action_context(
    agent_name: str,
    task: dict[str, Any],
    observation: dict[str, Any],
    tools: list[StructuredTool],
    remaining_steps: int,
    decision_timeout_s: float = 120.0,
) -> ActionContext:
    """Build one actor invocation's shared input; caller supplies the snapshot."""
    return {
        "decision_id": uuid4().hex,
        "agent_name": agent_name,
        "task": task,
        "observation": observation,
        "history": [],
        "allowed_tools": [tool_spec(tool) for tool in tools],
        "budget": {
            "remaining_steps": remaining_steps,
            "decision_timeout_s": decision_timeout_s,
        },
    }


def validate_action(
    context: ActionContext, decision: ActionDecision, tools: list[StructuredTool]
) -> tuple[bool, str]:
    """Check an action before execution; return (valid, reason)."""
    kind = decision.get("kind")
    if kind in ("finish", "defer"):
        if decision.get("tool_name") is not None or decision.get("tool_args") is not None:
            return False, "invalid_args"
        return True, "valid"
    if kind != "invoke":
        return False, "invalid_kind"

    name = decision.get("tool_name")
    allowed = {spec["name"] for spec in context["allowed_tools"]}
    by_name = {tool.name: tool for tool in tools}
    if not isinstance(name, str) or name not in allowed or name not in by_name:
        return False, "invalid_choice"
    args = decision.get("tool_args")
    if not isinstance(args, dict) or args.get("player_name") != context["agent_name"]:
        return False, "invalid_args"

    schema = by_name[name].args_schema.schema()
    properties = schema.get("properties", {})
    if any(key not in properties for key in args):
        return False, "invalid_args"
    if any(key not in args for key in schema.get("required", [])):
        return False, "invalid_args"
    primitive_types = {"string": str, "integer": int, "number": (int, float),
                       "array": list, "object": dict, "boolean": bool}
    for key, value in args.items():
        expected = properties[key].get("type")
        if expected in primitive_types:
            if expected in ("integer", "number") and isinstance(value, bool):
                return False, "invalid_args"
            if not isinstance(value, primitive_types[expected]):
                return False, "invalid_args"
    if name == "placeBlock" and args.get("facing") not in ("W", "E", "S", "N", "x", "y", "z", "A"):
        return False, "invalid_args"
    return True, "valid"


def guarded_tools(
    context: ActionContext, tools: list[StructuredTool], events: list[dict[str, Any]]
) -> list[StructuredTool]:
    """Keep the existing ReAct loop while validating every executable call."""
    wrapped = []
    for original in tools:
        def invoke(_original=original, **kwargs: Any) -> Any:
            decision: ActionDecision = {
                "kind": "invoke", "tool_name": _original.name,
                "tool_args": kwargs, "message": None,
            }
            valid, reason = validate_action(context, decision, tools)
            event = {
                "call_id": f"{context['decision_id']}:call:{len(events) + 1}",
                "decision": decision, "validation": reason,
                "policy": "legacy_react", "validation_stage": "before_execution",
                "history_length_before": len(context["history"]),
            }
            events.append(event)
            if not valid:
                event["execution"] = "not_called"
                feedback = {"message": f"Action rejected: {reason}", "status": False}
                context["history"].append({"tool": _original.name, "args": kwargs,
                                           "feedback": feedback})
                return feedback
            started = time.monotonic()
            try:
                feedback = _original.run(kwargs)
            except Exception as exc:
                event["execution"] = "exception"
                event["error_type"] = type(exc).__name__
                raise
            finally:
                event["execution_duration_s"] = time.monotonic() - started
            event["execution"] = "called"
            event["feedback"] = feedback
            context["history"].append({"tool": _original.name, "args": kwargs,
                                       "feedback": feedback})
            return feedback

        wrapped.append(StructuredTool.from_function(
            func=invoke,
            name=original.name,
            description=original.description,
            args_schema=original.args_schema,
            return_direct=original.return_direct,
        ))
    return wrapped


def complete_legacy_trace(
    context: ActionContext,
    action_list: list[dict[str, Any]],
    events: list[dict[str, Any]],
    final_answer: str,
    tools: list[StructuredTool],
) -> dict[str, Any]:
    """Include actions handled inside LangChain, including unknown tools."""
    trace = []
    remaining = list(events)
    for index, step in enumerate(action_list, start=1):
        decision_id = f"{context['decision_id']}:{index}"
        action = step.get("action", {})
        decision: ActionDecision = {
            "kind": "invoke", "tool_name": action.get("tool"),
            "tool_args": action.get("tool_input"), "message": None,
        }
        match = next((event for event in remaining
                      if event["decision"]["tool_name"] == decision["tool_name"]
                      and event["decision"]["tool_args"] == decision["tool_args"]), None)
        if match is not None:
            remaining.remove(match)
            trace.append({**match, "decision_id": decision_id})
            continue
        _, reason = validate_action(context, decision, tools)
        trace.append({
            "decision_id": decision_id, "decision": decision,
            "validation": reason, "validation_stage": "after_execution",
            "execution": "unobserved_by_guard", "feedback": step.get("feedback"),
            "policy": "legacy_react",
        })
    for event in remaining:
        trace.append({**event, "decision_id": event["call_id"],
                      "trace_status": "not_in_intermediate_steps"})
    return {
        "context": context,
        "events": trace,
        "termination": {"kind": "finish", "message": final_answer,
                        "success_verified": False},
    }
