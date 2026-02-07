# theme/loader.py

from pathlib import Path
import json

from .validator import validate_theme, ThemeValidationError

THEME_ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = THEME_ROOT / "themes"


def load_theme(name: str, *, fallback: str | None = "dracula") -> dict:
    path = THEMES_DIR / f"{name}.json"

    if not path.exists():
        if fallback and fallback != name:
            return load_theme(fallback, fallback=None)
        raise ThemeValidationError(f"Theme '{name}' not found at {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            theme = json.load(f)
    except json.JSONDecodeError as e:
        raise ThemeValidationError(f"Invalid JSON in theme '{name}'") from e

    validate_theme(theme)
    return theme
