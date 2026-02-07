# theme/__init__.py

from PySide6 import QtWidgets

from .utils import repolish_recursive


def apply_theme(
    app: QtWidgets.QApplication,
    *,
    theme_name: str,
    root: QtWidgets.QWidget | None = None,
) -> ThemeTokens:
    """
    Official entry point:
    - Loads theme json
    - Applies palette + stylesheet
    - Optionally repolishes the root widget tree (recommended on theme toggle)
    """
    theme = load_theme(theme_name)
    tokens = build_tokens(theme)

    app.setPalette(build_palette(theme))
    app.setStyleSheet(build_stylesheet(tokens))

    if root is not None:
        repolish_recursive(root)

    return tokens



def apply_theme(
    app: QtWidgets.QApplication,
    *,
    theme_name: str,
    root: QtWidgets.QWidget | None = None,
) -> ThemeTokens:
    """
    Official entry point:
    - Loads theme json
    - Applies palette + stylesheet
    - Optionally repolishes the root widget tree (recommended on theme toggle)
    """
    theme = load_theme(theme_name)
    tokens = build_tokens(theme)

    app.setPalette(build_palette(theme))
    app.setStyleSheet(build_stylesheet(tokens))

    if root is not None:
        repolish_recursive(root)

    return tokens
