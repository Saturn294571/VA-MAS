from common.optional import optional_dependencies


def init_language_model(args: dict):
    """Build the selected adapter; missing optional SDKs raise installation advice."""
    api_model = args.get("api_model", "")

    if args.get("provider") == "ollama" or (not args.get("provider") and api_model == "qwen3.8:27b"):
        with optional_dependencies("base"):
            from model.ollama_model import OllamaLanguageModel
        return OllamaLanguageModel(**{k: v for k, v in {
            "api_model": api_model, "api_base": args.get("api_base"),
            "role_name": args.get("role_name"), "num_ctx": args.get("num_ctx"),
            "timeout": args.get("timeout"),
        }.items() if v is not None})
    if "gemini" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "api_base": args.get("api_base", None),
            "thinking_level": args.get("thinking_level", None),
            "role_name": args.get("role_name", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        with optional_dependencies("base"):
            from model.google_model import GoogleLanguageModel
        return GoogleLanguageModel(**new_args)
    elif "gpt" in api_model and 'llama' not in api_model or "qwen" in api_model or "deepseek" in api_model or "default" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "api_base": args.get("api_base", None),
            "evaluation_strategy": args.get("evaluation_strategy", None),
            "enable_ReAct_prompting": args.get("enable_ReAct_prompting", None),
            "strategy": args.get("strategy", None),
            "role_name": args.get("role_name", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        with optional_dependencies("base"):
            from model.openai_models import OpenAILanguageModel
        return OpenAILanguageModel(**new_args)
    elif "glm" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "role_name": args.get("role_name", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        with optional_dependencies("providers"):
            from model.zhipu_model import ZhipuLanguageModel
        return ZhipuLanguageModel(**new_args)
    elif "vllm" in api_model or "llama" in api_model or "NAS" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "api_base": args.get("api_base", None),
            "role_name": args.get("role_name", None),
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        with optional_dependencies("base"):
            from model.vllm_model import VLLMLanguageModel
        return VLLMLanguageModel(**new_args)
    else:
        new_args = {
            "api_key": args.get("api_key", None),
            "model_tokenizer": args.get("model_tokenizer", None),
            "verbose": args.get("verbose", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        with optional_dependencies("huggingface"):
            from model.huggingface_model import HFLanguageModel
        return HFLanguageModel(**new_args)
