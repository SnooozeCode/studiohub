"""Click catcher widget for overlay interactions."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt


class ClickCatcher(QtWidgets.QWidget):
    """
    Transparent overlay widget that captures clicks.
    
    Used for modal-like overlays that should close when
    clicking outside a drawer or dialog.
    """
    
    clicked = QtCore.Signal()
    
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        """
        Initialize click catcher.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_attributes()
    
    def _setup_attributes(self) -> None:
        """Configure widget attributes."""
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse press events.
        
        Args:
            event: Mouse event
        """
        self.clicked.emit()
        event.accept()
