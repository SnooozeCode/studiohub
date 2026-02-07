from __future__ import annotations

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

from studiohub.style.typography.rules import apply_typography
from studiohub.style.utils.repolish import repolish


class PrintFailedDialog(QtWidgets.QDialog):
    """
    Dialog for recording a failed print.
    Compact, transactional, archival styling.
    """

    def __init__(
        self,
        parent,
        *,
        job_id: str,
        display_time: str,
        file_a: str,
        file_b: str | None,
        planned_in: float,
    ):
        super().__init__(parent)

        self.job_id = job_id
        self.planned_in = planned_in

        self.setWindowTitle("Print Failed")
        self.setModal(True)
        self.setObjectName("PrintFailedDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setMinimumWidth(400)

        self._build(
            display_time=display_time,
            file_a=file_a,
            file_b=file_b,
        )

    # -------------------------------------------------
    # UI
    # -------------------------------------------------

    def _build(self, *, display_time: str, file_a: str, file_b: str | None):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # -------------------------------------------------
        # Job row
        # -------------------------------------------------

        job_row = QtWidgets.QHBoxLayout()

        lbl_job = QtWidgets.QLabel("Job ID (Time)")
        val_time = QtWidgets.QLabel(display_time)

        apply_typography(lbl_job, "body")
        apply_typography(val_time, "body")

        # Bold label
        font = lbl_job.font()
        font.setWeight(QtGui.QFont.Bold)
        lbl_job.setFont(font)

        val_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        job_row.addWidget(lbl_job)
        job_row.addStretch(1)
        job_row.addWidget(val_time)

        root.addLayout(job_row)

        root.addWidget(self._divider())

        # -------------------------------------------------
        # File rows
        # -------------------------------------------------

        def file_row(label: str, value: str):
            h = QtWidgets.QHBoxLayout()
            l = QtWidgets.QLabel(f"{label}:")
            v = QtWidgets.QLabel(value)

            apply_typography(l, "body")
            apply_typography(v, "body")

            # Bold label
            font = l.font()
            font.setWeight(QtGui.QFont.Bold)
            l.setFont(font)

            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            h.addWidget(l)
            h.addStretch(1)
            h.addWidget(v)
            return h

        root.addLayout(file_row("File A", file_a))

        if file_b:
            root.addLayout(file_row("File B", file_b))

        root.addSpacing(4)

        # -------------------------------------------------
        # Length rows
        # -------------------------------------------------

        planned_row = QtWidgets.QHBoxLayout()

        lbl_planned = QtWidgets.QLabel("Planned Length")
        val_planned = QtWidgets.QLabel(f"{self.planned_in:.1f} in")

        apply_typography(lbl_planned, "body")
        apply_typography(val_planned, "body")

        # Bold label
        font = lbl_planned.font()
        font.setWeight(QtGui.QFont.Bold)
        lbl_planned.setFont(font)

        planned_row.addWidget(lbl_planned)
        planned_row.addStretch(1)
        planned_row.addWidget(val_planned)

        root.addLayout(planned_row)

        actual_row = QtWidgets.QHBoxLayout()

        lbl_actual = QtWidgets.QLabel("Actual Length")
        apply_typography(lbl_actual, "body")

        # Bold label
        font = lbl_actual.font()
        font.setWeight(QtGui.QFont.Bold)
        lbl_actual.setFont(font)


        self.actual_edit = QtWidgets.QLineEdit()
        self.actual_edit.setValidator(QDoubleValidator(0, self.planned_in, 1))
        self.actual_edit.setFixedWidth(40)
        apply_typography(self.actual_edit, "body")

        lbl_in = QtWidgets.QLabel("in")
        apply_typography(lbl_in, "body")

        actual_row.addWidget(lbl_actual)
        actual_row.addStretch(1)
        actual_row.addWidget(self.actual_edit)
        actual_row.addWidget(lbl_in)

        root.addLayout(actual_row)

        self.chk_failed_all = QtWidgets.QCheckBox("Print failed entirely")
        apply_typography(self.chk_failed_all, "body")

        self.chk_failed_all.toggled.connect(self._on_failed_all_toggled)


        root.addWidget(self.chk_failed_all)

        root.addWidget(self._divider())

        # -------------------------------------------------
        # Reason row (inline)
        # -------------------------------------------------

        reason_row = QtWidgets.QHBoxLayout()

        lbl_reason = QtWidgets.QLabel("Reason for Failure")
        apply_typography(lbl_reason, "body")

        # Bold label
        font = lbl_reason.font()
        font.setWeight(QtGui.QFont.Bold)
        lbl_reason.setFont(font)

        self.reason_combo = QtWidgets.QComboBox()
        apply_typography(self.reason_combo, "body")
        self.reason_combo.setFixedHeight(32)
        self.reason_combo.setFixedWidth(170)

        # Force square corners (no rounding)
        self.reason_combo.setStyleSheet("""
            QComboBox {
                border-radius: 0px;
            }
        """)

        self.reason_combo.addItem("Banding", "Failure Reason: Banding")
        self.reason_combo.addItem("Alignment", "Failure Reason: Alignment")
        self.reason_combo.addItem("Color issue", "Failure Reason: Color Issue")
        self.reason_combo.addItem("Paper feed / jam", "Failure Reason: Paper Jam")
        self.reason_combo.addItem("Template issue", "Failure Reason: Template Issue")
        self.reason_combo.addItem("Other", "Failure Reason: Other")

        reason_row.addWidget(lbl_reason)
        reason_row.addStretch(1)
        reason_row.addWidget(self.reason_combo)

        root.addLayout(reason_row)

        # -------------------------------------------------
        # Buttons (small + centered)
        # -------------------------------------------------

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        
        btn_ok = QtWidgets.QPushButton("Submit")
        btn_cancel = QtWidgets.QPushButton("Cancel")


        for btn in (btn_cancel, btn_ok):
            apply_typography(btn, "body")
            btn.setFixedHeight(28)
            btn.setMinimumWidth(80)

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_ok)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch(1)

        root.addSpacing(6)
        root.addLayout(btn_row)

        QtCore.QTimer.singleShot(0, self.actual_edit.setFocus)

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def get_actual_in(self) -> float:
        try:
            return float(self.actual_edit.text())
        except ValueError:
            return 0.0

    def get_reason(self) -> str:
        return self.reason_combo.currentData()

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _on_failed_all_toggled(self, checked: bool) -> None:
        """
        Disable actual length input when the print failed entirely.
        """
        if checked:
            self.actual_edit.setText("0")
            self.actual_edit.setDisabled(True)
        else:
            self.actual_edit.setDisabled(False)
            self.actual_edit.clear()

    @staticmethod
    def _divider() -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 10, 0, 10)  # ← vertical padding
        layout.setSpacing(0)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Plain)
        line.setObjectName("DialogDivider")

        layout.addWidget(line)
        return wrapper


    def showEvent(self, e):
        super().showEvent(e)
        repolish(self)
