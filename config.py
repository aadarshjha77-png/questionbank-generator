from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "config" / "settings.yaml"


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


def load_settings(path: Path = SETTINGS_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing settings file: {path}")

    with path.open("r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    if not isinstance(settings, dict):
        raise ConfigError("settings.yaml must contain a top-level mapping")

    _validate_settings(settings)
    return settings


def _validate_settings(settings: Dict[str, Any]) -> None:
    required_paths = [
        "openai.api_key",
        "openai.model",
        "openai.max_output_tokens",
        "generation.default_questions_per_chapter",
        "generation.min_questions_per_chapter",
        "generation.max_questions_per_chapter",
        "chapter_split.heading_patterns",
        "chapter_split.min_chapter_chars",
        "prompts.system",
        "prompts.user_template",
    ]
    for dotted in required_paths:
        if _get_nested(settings, dotted) is None:
            raise ConfigError(f"Missing required setting: {dotted}")


def _get_nested(data: Dict[str, Any], dotted_path: str) -> Any:
    value: Any = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value
