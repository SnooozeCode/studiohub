from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from studiohub.app.main_window import MainWindow
from studiohub.theme.styles.app_font import apply_base_app_font
from studiohub.constants import APP_VERSION


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SnooozeCo Studio Hub")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SnooozeCo")

    apply_base_app_font(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
