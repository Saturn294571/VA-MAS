"""Actionable errors for explicitly selected optional features."""
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def optional_dependencies(feature: str) -> Iterator[None]:
    """Translate missing imports into installation advice; other errors propagate."""
    try:
        yield
    except ModuleNotFoundError as exc:
        raise ImportError(
            f"Optional {feature} dependency {exc.name!r} is missing. "
            f"Install with: python -m pip install -r requirements/{feature}.txt"
        ) from exc
