from __future__ import annotations

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from .base import DashboardCard


class KPICard(DashboardCard):
    def __init__(
        self,
        title: str,
        value: str,
        *,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(title, parent=parent)

        # ---------------------------
        # Divider
        # ---------------------------
        divider = QtWidgets.QFrame()
        divider.setObjectName("KPIDivider")
        divider.setFixedHeight(1)
        self.add_widget(divider)

        # ---------------------------
        # Main row
        # ---------------------------
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(16)

        # LEFT — Issues / Missing
        meta_col = QtWidgets.QVBoxLayout()
        meta_col.setSpacing(6)
        meta_col.setAlignment(Qt.AlignBottom)

        self.lbl_issues = QtWidgets.QLabel("Issues: —")
        self.lbl_issues.setObjectName("KPIMetaLabel")

        self.lbl_missing = QtWidgets.QLabel("Missing: —")
        self.lbl_missing.setObjectName("KPIMetaLabel")

        meta_col.addStretch(1)
        meta_col.addWidget(self.lbl_issues)
        meta_col.addWidget(self.lbl_missing)

        # RIGHT — Big value
        value_col = QtWidgets.QVBoxLayout()
        value_col.setSpacing(4)
        value_col.setAlignment(Qt.AlignRight)
        value_col.setContentsMargins(0, 0, 36, 0)

        self.lbl_value = QtWidgets.QLabel(value)
        self.lbl_value.setObjectName("KPIValueXL")
        self.lbl_value.setAlignment(Qt.AlignRight)

        value_col.addStretch(1)
        value_col.addWidget(self.lbl_value)
        value_col.addStretch(2)

        # Assemble
        row.addLayout(meta_col)
        row.addStretch(1)
        row.addLayout(value_col)

        self.add_layout(row)

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def set_value(self, value: str) -> None:
        self.lbl_value.setText(value)

    def set_issues(self, count: int) -> None:
        self.lbl_issues.setText(f"Issues: {count}")

    def set_missing(self, count: int) -> None:
        self.lbl_missing.setText(f"Missing: {count}")
