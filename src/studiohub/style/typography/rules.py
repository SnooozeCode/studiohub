from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6 import QtWidgets, QtGui
from PySide6.QtWidgets import QWidget, QAbstractItemView, QApplication
from PySide6.QtGui import QFont, QFontDatabase

from studiohub.constants import UIConstants

# ============================================================
# Typography Scale
# (mirrors your original typography.py exactly)
# ============================================================

def build_typography_map(base_px: float):
    return {
        "h1-xl": (base_px * 1.9, QFont.Bold),
        "h1":    (base_px * 1.6, QFont.Bold),
        "h2":    (base_px * 1.35, QFont.DemiBold),
        "h3":    (base_px * 1.2, QFont.DemiBold),
        "h4":    (base_px * 1.1, QFont.Medium),
        "h5":    (base_px * 1.0, QFont.Medium),
        "h6":    (base_px * 0.95, QFont.Medium),

        "body":        (base_px, QFont.Normal),
        "body-strong": (base_px, QFont.Medium),
        "body-small":  (base_px * 0.9, QFont.Normal),

        "caption": (base_px * 0.9, QFont.Normal),
        "small":   (base_px * 0.85, QFont.Normal),
        "nav":     (base_px, QFont.Normal),

        "tree": (base_px * 0.9, QFont.Normal),
        "mono": (base_px * 0.9, QFont.Normal),
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

# Build once at import
_BASE_PX = UIConstants.BASE_FONT_PX
TYPOGRAPHY_MAP = build_typography_map(_BASE_PX)


def apply_typography(widget: QWidget, key: str) -> None:
    if key not in TYPOGRAPHY_MAP:
        return

    size, weight = TYPOGRAPHY_MAP[key]

    font = QFont(UIConstants.BASE_FONT_FAMILY)
    font.setPixelSize(int(round(size)))
    font.setWeight(weight)

    widget.setFont(font)
    widget.setProperty("typography", key)


def apply_view_typography(view: QAbstractItemView, key: str) -> None:
    if key not in TYPOGRAPHY_MAP:
        return

    size, weight = TYPOGRAPHY_MAP[key]

    font = QFont(UIConstants.BASE_FONT_FAMILY)
    font.setPixelSize(int(round(size)))
    font.setWeight(weight)

    view.setFont(font)


def apply_header_typography(header: QtWidgets.QHeaderView, key: str) -> None:
    if key not in TYPOGRAPHY_MAP:
        return

    size, weight = TYPOGRAPHY_MAP[key]

    font = QFont(UIConstants.BASE_FONT_FAMILY)
    font.setPixelSize(int(round(size)))
    font.setWeight(weight)

    header.setFont(font)
    header.viewport().setFont(font)
