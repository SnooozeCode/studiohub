from PySide6 import QtWidgets

from .core.loader import load_theme
from .core.tokens import build_tokens, ThemeTokens
from .stylesheet import build_stylesheet
from .styles.utils import repolish_recursive


def apply_theme(
    app: QtWidgets.QApplication,
    *,
    theme_name: str,
    root: QtWidgets.QWidget | None = None,
) -> ThemeTokens:
    theme = load_theme(theme_name)
    tokens = build_tokens(theme)

    app.setProperty("theme_tokens", tokens)

    app.setProperty("theme", theme_name)
    app.setStyleSheet(build_stylesheet(tokens))

    if root is not None:
        root.setProperty("theme", theme_name)
        repolish_recursive(root)

    return tokens
