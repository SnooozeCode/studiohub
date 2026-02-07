# theme/validator.py

from studiohub.theme.themes.schema import REQUIRED_COLOR_KEYS, REQUIRED_INTERACTION_KEYS


class ThemeValidationError(RuntimeError):
    pass


def _validate_string_map(section_name: str, data: dict) -> None:
    if not isinstance(data, dict):
        raise ThemeValidationError(f"Theme '{section_name}' must be a dictionary")

    for key, value in data.items():
        if not isinstance(value, str):
            raise ThemeValidationError(
                f"Theme '{section_name}.{key}' must be a string"
            )


def validate_theme(theme: dict) -> None:
    if not isinstance(theme, dict):
        raise ThemeValidationError("Theme root must be a dictionary")

    if "colors" not in theme:
        raise ThemeValidationError("Theme missing 'colors' section")

    if "interaction" not in theme:
        raise ThemeValidationError("Theme missing 'interaction' section")

    colors = theme["colors"]
    interaction = theme["interaction"]

    _validate_string_map("colors", colors)
    _validate_string_map("interaction", interaction)

    missing_colors = REQUIRED_COLOR_KEYS - colors.keys()
    if missing_colors:
        raise ThemeValidationError(
            "Theme is missing required color keys: "
            + ", ".join(sorted(missing_colors))
        )

    missing_interaction = REQUIRED_INTERACTION_KEYS - interaction.keys()
    if missing_interaction:
        raise ThemeValidationError(
            "Theme is missing required interaction keys: "
            + ", ".join(sorted(missing_interaction))
        )
