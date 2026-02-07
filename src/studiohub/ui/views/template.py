from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets


# =====================================================
# View Name
# =====================================================

class ExampleViewQt(QtWidgets.QFrame):
    """
    Example View.

    Structural guarantees:
      - State → Widgets → Layout → Init → Polish
      - No layouts before widgets
      - Role-based theming only
    """

    example_signal = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        # =================================================
        # STATE
        # =================================================
        self._loading = False

        # =================================================
        # ROOT SURFACE
        # =================================================
        self.setObjectName("ExampleView")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        # =================================================
        # WIDGETS (NO LAYOUT)
        # =================================================
        self.btn_primary = QtWidgets.QPushButton("Primary")
        self.btn_secondary = QtWidgets.QPushButton("Secondary")

        self.main_widget = QtWidgets.QWidget()

        # =================================================
        # ROOT LAYOUT (FIRST LAYOUT)
        # =================================================
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        root.addWidget(self.main_widget, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.btn_secondary)
        footer.addWidget(self.btn_primary)
        root.addLayout(footer)

        # =================================================
        # SIGNAL WIRING
        # =================================================
        self.btn_primary.clicked.connect(self.example_signal.emit)

        # =================================================
        # FINAL POLISH
        # =================================================
        from studiohub.style.styles.utils import repolish
        repolish(self)
