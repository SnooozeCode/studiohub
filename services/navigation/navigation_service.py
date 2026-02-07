"""Navigation service for managing view transitions."""
from __future__ import annotations

from typing import Callable

from PySide6 import QtCore, QtWidgets


class NavigationService(QtCore.QObject):
    """
    Manages application navigation and view lifecycle.
    
    Handles view switching, activation hooks, and navigation state.
    """
    
    view_changed = QtCore.Signal(str)  # Emits view key
    
    def __init__(
        self,
        stack: QtWidgets.QStackedWidget,
        views: dict[str, QtWidgets.QWidget],
        parent: QtCore.QObject | None = None,
    ):
        """
        Initialize navigation service.
        
        Args:
            stack: Stacked widget for view container
            views: Dictionary of view_key -> widget
            parent: Parent Qt object
        """
        super().__init__(parent)
        
        self._stack = stack
        self._views = views
        self._active_view_key: str = ""
        self._activation_hooks: dict[str, Callable[[], None]] = {}
    
    def register_activation_hook(
        self, 
        view_key: str, 
        hook: Callable[[], None]
    ) -> None:
        """
        Register a callback to run when a view is activated.
        
        Args:
            view_key: View identifier
            hook: Function to call on activation
        """
        self._activation_hooks[view_key] = hook
    
    def show_view(self, key: str) -> bool:
        """
        Navigate to the specified view.
        
        Args:
            key: View identifier
            
        Returns:
            True if navigation succeeded, False if view not found
        """
        widget = self._views.get(key)
        if not widget:
            return False
        
        self._active_view_key = key
        self._stack.setCurrentWidget(widget)
        
        # Configure stack sizing
        self._stack.setMinimumHeight(0)
        self._stack.setMaximumHeight(16777215)
        self._stack.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        
        # Run widget's own activation hook
        if hasattr(widget, "on_activated"):
            QtCore.QTimer.singleShot(0, widget.on_activated)
        
        # Run registered activation hook
        hook = self._activation_hooks.get(key)
        if hook:
            QtCore.QTimer.singleShot(0, hook)
        
        self.view_changed.emit(key)
        return True
    
    @property
    def active_view(self) -> str:
        """Get the currently active view key."""
        return self._active_view_key
    
    def get_view(self, key: str) -> QtWidgets.QWidget | None:
        """
        Get a view widget by key.
        
        Args:
            key: View identifier
            
        Returns:
            View widget or None if not found
        """
        return self._views.get(key)
