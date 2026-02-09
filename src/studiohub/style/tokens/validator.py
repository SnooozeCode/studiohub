from __future__ import annotations

import re
from typing import Any

from studiohub.style.tokens.schema import (
    REQUIRED_SURFACE_KEYS,
    REQUIRED_TEXT_KEYS,
    REQUIRED_BORDER_KEYS,
    REQUIRED_ACCENT_KEYS,
    REQUIRED_SEMANTIC_KEYS,
    REQUIRED_STATE_KEYS,
)

class ThemeValidationError(RuntimeError):
    pass

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

def _validate_color(name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise ThemeValidationError(f"Theme '{name}' must be a string")
    if not _HEX_RE.match(value):
        raise ThemeValidationError(f"Theme '{name}' must be a hex color like #RRGGBB or #RRGGBBAA")

def _validate_section(section_name: str, data: Any, required: set[str]) -> None:
    if not isinstance(data, dict):
        raise ThemeValidationError(f"Theme '{section_name}' must be an object")
    missing = required - data.keys()
    if missing:
        raise ThemeValidationError(f"Theme is missing required keys in '{section_name}': " + ", ".join(sorted(missing)))
    for key in required:
        _validate_color(f"{section_name}.{key}", data.get(key))

def validate_theme(theme: dict) -> None:
    if not isinstance(theme, dict):
        raise ThemeValidationError("Theme root must be an object")

    # meta is optional but recommended
    surface = theme.get("surface")
    text = theme.get("text")
    border = theme.get("border")
    accent = theme.get("accent")
    semantic = theme.get("semantic")
    state = theme.get("state")

    if surface is None: raise ThemeValidationError("Theme missing 'surface' section")
    if text is None: raise ThemeValidationError("Theme missing 'text' section")
    if border is None: raise ThemeValidationError("Theme missing 'border' section")
    if accent is None: raise ThemeValidationError("Theme missing 'accent' section")
    if semantic is None: raise ThemeValidationError("Theme missing 'semantic' section")
    if state is None: raise ThemeValidationError("Theme missing 'state' section")

    _validate_section("surface", surface, REQUIRED_SURFACE_KEYS)
    _validate_section("text", text, REQUIRED_TEXT_KEYS)
    _validate_section("border", border, REQUIRED_BORDER_KEYS)
    _validate_section("accent", accent, REQUIRED_ACCENT_KEYS)
    _validate_section("semantic", semantic, REQUIRED_SEMANTIC_KEYS)
    _validate_section("state", state, REQUIRED_STATE_KEYS)
