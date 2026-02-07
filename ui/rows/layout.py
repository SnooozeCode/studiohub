# ui/row_layouts.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from PySide6 import QtCore, QtWidgets


class RowProfile(Enum):
    STANDARD = auto()  # primary tables/trees (Print Manager, Mockup, Missing Files)
    COMPACT = auto()   # logs, dashboard lists (print log, index log, small panels)
    LOG = auto()    
    DENSE = auto()     # optional future use (debug/audit/history)


@dataclass(frozen=True)
class RowMetrics:
    row_height: int
    hscroll_policy: QtCore.Qt.ScrollBarPolicy
    vscroll_mode: QtWidgets.QAbstractItemView.ScrollMode
    alternating: bool
    uniform_row_heights: bool
    indentation: int


_METRICS: dict[RowProfile, RowMetrics] = {
    RowProfile.STANDARD: RowMetrics(
        row_height=34,
        hscroll_policy=QtCore.Qt.ScrollBarAlwaysOff,
        vscroll_mode=QtWidgets.QAbstractItemView.ScrollPerPixel,
        alternating=False,
        uniform_row_heights=True,
        indentation=10,
    ),
    RowProfile.COMPACT: RowMetrics(
        row_height=26,
        hscroll_policy=QtCore.Qt.ScrollBarAlwaysOff,
        vscroll_mode=QtWidgets.QAbstractItemView.ScrollPerPixel,
        alternating=False,
        uniform_row_heights=True,
        indentation=7,
    ),
    RowProfile.DENSE: RowMetrics(
        row_height=22,
        hscroll_policy=QtCore.Qt.ScrollBarAlwaysOff,
        vscroll_mode=QtWidgets.QAbstractItemView.ScrollPerPixel,
        alternating=False,
        uniform_row_heights=True,
        indentation=5
    ),
    RowProfile.LOG: RowMetrics(
        row_height=32,  # ← taller rows
        hscroll_policy=QtCore.Qt.ScrollBarAlwaysOff,
        vscroll_mode=QtWidgets.QAbstractItemView.ScrollPerPixel,
        alternating=False,
        uniform_row_heights=True,
        indentation=7,
    ),
}


def configure_view(
    view: QtWidgets.QAbstractItemView,
    *,
    profile: RowProfile,
    role: Optional[str] = None,
    alternating: Optional[bool] = None,
) -> None:
    m = _METRICS[profile]

    view.setProperty("row_profile", profile.name.lower())
    if role:
        view.setProperty("role", role)

    view.setAlternatingRowColors(
        m.alternating if alternating is None else alternating
    )

    view.setHorizontalScrollBarPolicy(m.hscroll_policy)
    view.setVerticalScrollMode(m.vscroll_mode)

    m = _METRICS[profile]

    view.setProperty("row_profile", profile.name.lower())
    if role:
        view.setProperty("role", role)

    if isinstance(view, QtWidgets.QTableView):
        vh = view.verticalHeader()
        vh.setVisible(False)

        # CRITICAL: make row height deterministic
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        vh.setDefaultSectionSize(m.row_height)
        vh.setMinimumSectionSize(m.row_height)

        view.setShowGrid(False)
        view.setWordWrap(False)  # keep row height stable if text is long


    # -----------------------------
    # TREES
    # -----------------------------

    view.setAlternatingRowColors(
        m.alternating if alternating is None else alternating
    )

    view.setHorizontalScrollBarPolicy(m.hscroll_policy)
    view.setVerticalScrollMode(m.vscroll_mode)


# =====================================================
# QSS generation (row density)
# =====================================================

def build_row_density_qss() -> str:
    """
    Generate QSS rules for tree/list row density based on RowMetrics.
    This should be appended to the global stylesheet.
    """
    rules: list[str] = []

    for profile, m in _METRICS.items():
        name = profile.name.lower()

        # Vertical padding derived from target row height
        # This is intentionally conservative to avoid text clipping
        padding_v = max(1, (m.row_height - 18) // 2)

        rules.append(f"""
        /* --- {profile.name} row density --- */
        QTreeWidget[row_profile="{name}"]::item,
        QListWidget[row_profile="{name}"]::item {{
            padding-top: {padding_v}px;
            padding-bottom: {padding_v}px;

            /* Deterministic row height */
            min-height: {m.row_height}px;

            font-size: {12 if profile != RowProfile.STANDARD else 13}px;
        }}
        """)

        rules.append(f"""
        /* --- {profile.name} table row density --- */
        QTableView[row_profile="{name}"]::item {{
            padding-top: {padding_v}px;
            padding-bottom: {padding_v}px;
            font-size: {12 if profile != RowProfile.STANDARD else 13}px;
        }}
        """)


    return "\n".join(rules)
