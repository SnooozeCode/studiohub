from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication, QStyleFactory

from studiohub.app.main_window import MainWindow
from studiohub.style.typography.fonts import apply_base_app_font
from studiohub.constants import APP_VERSION

from studiohub.style.tokens.loader import load_theme
from studiohub.style.tokens.tokens import build_tokens
from studiohub.style.palette import StudioPalette


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SnooozeCo Studio Hub")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SnooozeCo")

    apply_base_app_font(app)

    theme_name = "dracula"
    theme_dict = load_theme(theme_name)
    tokens = build_tokens(theme_dict)
    StudioPalette(tokens).apply(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
