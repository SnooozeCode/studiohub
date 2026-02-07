from PySide6.QtWidgets import QWidget

def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def repolish_recursive(widget: QWidget) -> None:
    repolish(widget)
    for child in widget.findChildren(QWidget):
        repolish(child)
