# studiohub/style/typography/rules.py
from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QWidget, QApplication, QPushButton, QToolButton, QLabel
from PySide6.QtCore import QObject

from studiohub.style.typography.config import TypographyConfig


class TypographyManager:
    """
    Central typography manager.
    This replaces the old TYPOGRAPHY_MAP approach.
    """
    
    def __init__(self):
        self.config = TypographyConfig
        self._font_cache = {}
    
    # In studiohub/style/typography/rules.py

    def get_font(self, style_key: str) -> QFont:
        """Get cached font for a style key."""
        if style_key in self._font_cache:
            return self._font_cache[style_key]
        
        # Handle legacy style keys
        style_map = {
            "h1-xl": "h1-xl", "h1": "h1", "h2": "h2", "h3": "h3",
            "h4": "h4", "h5": "h5", "h6": "h6",
            "body": "body", "body-strong": "body-strong", "body-small": "body-small",
            "caption": "caption", "small": "small", "nav": "nav",
            "tree": "tree", "mono": "mono",
        }
        
        mapped_key = style_map.get(style_key, "body")
        
        if mapped_key not in self.config.STYLES:
            mapped_key = "body"
        
        style = self.config.STYLES[mapped_key]
        
        # CRITICAL FIX: Create font properly
        font = QFont()
        font.setFamily(self.config.BASE_FONT_FAMILY)
        
        # Set pixel size FIRST
        font.setPixelSize(style.size_px)
        
        # ALSO set a reasonable point size based on pixel size
        # This prevents Qt from complaining about invalid point size
        # 96 DPI is typical, so point_size = pixel_size * 72/96
        point_size = (style.size_px * 72) / 96
        font.setPointSizeF(point_size)
        
        # Set weight
        font.setWeight(style.weight)
        
        # Set other properties
        font.setStyleStrategy(QFont.PreferAntialias)  # Better rendering
        
        self._font_cache[style_key] = font
        return font
    
    def apply_to_widget(self, widget: QWidget, style_key: str) -> None:
        """
        Apply typography to a widget.
        This maintains the EXACT same behavior as your old apply_typography().
        """
        font = self.get_font(style_key)
        widget.setFont(font)
        
        # Set property for QSS selectors (keeps styling hooks)
        widget.setProperty("typography", style_key)
        
        # Force style refresh
        widget.style().unpolish(widget)
        widget.style().polish(widget)


# Singleton instance (for backward compatibility)
_manager = None

def get_manager() -> TypographyManager:
    """Get or create the global typography manager."""
    global _manager
    if _manager is None:
        _manager = TypographyManager()
    return _manager


# ============================================================
# PUBLIC API - EXACTLY THE SAME AS BEFORE
# ============================================================

def apply_typography(widget: QWidget, key: str) -> None:
    """
    Apply typography to a widget.
    
    THIS IS IDENTICAL TO YOUR OLD FUNCTION.
    Usage: apply_typography(self._caption, "h5")
    
    Args:
        widget: The widget to style
        key: Typography key (h1, h2, body, caption, etc.)
    """
    get_manager().apply_to_widget(widget, key)


def apply_view_typography(view: QWidget, key: str) -> None:
    """
    Apply typography to a view (table, tree, etc.)
    Maintains backward compatibility.
    """
    get_manager().apply_to_widget(view, key)


def apply_header_typography(header: QWidget, key: str) -> None:
    """
    Apply typography to a header.
    Maintains backward compatibility.
    """
    get_manager().apply_to_widget(header, key)


def apply_app_typography(app: QApplication) -> None:
    """
    Set application-wide default font.
    New function to set base font.
    """
    default_font = get_manager().get_font("body")
    app.setFont(default_font)


# ============================================================
# OPTIONAL: Auto-styling for containers (keeps existing code working)
# ============================================================

def style_all_children(parent: QWidget) -> None:
    """
    Style all children that haven't been explicitly styled.
    This helps catch any widgets that might have been missed.
    """
    manager = get_manager()
    
    for child in parent.findChildren(QWidget):
        # Skip if already has typography property
        if child.property("typography"):
            continue
        
        # Try to infer from object name
        obj_name = child.objectName()
        
        # Common patterns from your codebase
        if obj_name.startswith("Panel"):
            if "Primary" in obj_name:
                manager.apply_to_widget(child, "h2")
            elif "Secondary" in obj_name:
                manager.apply_to_widget(child, "body")
            elif "Meta" in obj_name:
                manager.apply_to_widget(child, "small")
        
        elif "Status" in obj_name:
            manager.apply_to_widget(child, "body-small")
        
        elif "Title" in obj_name:
            manager.apply_to_widget(child, "h4")
        
        elif isinstance(child, (QPushButton, QToolButton)):
            manager.apply_to_widget(child, "body")
        
        elif isinstance(child, QLabel):
            manager.apply_to_widget(child, "body")