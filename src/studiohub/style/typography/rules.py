from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6 import QtWidgets, QtGui
from PySide6.QtWidgets import QWidget, QAbstractItemView

# ============================================================
# Base Typography Configuration
# ============================================================

BASE_FONT_FAMILY = "Inter"
BASE_PX = 13       # Global dial (change once, affects everything)

# ============================================================
# Typography Scale
# (mirrors your original typography.py exactly)
# ============================================================

TYPOGRAPHY_MAP = {
    # Headings (UI-safe)
    "h1-xl": (BASE_PX * 1.9, QFont.Bold),
    "h1":    (BASE_PX * 1.6, QFont.Bold),
    "h2":    (BASE_PX * 1.35, QFont.DemiBold),
    "h3":    (BASE_PX * 1.2, QFont.DemiBold),
    "h4":    (BASE_PX * 1.1, QFont.Medium),
    "h5":    (BASE_PX * 1.0, QFont.Medium),
    "h6":    (BASE_PX * 0.95, QFont.Medium),

    # Body
    "body":        (BASE_PX, QFont.Normal),
    "body-strong": (BASE_PX, QFont.Medium),
    "body-small":  (BASE_PX * 0.9, QFont.Normal),

    # Meta
    "caption": (BASE_PX * 0.9, QFont.Normal),
    "small":   (BASE_PX * 0.85, QFont.Normal),
    "nav":     (BASE_PX * 1, QFont.Normal),

    # Views
    "tree": (BASE_PX * 0.9, QFont.Normal),
    "mono": (BASE_PX * 0.9, QFont.Normal),
}


def build_qss(tokens) -> str:
    return f"""
    /* ============================================================
    Base Typography (Semantic, Size-Agnostic)
    ============================================================ */

    /* ------------------------------------------------------------
    Global text safety
    ------------------------------------------------------------ */

    QLabel,
    QPushButton,
    QToolButton {{
        /* Prevent ascender clipping on high DPI */
    }}

    /* ------------------------------------------------------------
    Headings
    ------------------------------------------------------------ */

    QLabel[typography^="h"] {{
        color: {tokens.text_primary};
    }}

    /* ------------------------------------------------------------
    Section headers / small caps
    ------------------------------------------------------------ */

    QLabel[typography="h6"] {{
        letter-spacing: 1px;
        color: {tokens.text_muted};
    }}

    QHeaderView[typography="h4"]::section {{
        font-size: {{ typography.h4.size }};
        font-weight: {{ typography.h4.weight }};
        letter-spacing: {{ typography.h4.tracking }};
    }}

    QLabel[typography="nav"] {{
        letter-spacing: 1px;
    }}
    
    /* ------------------------------------------------------------
    Body text
    ------------------------------------------------------------ */

    QLabel[typography="body"],
    QLabel[typography="body-strong"] {{
        color: {tokens.text_primary} ;
    }}

    /* ------------------------------------------------------------
    Secondary / muted text
    ------------------------------------------------------------ */

    QLabel[typography="caption"],
    QLabel[typography="small"] {{
        color: {tokens.text_muted};
    }}

    /* ------------------------------------------------------------
    Monospace
    ------------------------------------------------------------ */

    QLabel[typography="mono"] {{
        font-family: monospace;
        color: {tokens.text_primary};
    }}

    /* ------------------------------------------------------------
    ------------------------------------------------------------ */

    QPushButton {{
        color: {tokens.text_primary};
    }}
    QPushButton:hover {{
        color: {tokens.accent};
    }}
"""

# ============================================================
# Public API
# ============================================================

def apply_typography(widget: QWidget, key: str) -> None:
    """
    Apply semantic typography to a widget.

    This is the single source of truth for font sizing.
    """
    if key not in TYPOGRAPHY_MAP:
        return

    size, weight = TYPOGRAPHY_MAP[key]

    font = QFont(BASE_FONT_FAMILY)
    font.setPixelSize(int(round(size)))
    font.setWeight(weight)

    if key == "mono":
        font.setFamily("Consolas")

    widget.setFont(font)
    widget.setProperty("typography", key)


def apply_view_typography(view: QAbstractItemView, key: str) -> None:
    if key not in TYPOGRAPHY_MAP:
        return

    size, weight = TYPOGRAPHY_MAP[key]

    font = QFont(BASE_FONT_FAMILY)
    font.setPixelSize(int(round(size)))
    font.setWeight(weight)

    view.setFont(font)

def apply_header_typography(header: QtWidgets.QHeaderView, key: str) -> None:
    if key not in TYPOGRAPHY_MAP:
        return

    size, weight = TYPOGRAPHY_MAP[key]

    font = QtGui.QFont(BASE_FONT_FAMILY)
    font.setPixelSize(int(round(size)))
    font.setWeight(weight)

    header.setFont(font)
    header.viewport().setFont(font)
