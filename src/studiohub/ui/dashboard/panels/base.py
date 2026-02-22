# studiohub/ui/dashboard/panels/base.py
from __future__ import annotations

from typing import Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from studiohub.style.typography.rules import apply_typography


class BaseDashboardPanel(QWidget):
    """
    Base class for all dashboard panels with common patterns.
    
    Provides:
    - Standard typography roles (primary, secondary, meta, placeholder)
    - Consistent layout margins
    - Loading state management
    - Error state display
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._error: Optional[str] = None
        
        # Main layout - NO MARGINS (container provides them)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        
        # Standard labels (initially hidden)
        self._primary = self._create_label("PanelPrimary", "h2")
        self._secondary = self._create_label("PanelSecondary", "body", word_wrap=True)
        self._meta = self._create_label("PanelMeta", "small")
        self._placeholder = self._create_label("PanelPlaceholder", "body")
        self._placeholder.setText("—")
        
        # Add to layout (will be shown/hidden as needed)
        for widget in (self._primary, self._secondary, self._meta, self._placeholder):
            self._layout.addWidget(widget)
            widget.hide()
        
        self._layout.addStretch()
    
    def _create_label(self, obj_name: str, typography: str, word_wrap: bool = False) -> QLabel:
        """Create a standardized label."""
        label = QLabel()
        label.setObjectName(obj_name)
        apply_typography(label, typography)
        if word_wrap:
            label.setWordWrap(True)
        return label
    
    def set_loading(self, loading: bool, message: str = "Loading..."):
        """Set loading state."""
        self._loading = loading
        self._error = None
        
        if loading:
            self._hide_all()
            self._placeholder.setText(message)
            self._placeholder.show()
        else:
            self._refresh_display()
    
    def set_error(self, message: str):
        """Set error state."""
        self._loading = False
        self._error = message
        
        self._hide_all()
        self._placeholder.setText(f"Error: {message}")
        self._placeholder.show()
    
    def _hide_all(self):
        """Hide all content widgets."""
        for widget in (self._primary, self._secondary, self._meta, self._placeholder):
            widget.hide()
    
    def _refresh_display(self):
        """Refresh display based on current data."""
        # Override in subclasses
        pass
    
    def _show_data(self, primary: str = "", secondary: str = "", meta: str = ""):
        """Show data in standard labels."""
        self._placeholder.hide()
        
        if primary:
            self._primary.setText(primary)
            self._primary.show()
        else:
            self._primary.hide()
        
        if secondary:
            self._secondary.setText(secondary)
            self._secondary.show()
        else:
            self._secondary.hide()
        
        if meta:
            self._meta.setText(meta)
            self._meta.show()
        else:
            self._meta.hide()


class BaseProgressPanel(BaseDashboardPanel):
    """
    Base panel with progress bar support.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        from PySide6.QtWidgets import QProgressBar
        
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(20)
        
        # Insert progress bar after primary label
        self._layout.insertWidget(1, self._progress)
    
    def set_progress(self, value: int, maximum: int = 100, variant: str = ""):
        """Set progress bar value and style."""
        self._progress.setRange(0, maximum)
        self._progress.setValue(value)
        self._progress.setVisible(value > 0 and value < maximum)
        
        if variant:
            self._progress.setProperty("variant", variant)
            self._progress.style().unpolish(self._progress)
            self._progress.style().polish(self._progress)