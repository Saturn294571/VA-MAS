"""Local Ollama System One choice adapter for bounded actor decisions."""

from __future__ import annotations

import time
import uuid
from typing import Any

import requests

from tracer import current_tracer, safe_emit


def choose(state: dict[str, Any], choices: dict[str, str], *,
           model: str = "tev1:4b-q4_K_M", timeout: float = 30.0) -> str:
    """Select an offered ID; transport, malformed responses and unknown IDs fail."""
    if len(choices) < 2 or not all(isinstance(k, str) and isinstance(v, str)
                                   for k, v in choices.items()):
        raise ValueError("At least two named choices are required")
    request_id = uuid.uuid4().hex
    tracer = current_tracer()
    started = time.monotonic()
    safe_emit(tracer, "BA", "decision.request.start", request_id=request_id,
              model=model, provider="ollama", candidate_count=len(choices))
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.post("http://127.0.0.1:11434/v1/systemone", json={
                "model": model, "state": state,
                "questions": {"action": {"type": "choice", "instructions":
                    "Choose the next action that advances the task safely.",
                    "criteria": choices}},
            }, timeout=timeout)
            response.raise_for_status()
            answer = response.json()["answers"]["action"]["choice"]
        if not isinstance(answer, str) or answer not in choices:
            raise ValueError("Decision response is not an offered choice")
    except Exception as exc:
        safe_emit(tracer, "BA", "decision.request.end", request_id=request_id,
                  result_status="error", error_type=type(exc).__name__,
                  duration_s=time.monotonic() - started)
        raise
    safe_emit(tracer, "BA", "decision.request.end", request_id=request_id,
              result_status="ok", duration_s=time.monotonic() - started)
    return answer
