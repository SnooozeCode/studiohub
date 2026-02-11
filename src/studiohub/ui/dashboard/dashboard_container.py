from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


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
    No header tools.
    """

    def __init__(self, title: str, content: QWidget, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardSurface")
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("DashboardCardTitle")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(title_label)
        layout.addWidget(content)
