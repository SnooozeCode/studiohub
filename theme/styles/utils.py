# theme/utils.py

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def repolish_recursive(widget: QWidget) -> None:
    repolish(widget)
    for child in widget.findChildren(QWidget):
        repolish(child)


def set_props(widget: QWidget, **props) -> None:
    for key, value in props.items():
        widget.setProperty(key, value)
    repolish(widget)


def clear_props(widget: QWidget, *names: str) -> None:
    for name in names:
        widget.setProperty(name, None)
    repolish(widget)


def install_hover(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_Hover, True)

def with_alpha(hex_color: str, alpha: float) -> str:
    """
    Convert hex (#RRGGBB) to rgba(r,g,b,a)
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

