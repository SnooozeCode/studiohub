from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from studiohub.style.typography.rules import apply_typography

class RecentIndexEvents(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.container = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.container)

    def update_events(self, events: list[dict]) -> None:
        self._clear()

        if not events:
            self.layout.addWidget(QtWidgets.QLabel("No recent indexing activity"))
            return

        for evt in events:
            ts = evt.get("timestamp")
            ts_str = ts.strftime("%b %d · %I:%M %p").lstrip("0") if ts else "—"

            lbl = QtWidgets.QLabel(
                f"{ts_str} · Archive {evt.get('patents', 0)} · Studio {evt.get('studio', 0)}"
            )
            lbl.setProperty("typography", "body-small")
            apply_typography(lbl, "body-small")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.layout.addWidget(lbl)

    def _clear(self):
        while self.layout.count():
            w = self.layout.takeAt(0).widget()
            if w:
                w.deleteLater()