from __future__ import annotations

from typing import List, Dict

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QFont

from studiohub.style.typography.rules import apply_typography


class QueueRowFactory:
    """Canonical queue row widgets.

    This is extracted from Print Manager and intended to be the single source of truth
    for all queue-style rows across the app (Print Manager, Mockup Generator, dashboard previews, etc.).
    """

    def __init__(self, *, badge_width: int, indicator_width: int):
        self._badge_width = int(badge_width)
        self._indicator_width = int(indicator_width)

    # -------------------------------------------------
    # Base frame (matches Print Manager)
    # -------------------------------------------------

    def base_row_frame(self, *, variant: str) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setObjectName("QueueRow")
        frame.setProperty("role", "queue-row")
        frame.setProperty("variant", variant)
        frame.setProperty("selected", False)

        frame.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        frame.setFocusPolicy(QtCore.Qt.NoFocus)

        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # This controls row height
        frame.setMinimumHeight(42)

        return frame

    # -------------------------------------------------
    # Public builders
    # -------------------------------------------------

    def build_pair_frame(self, pair: List[dict]) -> QtWidgets.QFrame:
        frame = self.base_row_frame(variant="pair")
        layout = frame.layout()

        names = QtWidgets.QVBoxLayout()
        names.setSpacing(2)
        for p in pair:
            lbl = QtWidgets.QLabel((p or {}).get("name", ""))
            apply_typography(lbl, "body-small")
            lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            lbl.setFocusPolicy(QtCore.Qt.NoFocus)
            lbl.setProperty("typography", "body")
            names.addWidget(lbl)

        layout.addLayout(names, 1)

        badge = self.build_badge("12×18 · 2-UP", variant="pair")
        badge.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(badge)

        ind = self.build_indicator()
        ind.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(ind)

        return frame

    def build_single_frame(
        self,
        it: dict,
        *,
        show_badge: bool = True,
        show_indicator: bool = True,
    ) -> QtWidgets.QFrame:
        
        frame = self.base_row_frame(variant="single")
        layout = frame.layout()

        lbl = QtWidgets.QLabel((it or {}).get("name", ""))
        lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        lbl.setFocusPolicy(QtCore.Qt.NoFocus)
        apply_typography(lbl, "body")
        layout.addWidget(lbl, 1)

        size_txt = ((it or {}).get("size") or "").replace("x", "×")
        badge = self.build_badge(size_txt, variant="single")
        if show_badge:
            badge.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(badge)

        if show_indicator:
            ind = self.build_indicator()
            ind.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(ind)

        return frame

    # -------------------------------------------------
    # Internals (matches Print Manager)
    # -------------------------------------------------

    def build_badge(self, text: str, *, variant: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setFixedWidth(self._badge_width)
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setFocusPolicy(QtCore.Qt.NoFocus)
        apply_typography(lbl, "caption")

        # Semantic styling hooks
        lbl.setProperty("role", "queue-badge")
        lbl.setProperty("variant", variant)

        # Non-color polish only (shape/spacing/type)
        lbl.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 6px;
                font-weight: 600;
            }
        """)
        return lbl

    def build_indicator(self) -> QtWidgets.QFrame:
        bar = QtWidgets.QFrame()
        bar.setFixedWidth(self._indicator_width)
        bar.setFocusPolicy(QtCore.Qt.NoFocus)

        # Semantic styling hook
        bar.setProperty("role", "queue-indicator")

        # No colors here; theme decides
        return bar
