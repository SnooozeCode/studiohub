from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt

from studiohub.ui.sidebar.sidebar_button import SidebarButton, ICON_COL_WIDTH, LABEL_COL_GAP


class _TreePrefix(QtWidgets.QWidget):
    """
    Draws vertical trunk + elbow aligned to parent icon center.
    """

    def __init__(self, *, is_last: bool):
        super().__init__()
        self.is_last = is_last
        self.setFixedWidth(ICON_COL_WIDTH)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 40))
        pen.setWidth(1)
        painter.setPen(pen)

        h = self.height()
        mid = h // 2
        x = ICON_COL_WIDTH // 2

        # vertical trunk
        if not self.is_last:
            painter.drawLine(x, 0, x, h)
        else:
            painter.drawLine(x, 0, x, mid)

        # elbow
        painter.drawLine(x, mid, x + 14, mid)



class SidebarGroup(QtWidgets.QWidget):
    """
    Expandable sidebar group with tree-style children.
    """

    def __init__(self, label: str, icon: str | None = None):
        super().__init__()

        self._expanded = False
        self._rows: list[QtWidgets.QWidget] = []

        self.setObjectName("SidebarGroup")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -------------------------------------------------
        # Group header
        # -------------------------------------------------
        self.header = SidebarButton(label, icon=icon, show_indicator=True,)
        self.header.set_trailing_icon("expand", muted=True)
        self.header.button.clicked.connect(self.toggle)

        layout.addWidget(self.header)

        # -------------------------------------------------
        # Child container
        # -------------------------------------------------
        self.container = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        self.container.setVisible(False)

        layout.addWidget(self.container)

    # =================================================
    # Public API
    # =================================================
    def add_button(self, button: SidebarButton):
        row = QtWidgets.QWidget()
        row.setObjectName("SidebarChildRow")
        row.setAttribute(Qt.WA_StyledBackground, True)

        # Lock row height so nothing can vertically blow up
        row_h = button.height()
        row.setFixedHeight(row_h)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )

        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        # LEFT EDGE INDICATOR (same x as top-level indicators)
        indicator = QtWidgets.QFrame()
        indicator.setObjectName("SidebarIndicator")
        indicator.setFixedWidth(3)
        indicator.setFixedHeight(row_h)
        indicator.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        indicator.setAttribute(Qt.WA_StyledBackground, True)  # 🔑 make QSS background paint
        indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        prefix = _TreePrefix(is_last=True)

        row_layout.addWidget(indicator)
        row_layout.addWidget(prefix)
        row_layout.addSpacing(LABEL_COL_GAP)
        row_layout.addWidget(button, 1)

        # store indicator ref on the row so activate() can repolish it directly
        row._indicator = indicator  # noqa: SLF001 (intentional internal handle)

        self._rows.append(row)
        self.container_layout.addWidget(row)
        self._update_prefixes()
        return row




    def set_collapsed(self, collapsed: bool):
        self.header.set_collapsed(collapsed)
        self.container.setVisible(not collapsed and self._expanded)

    # =================================================
    # Expand / Collapse
    # =================================================
    def toggle(self):
        sidebar = self.parentWidget()
        if sidebar and sidebar._collapsed:
            sidebar.toggle_collapsed()
            return

        self._expanded = not self._expanded
        self.container.setVisible(self._expanded)

        if self._expanded:
            # Parent expanded → down caret
            self.header.set_trailing_icon("caret-down", muted=True)

            # Children visible → show right caret
            for row in self._rows:
                btn = row.layout().itemAt(3).widget()  # SidebarButton
                btn.set_trailing_icon("caret-right", muted=True)
        else:
            # Parent collapsed → return to expand icon
            self.header.set_trailing_icon("expand", muted=True)

            # Children hidden → no caret
            for row in self._rows:
                btn = row.layout().itemAt(3).widget()
                btn.set_trailing_icon(None)


    # =================================================
    # Internals
    # =================================================
    def _update_prefixes(self):
        for i, row in enumerate(self._rows):
            prefix = row.layout().itemAt(0).widget()
            prefix.is_last = (i == len(self._rows) - 1)
            prefix.update()
