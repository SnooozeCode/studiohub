from __future__ import annotations

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt


class PrintEconomicsViewQt(QtWidgets.QWidget):
    """
    Print Economics View

    System-level SKU economics and performance analysis.
    Visual-first, table-dominant layout.
    Mock data only.
    """

    VIEW_KEY = "print_economics"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addWidget(self._build_header())
        root.addWidget(self._build_kpi_strip())
        root.addWidget(self._build_table(), 1)

    # -----------------------------------------------------
    # Header / Filters
    # -----------------------------------------------------

    def _build_header(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Print Economics")
        title.setObjectName("ViewTitle")
        layout.addWidget(title)

        layout.addStretch(1)

        layout.addWidget(self._filter("Period", ["Month", "Quarter", "Year"]))
        layout.addWidget(self._filter("Source", ["Both", "Archive", "Studio"]))
        layout.addWidget(self._filter("Size", ["All", "12×18", "18×24", "24×36"]))

        waste = QtWidgets.QCheckBox("Include Waste")
        waste.setChecked(True)
        waste.setObjectName("InlineCheckbox")
        layout.addWidget(waste)

        return w

    def _filter(self, label: str, items: list[str]) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        l = QtWidgets.QLabel(label)
        l.setObjectName("FilterLabel")
        layout.addWidget(l)

        cb = QtWidgets.QComboBox()
        cb.addItems(items)
        cb.setObjectName("FilterCombo")
        layout.addWidget(cb)

        return w

    # -----------------------------------------------------
    # KPI Strip (Context Only)
    # -----------------------------------------------------

    def _build_kpi_strip(self) -> QtWidgets.QWidget:
        strip = QtWidgets.QFrame()
        strip.setObjectName("KpiStrip")

        layout = QtWidgets.QHBoxLayout(strip)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(36)

        layout.addWidget(self._kpi_block("Avg Cost / Print", "$3.84"))
        layout.addWidget(self._kpi_block("Waste Cost", "$47.20"))
        layout.addWidget(self._kpi_block("Reprint Cost", "$22.80"))
        layout.addStretch(1)
        layout.addWidget(self._kpi_block("Worst SKU", "24×36 · Apollo Guidance"))

        return strip

    def _kpi_block(self, label: str, value: str) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        l = QtWidgets.QLabel(label)
        l.setObjectName("KpiLabel")
        layout.addWidget(l)

        v = QtWidgets.QLabel(value)
        v.setObjectName("KpiValue")
        layout.addWidget(v)

        return w

    # -----------------------------------------------------
    # SKU Performance Table (Primary Surface)
    # -----------------------------------------------------

    def _build_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QtWidgets.QLabel("SKU Performance")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        table = QtWidgets.QTableWidget(6, 11)
        table.setObjectName("EconomicsTable")

        table.setHorizontalHeaderLabels(
            [
                "Poster",
                "Src",
                "Size",
                "Prints",
                "Avg Cost",
                "Waste %",
                "Waste $",
                "Reprint %",
                "Total Cost",
                "Rank (Size)",
                "Flag",
            ]
        )

        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSortingEnabled(True)
        table.setWordWrap(False)

        # ---- Mock rows ----
        mock_rows = [
            ("Apollo Guidance", "ARC", "24×36", 14, 6.12, "22%", "$18.30", "21%", "$85.68", "3 / 5", "⚠⚠"),
            ("Saturn V", "ARC", "24×36", 6, 5.88, "18%", "$6.34", "17%", "$35.28", "4 / 5", "⚠"),
            ("NES Controller", "STU", "18×24", 31, 3.42, "9%", "$9.56", "3%", "$106.02", "2 / 8", ""),
            ("Wright Flyer", "ARC", "12×18", 54, 2.18, "4%", "$4.71", "0%", "$117.72", "1 / 12", ""),
            ("PS2 Logo", "STU", "12×18", 62, 1.94, "3%", "$3.61", "0%", "$120.28", "2 / 12", ""),
            ("NES Zapper", "STU", "18×24", 9, 3.88, "14%", "$4.89", "11%", "$34.92", "6 / 8", "⚠"),
        ]

        for r, row in enumerate(mock_rows):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(val))

                # Right-align numeric-ish columns
                if c >= 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                table.setItem(r, c, item)

        header = table.horizontalHeader()
        header.setStretchLastSection(True)

        # Sensible defaults (user can resize)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)  # Poster
        for i in range(1, table.columnCount()):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)

        layout.addWidget(table, 1)
        return w

    # -----------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------

    def on_activated(self) -> None:
        """
        Called by hub when view becomes active.
        Real aggregation will hook in here later.
        """
        pass
