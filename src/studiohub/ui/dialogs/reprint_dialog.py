from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from studiohub.services.print_log_state import PrintJobRecord
from studiohub.style.styles.typography import apply_typography
from studiohub.style.styles.utils import repolish


# =====================================================
# Reprint Request (pure intent)
# =====================================================

@dataclass(frozen=True)
class ReprintRequest:
    parent_job_id: str
    timestamp: datetime
    mode: str
    size: str
    files: List[Dict[str, Any]]
    mark_as_reprint: bool


# =====================================================
# Reprint Dialog
# =====================================================

class ReprintDialog(QtWidgets.QDialog):
    """
    Confirmation dialog for reprinting a job.

    Responsibilities:
    - Display job context
    - Confirm reprint intent
    - Return a ReprintRequest

    Does NOT:
    - Trigger printing
    - Write logs
    - Compute cost
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        *,
        job: PrintJobRecord,
    ) -> None:
        super().__init__(parent)

        self._job = job
        self._request: ReprintRequest | None = None

        self.setWindowTitle("Reprint Job")
        self.setModal(True)
        self.setObjectName("ReprintDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Slightly wider than failure dialog for breathing room
        self.setMinimumWidth(460)

        self._build()

    # -------------------------------------------------
    # UI
    # -------------------------------------------------

    def _build(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # -------------------------------------------------
        # Job info
        # -------------------------------------------------

        def info_row(label: str, value: str):
            row = QtWidgets.QHBoxLayout()
            l = QtWidgets.QLabel(f"{label}:")
            v = QtWidgets.QLabel(value)

            apply_typography(l, "label")
            apply_typography(v, "body")

            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row.addWidget(l)
            row.addStretch(1)
            row.addWidget(v)
            return row

        display_time = self._job.timestamp.strftime("%m/%d/%Y %I:%M %p")
        root.addLayout(info_row("Job", display_time))

        root.addWidget(self._divider())

        # -------------------------------------------------
        # Files
        # -------------------------------------------------

        for idx, f in enumerate(self._job.files):
            label = "File A" if idx == 0 else "File B"
            poster = f.get("poster_id") or ""
            root.addLayout(info_row(label, poster))

        # -------------------------------------------------
        # Options
        # -------------------------------------------------

        root.addWidget(self._divider())

        self.chk_reprint = QtWidgets.QCheckBox("Mark as reprint")
        self.chk_reprint.setChecked(True)
        apply_typography(self.chk_reprint, "body")
        root.addWidget(self.chk_reprint)

        # Placeholder for future extensibility (disabled on purpose)
        self.chk_override = QtWidgets.QCheckBox("Override size (coming soon)")
        self.chk_override.setEnabled(False)
        apply_typography(self.chk_override, "body-muted")
        root.addWidget(self.chk_override)

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )

        # Make buttons feel lighter / less dominant
        btns.setCenterButtons(True)

        apply_typography(btns.button(QtWidgets.QDialogButtonBox.Ok), "body")
        apply_typography(btns.button(QtWidgets.QDialogButtonBox.Cancel), "body")

        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)

        root.addSpacing(8)
        root.addWidget(btns)

        QtCore.QTimer.singleShot(0, self.chk_reprint.setFocus)

    # -------------------------------------------------
    # Actions
    # -------------------------------------------------

    def _on_accept(self) -> None:
        self._request = ReprintRequest(
            parent_job_id=self._job.timestamp.isoformat(),
            timestamp=datetime.utcnow(),
            mode=self._job.mode,
            size=self._job.size,
            files=list(self._job.files),
            mark_as_reprint=self.chk_reprint.isChecked(),
        )
        self.accept()

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def get_request(self) -> ReprintRequest:
        if self._request is None:
            raise RuntimeError("ReprintDialog accepted without request")
        return self._request

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @staticmethod
    def _divider() -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setContentsMargins(0, 6, 0, 6)
        return line

    def showEvent(self, e):
        super().showEvent(e)
        repolish(self)
