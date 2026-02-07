from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from studiohub.theme.styles.typography import apply_typography
from PySide6.QtGui import QFont

class DashboardPrintJobEntry(QtWidgets.QFrame):
    """Single recent print job row (read-only, reprintable)."""

    reprint_requested = QtCore.Signal(dict)

    def __init__(
        self,
        *,
        names: list[str],
        is_two_up: bool,
        row_parity: int = 0,
        parent=None,
    ):
        super().__init__(parent)

        ROW_HEIGHT = 18

        self.setObjectName("DashboardPrintJobEntry")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("row", "even" if row_parity % 2 == 0 else "odd")

        self.setCursor(Qt.PointingHandCursor)

        grid = QtWidgets.QGridLayout(self)
        # No left padding so indicator is flush; keep vertical + right padding
        grid.setContentsMargins(0, 4, 6, 4)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)

        # -------------------------------------------------
        # Left indicator (styled via QSS, ledger-style)
        # -------------------------------------------------
        indicator = QtWidgets.QFrame()
        indicator.setObjectName("LedgerIndicator")
        indicator.setProperty("role", "print-job")
        indicator.setProperty("variant", "two-up" if is_two_up else "single")

        indicator.setFixedWidth(6)
        indicator.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Expanding,
        )

        def _make_name_label(text: str) -> QtWidgets.QLabel:
            lbl = QtWidgets.QLabel(text or "—")
            apply_typography(lbl, "body-small")
            lbl.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred,
            )
            return lbl

        name1 = _make_name_label(names[0] if names else "—")

        if is_two_up:
            name2 = _make_name_label(names[1] if len(names) > 1 else "—")
            grid.addWidget(indicator, 0, 0, 2, 1)
            grid.addWidget(name1, 0, 1)
            grid.addWidget(name2, 1, 1)
            grid.setRowMinimumHeight(0, ROW_HEIGHT)
            grid.setRowMinimumHeight(1, ROW_HEIGHT)
        else:
            grid.addWidget(indicator, 0, 0)
            grid.addWidget(name1, 0, 1)
            grid.setRowMinimumHeight(0, ROW_HEIGHT)

    # =========================================================
    # Interaction
    # =========================================================

    def mouseDoubleClickEvent(self, event):
        # Double-click = reprint
        if event.button() == Qt.LeftButton:
            job = self.property("job_payload")
            if job:
                self.reprint_requested.emit(job)

    def contextMenuEvent(self, event):
        job = self.property("job_payload")
        if not job:
            return

        menu = QtWidgets.QMenu(self)
        act_reprint = menu.addAction("Reprint…")

        if menu.exec(event.globalPos()) == act_reprint:
            self.reprint_requested.emit(job)


class RecentPrintJobs(QtWidgets.QWidget):
    """Panel for rendering recent print jobs with reprint action."""

    reprint_requested = QtCore.Signal(list)  # list[dict] of print-log entries

    def __init__(self, parent=None):
        super().__init__(parent)

        self.container = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.container)

    # =========================================================
    # Public API
    # =========================================================

    def update_jobs(self, jobs: list[dict]) -> None:
        self._clear()

        if not jobs:
            self.layout.addWidget(QtWidgets.QLabel("No recent print jobs"))
            return

        for idx, job in enumerate(jobs):
            schema = job.get("schema", "print_log_v1")
            mode = (job.get("mode") or "single").lower()
            is_two_up = (mode == "2up")

            names: list[str] = []

            # ----------------------------------------------
            # v2 schema (authoritative)
            # ----------------------------------------------
            if schema == "print_log_v2":
                for f in job.get("files", []):
                    if isinstance(f, dict):
                        # Prefer logical poster ID for display
                        pid = f.get("poster_id")
                        if pid:
                            names.append(pid)
                        else:
                            path = f.get("path")
                            if path:
                                names.append(Path(path).stem)

            # ----------------------------------------------
            # v1 schema (legacy)
            # ----------------------------------------------
            else:
                for key in ("file_1", "file_2"):
                    fname = job.get(key)
                    if fname:
                        names.append(Path(fname).stem)

            # ----------------------------------------------
            # Normalize for display
            # ----------------------------------------------
            if is_two_up:
                display_names = (names + ["—", "—"])[:2]
            else:
                display_names = [names[0]] if names else ["—"]

            entry = DashboardPrintJobEntry(
                names=display_names,
                is_two_up=is_two_up,
                row_parity=idx,
            )
            entry.setProperty("job_payload", job)
            entry.reprint_requested.connect(self._on_reprint)

            self.layout.addWidget(entry)

    # =========================================================
    # Internals
    # =========================================================

    def _on_reprint(self, job: dict):
        self.reprint_requested.emit([job])

    def _clear(self):
        while self.layout.count():
            w = self.layout.takeAt(0).widget()
            if w:
                w.deleteLater()
