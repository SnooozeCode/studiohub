from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSpacerItem,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QBoxLayout,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
)
from PySide6.QtGui import QIcon, QPixmap, QColor

from studiohub.ui.sidebar.sidebar_button import SidebarButton
from studiohub.ui.sidebar.sidebar_group import SidebarGroup
from studiohub.ui.icons import render_svg

ROOT = Path(__file__).resolve().parents[2]

class SidebarDivider(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SidebarDividerWrapper")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)  # ← THIS is the spacing
        layout.setSpacing(0)

        line = QFrame()
        line.setObjectName("SidebarDivider")
        line.setFixedHeight(1)
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.setAttribute(Qt.WA_StyledBackground, True)

        layout.addWidget(line)


class Sidebar(QWidget):

    refresh_requested = Signal()
    theme_toggle_requested = Signal()
    notifications_requested = Signal()

    def __init__(self, *, width: int = 240):
        super().__init__()
        self.setObjectName("leftMenuBg")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._group_children: dict[str, set[str]] = {}

        self._notifications_button: SidebarButton | None = None
        self._notifications_drawer_valid = True  # Flag to track if drawer is working

        self._groups: dict[str, SidebarGroup] = {}
        self._buttons: dict[str, SidebarButton] = {}
        self._top_hubs: list[str] = []
        self._bottom_hubs: list[str] = []

        self._expanded_width = width
        self._collapsed_width = 64
        self._collapsed = False
        self._theme = "dracula"

        self._anim_min = None
        self._anim_max = None
        self._is_animating = False

        self.setProperty("role", "sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # -------------------------------------------------
        # Header
        # -------------------------------------------------
        self._header = QFrame()
        self._header.setObjectName("SidebarHeader")
        self._header.setAttribute(Qt.WA_StyledBackground, True)
        self._header.setFixedHeight(80)
        self._header.setAttribute(Qt.WA_StyledBackground, True)

        hl = QVBoxLayout(self._header)
        hl.setContentsMargins(0, 12, 0, 12)

        self._logo = QLabel(alignment=Qt.AlignCenter)
        hl.addStretch(1)
        hl.addWidget(self._logo)
        hl.addStretch(1)

        self._layout.addWidget(self._header)

        self._spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

        # -------------------------------------------------
        # Footer
        # -------------------------------------------------
        self._footer = QFrame()
        self._footer.setObjectName("SidebarFooter")
        self._footer.setAttribute(Qt.WA_StyledBackground, True)

        self._footer_layout = QBoxLayout(QBoxLayout.LeftToRight, self._footer)
        self._footer_layout.setContentsMargins(12, 16, 12, 16)

        self.btn_refresh = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)

        self.btn_theme = QPushButton()
        self.btn_theme.clicked.connect(self.theme_toggle_requested.emit)

        self.btn_settings = QPushButton()

        for b in (self.btn_refresh, self.btn_theme, self.btn_settings):
            b.setObjectName("SidebarUtility")
            b.setFixedSize(32, 32)
            b.setIconSize(QSize(20, 20))
            b.setCursor(Qt.PointingHandCursor)

        self._footer_layout.addStretch(1)
        self._footer_layout.addWidget(self.btn_refresh)
        self._footer_layout.addStretch(1)
        self._footer_layout.addWidget(self.btn_theme)
        self._footer_layout.addStretch(1)
        self._footer_layout.addWidget(self.btn_settings)
        self._footer_layout.addStretch(1)

        self._footer_buttons = [self.btn_refresh, self.btn_theme, self.btn_settings]

        self._set_footer_icons()
        self._update_theme_toggle_icon()

    # =================================================
    # Compatibility hook (DO NOT REMOVE)
    # =================================================
    def _sidebar_on_theme_changed(self, theme_name: str) -> None:
        self._theme = theme_name
        self.set_logo(theme_name)

    # =================================================
    # Groups & Buttons
    # =================================================
    def add_group(self, key: str, label: str, icon: str):
        group = SidebarGroup(label, icon)
        self._groups[key] = group
        self._top_hubs.append(key)
        self._group_children[key] = set()

    def add_group_item(self, group_key: str, item_key: str, label: str, on_click):
        group = self._groups[group_key]

        btn = SidebarButton(
            label,
            show_icon_column=False,
            show_indicator=False,
        )
        btn.set_trailing_icon("caret-right", muted=True)

        btn.button.clicked.connect(lambda _, k=item_key: self.activate(k))
        btn.button.clicked.connect(on_click)

        self._buttons[item_key] = btn
        self._group_children[group_key].add(item_key)

        # 👇 CAPTURE THE ROW
        row = group.add_button(btn)

        # 👇 STORE ROW REFERENCE
        btn._parent_row = row

    def add_hub(self, key: str, label: str, on_click, *, bottom: bool = False):
        btn = SidebarButton(label, icon=key)
        btn.button.clicked.connect(lambda _, k=key: self.activate(k))
        btn.button.clicked.connect(on_click)

        self._buttons[key] = btn
        (self._bottom_hubs if bottom else self._top_hubs).append(key)

    # =================================================
    # Layout
    # =================================================
    def finalize(self):
        self._add_menu_button()

        for key in self._top_hubs:
            if key in self._groups:
                self._layout.addWidget(self._groups[key])
            else:
                self._layout.addWidget(self._buttons[key])

        self._layout.addItem(self._spacer)

        for key in self._bottom_hubs:
            self._layout.addWidget(self._buttons[key])

        self._layout.addWidget(self._footer)


    def _add_menu_button(self):
        # Menu (collapse toggle)
        self._layout.addSpacing(10)

        self._menu_button = SidebarButton("Menu", icon="menu")
        self._menu_button.button.clicked.connect(self.toggle_collapsed)
        self._layout.addWidget(self._menu_button)

        # Create notifications button with safe click handler
        self._notifications_button = SidebarButton(
            "Notifications",
            icon="notification",
            show_indicator=True,
        )
        
        # Use a safe wrapper for the click handler
        self._notifications_button.button.clicked.connect(self._safe_toggle_notifications)
        
        self._layout.addWidget(self._notifications_button)

        # ──────────── Divider ────────────
        self._layout.addWidget(SidebarDivider())


    def _safe_toggle_notifications(self):
        """
        Safely emit notifications signal with error handling.
        Prevents crashes if the notifications drawer isn't properly initialized.
        """
        try:
            # Check if main window exists and has the expected method
            main_window = self.window()
            if main_window and hasattr(main_window, '_toggle_notifications'):
                self.notifications_requested.emit()
            else:
                # Fallback: log warning and maybe show a tooltip
                print("[Sidebar] Notifications drawer not available")
                
                # Optional: Show a temporary tooltip on the button
                if self._notifications_button:
                    self._notifications_button.setToolTip("Notifications not available")
                    QTimer.singleShot(2000, lambda: self._notifications_button.setToolTip(""))
        except Exception as e:
            print(f"[Sidebar] Error toggling notifications: {e}")
            # Mark drawer as invalid to prevent future attempts
            self._notifications_drawer_valid = False


    # =================================================
    # State
    # =================================================

    def activate(self, active_key: str):
        # -------------------------------------------------
        # 1) Clear all button + row states
        # -------------------------------------------------
        for btn in self._buttons.values():
            btn.set_active(False)

            if hasattr(btn, "_parent_row"):
                r = btn._parent_row
                r.setProperty("active", False)

                r.style().unpolish(r)
                r.style().polish(r)
                r.update()

                ind = getattr(r, "_indicator", None)
                if ind is not None:
                    ind.style().unpolish(ind)
                    ind.style().polish(ind)
                    ind.update()

        # -------------------------------------------------
        # 2) Clear parent icon-only active states
        # -------------------------------------------------
        for group in self._groups.values():
            group.header.set_icon_active(False)

        # -------------------------------------------------
        # 3) Activate the selected button
        # -------------------------------------------------
        btn = self._buttons.get(active_key)
        if not btn:
            return

        btn.set_active(True)

        # -------------------------------------------------
        # 4) Activate CHILD ROW INDICATOR (only this one)
        # -------------------------------------------------
        if hasattr(btn, "_parent_row"):
            r = btn._parent_row
            r.setProperty("active", True)

            r.style().unpolish(r)
            r.style().polish(r)
            r.update()

            ind = getattr(r, "_indicator", None)
            if ind is not None:
                ind.style().unpolish(ind)
                ind.style().polish(ind)
                ind.update()

        # -------------------------------------------------
        # 5) Icon-only active for parent group
        # -------------------------------------------------
        for group_key, children in self._group_children.items():
            if active_key in children:
                self._groups[group_key].header.set_icon_active(True)
                break



    def _rebuild_footer_layout(self, collapsed: bool):
        while self._footer_layout.count():
            item = self._footer_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if collapsed:
            self._footer_layout.setDirection(QBoxLayout.TopToBottom)
            self._footer_layout.setAlignment(Qt.AlignHCenter)
            self._footer_layout.setContentsMargins(0,16, 0, 16)
            self._footer_layout.setSpacing(18)

            for b in self._footer_buttons:
                self._footer_layout.addWidget(b, alignment=Qt.AlignHCenter)
        else:
            self._footer_layout.setDirection(QBoxLayout.LeftToRight)
            self._footer_layout.setAlignment(Qt.AlignCenter)
            self._footer_layout.setContentsMargins(12, 16, 12, 16)
            self._footer_layout.setSpacing(0)

            self._footer_layout.addStretch(1)
            self._footer_layout.addWidget(self.btn_refresh)
            self._footer_layout.addStretch(1)
            self._footer_layout.addWidget(self.btn_theme)
            self._footer_layout.addStretch(1)
            self._footer_layout.addWidget(self.btn_settings)
            self._footer_layout.addStretch(1)


    def toggle_collapsed(self):
        if self._is_animating:
            return

        self._collapsed = not self._collapsed

        start = self._expanded_width if self._collapsed else self._collapsed_width
        end = self._collapsed_width if self._collapsed else self._expanded_width

        self._animate_width(start, end)

        for btn in self._buttons.values():
            btn.set_collapsed(self._collapsed)

        for g in self._groups.values():
            g.set_collapsed(self._collapsed)

            if self._collapsed:
                g._expanded = False
                g.container.setVisible(False)

        self._menu_button.set_collapsed(self._collapsed)

        if self._notifications_button:
            self._notifications_button.set_collapsed(self._collapsed)

        # 🔥 alignment fix
        self._layout.setAlignment(
            Qt.AlignHCenter if self._collapsed else Qt.AlignLeft
        )

        self._rebuild_footer_layout(self._collapsed)

        self._update_logo()

    def set_refresh_enabled(self, enabled: bool):
        """
        Enable / disable the refresh footer button.
        Used during cache warming and long-running operations.
        """
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.setEnabled(enabled)
            self.btn_refresh.setProperty("disabled", not enabled)
            self.btn_refresh.style().unpolish(self.btn_refresh)
            self.btn_refresh.style().polish(self.btn_refresh)


    # =================================================
    # Animation
    # =================================================
    def _animate_width(self, start: int, end: int):
        self._is_animating = True

        self._anim_min = QPropertyAnimation(self, b"minimumWidth")
        self._anim_max = QPropertyAnimation(self, b"maximumWidth")

        for anim in (self._anim_min, self._anim_max):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(start)
            anim.setEndValue(end)

        self._anim_max.finished.connect(
            lambda: setattr(self, "_is_animating", False)
        )

        self._anim_min.start()
        self._anim_max.start()

    # =================================================
    # Theme / Icons
    # =================================================
    def set_logo(self, theme: str):
        self._theme = theme
        self._update_logo()
        self._update_theme_toggle_icon()
        self._set_footer_icons()

        for btn in self._buttons.values():
            btn.refresh_theme()

    def _update_logo(self):
        name = "logo-dracula" if self._theme == "dracula" else "logo-alucard"
        suffix = "-sq" if self._collapsed else ""
        path = ROOT / "assets" / "icons" / f"{name}{suffix}.png"

        if path.exists():
            pm = QPixmap(str(path))
            self._logo.setPixmap(pm.scaledToHeight(28, Qt.SmoothTransformation))
        else:
            self._logo.clear()

    def _update_theme_toggle_icon(self):
        icon = "theme_to_light" if self._theme == "dracula" else "theme_to_dark"
        color = QColor(235, 235, 235) if self._theme == "dracula" else QColor(35, 35, 35)

        self.btn_theme.setIcon(
            QIcon(render_svg(icon, size=20, color=color))
        )

    def _set_footer_icons(self):
        color = QColor(235, 235, 235) if self._theme == "dracula" else QColor(35, 35, 35)

        self.btn_refresh.setIcon(
            QIcon(render_svg("refresh", size=18, color=color))
        )
        self.btn_settings.setIcon(
            QIcon(render_svg("settings", size=20, color=color))
        )