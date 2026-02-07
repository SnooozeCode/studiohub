from PySide6 import QtWidgets, QtCore

class NotesPanel(QtWidgets.QWidget):
    notes_changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.text = QtWidgets.QPlainTextEdit()
        self.text.setPlaceholderText("Notes…")
        self.text.setProperty("role", "notes")

        layout.addWidget(self.text, 1)

        self.text.textChanged.connect(
            lambda: self.notes_changed.emit(self.text.toPlainText())
        )

    def set_notes(self, text: str):
        self.text.blockSignals(True)
        self.text.setPlainText(text or "")
        self.text.blockSignals(False)
