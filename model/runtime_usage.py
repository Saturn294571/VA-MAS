"""Provider-neutral runtime accounting schema and process-local thread lock."""
import json
import os
import threading
import time

TOKEN_FILE_LOCK = threading.Lock()

def ensure_runtime_files() -> None:
    """Create legacy accounting files on demand; filesystem errors propagate."""
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

