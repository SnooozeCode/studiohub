# hub_models/print_jobs_model_qt.py
from __future__ import annotations

from typing import Any, List

from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt

from studiohub.services.print_log_state import PrintLogState, PrintJobRecord


# =====================================================
# Column Map
# =====================================================

COL_TIME   = 0
COL_FILE_A = 1
COL_FILE_B = 2
COL_FORMAT = 3
COL_LENGTH = 4
COL_COST   = 5
COL_STATUS = 6
COL_FAILED = 7

COLUMN_COUNT = 8

HEADERS = (
    "Time",
    "File A",
    "File B",
    "Format",
    "Length",
    "Cost",
    "Status",
    "",
)


# =====================================================
# Custom Roles
# =====================================================

ROLE_JOB = Qt.UserRole
ROLE_IS_FAILED = Qt.UserRole + 1


# =====================================================
# Print Jobs Table Model
# =====================================================

class PrintJobsModelQt(QtCore.QAbstractTableModel):
    """
    Canonical Print Jobs table model.

    Consumes:
      - PrintLogState (event-merged job records)

    Owns:
      - Display formatting
      - Derived status logic
      - Length + cost presentation

    NEVER mutates data.
    """
    status_message = QtCore.Signal(str)
    
    def __init__(
        self,
        *,
        print_log_state: PrintLogState,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._state = print_log_state
        self._rows: List[PrintJobRecord] = []

        self._failed_bg = QtGui.QColor("#3a1f1f")

        self._state.changed.connect(self._on_state_changed)
        self._on_state_changed()

    # -------------------------------------------------
    # State -> Rows
    # -------------------------------------------------

    def _on_state_changed(self) -> None:
        self.beginResetModel()
        self._rows = list(self._state.jobs)
        self.endResetModel()

    # -------------------------------------------------
    # Qt Model Interface
    # -------------------------------------------------

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return COLUMN_COUNT

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(HEADERS):
            return HEADERS[section]
        return None

    def data(self, index: QtCore.QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if not (0 <= row < len(self._rows)):
            return None

        job = self._rows[row]

        is_failed = bool(getattr(job, "failed", False))
        is_reprinted = bool(getattr(job, "reprinted", False)) if is_failed else False

        # -----------------------------
        # Custom roles
        # -----------------------------
        if role == ROLE_JOB:
            return job

        if role == ROLE_IS_FAILED:
            return is_failed

        # -----------------------------
        # Alignment
        # -----------------------------
        if role == Qt.TextAlignmentRole:
            if col in (COL_FORMAT, COL_LENGTH, COL_COST, COL_STATUS, COL_FAILED):
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        # -----------------------------
        # Background
        # -----------------------------
        if role == Qt.BackgroundRole and is_failed:
            return self._failed_bg

        # -----------------------------
        # Tooltips
        # -----------------------------
        if role == Qt.ToolTipRole:
            if col == COL_STATUS and is_failed:

                lines = []
                failed_at = getattr(job, "failed_at", None)
                reprinted_at = getattr(job, "reprinted_at", None)
                reason = getattr(job, "fail_reason", None)

                if failed_at:
                    lines.append(f"Failed at {failed_at:%m/%d/%Y %I:%M %p}")

                if reprinted_at:
                    lines.append(f"Reprinted at {reprinted_at:%m/%d/%Y %I:%M %p}")

                if reason:
                    lines.append(reason)

                return "\n".join(lines) if lines else None

        # -----------------------------
        # Display
        # -----------------------------
        if role == Qt.DisplayRole:
            if col == COL_TIME:
                return job.timestamp.strftime("%m/%d/%Y %I:%M %p")

            if col == COL_FILE_A:
                return job.files[0].get("poster_id", "") if job.files else ""

            if col == COL_FILE_B:
                return job.files[1].get("poster_id", "") if len(job.files) > 1 else ""

            if col == COL_FORMAT:
                mode = (job.mode or "").lower()
                return "2-UP" if mode == "2up" else (job.size or "")

            if col == COL_LENGTH:
                planned = self._planned_length_for(job)
                actual_in = getattr(job, "actual_in", None)
                if is_failed and actual_in is not None and planned:
                    return f'{float(actual_in):.1f}" / {planned:.0f}"'
                return f'{planned:.0f}"' if planned else ""

            if col == COL_COST:
                actual_in = getattr(job, "actual_in", None)
                if is_failed and actual_in is not None:
                    planned = self._planned_length_for(job)
                    if planned:
                        try:
                            ratio = float(actual_in) / float(planned)
                            ratio = max(0.0, min(ratio, 1.0))
                            return f"${job.cost_usd * ratio:.2f}"
                        except Exception:
                            pass
                return f"${job.cost_usd:.2f}"

            if col == COL_STATUS:
                if is_reprinted:
                    return "Reprinted"
                if is_failed:
                    return "Failed"
                return "Success"

            if col == COL_FAILED:
                return ""

        return None

    # -------------------------------------------------
    # Utilities
    # -------------------------------------------------

    @staticmethod
    def _planned_length_for(job: PrintJobRecord) -> float:
        mode = (job.mode or "").lower()
        size = job.size

        if mode == "2up":
            return 24.0
        if size == "12x18":
            return 18.0
        if size == "18x24":
            return 24.0
        if size == "24x36":
            return 36.0
        return 0.0
