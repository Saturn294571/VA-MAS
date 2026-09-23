"""Google Gemini adapters behind the interfaces already used by VillagerAgent.

The rest of the project should not import a Google SDK or know how Gemini is
authenticated. Google exposes an official OpenAI-compatible endpoint, so the
adapter reuses the project's existing ``openai`` dependency and keeps provider
details in this module.
"""

import json
import logging
import os
import random
import threading
import time
from typing import Iterable, List, Optional

from openai import OpenAI
from retry import retry

from model.abstract_language_model import AbstractLanguageModel
from model.utils import extract_info


logger = logging.getLogger(__name__)

GOOGLE_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = os.environ.get("VILLAGER_LLM_MODEL", "gemini-3.8-flash")
DEFAULT_GEMINI_THINKING_LEVEL = os.environ.get(
    "VILLAGER_LLM_THINKING_LEVEL", "low"
)
DEFAULT_GEMINI_ACTOR_MAX_TOKENS = int(
    os.environ.get("VILLAGER_ACTOR_MAX_TOKENS", "512")
)
DEFAULT_GEMINI_EMBEDDING_MODEL = os.environ.get(
    "VILLAGER_EMBEDDING_MODEL", "gemini-embedding-001"
)
PRICING_AS_OF = "2026-09-23"

SUPPORTED_GEMINI_MODELS = {
    "gemini-3.8-flash": {"thinking_level": "low", "input": 0.75, "output": 3.75},
    "gemini-3.5-flash-lite": {"thinking_level": "minimal", "input": 0.30, "output": 2.50},
}
SUPPORTED_THINKING_LEVELS = {"minimal", "low", "medium", "high"}

_TOKEN_FILE_LOCK = threading.Lock()


def load_google_api_keys(
    api_key: Optional[str] = None,
    api_key_list: Optional[Iterable[str]] = None,
    required: bool = True,
) -> List[str]:
    """Resolve credentials without reading a repository-local key file."""
    candidates = list(api_key_list or [])
    if api_key:
        candidates.insert(0, api_key)
    if not candidates:
        env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if env_key:
            candidates.append(env_key)

    keys = []
    for candidate in candidates:
        if candidate and candidate not in keys:
            keys.append(candidate)
    if required and not keys:
        raise ValueError(
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) before using the Gemini API."
        )
    return keys


def _validate_google_base_url(api_base: Optional[str]) -> str:
    if api_base and api_base.rstrip("/") != GOOGLE_OPENAI_BASE_URL.rstrip("/"):
        raise ValueError(
            "Gemini calls must use Google's official endpoint: "
            f"{GOOGLE_OPENAI_BASE_URL}"
        )
    return GOOGLE_OPENAI_BASE_URL


def _validate_model_settings(api_model: str, thinking_level: Optional[str]) -> str:
    if api_model not in SUPPORTED_GEMINI_MODELS:
        raise ValueError(
            f"Unsupported Gemini model {api_model!r}; choose one of "
            f"{sorted(SUPPORTED_GEMINI_MODELS)}."
        )
    resolved = thinking_level or SUPPORTED_GEMINI_MODELS[api_model]["thinking_level"]
    if resolved not in SUPPORTED_THINKING_LEVELS:
        raise ValueError(
            f"Unsupported thinking level {resolved!r}; choose one of "
            f"{sorted(SUPPORTED_THINKING_LEVELS)}."
        )
    return resolved


def _usage_value(usage, field, default=0):
    if usage is None:
        return default
    if isinstance(usage, dict):
        return usage.get(field, default) or default
    return getattr(usage, field, default) or default


def _ensure_runtime_files():
    os.makedirs("data", exist_ok=True)
    os.makedirs(".cache", exist_ok=True)
    if not os.path.exists("data/google.logs"):
        with open("data/google.logs", "w", encoding="utf-8") as log_file:
            log_file.write("")
    if not os.path.exists("data/tokens.json"):
        with open("data/tokens.json", "w", encoding="utf-8") as token_file:
            json.dump(
                {
                    "dates": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "tokens_used": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "thinking_tokens": 0,
                    "successful_requests": 0,
                    "total_cost": 0,
                    "action_cost": 0,
                    "model_usage": {},
                },
                token_file,
            )


def _record_token_usage(usage, model, thinking_level):
    _ensure_runtime_files()
    prompt_tokens = _usage_value(usage, "prompt_tokens")
    completion_tokens = _usage_value(usage, "completion_tokens")
    total_tokens = _usage_value(
        usage, "total_tokens", prompt_tokens + completion_tokens
    )
    details = _usage_value(usage, "completion_tokens_details", {})
    thinking_tokens = _usage_value(details, "reasoning_tokens")
    price = SUPPORTED_GEMINI_MODELS[model]
    request_cost = (
        prompt_tokens * price["input"] + completion_tokens * price["output"]
    ) / 1_000_000

    with _TOKEN_FILE_LOCK:
        with open("data/tokens.json", "r", encoding="utf-8") as token_file:
            tokens = json.load(token_file)
        for key in (
            "tokens_used",
            "prompt_tokens",
            "completion_tokens",
            "thinking_tokens",
            "successful_requests",
            "total_cost",
        ):
            tokens.setdefault(key, 0)
        tokens.setdefault("model_usage", {})
        tokens["dates"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        tokens["tokens_used"] += total_tokens
        tokens["prompt_tokens"] += prompt_tokens
        tokens["completion_tokens"] += completion_tokens
        tokens["thinking_tokens"] += thinking_tokens
        tokens["successful_requests"] += 1
        tokens["total_cost"] += request_cost

        model_usage = tokens["model_usage"].setdefault(
            model,
            {
                "thinking_level": thinking_level,
                "pricing_as_of": PRICING_AS_OF,
                "pricing_usd_per_million_tokens": {
                    "input": price["input"],
                    "output": price["output"],
                },
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "thinking_tokens": 0,
                "requests": 0,
                "cost_usd": 0,
            },
        )
        model_usage["prompt_tokens"] += prompt_tokens
        model_usage["completion_tokens"] += completion_tokens
        model_usage["thinking_tokens"] += thinking_tokens
        model_usage["requests"] += 1
        model_usage["cost_usd"] += request_cost
        with open("data/tokens.json", "w", encoding="utf-8") as token_file:
            json.dump(tokens, token_file, indent=2)


def create_google_chat_model(
    api_model: str = DEFAULT_GEMINI_MODEL,
    api_key: Optional[str] = None,
    api_key_list: Optional[Iterable[str]] = None,
    api_base: Optional[str] = None,
    thinking_level: Optional[str] = None,
    temperature: float = 0,
    max_tokens: int = DEFAULT_GEMINI_ACTOR_MAX_TOKENS,
):
    """Create the LangChain chat model used only by Minecraft actor agents."""
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.chat_models import ChatOpenAI

    keys = load_google_api_keys(api_key, api_key_list)
    level = _validate_model_settings(api_model, thinking_level)

    class GoogleUsageCallback(BaseCallbackHandler):
        def on_llm_end(self, response, **kwargs):
            llm_output = response.llm_output or {}
            usage = llm_output.get("token_usage")
            if usage:
                _record_token_usage(usage, api_model, level)

    return ChatOpenAI(
        model=api_model,
        temperature=temperature,
        max_tokens=max_tokens,
        openai_api_key=random.choice(keys),
        base_url=_validate_google_base_url(api_base),
        model_kwargs={"extra_body": {"reasoning_effort": level}},
        callbacks=[GoogleUsageCallback()],
    )


class GoogleEmbeddingModel:
    """Small LangChain-compatible embedding adapter with lazy API setup."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_key_list: Optional[Iterable[str]] = None,
        api_base: Optional[str] = None,
        model: str = DEFAULT_GEMINI_EMBEDDING_MODEL,
    ):
        self.api_key = api_key
        self.api_key_list = list(api_key_list or [])
        self.api_base = _validate_google_base_url(api_base)
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            keys = load_google_api_keys(self.api_key, self.api_key_list)
            self._client = OpenAI(
                api_key=random.choice(keys),
                base_url=self.api_base,
                max_retries=5,
            )
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def embed_documents(self, texts: List[str], chunk_size=None) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class GoogleLanguageModel(AbstractLanguageModel):
    """Gemini implementation of VillagerAgent's control-plane LLM contract."""

    _supported_models = list(SUPPORTED_GEMINI_MODELS)

    def __init__(
        self,
        api_key: str = "",
        api_model: str = DEFAULT_GEMINI_MODEL,
        role_name: str = "",
        api_key_list=None,
        api_base: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ):
        self.api_key_list = load_google_api_keys(api_key, api_key_list)
        self.api_key = self.api_key_list[0]
        self.api_model = api_model
        self.thinking_level = _validate_model_settings(api_model, thinking_level)
        self.api_base = _validate_google_base_url(api_base)
        self.role_name = role_name
        self.cache_path = "google.cache"
        self.client = self._new_client()
        self._ensure_runtime_files()

    def _new_client(self):
        return OpenAI(
            api_key=random.choice(self.api_key_list),
            base_url=self.api_base,
            max_retries=5,
        )

    @staticmethod
    def _ensure_runtime_files():
        _ensure_runtime_files()

    def generate_thoughts(self, state, k):
        pass

    def evaluate_states(self, states):
        pass

    def _cache_key(self, model, messages, max_tokens, temperature, stop):
        return json.dumps(
            {
                "model": model,
                "thinking_level": self.thinking_level,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stop": stop,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    def cache_api_call_handler(self, cache_key):
        path = os.path.join(".cache", self.cache_path)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as cache_file:
            return json.load(cache_file).get(cache_key)

    def save_cache(self, cache_key, response):
        path = os.path.join(".cache", self.cache_path)
        cache = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as cache_file:
                cache = json.load(cache_file)
        cache[cache_key] = response
        with open(path, "w", encoding="utf-8") as cache_file:
            json.dump(cache, cache_file, ensure_ascii=False)

    def _update_token_usage(self, usage, model):
        _record_token_usage(usage, model, self.thinking_level)

    def _record_ui_log(self, prompt, content):
        if not self.role_name:
            return
        os.makedirs("ui/logs", exist_ok=True)
        path = f"ui/logs/{self.role_name}.json"
        logs = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as log_file:
                logs = json.load(log_file)
        logs.append({"prompt": prompt, "response": content})
        with open(path, "w", encoding="utf-8") as log_file:
            json.dump(logs, log_file, ensure_ascii=False)

    @retry(tries=5, delay=10, backoff=2, max_delay=60)
    def few_shot_generate_thoughts(
        self,
        system_prompt: str = "",
        example_prompt=None,
        max_tokens=2048,
        temperature=0.0,
        k=1,
        stop=None,
        cache_enabled=True,
        api_model="",
        check_tags=None,
        json_check=False,
        stream=False,
    ):
        del k, stream  # Non-streaming responses preserve provider usage accounting.
        example_prompt = [] if example_prompt is None else example_prompt
        check_tags = [] if check_tags is None else check_tags
        if isinstance(example_prompt, str):
            example_prompt = [example_prompt]
        if len(example_prompt) % 2 != 1 and example_prompt:
            raise ValueError("example prompt should be odd number or empty")

        model = api_model or self.api_model
        if model != self.api_model:
            _validate_model_settings(model, self.thinking_level)
        messages = [{"role": "system", "content": system_prompt}]
        for index, prompt_part in enumerate(example_prompt):
            messages.append(
                {
                    "role": "user" if index % 2 == 0 else "assistant",
                    "content": prompt_part,
                }
            )
        prompt = str(system_prompt) + "\n" + "\n".join(example_prompt)
        cache_key = self._cache_key(model, messages, max_tokens, temperature, stop)
        if cache_enabled:
            content = self.cache_api_call_handler(cache_key)
            if content is not None:
                self._record_ui_log(prompt, content)
                return content

        request = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "extra_body": {"reasoning_effort": self.thinking_level},
        }
        if stop is not None:
            request["stop"] = stop

        start_time = time.time()
        response = self.client.chat.completions.create(**request)
        content = response.choices[0].message.content or ""
        self._update_token_usage(response.usage, model)

        for tag in check_tags:
            if tag not in content:
                raise ValueError(f"tag {tag} not in content {content}")
        if json_check and not extract_info(content):
            raise ValueError(f"content {content} is not json")
        if cache_enabled:
            self.save_cache(cache_key, content)

        elapsed = time.time() - start_time
        with open("data/google.logs", "a", encoding="utf-8") as log_file:
            log_file.write(
                f"\n-----------\nModel: {model}\nThinking: {self.thinking_level}"
                f"\nLatency: {elapsed:.6f}\nPrompt: {messages}\n"
            )
        self._record_ui_log(prompt, content)
        if os.path.exists("data/llm_inference.json"):
            with open("data/llm_inference.json", "r", encoding="utf-8") as log_file:
                inference_log = json.load(log_file)
            inference_log["time"] = inference_log.get("time", 0) + elapsed
            with open("data/llm_inference.json", "w", encoding="utf-8") as log_file:
                json.dump(inference_log, log_file)
        return content
