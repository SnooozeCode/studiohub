from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .repolish import repolish


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
