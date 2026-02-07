from __future__ import annotations

from datetime import datetime

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from PySide6.QtGui import QFont
from studiohub.style.typography.rules import apply_typography


def format_date(date_str: str | None) -> str:
    """Convert ISO date string → human-readable dashboard date."""
    if not date_str:
        return "—"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%b %d, %Y")
    except Exception:
        return "—"


class DashboardCard(QtWidgets.QFrame):
    """
    Base dashboard surface.

    GRID-NEUTRAL DESIGN:
    - No outer margins
    - No implicit vertical spacing
    - No minimum or fixed heights
    - Fully controlled by parent layout/grid
    """

    def __init__(
        self,
        title: str = "",
        *,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        self.setObjectName("DashboardCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        # ----------------------------------------------------
        # Outer layout (GRID-NEUTRAL)
        # ----------------------------------------------------
        self._outer = QtWidgets.QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        # ----------------------------------------------------
        # Header row
        # ----------------------------------------------------
        self.header = QtWidgets.QWidget(self)
        self.header.setObjectName("DashboardCardHeader")
        self.header.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )

        header_layout = QtWidgets.QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 12, 12, 6)
        header_layout.setSpacing(8)

        self.lbl_title = QtWidgets.QLabel(title)
        self.lbl_title.setProperty("typography", "h6")
        apply_typography(self.lbl_title, "h6")
        self.lbl_title.setObjectName("DashboardCardTitle")
        self.lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Right column (value + optional subtitle)
        self._header_right = QtWidgets.QWidget(self.header)
        self._header_right.setObjectName("DashboardCardHeaderRight")
        self._header_right.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Minimum,
        )

        self._header_right_layout = QtWidgets.QVBoxLayout(self._header_right)
        self._header_right_layout.setContentsMargins(0, 0, 0, 0)
        self._header_right_layout.setSpacing(2)
        self._header_right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._header_right_slot = QtWidgets.QWidget(self._header_right)
        self._header_right_slot.setObjectName("DashboardCardHeaderRightSlot")
        self._header_right_slot.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Minimum,
        )

        self._header_right_slot_layout = QtWidgets.QHBoxLayout(self._header_right_slot)
        self._header_right_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._header_right_slot_layout.setSpacing(4)
        self._header_right_slot_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.lbl_subtitle = QtWidgets.QLabel("")
        self.lbl_subtitle.setProperty("typography", "caption")
        apply_typography(self.lbl_subtitle, "small")
        self.lbl_subtitle.setObjectName("DashboardCardSubtitle")
        self.lbl_subtitle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_subtitle.hide()

        font = self.lbl_subtitle.font()
        font.setStyleStrategy(QFont.PreferQuality)
        self.lbl_subtitle.setFont(font)
        self.lbl_subtitle.setAttribute(Qt.WA_SetFont, True)

        self._header_right_layout.addWidget(self._header_right_slot)
        self._header_right_layout.addWidget(self.lbl_subtitle)

        header_layout.addWidget(self.lbl_title, 1)
        header_layout.addWidget(self._header_right, 0)

        # ----------------------------------------------------
        # Optional divider (off by default)
        # ----------------------------------------------------
        self._header_divider = QtWidgets.QFrame(self)
        self._header_divider.setObjectName("KPIDivider")
        self._header_divider.setFixedHeight(1)
        self._header_divider.hide()

        # ----------------------------------------------------
        # Content host (expanding)
        # ----------------------------------------------------

        self.content_host = QtWidgets.QWidget(self)
        self.content_host.setObjectName("DashboardCardContentHost")
        self.content_host.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        host_layout = QtWidgets.QVBoxLayout(self.content_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        # ----------------------------------------------------
        # Inner padding container (VISUAL ONLY)
        # ----------------------------------------------------
        self._content_inner = QtWidgets.QWidget(self.content_host)
        self._content_inner.setObjectName("DashboardCardContentInner")
        self._content_inner.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        self.content = QtWidgets.QVBoxLayout(self._content_inner)
        self.content.setContentsMargins(12, 12, 12, 12)  # ✅ visual padding restored
        self.content.setSpacing(8)

        host_layout.addWidget(self._content_inner, 1)


        # ----------------------------------------------------
        # Assemble
        # ----------------------------------------------------
        self._outer.addWidget(self.header)
        self._outer.addWidget(self._header_divider)
        self._outer.addWidget(self.content_host, 1)

    # --------------------------------------------------------
    # Header API
    # --------------------------------------------------------

    def set_subtitle(self, text: str | None) -> None:
        if text:
            self.lbl_subtitle.setText(text)
            self.lbl_subtitle.show()
        else:
            self.lbl_subtitle.clear()
            self.lbl_subtitle.hide()

    def set_header_divider(self, visible: bool) -> None:
        self._header_divider.setVisible(bool(visible))

    def clear_header_right(self) -> None:
        while self._header_right_slot_layout.count():
            item = self._header_right_slot_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def set_header_widget(self, widget: QtWidgets.QWidget) -> None:
        self.clear_header_right()
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Minimum,
        )
        self._header_right_slot_layout.addWidget(widget)

    def set_header_value(
        self,
        value: str,
        *,
        unit: str | None = None,
        style: str = "title",
    ) -> None:
        self.clear_header_right()

        lbl_value = QtWidgets.QLabel(str(value))
        lbl_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if style == "kpi":
            lbl_value.setObjectName("KPIValue")
            lbl_value.setProperty("typography", "h4")
            apply_typography(lbl_value, "h4")
        else:
            # "title" style: smaller than KPI but still emphasized
            lbl_value.setObjectName("DashboardCardHeaderValue")
            lbl_value.setProperty("typography", "h6")
            apply_typography(lbl_value, "h6")

        self._header_right_slot_layout.addWidget(lbl_value)

        if unit:
            lbl_unit = QtWidgets.QLabel(str(unit))
            lbl_unit.setProperty("typography", "caption")
            lbl_unit.setObjectName("KPIUnit")
            lbl_unit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._header_right_slot_layout.addWidget(lbl_unit)

    # --------------------------------------------------------
    # Content helpers
    # --------------------------------------------------------

    def add_widget(self, widget: QtWidgets.QWidget, stretch: int = 0) -> None:
        self.content.addWidget(widget, stretch)

    def add_layout(self, layout: QtWidgets.QLayout, stretch: int = 0) -> None:
        self.content.addLayout(layout, stretch)
