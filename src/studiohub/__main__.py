from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from studiohub.app.main_window import MainWindow
from studiohub.constants import APP_VERSION
from studiohub.style.tokens.loader import load_theme
from studiohub.style.tokens.tokens import build_tokens
from studiohub.style.palette import StudioPalette
from studiohub.style.typography.fonts import load_app_fonts
from studiohub.utils.logging import setup_logging, set_root_logger, get_logger
from studiohub.config.paths import get_appdata_root

def main() -> int:
    # Setup logging FIRST
    appdata_root = get_appdata_root()
    root_logger = setup_logging(
        appdata_root,
        log_level="DEBUG",  # Use INFO in production
        json_format=False,   # Set to True for production log aggregation
    )
    set_root_logger(root_logger)
    logger = get_logger(__name__)
    
    try:
        logger.info("Starting StudioHub application")
        
        app = QApplication(sys.argv)
        
        # Fonts
        load_app_fonts()
        logger.debug("Fonts loaded")
        
        # Apply app-wide typography FIRST
        from studiohub.style.typography.rules import apply_app_typography
        apply_app_typography(app)
        
        app.setApplicationName("SnooozeCo Studio Hub")
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("SnooozeCo")
        
        # Then theme (colors only)
        theme_name = "dracula"
        logger.info(f"Loading theme: {theme_name}")
        theme_dict = load_theme(theme_name)
        tokens = build_tokens(theme_dict)
        StudioPalette(tokens).apply(app)
        
        window = MainWindow()
        
        # Ensure all widgets in the window are styled
        from studiohub.style.typography.widget_styler import WidgetStyler
        WidgetStyler.style_widget_tree(window)
        
        window.show()
        logger.info("Main window displayed")
        
        exit_code = app.exec()
        logger.info(f"Application exiting with code {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())