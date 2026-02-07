# ui/delegates/failed_icon_delegate.py
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from studiohub.ui.icons import render_svg

try:
    from studiohub.hub_models.print_jobs_model_qt import ROLE_IS_FAILED, ROLE_JOB
except Exception:
    ROLE_IS_FAILED = Qt.UserRole + 1
    ROLE_JOB = Qt.UserRole


class FailedIconDelegate(QtWidgets.QStyledItemDelegate):
    """
    Failed / Reprint icon delegate.

    States:
    - Normal job:                  red "mark failed" icon (clickable)
    - Failed job (not reprinted):  reprint icon (clickable)
    - Failed + reprinted:          muted reprint icon (NOT clickable)

    Contract:
    - ROLE_IS_FAILED -> bool
    - ROLE_JOB -> PrintJobRecord with .reprinted bool
    """

    clicked = QtCore.Signal(QtCore.QModelIndex, str)  # (index, action)

    ICON_SIZE = 14

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._fail_active: QtGui.QPixmap | None = None
        self._reprint_active: QtGui.QPixmap | None = None
        self._reprint_disabled: QtGui.QPixmap | None = None

    # -------------------------------------------------
    # Icon cache
    # -------------------------------------------------

    def _ensure_icons(self) -> None:
        if self._fail_active is None:
            self._fail_active = render_svg(
                "status_missing",
                size=self.ICON_SIZE,
                color=QtGui.QColor("#FF6B6B"),
            )

        if self._reprint_active is None:
            self._reprint_active = render_svg(
                "refresh",
                size=self.ICON_SIZE,
                color=QtGui.QColor("#7AA2F7"),
            )

        if self._reprint_disabled is None:
            self._reprint_disabled = render_svg(
                "refresh",
                size=self.ICON_SIZE,
                color=QtGui.QColor("#5A6E73"),
            )

    # -------------------------------------------------
    # Paint
    # -------------------------------------------------

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        self._ensure_icons()
        painter.save()

        job = index.data(ROLE_JOB)
        is_failed = bool(index.data(ROLE_IS_FAILED))
        is_reprinted = bool(getattr(job, "reprinted", False))

        clickable = (not is_failed) or (is_failed and not is_reprinted)

        if (option.state & QtWidgets.QStyle.State_MouseOver) and clickable:
            painter.fillRect(option.rect, QtGui.QColor(122, 162, 247, 28))

        # --- Icon selection ---
        if is_failed and is_reprinted:
            icon = self._reprint_disabled
        elif is_failed:
            icon = self._reprint_active
        else:
            icon = self._fail_active

        x = option.rect.center().x() - icon.width() // 2
        y = option.rect.center().y() - icon.height() // 2
        painter.drawPixmap(x, y, icon)

        painter.restore()

    # -------------------------------------------------
    # Interaction
    # -------------------------------------------------

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if isinstance(event, QtGui.QMouseEvent) and event.button() != Qt.LeftButton:
                return False

            job = index.data(ROLE_JOB)
            is_failed = bool(index.data(ROLE_IS_FAILED))
            is_reprinted = bool(getattr(job, "reprinted", False))

            # Failed + reprinted → disabled
            if is_failed and is_reprinted:
                return False

            if is_failed:
                self.clicked.emit(index, "reprint")
            else:
                self.clicked.emit(index, "fail")

            return True

        return False
