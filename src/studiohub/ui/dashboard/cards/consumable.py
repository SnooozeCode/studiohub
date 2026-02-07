from __future__ import annotations

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPalette
from PySide6.QtSvg import QSvgRenderer

from .base import DashboardCard
from datetime import datetime


class ConsumableKPICard(DashboardCard):
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

    def __init__(
        self,
        title: str,
        *,
        unit: str = "",
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(title=title, parent=parent)


        # ----------------------------
        # Exposed KPI value (header-owned)
        # ----------------------------
        self.lbl_value = QtWidgets.QLabel("—")
        self.lbl_value.setObjectName("KPIValue")

        self.lbl_unit = QtWidgets.QLabel(unit)
        self.lbl_unit.setObjectName("KPIUnit")

        # ----------------------------
        # Progress bar
        # ----------------------------
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setMinimumHeight(12)
        self.progress.setMaximumHeight(15)


        self.add_widget(self.progress)

        # ----------------------------
        # Meta row
        # ----------------------------
        meta_row = QtWidgets.QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)

        self.lbl_last_replaced = QtWidgets.QLabel("Last replaced: —")
        self.lbl_last_replaced.setObjectName("KPIMetaMuted")

        meta_row.addWidget(self.lbl_last_replaced)
        meta_row.addStretch(1)

        self.btn_replace = QToolButton()
        self.btn_replace.setObjectName("ReplaceButton")

        accent = self.palette().color(QPalette.Highlight)
        self.btn_replace.setIcon(
            ConsumableKPICard.tinted_svg_icon(
                "assets/icons/replace.svg",
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

        self.add_layout(meta_row)

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
    # API
    # -------------------------------------------------

    def set_status(self, value, percent: int) -> None:
        self.lbl_value.setText(str(value))
        self.progress.setValue(max(0, min(100, int(percent))))

    def set_last_replaced(self, date_str: str | None) -> None:
        formatted = self._format_timestamp(date_str)
        self.lbl_last_replaced.setText(f"Last replaced: {formatted}")
