from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from studiohub.theme.styles.utils import repolish
from PySide6.QtGui import QFont
from studiohub.theme.styles.typography import apply_typography, BASE_PX


# ============================================================
# Layout constants (CRITICAL for alignment)
# ============================================================

VALUE_COL_WIDTH = 42
DELTA_COL_WIDTH = 44
MARKER_WIDTH = 4
LABEL_INDENT = 6


class LedgerBarRow(QtWidgets.QWidget):
    """
    Shared ledger-style bar row used by:
    - Print Count (Archive / Studio)
    - Archive Completion
    """

    BAR_V_INSET = 0  # smaller = thicker bar

    def __init__(
        self,
        *,
        label: str,
        bar_role: str,  # "archive" | "studio"
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        self.setFont(QFont())
        self._value = 0
        self._delta = 0
        self._fractiontion = 0.0

        self.setObjectName("CostRow")

        self.setFixedHeight(int(BASE_PX * 2.1))
        self.setProperty("barRole", bar_role)
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Zero marker
        self.zero_marker = QtWidgets.QFrame()
        self.zero_marker.setObjectName("CostMarker")
        self.zero_marker.setFixedSize(MARKER_WIDTH, 14)
        self.zero_marker.hide()

        # Label
        self.label = QtWidgets.QLabel(label)
        apply_typography(self.label, "caption")
        self.label.setObjectName("CostLabel")
        self.label.setContentsMargins(LABEL_INDENT, 0, 0, 0)

        # Value
        self.value_lbl = QtWidgets.QLabel("0")
        apply_typography(self.value_lbl, "caption")
        self.value_lbl.setObjectName("CostAmount")
        self.value_lbl.setFixedWidth(VALUE_COL_WIDTH)
        self.value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Delta (optional; can stay unused)
        self.delta_lbl = QtWidgets.QLabel("")
        apply_typography(self.delta_lbl, "caption")
        self.delta_lbl.setObjectName("LedgerDelta")
        self.delta_lbl.setFixedWidth(DELTA_COL_WIDTH)
        self.delta_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self.zero_marker)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.delta_lbl)

        # Bar layer
        self.bar = QtWidgets.QFrame(self)
        self.bar.setObjectName("PVSBar")
        self.bar.setAttribute(Qt.WA_StyledBackground, True)
        self.bar.lower()

    # -----------------------------------------------------

    def set_values(self, value: int, delta: int = 0) -> None:
        self._value = max(0, int(value))
        self._delta = int(delta)

        self.value_lbl.setText(str(self._value))
        self.zero_marker.setVisible(self._value == 0)

        if delta:
            arrow = "▴" if delta >= 0 else "▾"
            self.delta_lbl.setText(f"{arrow} ({abs(delta)})")
        else:
            self.delta_lbl.setText("")

        self._update_delta_semantics()

    def set_fraction(self, frac: float) -> None:
        self._fractiontion = max(0.0, min(1.0, frac))
        self._update_bar_geometry()

    # -----------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_bar_geometry()

    def _update_bar_geometry(self) -> None:
        inset = self.BAR_V_INSET
        h = max(1, self.height() - (inset * 2))

        if self._fractiontion >= 1.0:
            # FULL BAR — ignore marker offset
            w = self.width()
        else:
            w = int(self.width() * self._fractiontion)

        self.bar.setGeometry(0, inset, w, h)

    def _update_delta_semantics(self) -> None:
        if self._delta > 0:
            self.delta_lbl.setProperty("delta", "up")
        elif self._delta < 0:
            self.delta_lbl.setProperty("delta", "down")
        else:
            self.delta_lbl.setProperty("delta", "neutral")

        repolish(self.delta_lbl)
