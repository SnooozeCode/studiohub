from __future__ import annotations

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from studiohub.style.tokens.tokens import ThemeTokens



class StudioPalette:
    def __init__(self, tokens):
        self.tokens = tokens

    def apply(self, app):
        pal = app.palette()

        # Core
        pal.setColor(QPalette.Window, QColor(self.tokens.bg_app))
        pal.setColor(QPalette.Base, QColor(self.tokens.bg_surface))
        pal.setColor(QPalette.Text, QColor(self.tokens.text_primary))
        pal.setColor(QPalette.ButtonText, QColor(self.tokens.text_primary))

        # Selection / accent
        pal.setColor(QPalette.Highlight, QColor(self.tokens.accent))
        pal.setColor(QPalette.HighlightedText, QColor(self.tokens.text_primary))

        # Disabled
        pal.setColor(
            QPalette.Disabled,
            QPalette.Text,
            QColor(self.tokens.text_disabled),
        )

        # --------------------------------------------
        # 🔑 SCROLLBAR / WINDOWS STYLE FIX
        # --------------------------------------------
        pal.setColor(QPalette.AlternateBase, QColor(self.tokens.bg_surface))
        pal.setColor(QPalette.Dark, QColor(self.tokens.border))
        pal.setColor(QPalette.Mid, QColor(self.tokens.border))
        pal.setColor(QPalette.Midlight, QColor(self.tokens.border))

        # Prevent Windows accent bleed
        pal.setColor(QPalette.Light, QColor(self.tokens.bg_surface))

        app.setPalette(pal)
