"""Placeholder view widget for empty states."""
from __future__ import annotations

from PySide6 import QtWidgets


class PlaceholderView(QtWidgets.QFrame):
    """
    Simple placeholder view for displaying empty states.
    
    Displays a title and body text centered in the frame.
    """
    
    def __init__(self, title: str, body: str, parent: QtWidgets.QWidget | None = None):
        """
        Initialize placeholder view.
        
        Args:
            title: Main heading text
            body: Explanatory body text
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui(title, body)
    
    def _setup_ui(self, title: str, body: str) -> None:
        """Setup the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Title
        title_label = QtWidgets.QLabel(title)
        title_label.setProperty("role", "view-title")
        layout.addWidget(title_label)
        
        # Body
        body_label = QtWidgets.QLabel(body)
        body_label.setWordWrap(True)
        body_label.setObjectName("Muted")
        layout.addWidget(body_label)
        
        layout.addStretch(1)
