# hub_views/print_jobs_view_qt.py
from __future__ import annotations

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from studiohub.hub_models.print_jobs_model_qt import (
    PrintJobsModelQt,
    PrintJobRecord,
    ROLE_JOB,
)

from studiohub.hub_models.print_manager_model_qt import PrintManagerModelQt
from studiohub.ui.delegates.failed_icon_delegate import FailedIconDelegate
from studiohub.ui.dialogs.print_failed import PrintFailedDialog
from studiohub.ui.dialogs.reprint_dialog import ReprintDialog, ReprintRequest

from studiohub.style.typography.rules import apply_header_typography, apply_view_typography
from studiohub.style.utils.repolish import repolish


class PrintJobsViewQt(QtWidgets.QFrame):
    """
    Print Jobs View (canonical)

    View responsibilities ONLY:
    - Table wiring
    - Dialog orchestration
    - Forwarding actions to state / manager
    """

    ROW_HEIGHT = 44
    HEADER_HEIGHT = 40

    # Column indices (authoritative)
    COL_TIME   = 0
    COL_FILE_A = 1
    COL_FILE_B = 2
    COL_FORMAT = 3
    COL_LENGTH = 4
    COL_COST   = 5
    COL_STATUS = 6
    COL_FAILED = 7

    FIXED_COL_WIDTH = 92

    def __init__(
        self,
        *,
        config_manager,
        print_log_state,
        paper_ledger,
        print_manager_model: PrintManagerModelQt,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.config = config_manager
        self.print_log_state = print_log_state
        self.paper_ledger = paper_ledger
        self.print_manager_model = print_manager_model

        self._dialog_open = False

        self.setObjectName("PrintJobsView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build()
        self._wire_signals()

    # -------------------------------------------------
    # UI
    # -------------------------------------------------

    def _build(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.table = QtWidgets.QTableView(self)
        self.table.setObjectName("PrintJobsTable")

        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        # Disable visual selection
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self.ROW_HEIGHT)

        header = self.table.horizontalHeader()
        header.setFixedHeight(self.HEADER_HEIGHT)
        header.setHighlightSections(False)

        apply_view_typography(self.table, "body-small")
        apply_header_typography(header, "h4")

        self.table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        root.addWidget(self.table, 1)

        # -----------------------------
        # Model
        # -----------------------------
        self.model = PrintJobsModelQt(
            print_log_state=self.print_log_state,
            parent=self,
        )
        self.table.setModel(self.model)

        # -----------------------------
        # Column sizing
        # -----------------------------
        header.setSectionResizeMode(self.COL_TIME, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_FILE_A, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_FILE_B, QtWidgets.QHeaderView.Stretch)

        for col in (
            self.COL_FORMAT,
            self.COL_LENGTH,
            self.COL_COST,
            self.COL_STATUS,
            self.COL_FAILED,
        ):
            header.setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)
            self.table.setColumnWidth(col, self.FIXED_COL_WIDTH)

        # -----------------------------
        # Delegate
        # -----------------------------
        delegate = FailedIconDelegate(self.table)
        delegate.clicked.connect(self._on_failed_action)
        self.table.setItemDelegateForColumn(self.COL_FAILED, delegate)

        repolish(self)

    # -------------------------------------------------
    # Signals
    # -------------------------------------------------

    def _wire_signals(self) -> None:
        self.print_log_state.changed.connect(self.refresh)
        self.paper_ledger.changed.connect(self.refresh)

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def refresh(self) -> None:
        self.table.viewport().update()
        repolish(self)

    # -------------------------------------------------
    # Delegate actions
    # -------------------------------------------------

    def _on_failed_action(self, index: QtCore.QModelIndex, action: str) -> None:
        if self._dialog_open or not index.isValid():
            return

        job = index.data(ROLE_JOB)
        if not isinstance(job, PrintJobRecord):
            return

        if action == "fail":
            self._open_failed_dialog(job)
        elif action == "reprint":
            self._open_reprint_dialog(job)

    # -------------------------------------------------
    # Dialogs
    # -------------------------------------------------

    def _open_failed_dialog(self, job: PrintJobRecord) -> None:
        self._dialog_open = True
        try:
            dlg = PrintFailedDialog(
                self,
                job_id=job.timestamp.isoformat(),
                display_time=job.timestamp.strftime("%m/%d/%Y %I:%M %p"),
                file_a=job.files[0]["poster_id"] if job.files else "",
                file_b=job.files[1]["poster_id"] if len(job.files) > 1 else None,
                planned_in=self._planned_length_for(job),
            )

            if dlg.exec() != QtWidgets.QDialog.Accepted:
                return

            self.print_log_state.record_failure(
                job_id=job.timestamp.isoformat(),
                actual_in=dlg.get_actual_in(),
                reason=dlg.get_reason(),
            )

        finally:
            self._dialog_open = False

    def _open_reprint_dialog(self, job: PrintJobRecord) -> None:
        self._dialog_open = True
        try:
            dlg = ReprintDialog(self, job=job)
            if dlg.exec() != QtWidgets.QDialog.Accepted:
                return

            request = dlg.get_request()

            # 1) Send to Photoshop via PrintManager pathway (no duplication)
            self._send_reprint_to_photoshop(request)

            # 2) Mark the ORIGINAL job as reprinted (event)
            self.print_log_state.record_reprint(
                parent_job_id=request.parent_job_id,
                reprinted_at=request.timestamp,
                reprint_job_id=request.timestamp.isoformat(),
            )

        finally:
            self._dialog_open = False

    # -------------------------------------------------
    # Print pipeline bridge
    # -------------------------------------------------

    def _send_reprint_to_photoshop(self, request: ReprintRequest) -> None:
        if not self.print_manager_model:
            raise RuntimeError("PrintManagerModel not available")

        payload = {
            "schema": "print_log_v2",
            "timestamp": request.timestamp.isoformat(),
            "mode": request.mode,
            "size": request.size,
            "files": request.files,
        }

        self.print_manager_model.send_reprint_job(payload)

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
