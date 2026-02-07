from __future__ import annotations

from datetime import datetime, timezone

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPalette
from PySide6.QtSvg import QSvgRenderer

from studiohub.ui.dialogs.replace_paper import ReplacePaperDialog
from studiohub.style.utils.repolish import repolish
from studiohub.style.typography.rules import apply_typography
from studiohub.utils.paths import asset_path


class PaperPanel(QtWidgets.QWidget):
    """
    Paper panel body (NO header).

    Intended to live inside a DashboardCard titled "PAPER STOCK".
    The card header owns the value + unit (e.g., "120 ft").
    """

    # name, total_length
    replace_requested = QtCore.Signal(str, float)

    # ============================================================
    # Construction
    # ============================================================

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("PaperPanel")

        # Local cached state (for dialog defaults only)
        self._current_paper_name: str = ""
        self._current_total_length: float = 60.0

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # -------------------------------------------------
        # Subtitle (paper name)
        # -------------------------------------------------
        self.subtitle = QtWidgets.QLabel("—")
        apply_typography(self.subtitle, "caption")
        self.subtitle.setObjectName("DashboardCardSubtitle")
        self.subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.subtitle)

        # -------------------------------------------------
        # Progress bar
        # -------------------------------------------------
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(24)
        root.addWidget(self.progress)

        # -------------------------------------------------
        # Meta row
        # -------------------------------------------------
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
            self.tinted_svg_icon(
                asset_path("icons", "replace.svg"),
                accent,
                QtCore.QSize(16, 16),
            )
        )
        self.btn_replace.setIconSize(QtCore.QSize(16, 16))
        self.btn_replace.setAutoRaise(True)
        self.btn_replace.setCursor(Qt.PointingHandCursor)
        self.btn_replace.setToolTip("Replace paper roll")
        self.btn_replace.clicked.connect(self._on_replace_clicked)

        meta_row.addWidget(self.btn_replace)
        root.addLayout(meta_row)

        root.addStretch(1)

    # ============================================================
    # Qt Events
    # ============================================================

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure theme updates correctly on show / theme switch
        repolish(self)

    def _format_timestamp(self, ts: str | None) -> str:
        if not ts:
            return "—"

        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            local_dt = dt.astimezone()
            return local_dt.strftime("%b %d, %Y · %I:%M %p")
        except Exception:
            return "—"


    # ============================================================
    # Replace Flow
    # ============================================================

    def _on_replace_clicked(self) -> None:
        dlg = ReplacePaperDialog(self)

        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return

        name, length = dlg.get_values()

        if not name or length <= 0:
            return

        # Emit intent only — NO logging here
        self.replace_requested.emit(name, float(length))

    
    # ============================================================
    # Helpers
    # ============================================================

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

    # ============================================================
    # Public API (called by parent / metrics)
    # ============================================================

    def set_paper_name(self, name: str) -> None:
        self._current_paper_name = name or ""
        if name:
            self.subtitle.setText(f"Paper Name: {name}")
        else:
            self.subtitle.setText("Paper: —")

    def set_total_length(self, total_length: float) -> None:
        """
        Stored for dialog defaults only.
        """
        self._current_total_length = float(total_length or 0.0)

    def set_progress(self, percent: int) -> None:
        self.progress.setValue(max(0, min(100, int(percent))))

    def set_last_replaced(self, date_str: str | None) -> None:
        self.lbl_last_replaced.setText(
            f"Last replaced: {self._format_timestamp(date_str)}"
        )
