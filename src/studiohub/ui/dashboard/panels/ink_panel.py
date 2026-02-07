from __future__ import annotations

from datetime import datetime

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPalette
from PySide6.QtSvg import QSvgRenderer

from studiohub.style.typography.rules import apply_typography
from studiohub.utils.paths import asset_path

class InkPanel(QtWidgets.QWidget):
    """
    Ink panel body (NO header).

    Intended to live inside a DashboardCard titled "INK LEVELS".
    The card header owns the value + unit (e.g., "84 %").
    """

    replace_requested = QtCore.Signal()

    @staticmethod
    def tinted_svg_icon(path: str, color: QColor, size: QtCore.QSize) -> QIcon:
        pixmap = QPixmap(size)
        pixmap.fill(QtCore.Qt.transparent)

        renderer = QSvgRenderer(path)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()

        return QIcon(pixmap)

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # -------------------------------------------------
        # Panel description (matches StudioPanel pattern)
        # -------------------------------------------------
        self.description = QtWidgets.QLabel(
            "Check current ink levels in TC-21 (Estimated)."
        )
        apply_typography(self.description, "caption")
        self.description.setObjectName("DashboardCardSubtitle")
        self.description.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.description)

        # Progress bar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(24)
        root.addWidget(self.progress)

        # Meta row
        meta_row = QtWidgets.QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)

        self.lbl_last_replaced = QtWidgets.QLabel("Last replaced: —")
        apply_typography(self.lbl_last_replaced, "caption")
        self.lbl_last_replaced.setObjectName("KPIMetaMuted")
        meta_row.addWidget(self.lbl_last_replaced)
        meta_row.addStretch(1)

        self.btn_replace = QToolButton()
        self.btn_replace.setObjectName("ReplaceButton")

        accent = self.palette().color(QPalette.Highlight)
        self.btn_replace.setIcon(
            InkPanel.tinted_svg_icon(
                asset_path("icons", "replace.svg"),
                accent,
                QtCore.QSize(16, 16),
            )
        )
        self.btn_replace.setIconSize(QtCore.QSize(16, 16))
        self.btn_replace.setAutoRaise(True)
        self.btn_replace.setCursor(Qt.PointingHandCursor)
        self.btn_replace.setToolTip("Mark as replaced")
        self.btn_replace.clicked.connect(self.replace_requested.emit)

        meta_row.addWidget(self.btn_replace)
        root.addLayout(meta_row)
        root.addStretch(1)

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _format_timestamp(self, ts: str | None) -> str:
        if not ts:
            return "—"
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime("%b %d, %Y · %I:%M %p")
        except Exception:
            return "—"

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def set_progress(self, percent: int) -> None:
        self.progress.setValue(max(0, min(100, int(percent))))

    def set_last_replaced(self, date_str: str | None) -> None:
        self.lbl_last_replaced.setText(f"Last replaced: {self._format_timestamp(date_str)}")
