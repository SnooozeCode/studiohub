from __future__ import annotations

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from studiohub.style.utils.repolish import repolish
from studiohub.ui.dashboard.components.ledger_bar_row import LedgerBarRow
from studiohub.style.typography.rules import apply_typography


# ============================================================
# Layout constants (CRITICAL for alignment)
# ============================================================

VALUE_COL_WIDTH = 42
DELTA_COL_WIDTH = 44
MARKER_WIDTH = 4
LABEL_INDENT = 6

# ============================================================
# Main Panel
# ============================================================

class ArchiveVsStudioChart(QtWidgets.QFrame):
    """
    Ledger-style panel.
    Bars are layered frames; colors are 100% QSS-driven.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
    
        self._bar_limit = 50  # default expected monthly prints

        self.setObjectName("ArchiveVsStudioPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._archive = 0
        self._studio = 0
        self._delta_archive = 0
        self._delta_studio = 0
        self._delta_total = 0

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Subtitle
        self.subtitle = QtWidgets.QLabel("How many prints from each source.")
        apply_typography(self.subtitle, "caption")
        self.subtitle.setObjectName("DashboardCardSubtitle")
        self.subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.subtitle)

        # Rows
        self.row_archive = LedgerBarRow(label="ARCHIVE", bar_role="archive")
        self.row_studio  = LedgerBarRow(label="STUDIO",  bar_role="studio")

        root.addWidget(self.row_archive)
        root.addWidget(self.row_studio)

        root.addSpacing(6)

        # Divider (same behavior as Monthly Cost)
        self.divider = QtWidgets.QFrame()
        self.divider.setObjectName("LedgerDivider")
        self.divider.setFixedHeight(1)
        self.divider.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        root.addWidget(self.divider, 0, Qt.AlignLeft)

        root.addSpacing(8)

        # -----------------------------
        # TOTAL PRINTS ROW (ALIGNED)
        # -----------------------------

        total_row = QtWidgets.QHBoxLayout()
        total_row.setContentsMargins(LABEL_INDENT, 0, 0, 0)

        self.total_label = QtWidgets.QLabel("TOTAL PRINTS")
        apply_typography(self.total_label, "body-small")
        self.total_label.setObjectName("LedgerTotalLabel")

        self.total_value = QtWidgets.QLabel("0")
        apply_typography(self.total_value, "body-small")
        self.total_value.setObjectName("LedgerTotalAmount")
        self.total_value.setFixedWidth(VALUE_COL_WIDTH)
        self.total_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.total_delta = QtWidgets.QLabel("▴ (0)")
        apply_typography(self.total_delta, "body-small")
        self.total_delta.setObjectName("LedgerDelta")
        self.total_delta.setFixedWidth(DELTA_COL_WIDTH)
        self.total_delta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        total_row.addWidget(self.total_label, 1)
        total_row.addWidget(self.total_value)
        total_row.addWidget(self.total_delta)


        root.addLayout(total_row)

        # Footer
        self.footer = QtWidgets.QLabel("vs last month")
        apply_typography(self.footer, "small")
        self.footer.setObjectName("LedgerFooter")
        self.footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        root.addWidget(self.footer)

        repolish(self)

    # -----------------------------------------------------

    def set_values(
        self,
        *,
        archive: int,
        studio: int,
        delta_archive: int = 0,
        delta_studio: int = 0,
        delta_total: int = 0,
    ) -> None:
        self._archive = max(0, int(archive))
        self._studio = max(0, int(studio))

        self._delta_archive = int(delta_archive)
        self._delta_studio = int(delta_studio)
        self._delta_total = int(delta_total)

        total = max(1, self._archive + self._studio)

        self.row_archive.set_values(self._archive, self._delta_archive)
        self.row_studio.set_values(self._studio, self._delta_studio)

        self.row_archive.set_fraction(self._archive / total)
        self.row_studio.set_fraction(self._studio / total)

        self.total_value.setText(str(self._archive + self._studio))

        arrow = "▴" if self._delta_total >= 0 else "▾"
        self.total_delta.setText(f"{arrow} ({abs(self._delta_total)})")

        if self._delta_total > 0:
            self.total_delta.setProperty("delta", "up")
        elif self._delta_total < 0:
            self.total_delta.setProperty("delta", "down")
        else:
            self.total_delta.setProperty("delta", "neutral")

        repolish(self.total_delta)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.divider.setFixedWidth(int(self.width() * 0.15))
