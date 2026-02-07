from __future__ import annotations

from PySide6 import QtWidgets

from studiohub.style.tokens.loader import load_theme
from studiohub.style.tokens.tokens import build_tokens, ThemeTokens
from studiohub.style.stylesheet import build_stylesheet
from studiohub.style.utils.repolish import repolish_recursive


def apply_style(
    app: QtWidgets.QApplication,
    *,
    theme_name: str,
    root: QtWidgets.QWidget | None = None,
) -> ThemeTokens:
    """
    Apply the application style system.

    Responsibilities:
    - Load theme definition
    - Build design tokens
    - Apply QSS stylesheet
    - Trigger widget repolish if needed
    """

    theme = load_theme(theme_name)
    tokens = build_tokens(theme)

    app.setProperty("style_tokens", tokens)
    app.setProperty("theme", theme_name)
    app.setStyleSheet(build_stylesheet(tokens))

    if root is not None:
        root.setProperty("theme", theme_name)
        repolish_recursive(root)

    return tokens
