"""Local Ollama adapter for AC generation and the LangChain Minecraft actor.

Using the native chat endpoint explicitly controls Qwen's thinking mode. This
adapter does not fall back to a remote provider or send prompts off-host.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any, Optional
from urllib.parse import urlsplit

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from model.abstract_language_model import AbstractLanguageModel
from model.google_model import _TOKEN_FILE_LOCK, _ensure_runtime_files
from model.utils import extract_info
from tracer import current_component, current_tracer, safe_emit

DEFAULT_OLLAMA_MODEL = "qwen3.8:27b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"


def validate_ollama_base_url(value: str) -> str:
    """Accept only a local HTTP endpoint without credentials or a custom path."""
    if not isinstance(value, str):
        raise ValueError("Ollama base_url must be a local HTTP origin")
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ValueError("Ollama base_url must be a local HTTP origin")
    return value.rstrip("/")


def _record_local_usage(model: str, prompt_tokens: Any, completion_tokens: Any) -> None:
    """Share the Gemini accounting lock; local monetary cost is not estimated."""
    _ensure_runtime_files()
    with _TOKEN_FILE_LOCK:
        with open("data/tokens.json", encoding="utf-8") as source:
            tokens = json.load(source)
        tokens.setdefault("model_usage", {})
        key = f"ollama/{model}"
        record = tokens["model_usage"].setdefault(key, {
            "provider": "ollama", "prompt_tokens": 0, "completion_tokens": 0,
            "requests": 0, "missing_usage": 0, "cost_usd": None,
        })
        record["requests"] += 1
        tokens["successful_requests"] = tokens.get("successful_requests", 0) + 1
        if not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
            record["missing_usage"] += 1
        else:
            record["prompt_tokens"] += prompt_tokens
            record["completion_tokens"] += completion_tokens
            tokens["prompt_tokens"] = tokens.get("prompt_tokens", 0) + prompt_tokens
            tokens["completion_tokens"] = tokens.get("completion_tokens", 0) + completion_tokens
            tokens["tokens_used"] = tokens.get("tokens_used", 0) + prompt_tokens + completion_tokens
        with open("data/tokens.json", "w", encoding="utf-8") as target:
            json.dump(tokens, target, indent=2)


def _local_post(url: str, *, payload: dict[str, Any], timeout: float):
    """Connect to the validated local origin without environment proxy settings."""
    with requests.Session() as session:
        session.trust_env = False
        return session.post(url, json=payload, timeout=timeout)


def ollama_chat(
    *, model: str, base_url: str, messages: list[dict[str, str]], max_tokens: int,
    temperature: float, stop: Optional[list[str]], num_ctx: Optional[int],
    timeout: float, actor_name: Optional[str] = None,
) -> dict[str, Any]:
    """Call local Ollama once; transport and malformed-response errors propagate."""
    base_url = validate_ollama_base_url(base_url)
    options: dict[str, Any] = {"num_predict": max_tokens, "temperature": temperature}
    if stop:
        options["stop"] = stop
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    payload = {"model": model, "messages": messages, "stream": False,
               "think": False, "options": options}
    request_id = uuid.uuid4().hex
    component = current_component("BA" if actor_name else "LLM")
    tracer = current_tracer()
    started = time.monotonic()
    safe_emit(tracer, component, "llm.request.start", request_id=request_id,
              agent_id=actor_name, model=model, provider="ollama")
    try:
        response = _local_post(f"{base_url}/api/chat", payload=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        content = body.get("message", {}).get("content")
        if not body.get("done") or not isinstance(content, str):
            raise ValueError("Invalid Ollama chat response")
    except Exception as exc:
        safe_emit(tracer, component, "llm.request.end", request_id=request_id,
                  agent_id=actor_name, model=model, provider="ollama", result_status="error",
                  error_type=type(exc).__name__, duration_s=time.monotonic() - started)
        raise
    prompt_tokens = body.get("prompt_eval_count")
    completion_tokens = body.get("eval_count")
    _record_local_usage(model, prompt_tokens, completion_tokens)
    def seconds(field: str) -> Optional[float]:
        value = body.get(field)
        return value / 1e9 if isinstance(value, (int, float)) else None

    if not content.strip():
        safe_emit(tracer, component, "llm.request.end", request_id=request_id,
                  agent_id=actor_name, model=model, provider="ollama", result_status="error",
                  error_type="EmptyResponse", duration_s=time.monotonic() - started,
                  finish_reason=body.get("done_reason"), prompt_tokens=prompt_tokens,
                  completion_tokens=completion_tokens)
        raise ValueError("Ollama returned an empty response")
    safe_emit(tracer, component, "llm.request.end", request_id=request_id,
              agent_id=actor_name, model=model, provider="ollama", result_status="ok",
              duration_s=time.monotonic() - started, finish_reason=body.get("done_reason"),
              prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
              load_duration_s=seconds("load_duration"),
              prompt_eval_duration_s=seconds("prompt_eval_duration"),
              eval_duration_s=seconds("eval_duration"))
    return body


class OllamaLanguageModel(AbstractLanguageModel):
    """Native Ollama implementation of the existing control-plane interface."""

    def __init__(self, api_model: str = DEFAULT_OLLAMA_MODEL,
                 api_base: str = DEFAULT_OLLAMA_BASE_URL, role_name: str = "",
                 num_ctx: Optional[int] = None, timeout: float = 300.0):
        self.api_model = api_model
        self.api_base = validate_ollama_base_url(api_base)
        self.role_name = role_name
        self.num_ctx = num_ctx
        self.timeout = timeout
        self._cache: dict[str, str] = {}
        self._cache_lock = threading.Lock()

    def generate_thoughts(self, state, k):
        raise NotImplementedError("Use few_shot_generate_thoughts")

    def evaluate_states(self, states):
        raise NotImplementedError("Use few_shot_generate_thoughts")

    def few_shot_generate_thoughts(self, system_prompt: str = "", example_prompt=None,
                                   max_tokens=2048, temperature=0.0, k=1, stop=None,
                                   cache_enabled=True, api_model="", check_tags=None,
                                   json_check=False, stream=False):
        del k, stream
        prompt = [] if example_prompt is None else example_prompt
        if isinstance(prompt, str):
            prompt = [prompt]
        if prompt and len(prompt) % 2 != 1:
            raise ValueError("example prompt should be odd number or empty")
        # The legacy blueprint helper supplies the entire request as the first
        # positional argument. Ollama requires a user message in every chat.
        messages = ([{"role": "system", "content": system_prompt}] if prompt
                    else [{"role": "user", "content": system_prompt}])
        messages.extend({"role": "user" if i % 2 == 0 else "assistant", "content": text}
                        for i, text in enumerate(prompt))
        model = api_model or self.api_model
        cache_key = json.dumps([model, messages, max_tokens, temperature, stop, self.num_ctx],
                               sort_keys=True, ensure_ascii=False)
        if cache_enabled:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
            if cached is not None:
                safe_emit(current_tracer(), current_component(self.role_name or "LLM"),
                          "llm.cache_hit", model=model, provider="ollama", cache_hit=True)
                return cached
        result = ollama_chat(model=model, base_url=self.api_base, messages=messages,
                             max_tokens=max_tokens, temperature=temperature, stop=stop,
                             num_ctx=self.num_ctx, timeout=self.timeout)
        content = result["message"]["content"]
        for tag in check_tags or []:
            if tag not in content:
                raise ValueError(f"Required response tag missing: {tag}")
        if json_check and not extract_info(content):
            raise ValueError("Ollama response is not valid expected JSON")
        if cache_enabled:
            with self._cache_lock:
                self._cache[cache_key] = content
        return content


class OllamaActorChatModel(BaseChatModel):
    """LangChain chat interface for the existing structured ReAct actor."""

    model: str = DEFAULT_OLLAMA_MODEL
    base_url: str = DEFAULT_OLLAMA_BASE_URL
    actor_name: Optional[str] = None
    max_tokens: int = 1024
    num_ctx: Optional[int] = None
    timeout: float = 300.0
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "local_ollama_chat"

    def _generate(self, messages: list[BaseMessage], stop: Optional[list[str]] = None,
                  run_manager=None, **kwargs: Any) -> ChatResult:
        del run_manager, kwargs
        roles = {"human": "user", "ai": "assistant", "system": "system"}
        converted = []
        for message in messages:
            if message.type not in roles or not isinstance(message.content, str):
                raise ValueError(f"Unsupported actor message type: {message.type}")
            converted.append({"role": roles[message.type], "content": message.content})
        result = ollama_chat(model=self.model, base_url=self.base_url, messages=converted,
                             max_tokens=self.max_tokens, temperature=self.temperature,
                             stop=stop, num_ctx=self.num_ctx, timeout=self.timeout,
                             actor_name=self.actor_name)
        generation = ChatGeneration(message=AIMessage(content=result["message"]["content"]),
                                    generation_info={"finish_reason": result.get("done_reason")})
        return ChatResult(generations=[generation], llm_output={"model": self.model})


def create_ollama_chat_model(*, model: str, base_url: str = DEFAULT_OLLAMA_BASE_URL,
                             actor_name: Optional[str] = None, max_tokens: int = 1024,
                             num_ctx: Optional[int] = None, timeout: float = 300.0) -> OllamaActorChatModel:
    return OllamaActorChatModel(model=model, base_url=validate_ollama_base_url(base_url),
                                actor_name=actor_name, max_tokens=max_tokens,
                                num_ctx=num_ctx, timeout=timeout, temperature=0)
