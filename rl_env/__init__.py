"""Optional reinforcement learning models, loaded only when requested."""
from importlib import import_module
from typing import Any
from common.optional import optional_dependencies

__all__ = ["MinecraftRLEnv", "MinecraftDQN", "PPO"]
_MODULES = {"MinecraftRLEnv": "minecraft_rl_env", "MinecraftDQN": "minecraft_dqn", "PPO": "minecraft_ppo"}


def __getattr__(name: str) -> Any:
    """Load a public RL class; unknown names or missing packages fail explicitly."""
    if name not in _MODULES:
        raise AttributeError(name)
    with optional_dependencies("rl"):
        value = getattr(import_module(f"rl_env.{_MODULES[name]}"), name)
    globals()[name] = value
    return value
