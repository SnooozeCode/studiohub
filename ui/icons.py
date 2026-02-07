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

ICONS = {
    # Sidebar
    "menu": ICON_ROOT / "sidebar" / "menu.svg",
    "dashboard": ICON_ROOT / "sidebar" / "dashboard.svg",
    "print_manager": ICON_ROOT / "sidebar" / "printer.svg",
    "print_economics": ICON_ROOT / "sidebar" / "economics.svg",
    "mockup_generator": ICON_ROOT / "sidebar" / "mockup.svg",
    "missing_files": ICON_ROOT / "sidebar" / "warning.svg",
    "caret-right": ICON_ROOT / "sidebar" / "chevron-right.svg",
    "caret-down": ICON_ROOT / "sidebar" / "chevron-down.svg",
    "expand": ICON_ROOT / "sidebar" / "plus.svg",
    "notification": ICON_ROOT / "sidebar" / "notification.svg",
    # Sidebar Footer
    "refresh": ICON_ROOT / "sidebar" / "refresh.svg",
    "theme_to_light": ICON_ROOT / "sidebar" / "light.svg",
    "theme_to_dark": ICON_ROOT / "sidebar" / "dark.svg",
    "settings": ICON_ROOT / "sidebar" / "settings.svg",
    # Missing Files
    "status_ok": ICON_ROOT / "sidebar" / "okay.svg",
    "status_missing": ICON_ROOT / "sidebar" / "missing.svg",
    # Settings
    "edit": ICON_ROOT / "edit.svg",
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
