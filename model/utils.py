"""Compatibility imports for model response parsing."""
import logging
from common.parsing import find_correct_data, _fix_missing_commas_in_object, parse_info


def extract_info(text: str, guard_keys: list[str] = []) -> list[dict]:
    """Return extracted objects, or [] on any legacy model parsing failure."""
    try:
        return parse_info(text, guard_keys, recover_yaml_errors=False)
    except Exception as exc:
        logging.getLogger(__name__).warning("Response extraction failed (%s)", type(exc).__name__)
        return []
