from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
from PySide6.QtCore import Qt
from studiohub.style.typography.rules import apply_typography

class DashboardSurface(QFrame):
    """
    The canonical dashboard panel surface.
    This is where theme tokens apply.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardSurface")
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._layout = layout

    def add_content(self, widget: QWidget):
        self._layout.addWidget(widget)


class DashboardContainer(QFrame):
    """
    Clean dashboard panel container.
    Title with optional header widget on the same line.
    Content fills the rest.
    """

    def __init__(self, title: str, content: QWidget, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardSurface")
        self.setFrameShape(QFrame.NoFrame)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # =====================================================
        # Header row (title + optional widget)
        # =====================================================
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("DashboardCardTitle")
        apply_typography(self.title_label, "h3")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header_layout.addWidget(self.title_label)

        # Header widget (right-aligned) - initially empty
        self.header_widget = None
        header_layout.addStretch()  # Push title left, header widget right

        # Store header layout for later use
        self.header_layout = header_layout
        layout.addLayout(header_layout)

        # Content
        self.content = content
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(content)

    def set_header_widget(self, widget: QWidget):
        """Set a widget to appear in the header (right-aligned)."""
        # Remove existing header widget if any
        if self.header_widget:
            self.header_layout.removeWidget(self.header_widget)
            self.header_widget.setParent(None)
            self.header_widget.deleteLater()

        # Add new widget
        self.header_widget = widget
        widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.header_layout.addWidget(widget)

    def replace_content(self, new_content: QWidget):
        """Replace the current content widget with a new one."""
        # Remove old content
        if self.content:
            layout = self.layout()
            layout.removeWidget(self.content)
            self.content.setParent(None)
            self.content.deleteLater()

        # Add new content
        self.content = new_content
        new_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout().addWidget(new_content)

    def set_title(self, title: str):
        """Update the container title."""
        self.title_label.setText(title)