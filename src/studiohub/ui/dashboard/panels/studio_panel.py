from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from studiohub.theme.styles.utils import repolish
from studiohub.ui.dashboard.components.ledger_bar_row import LedgerBarRow
from studiohub.theme.styles.typography import apply_typography

class StudioPanel(QtWidgets.QFrame):
    """
    Studio panel body.

    Mirrors ArchiveStatusPanel structurally:
    - Panel description
    - Ledger bar
    - Diagnostics (issues / missing)

    Differences:
    - No percentage semantics
    - No health state
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._issues = 0
        self._missing = 0
        self._fraction = 0.0

        self.setObjectName("StudioPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        # -------------------------------------------------
        # Panel description
        # -------------------------------------------------
        self.description = QtWidgets.QLabel(
            "Studio archive health and file diagnostics."
        )
        apply_typography(self.description, "caption")
        self.description.setObjectName("DashboardCardSubtitle")
        self.description.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.description)

        # -------------------------------------------------
        # Studio ledger bar
        # -------------------------------------------------
        self.complete_row = LedgerBarRow(
            label="COMPLETE",
            bar_role="studio",
        )

        # For Archive completion, delta is not meaningful.
        # Keep column alignment but render blank / collapsed.
        try:
            self.complete_row.delta_lbl.setText("")
            self.complete_row.delta_lbl.hide()
            self.complete_row.delta_lbl.setFixedWidth(0)

            # 6px inset from the right edge of the bar
            self.complete_row.value_lbl.setContentsMargins(0, 0, 6, 0)
        except Exception:
            pass

        root.addWidget(self.complete_row, 0)

        # -------------------------------------------------
        # Diagnostics
        # -------------------------------------------------
        diag = QtWidgets.QHBoxLayout()
        diag.setContentsMargins(0, 0, 0, 0)

        self.issues_lbl = QtWidgets.QLabel("Issues: —")
        apply_typography(self.issues_lbl, "caption")
        self.issues_lbl.setObjectName("KPIMetaMuted")
        self.issues_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.missing_lbl = QtWidgets.QLabel("Missing: —")
        apply_typography(self.missing_lbl, "caption")
        self.missing_lbl.setObjectName("KPIMetaMuted")
        self.missing_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        diag.addWidget(self.issues_lbl, 1)
        diag.addWidget(self.missing_lbl, 0)

        root.addLayout(diag)
        root.addStretch(1)

        repolish(self)

    # -------------------------------------------------
    # Public API (mirrors Archive)
    # -------------------------------------------------

    def set_values(self, *, issues: int, missing: int, fraction: float | None = None) -> None:
        self._issues = max(0, int(issues))
        self._missing = max(0, int(missing))

        self.issues_lbl.setText(f"Issues: {self._issues}")
        self.missing_lbl.setText(f"Missing: {self._missing}")

        if fraction is not None:
            self._fraction = max(0.0, min(1.0, float(fraction)))
            self.complete_row.set_fraction(self._fraction)

            percent = int(round(self._fraction * 100))
            self.complete_row.value_lbl.setText(f"{percent}%")

            # Align with Archive / Print Count
            self.complete_row.value_lbl.setContentsMargins(0, 0, 6, 0)

        repolish(self)


