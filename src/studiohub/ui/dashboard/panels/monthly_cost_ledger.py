from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from studiohub.style.styles.typography import apply_typography


# ============================================================
# DTO
# ============================================================

@dataclass(frozen=True)
class MonthlyCostBreakdown:
    ink: float
    paper: float
    shipping_supplies: float
    prints: int

    @property
    def total(self) -> float:
        return self.ink + self.paper + self.shipping_supplies

    @property
    def avg_per_print(self) -> float:
        if not self.prints:
            return 0.0
        return self.total / self.prints


# ============================================================
# Cost Row
# ============================================================

class _CostRow(QtWidgets.QWidget):
    def __init__(self, label: str, amount: float, marker_color: str, parent=None):
        super().__init__(parent)

        self.setObjectName("CostRow")

        marker = QtWidgets.QFrame()
        marker.setObjectName("CostMarker")
        marker.setProperty("markerColor", marker_color)
        marker.setFixedWidth(6)

        self.label = QtWidgets.QLabel(label)
        self.label.setObjectName("CostLabel")
        apply_typography(self.label, "caption")

        self.amount = QtWidgets.QLabel(f"${amount:,.2f}")
        self.amount.setObjectName("CostAmount")
        apply_typography(self.amount, "caption")
        self.amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        row.addWidget(marker)
        row.addWidget(self.label, 1)
        row.addWidget(self.amount)


# ============================================================
# Panel
# ============================================================

class MonthlyCostLedgerPanel(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("MonthlyCostLedgerPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Panel subtitle (matches Patents vs Studio)
        self.subtitle = QtWidgets.QLabel("Production cost across all prints.")
        apply_typography(self.subtitle, "caption")
        self.subtitle.setObjectName("DashboardCardSubtitle")
        self.subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.subtitle)

        # Rows container
        self.rows_container = QtWidgets.QVBoxLayout()
        self.rows_container.setSpacing(10)
        root.addLayout(self.rows_container)

        # Divider (matches DashboardCard ledger divider)
        self.divider = QtWidgets.QFrame()
        self.divider.setObjectName("LedgerDivider")
        self.divider.setFixedHeight(1)
        self.divider.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )

        root.addWidget(self.divider, 0, Qt.AlignLeft)


        # Total row
        total_row = QtWidgets.QHBoxLayout()
        total_row.setContentsMargins(0, 0, 0, 0)

        self.total_label = QtWidgets.QLabel("TOTAL")
        apply_typography(self.total_label, "caption")
        self.total_label.setObjectName("LedgerTotalLabel")

        self.total_amount = QtWidgets.QLabel("$0.00")
        apply_typography(self.total_amount, "caption")
        self.total_amount.setObjectName("LedgerTotalAmount")
        self.total_amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        total_row.addWidget(self.total_label, 1)
        total_row.addWidget(self.total_amount)
        root.addLayout(total_row)

        # Footer
        self.footer = QtWidgets.QLabel("")
        apply_typography(self.footer, "small")
        self.footer.setObjectName("LedgerFooter")
        self.footer.setAlignment(Qt.AlignHCenter)
        root.addWidget(self.footer)


        # -------------------------------------------------
        # Initialize with zero values so rows always render
        # -------------------------------------------------
        self.update_costs(
            MonthlyCostBreakdown(
                paper=0.0,
                ink=0.0,
                shipping_supplies=0.0,
                prints=0,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.divider.setFixedWidth(int(self.width() * 0.7))


    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def update_costs(self, data: MonthlyCostBreakdown) -> None:
        # Clear existing rows
        while self.rows_container.count():
            item = self.rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows_container.addWidget(
            _CostRow("Paper", data.paper, "paper")
        )
        self.rows_container.addWidget(
            _CostRow("Ink", data.ink, "ink")
        )
        self.rows_container.addWidget(
            _CostRow("Shipping Supplies", data.shipping_supplies, "shipping")
        )

        self.total_amount.setText(f"${data.total:,.2f}")
        self.footer.setAlignment(Qt.AlignHCenter)
        self.footer.setText(
            f"{data.prints} prints · Avg ${data.avg_per_print:,.2f} per print"
        )

