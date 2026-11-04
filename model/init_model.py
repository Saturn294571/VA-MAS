"""Factory for the two generative providers used by the current RQ."""
from model.abstract_language_model import AbstractLanguageModel
from common.optional import optional_dependencies

ARCHIVE_BRANCH = "archive/full-features-20261104"


def init_language_model(args: dict) -> AbstractLanguageModel:
    """Build Gemini/Ollama; unsupported providers/models raise ValueError before I/O."""
    model = args.get("api_model", "")
    provider = args.get("provider")
    if provider is None:
        provider = "gemini" if isinstance(model, str) and "gemini" in model else (
            "ollama" if model == "qwen3.8:27b" else None)
    if provider == "ollama":
        with optional_dependencies("base"):
            from model.ollama_model import OllamaLanguageModel
        return OllamaLanguageModel(**{key: value for key, value in {
            "api_model": model, "api_base": args.get("api_base"),
            "role_name": args.get("role_name"), "num_ctx": args.get("num_ctx"),
            "timeout": args.get("timeout"),
        }.items() if value is not None})
    if provider == "gemini" and isinstance(model, str) and "gemini" in model:
        with optional_dependencies("base"):
            from model.google_model import GoogleLanguageModel
        return GoogleLanguageModel(**{key: value for key, value in {
            "api_key": args.get("api_key"), "api_model": model,
            "api_base": args.get("api_base"), "thinking_level": args.get("thinking_level"),
            "role_name": args.get("role_name"), "api_key_list": args.get("api_key_list"),
        }.items() if value is not None})
    raise ValueError(f"Core supports Gemini and Ollama; other adapters are on {ARCHIVE_BRANCH}")
