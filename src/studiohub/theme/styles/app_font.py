from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from studiohub.theme.styles.typography import BASE_FONT_FAMILY, BASE_PX


def apply_base_app_font(app: QApplication) -> None:
    font = QFont(BASE_FONT_FAMILY)
    font.setPointSizeF(BASE_PX)
    app.setFont(font)
