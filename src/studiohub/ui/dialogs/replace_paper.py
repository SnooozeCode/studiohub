from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

from studiohub.style.utils.repolish import repolish


class ReplacePaperDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent=None,
        *,
        current_name: str = "",
        current_total_length: float = 0.0,
    ):
        super().__init__(parent)

        self.setObjectName("ReplacePaperDialog")
        self.setWindowTitle("Replace Paper Roll")
        self.setModal(True)

        self._current_name = current_name
        self._current_total_length = current_total_length

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        form = QtWidgets.QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignLeft)

        # ---- Paper name ----
        self.paper_name_edit = QtWidgets.QLineEdit()
        self.paper_name_edit.setObjectName("DialogLineEdit")
        self.paper_name_edit.setText(self._current_name)
        self.paper_name_edit.selectAll()

        # ---- Total length (simple numeric input; no spinbox) ----
        self.paper_length_edit = QtWidgets.QLineEdit()
        self.paper_length_edit.setObjectName("DialogLineEdit")
        self.paper_length_edit.setPlaceholderText("Feet")
        self.paper_length_edit.setValidator(QDoubleValidator(0.0, 10_000.0, 2, self))

        if self._current_total_length > 0:
            self.paper_length_edit.setText(f"{self._current_total_length:.1f}")

        FIELD_WIDTH = 260  # dialog-scale, not global
        self.paper_name_edit.setMinimumWidth(FIELD_WIDTH)
        self.paper_length_edit.setMinimumWidth(FIELD_WIDTH)

        form.addRow("Paper Name:", self.paper_name_edit)
        form.addRow("Total Length:", self.paper_length_edit)

        root.addLayout(form)

        # ---- Buttons (explicit; avoids QDialogButtonBox oddities) ----
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setObjectName("DialogCancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_yes = QtWidgets.QPushButton("Yes")
        self.btn_yes.setObjectName("DialogAccept")
        self.btn_yes.setDefault(True)
        self.btn_yes.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_yes)
        root.addLayout(btn_row)

        QtCore.QTimer.singleShot(0, self.paper_name_edit.setFocus)

    # ============================================================
    # Theme Handling
    # ============================================================

    def showEvent(self, event):
        super().showEvent(event)
        repolish(self)

    # ============================================================
    # Public API
    # ============================================================

    def get_values(self) -> tuple[str, float]:
        name = self.paper_name_edit.text().strip()
        try:
            total = float(self.paper_length_edit.text().strip() or 0)
        except ValueError:
            total = 0.0
        return (name, total)
