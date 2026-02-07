"""Application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from studiohub.constants import APP_VERSION
from studiohub.hub.main_window import MainWindow
from studiohub.theme.styles.app_font import apply_base_app_font

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def setup_application() -> QApplication:
    """
    Create and configure QApplication.
    
    Returns:
        Configured application instance
    """
    app = QApplication(sys.argv)
    app.setApplicationName("SnooozeCo Studio Hub")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SnooozeCo")
    
    # Setup fonts
    apply_base_app_font(app)
    
    return app


def main() -> int:
    """
    Application entry point.
    
    Returns:
        Exit code
    """
    # Create application
    app = setup_application()
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    exit_code = app.exec()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
