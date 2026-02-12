from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QFontDatabase

from studiohub.app.main_window import MainWindow
from studiohub.style.typography.fonts import apply_base_app_font
from studiohub.constants import APP_VERSION

from studiohub.style.tokens.loader import load_theme
from studiohub.style.tokens.tokens import build_tokens
from studiohub.style.palette import StudioPalette
from studiohub.style.typography.fonts import load_app_fonts, print_base_font


def main() -> int:
    app = QApplication(sys.argv)

    # Fonts
    load_app_fonts()
    apply_base_app_font(app)
    print_base_font()

    app.setApplicationName("SnooozeCo Studio Hub")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SnooozeCo")

    theme_name = "dracula"
    theme_dict = load_theme(theme_name)
    tokens = build_tokens(theme_dict)
    StudioPalette(tokens).apply(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
