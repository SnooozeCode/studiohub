from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QSizePolicy,
)


# ============================================================
# Base Panel
# ============================================================

class BasePanel(QFrame):
    HEADER_HEIGHT = 48

    def __init__(
        self,
        *,
        title: str,
        primary_text: Optional[str] = None,
        secondary_text: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.setObjectName("Panel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(16, 14, 16, 14)
        self._root_layout.setSpacing(10)

        # ---------------- Header ----------------
        self._header = QFrame(self)
        self._header.setObjectName("PanelHeader")
        self._header.setFixedHeight(self.HEADER_HEIGHT)
        self._header.setCursor(Qt.PointingHandCursor)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("PanelTitle")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch(1)

        self._primary_label = QLabel(primary_text or "")
        self._primary_label.setObjectName("PanelPrimary")
        header_layout.addWidget(self._primary_label)

        self._secondary_label = QLabel(secondary_text or "")
        self._secondary_label.setObjectName("PanelSecondary")
        self._secondary_label.setVisible(bool(secondary_text))
        header_layout.addWidget(self._secondary_label)

        self._root_layout.addWidget(self._header)

        self._footer: Optional[QLabel] = None
        self._expand_button: Optional[QPushButton] = None

    # ---------------- Public API ----------------

    def set_primary_text(self, text: str) -> None:
        self._primary_label.setText(text)

    def set_secondary_text(self, text: Optional[str]) -> None:
        self._secondary_label.setText(text or "")
        self._secondary_label.setVisible(bool(text))

    def set_footer_text(self, text: Optional[str]) -> None:
        if not text:
            if self._footer:
                self._footer.setVisible(False)
            return

        if not self._footer:
            self._footer = QLabel(self)
            self._footer.setObjectName("PanelFooter")
            self._root_layout.addWidget(self._footer)

        self._footer.setText(text)
        self._footer.setVisible(True)

    # ---------------- Internal ----------------

    def _install_expand_button(self, button: QPushButton) -> None:
        self._expand_button = button
        self._header.layout().addWidget(button)


# ============================================================
# Extendable Panel
# ============================================================

class ExtendablePanel(BasePanel):
    def __init__(
        self,
        *,
        title: str,
        primary_text: Optional[str] = None,
        secondary_text: Optional[str] = None,
        expanded_max_height: int,
        content_factory: Optional[Callable[[], QWidget]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            title=title,
            primary_text=primary_text,
            secondary_text=secondary_text,
            parent=parent,
        )

        self._expanded_max_height = expanded_max_height
        self._content_factory = content_factory
        self._content_initialized = False
        self._is_expanded = False

        # Expand button
        self._expand_btn = QPushButton("▸")
        self._expand_btn.setObjectName("PanelExpandButton")
        self._expand_btn.setFixedSize(QSize(16, 16))
        self._expand_btn.setFlat(True)
        self._expand_btn.setCursor(Qt.PointingHandCursor)

        self._install_expand_button(self._expand_btn)

        # Content wrapper
        self._content_wrapper = QFrame(self)
        self._content_wrapper.setObjectName("PanelContent")
        self._content_wrapper.setMaximumHeight(0)
        self._content_wrapper.setVisible(False)

        self._content_layout = QVBoxLayout(self._content_wrapper)
        self._content_layout.setContentsMargins(0, 10, 0, 0)
        self._content_layout.setSpacing(8)

        self._root_layout.addWidget(self._content_wrapper)

        # Animation
        self._anim = QPropertyAnimation(self._content_wrapper, b"maximumHeight", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # Signals
        self._expand_btn.clicked.connect(self.toggle)
        self._header.mouseReleaseEvent = self._on_header_clicked  # type: ignore

    # ---------------- Expand Logic ----------------

    def toggle(self) -> None:
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self) -> None:
        if self._is_expanded:
            return

        self._ensure_content()
        self._content_wrapper.setVisible(True)

        self._anim.stop()
        self._anim.setStartValue(0)
        self._anim.setEndValue(self._expanded_max_height)
        self._anim.start()

        self._expand_btn.setText("▾")
        self._is_expanded = True

    def collapse(self) -> None:
        if not self._is_expanded:
            return

        self._anim.stop()
        self._anim.setStartValue(self._content_wrapper.maximumHeight())
        self._anim.setEndValue(0)
        self._anim.start()

        self._expand_btn.setText("▸")
        self._is_expanded = False

    # ---------------- Internal ----------------

    def _ensure_content(self) -> None:
        if self._content_initialized:
            return

        if self._content_factory:
            self._content_layout.addWidget(self._content_factory())

        self._content_initialized = True

    def _on_header_clicked(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.toggle()
