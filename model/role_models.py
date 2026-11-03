"""Explicit per-role model choices for comparable VA runs."""

import os
from typing import Any

from model.ollama_model import DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL, validate_ollama_base_url


def resolve_role_models(choices: Any, baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Resolve TD, SM, AC and BA, with optional shared default and role overrides."""
    if choices is None:
        choices = {}
    if not isinstance(choices, dict) or set(choices) - {"default", "td", "sm", "ac", "ba"}:
        raise ValueError("model_roles supports default, td, sm, ac and ba objects")
    shared = choices.get("default", {})
    if not isinstance(shared, dict):
        raise ValueError("model_roles.default must be an object")
    result = {}
    for role in ("td", "sm", "ac", "ba"):
        choice = choices.get(role, shared)
        if not isinstance(choice, dict) or set(choice) - {"provider", "model", "base_url", "num_ctx", "timeout"}:
            raise ValueError(f"Invalid {role} model settings")
        provider = choice.get("provider", "gemini")
        if provider == "gemini":
            if set(choice) - {"provider"}:
                raise ValueError(f"{role} Gemini uses the shared baseline model settings")
            result[role] = {**baseline, "provider": "gemini"}
        elif provider == "ollama":
            model = choice.get("model", DEFAULT_OLLAMA_MODEL)
            base = choice.get("base_url", DEFAULT_OLLAMA_BASE_URL)
            num_ctx = choice.get("num_ctx")
            timeout = choice.get("timeout", 300.0)
            if not isinstance(model, str) or not model.strip():
                raise ValueError(f"{role} Ollama model must be a non-empty string")
            if num_ctx is not None and (type(num_ctx) is not int or num_ctx <= 0):
                raise ValueError(f"{role} num_ctx must be a positive integer")
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError(f"{role} timeout must be positive")
            result[role] = {"provider": "ollama", "api_model": model,
                            "api_base": validate_ollama_base_url(base),
                            "num_ctx": num_ctx, "timeout": float(timeout)}
        else:
            raise ValueError(f"Unsupported {role} provider: {provider}")
    return result


def standalone_model_config() -> dict[str, Any]:
    """Use Gemini for standalone tools; local Ollama requires an explicit override."""
    provider = os.environ.get("VILLAGER_GENERATION_PROVIDER", "gemini")
    if provider == "ollama":
        choice = {"provider": "ollama", "model": os.environ.get("VILLAGER_LOCAL_MODEL", DEFAULT_OLLAMA_MODEL),
                  "base_url": os.environ.get("VILLAGER_LOCAL_BASE_URL", DEFAULT_OLLAMA_BASE_URL)}
        return resolve_role_models({"default": choice}, {})["ba"]
    if provider == "gemini":
        from model.google_model import (DEFAULT_GEMINI_MODEL, DEFAULT_GEMINI_THINKING_LEVEL,
                                        GOOGLE_OPENAI_BASE_URL, load_google_api_keys)
        keys = load_google_api_keys()
        return {"provider": "gemini", "api_model": DEFAULT_GEMINI_MODEL,
                "api_base": GOOGLE_OPENAI_BASE_URL, "thinking_level": DEFAULT_GEMINI_THINKING_LEVEL,
                "api_key_list": keys, "api_key": keys[0]}
    raise ValueError("VILLAGER_GENERATION_PROVIDER must be ollama or gemini")


def configure_actor_model(agent_class: Any, config: dict[str, Any]) -> None:
    """Apply the selected provider to the Minecraft Agent class."""
    agent_class.model = config["api_model"]
    agent_class.model_provider = config["provider"]
    if config["provider"] == "ollama":
        agent_class.ollama_base_url = config["api_base"]
        agent_class.ollama_num_ctx = config.get("num_ctx")
        agent_class.ollama_timeout = config.get("timeout", 300.0)
        agent_class.api_key_list = []
    else:
        agent_class.base_url = config["api_base"]
        agent_class.thinking_level = config["thinking_level"]
        agent_class.api_key_list = config["api_key_list"]
