from pathlib import Path
from PySide6.QtGui import QPixmap, QColor, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt

# Resolve project root safely
ROOT = Path(__file__).resolve().parents[1]

ICON_ROOT = ROOT / "assets" / "icons"

# -------------------------------------------------
# Semantic icon registry
# -------------------------------------------------
from pathlib import Path
from studiohub.utils.paths import asset_path

ICONS = {
    "menu": Path(asset_path("icons", "sidebar", "menu.svg")),
    "dashboard": Path(asset_path("icons", "sidebar", "dashboard.svg")),
    "print_manager": Path(asset_path("icons", "sidebar", "printer.svg")),
    "print_economics": Path(asset_path("icons", "sidebar", "economics.svg")),
    "mockup_generator": Path(asset_path("icons", "sidebar", "mockup.svg")),
    "missing_files": Path(asset_path("icons", "sidebar", "warning.svg")),
    "caret-right": Path(asset_path("icons", "sidebar", "chevron-right.svg")),
    "caret-down": Path(asset_path("icons", "sidebar", "chevron-down.svg")),
    "expand": Path(asset_path("icons", "sidebar", "plus.svg")),
    "notification": Path(asset_path("icons", "sidebar", "notification.svg")),
    "refresh": Path(asset_path("icons", "sidebar", "refresh.svg")),
    "theme_to_light": Path(asset_path("icons", "sidebar", "light.svg")),
    "theme_to_dark": Path(asset_path("icons", "sidebar", "dark.svg")),
    "settings": Path(asset_path("icons", "sidebar", "settings.svg")),
    "status_ok": Path(asset_path("icons", "sidebar", "okay.svg")),
    "status_missing": Path(asset_path("icons", "sidebar", "missing.svg")),
    "edit": Path(asset_path("icons", "edit.svg")),
}


# -------------------------------------------------
# SVG renderer
# -------------------------------------------------

def render_svg(
    icon_name: str,
    *,
    size: int,
    color: QColor,
) -> QPixmap:
    """
    Render a named SVG icon with tinting.
    """

    path = ICONS.get(icon_name)
    if not path or not path.exists():
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        return pm

    base = QPixmap(size, size)
    base.fill(Qt.transparent)

    renderer = QSvgRenderer(str(path))
    painter = QPainter(base)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    tinted = QPixmap(size, size)
    tinted.fill(Qt.transparent)

    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode_Source)
    painter.drawPixmap(0, 0, base)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()

    return tinted
