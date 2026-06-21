"""Prompt template loading and rendering helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache(maxsize=64)
def load_prompt_template(relative_path: str) -> str:
    """Load a prompt template from the repository-level prompts directory."""

    path = _resolve_prompt_path(relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {relative_path}")
    return path.read_text(encoding="utf-8").rstrip("\n")


def render_prompt_template(relative_path: str, **values: Any) -> str:
    """Render a prompt template with named placeholders."""

    template = load_prompt_template(relative_path)
    return template.format(**values)


def _resolve_prompt_path(relative_path: str) -> Path:
    root = PROMPT_ROOT.resolve()
    path = (PROMPT_ROOT / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Prompt template path escapes prompt root: {relative_path}") from exc
    return path
