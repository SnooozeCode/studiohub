# studiohub/style/typography/widget_styler.py
"""
Ensures all widgets in a view get proper typography.
"""

from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QToolButton, QTreeView, QTableView, QHeaderView
from studiohub.style.typography.rules import apply_typography

class WidgetStyler:
    """
    Walks widget trees and applies consistent typography.
    """
    
    @classmethod
    def style_widget(cls, widget: QWidget):
        """Apply typography to a single widget based on its type and properties."""
        
        # Check if already has explicit typography property
        if widget.property("typography"):
            return
        
        # Style based on widget type and object name
        obj_name = widget.objectName()
        
        # Label styling
        if isinstance(widget, QLabel):
            if obj_name.startswith("Panel"):
                if "Primary" in obj_name:
                    apply_typography(widget, "h2")
                elif "Secondary" in obj_name:
                    apply_typography(widget, "body")
                elif "Meta" in obj_name:
                    apply_typography(widget, "small")
                else:
                    apply_typography(widget, "body")
            elif "Status" in obj_name:
                apply_typography(widget, "body-small")
            elif "Title" in obj_name:
                apply_typography(widget, "h4")
            elif obj_name == "DashboardCardTitle":
                apply_typography(widget, "h3")
            elif obj_name == "ActionTitle":
                apply_typography(widget, "h2")
            elif obj_name == "ActionSubtitle":
                apply_typography(widget, "h6")
            else:
                # Check role property
                role = widget.property("role")
                if role == "section-title":
                    apply_typography(widget, "h3")
                elif role == "field-label":
                    apply_typography(widget, "body-strong")
                elif role == "muted":
                    apply_typography(widget, "caption")
                else:
                    apply_typography(widget, "body")
        
        # Button styling
        elif isinstance(widget, (QPushButton, QToolButton)):
            if obj_name == "SourceToggle":
                apply_typography(widget, "body")
            elif obj_name == "SidebarUtility":
                # Icons only, no text
                pass
            else:
                apply_typography(widget, "body")
        
        # Tree/Table styling
        elif isinstance(widget, (QTreeView, QTableView)):
            apply_typography(widget, "tree")
        
        # Header styling
        elif isinstance(widget, QHeaderView):
            apply_typography(widget, "h4")
    
    @classmethod
    def style_widget_tree(cls, widget: QWidget):
        """
        Recursively style a widget and all its children.
        Call this after creating a view.
        """
        cls.style_widget(widget)
        
        for child in widget.findChildren(QWidget):
            cls.style_widget(child)