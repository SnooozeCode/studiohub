from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo
from PySide6.QtWidgets import QApplication

from studiohub.constants import UIConstants


def apply_base_app_font(app: QApplication) -> None:
    font = QFont(UIConstants.BASE_FONT_FAMILY)
    font.setPointSizeF(UIConstants.BASE_FONT_PX)
    app.setFont(font)


def load_app_fonts():
    font_dir = Path(__file__).resolve().parents[2] / "assets" / "fonts"

    for font_file in font_dir.glob("*.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id == -1:
            print("Failed to load:", font_file)
        else:
            families = QFontDatabase.applicationFontFamilies(font_id)


def print_base_font():
    app = QApplication.instance()
    if not app:
        return

    font = app.font()
    info = QFontInfo(font)

    print(f"[Font] {info.family()} {font.pointSizeF()}")