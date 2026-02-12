from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QHeaderView


# =====================================================
# Table Model
# =====================================================

class IndexLogTableModel(QtCore.QAbstractTableModel):
    HEADERS = [
        "Time",
        "Source",
        "Archive",
        "Studio",
        "Total",
        "Duration (ms)",
        "Status",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict[str, Any]] = []

    # ----------------------------
    # Helpers
    # ----------------------------

    def _format_timestamp(self, ts: str) -> str:
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime("%m/%d/%Y  %I:%M %p")
        except Exception:
            return ts

    def _format_source(self, raw: str) -> str:
        mapping = {
            "startup": "Startup",
            "refresh_all": "Refresh",
            "manual": "Manual",
        }
        return mapping.get(raw, raw.replace("_", " ").title())

    def _safe_int(self, value) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    # ----------------------------
    # Qt model overrides
    # ----------------------------

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return None

        if role == QtCore.Qt.DisplayRole:
            return self.HEADERS[section]

        if role == QtCore.Qt.FontRole:
            f = QtGui.QFont()
            f.setBold(True)
            return f

        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter

        return None

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        archive = self._safe_int(row.get("Archive"))
        studio = self._safe_int(row.get("Studio"))
        total = archive + studio

        if role == QtCore.Qt.DisplayRole:
            return [
                self._format_timestamp(row.get("Time", "")),
                self._format_source(row.get("Source", "")),
                archive,
                studio,
                total,
                f'{self._safe_int(row.get("Duration (ms)")):,}',
                row.get("Status", ""),
            ][col]

        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter

        if role == QtCore.Qt.FontRole and col == 6:
            if row.get("Status") == "ERROR":
                f = QtGui.QFont()
                f.setBold(True)
                return f

        if role == QtCore.Qt.ForegroundRole and col == 6:
            if row.get("Status") == "ERROR":
                return QtGui.QBrush(QtGui.QColor("#ff6b6b"))

        return None

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()


# =====================================================
# Index Log View
# =====================================================

class IndexLogViewQt(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ----------------------------
        # Header
        # ----------------------------
        top_header = QtWidgets.QHBoxLayout()

        title = QtWidgets.QLabel("Index Log")
        f = title.font()
        f.setBold(True)
        title.setFont(f)

        top_header.addWidget(title)
        top_header.addStretch(1)
        root.addLayout(top_header)

        # ----------------------------
        # Table
        # ----------------------------
        self.table = QtWidgets.QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        self.model = IndexLogTableModel(parent=self)
        self.table.setModel(self.model)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Fixed)

        # Column widths
        self.table.setColumnWidth(0, 190)  # Time
        self.table.setColumnWidth(1, 140)  # Source
        self.table.setColumnWidth(2, 90)   # Archive
        self.table.setColumnWidth(3, 90)   # Studio
        self.table.setColumnWidth(4, 90)   # Total
        self.table.setColumnWidth(5, 130)  # Duration
        self.table.setColumnWidth(6, 90)   # Status

        self.table.verticalHeader().setDefaultSectionSize(42)

        root.addWidget(self.table, 1)

        QtCore.QTimer.singleShot(
            0,
            lambda: self._apply_initial_column_layout()
        )


    def _apply_initial_column_layout(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Source stretches

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.model.set_rows(rows)

    def showEvent(self, event):
        super().showEvent(event)
        self.table.horizontalHeader().setStretchLastSection(True)
