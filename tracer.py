"""Run-local lifecycle events for comparing VA decision policies.

Enable explicitly with VILLAGER_TRACE_DIR. No files are created on import.
Events contain metadata only; prompts, credentials and tool arguments are not
accepted by the instrumentation in this module.
"""

from __future__ import annotations

import contextvars
import fcntl
import functools
import json
import os
import subprocess
import time
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


TRACE_ENV = "VILLAGER_TRACE_DIR"
_scope = contextvars.ContextVar("villager_trace_scope", default={})
_ALLOWED = frozenset({
    "task_id", "parent_task_id", "agent_id", "decision_id", "request_id", "model", "provider", "policy",
    "assignment_mode", "candidate_count", "required_agents", "agent_count",
    "tool", "tool_status", "validation", "execution", "finish_reason", "prompt_tokens",
    "completion_tokens", "thinking_tokens", "total_tokens", "cost_usd",
    "cache_hit", "error_type", "result_status", "score", "end_reason",
    "graph_nodes", "graph_edges", "reason", "duration_s", "actor_run_id",
    "load_duration_s", "prompt_eval_duration_s", "eval_duration_s",
})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _safe_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Allow only known scalar metrics, preventing accidental prompt/key logging."""
    return {key: value for key, value in attributes.items()
            if key in _ALLOWED and (value is None or isinstance(value, (str, int, float, bool)))}


class Tracer:
    """Append run events safely across threads and processes.

    Creates its directory when constructed; write failures are reported by the
    caller of this class. Runtime helpers below degrade to a warning instead of
    changing the benchmark's behavior.
    """

    def __init__(self, directory: str | Path, run_id: str | None = None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_path = self.directory / "events.jsonl"
        self.run_id = run_id or self.directory.parent.name

    def emit(self, component: str, event: str, **attributes: Any) -> None:
        record = {"schema_version": 1, "run_id": self.run_id, "time_utc": _utc_now(),
                  "component": component, "event": event,
                  "pid": os.getpid(), **_safe_attributes(_scope.get()),
                  **_safe_attributes(attributes)}
        scope = _scope.get()
        if scope.get("span_id"):
            record["span_id"] = scope["span_id"]
        if scope.get("parent_span_id"):
            record["parent_span_id"] = scope["parent_span_id"]
        line = json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
        with self.events_path.open("a", encoding="utf-8") as output:
            fcntl.flock(output, fcntl.LOCK_EX)
            try:
                output.write(line)
                output.flush()
            finally:
                fcntl.flock(output, fcntl.LOCK_UN)

    @contextmanager
    def span(self, component: str, event: str, **attributes: Any) -> Iterator[None]:
        """Record start/end and elapsed wall time; re-raise the original error."""
        parent = _scope.get()
        scope = {**parent, **_safe_attributes(attributes), "component": component,
                 "span_id": uuid.uuid4().hex,
                 "parent_span_id": parent.get("span_id")}
        token = _scope.set(scope)
        start = time.monotonic()
        safe_emit(self, component, event + ".start")
        try:
            yield
        except BaseException as exc:
            safe_emit(self, component, event + ".end", result_status="error",
                      error_type=type(exc).__name__, duration_s=time.monotonic() - start)
            raise
        else:
            safe_emit(self, component, event + ".end", result_status="ok",
                      duration_s=time.monotonic() - start)
        finally:
            _scope.reset(token)


def safe_emit(tracer: Tracer | None, component: str, event: str, **attributes: Any) -> None:
    if tracer is None:
        return
    try:
        tracer.emit(component, event, **attributes)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Trace write failed: {type(exc).__name__}", file=__import__("sys").stderr)


def current_tracer() -> Tracer | None:
    """Attach to an explicitly configured run, otherwise leave tracing disabled."""
    directory = os.environ.get(TRACE_ENV)
    if not directory:
        return None
    try:
        return Tracer(directory)
    except OSError as exc:
        print(f"Trace setup failed: {type(exc).__name__}", file=__import__("sys").stderr)
        return None


def current_component(default: str = "LLM") -> str:
    return _scope.get().get("component", default)


@contextmanager
def trace_scope(**attributes: Any) -> Iterator[None]:
    """Attach task/decision identifiers to events in the current thread."""
    token = _scope.set({**_scope.get(), **_safe_attributes(attributes)})
    try:
        yield
    finally:
        _scope.reset(token)


def traced(component: str, event: str):
    """Instrument a method, extracting task/agent identity where available."""
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            tracer = current_tracer()
            if tracer is None:
                return func(self, *args, **kwargs)
            task = kwargs.get("task") or (args[0] if args else None)
            attributes = {}
            if getattr(task, "id", None):
                attributes["task_id"] = str(task.id)
            if component == "BA" and getattr(self, "name", None):
                attributes["agent_id"] = self.name
            with tracer.span(component, event, **attributes):
                return func(self, *args, **kwargs)
        return wrapper
    return decorate


def write_manifest(directory: Path, settings: dict[str, Any]) -> None:
    """Write an allowlisted run manifest; unknown conditions remain unknown."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                text=True, check=True, timeout=3).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                    text=True, check=True, timeout=5).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        commit = None
        dirty = None
    allowed = {"task_name", "task_type", "task_idx", "agent_num", "controller_mode",
               "assignment_policy", "role", "model", "thinking_level", "dig_needed",
               "max_task_num", "host", "port", "repeat", "world", "difficulty", "spawn",
               "td_provider", "td_model", "td_num_ctx", "sm_provider", "sm_model", "sm_num_ctx",
               "ac_provider", "ac_model", "ac_num_ctx", "ba_provider", "ba_model", "ba_num_ctx"}
    manifest = {"schema_version": 1, "run_id": directory.parent.name,
                "created_utc": _utc_now(), "git_commit": commit, "git_dirty": dirty,
                "settings": {k: v for k, v in settings.items() if k in allowed},
                "unrecorded_conditions": ["world", "difficulty", "spawn", "repeat"]}
    manifest["unrecorded_conditions"] = [k for k in manifest["unrecorded_conditions"] if k not in manifest["settings"]]
    (directory.parent / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def summarize(directory: str | Path, status: str = "unknown") -> dict[str, Any]:
    """Regenerate a summary from complete JSONL records; tolerate an interrupted line."""
    directory = Path(directory)
    events = []
    invalid_lines = 0
    path = directory / "events.jsonl"
    if path.exists():
        with path.open(encoding="utf-8") as source:
            for line in source:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    invalid_lines += 1
    counts = Counter(f"{e['component']}.{e['event']}" for e in events)
    durations = defaultdict(float)
    usage = defaultdict(lambda: {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0,
                                 "thinking_tokens": 0, "cost_usd": 0.0, "missing_usage": 0,
                                 "unpriced_requests": 0})
    by_agent = defaultdict(lambda: {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0,
                                    "thinking_tokens": 0, "cost_usd": 0.0, "missing_usage": 0,
                                    "unpriced_requests": 0})
    finish_reasons = Counter()
    action_validations = Counter()
    assignment_modes = Counter()
    for event in events:
        if event["event"].endswith(".end") and isinstance(event.get("duration_s"), (int, float)):
            durations[f"{event['component']}.{event['event']}"] += event["duration_s"]
        if event["event"] == "llm.request.end" and event.get("result_status") == "ok":
            buckets = [usage[event["component"]]]
            if event.get("agent_id"):
                buckets.append(by_agent[event["agent_id"]])
            for bucket in buckets:
                bucket["requests"] += 1
                if event.get("prompt_tokens") is None or event.get("completion_tokens") is None:
                    bucket["missing_usage"] += 1
                if event.get("cost_usd") is None:
                    bucket["unpriced_requests"] += 1
                for key in ("prompt_tokens", "completion_tokens", "thinking_tokens", "cost_usd"):
                    bucket[key] += event.get(key) or 0
            finish_reasons[str(event.get("finish_reason") or "unavailable")] += 1
        if event["event"] == "action.selected":
            action_validations[str(event.get("validation") or "unavailable")] += 1
        if event["event"] == "task.assigned":
            assignment_modes[str(event.get("assignment_mode") or "unavailable")] += 1
    score_path = directory.parent / "score.json"
    try:
        score = json.loads(score_path.read_text(encoding="utf-8")) if score_path.exists() else None
    except (OSError, json.JSONDecodeError):
        score = None
    run_end = next((event for event in reversed(events) if event["component"] == "RUN" and event["event"] == "run.end"), {})
    summary = {"schema_version": 1, "run_id": directory.parent.name, "status": status,
               "generated_utc": _utc_now(), "events": len(events), "invalid_lines": invalid_lines,
               "wall_clock_s": run_end.get("duration_s"),
               "event_counts": dict(counts), "duration_sums": dict(durations),
               "llm_usage_by_component": dict(usage), "llm_usage_by_agent": dict(by_agent),
               "llm_finish_reasons": dict(finish_reasons), "action_validations": dict(action_validations),
               "assignment_modes": dict(assignment_modes), "judger_score": score,
               "limitations": ["duration sums may overlap; they are not elapsed wall time",
                               "usage excludes unavailable metrics and failed requests",
                               "local inference cost is unpriced and excluded from cost_usd"]}
    temp = directory.parent / "summary.json.tmp"
    temp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(directory.parent / "summary.json")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Regenerate a run trace summary")
    parser.add_argument("trace_dir")
    parser.add_argument("--status", default="recovered")
    args = parser.parse_args()
    print(json.dumps(summarize(args.trace_dir, args.status), indent=2))
