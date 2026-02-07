from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QSizePolicy,
    QLabel,
    QGraphicsOpacityEffect,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt, QSize, Property, QPropertyAnimation, QPoint

from studiohub.ui.icons import render_svg
from studiohub.theme.styles.typography import apply_typography

ICON_COL_WIDTH = 48
LABEL_COL_GAP = 12
ACTION_COL_WIDTH = 12

ICON_BOX_EXPANDED = 24
ICON_GLYPH_EXPANDED = 20

ICON_BOX_COLLAPSED = 24
ICON_GLYPH_COLLAPSED = 20


class NotificationBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("SidebarNotificationBadge")
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_StyledBackground, True)

        font = self.font()
        font.setPointSize(7)  # base size; QSS may override
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)

        self.hide()

    def set_count(self, count: int):
        if count <= 0:
            self.hide()
            return
        self.setText("9+" if count > 9 else str(count))
        self.show()

    def set_compact(self, compact: bool):
        if compact:
            self.setProperty("variant", "compact")
            self.setFixedSize(14, 14)
        else:
            self.setProperty("variant", "inline")
            self.setFixedSize(18, 18)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class SidebarButton(QWidget):
    def __init__(
        self,
        text: str,
        *,
        icon: str | None = None,
        trailing_icon: str | None = None,
        indent: int = 0,
        indicator_width: int = 3,
        row_height: int = 56,
        show_icon_column: bool = True,
        show_indicator: bool = True,
        on_click: callable | None = None,
    ):
        super().__init__()

        # -------------------------------------------------
        # State
        # -------------------------------------------------
        self._on_click = on_click

        self._icon_name = icon
        self._collapsed = False

        self._badge_count = 0

        # Leading caret (child navigation)
        self._leading_icon_name: str | None = None
        self._leading_icon_muted = True

        # Trailing caret (group expand)
        self._trailing_icon_name = trailing_icon
        self._trailing_icon_muted = True

        self._icon_box = ICON_BOX_EXPANDED
        self._icon_glyph = ICON_GLYPH_EXPANDED
        self._indent = indent

        self._icon_color = QColor("#000000")  # fallback only
        self._show_icon_column = show_icon_column
        self._show_indicator = show_indicator

        self.setObjectName("SidebarButton")
        self.setProperty("role", "sidebar-item")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(row_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # -------------------------------------------------
        # Badge (MUST exist early)
        # -------------------------------------------------
        self.badge = NotificationBadge(self)
        self.badge.hide()

        # -------------------------------------------------
        # Active indicator
        # -------------------------------------------------
        self.indicator = QFrame()
        self.indicator.setObjectName("SidebarIndicator")
        self.indicator.setProperty("role", "sidebar-indicator")
        self.indicator.setFixedWidth(indicator_width)
        self.indicator.setFixedHeight(row_height)
        self.indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if not self._show_indicator:
            self.indicator.hide()
            self.indicator.setFixedWidth(0)

        # -------------------------------------------------
        # Button shell
        # -------------------------------------------------
        self.button = QPushButton()
        self.button.setObjectName("SidebarButtonText")
        self.button.setFlat(True)
        self.button.setAttribute(Qt.WA_StyledBackground, True)
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.setFixedHeight(row_height)
        self.button.setIconSize(QSize(self._icon_box, self._icon_box))
        self.button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.button.clicked.connect(self._handle_click)

        btn_layout = QHBoxLayout(self.button)
        btn_layout.setContentsMargins(self._indent, 0, 12, 0)
        btn_layout.setSpacing(0)

        # -------------------------------------------------
        # ICON COLUMN spacer (reserves width; DOES NOT own icon)
        # -------------------------------------------------
        self._icon_spacer = QWidget(self.button)
        self._icon_spacer.setFixedWidth(ICON_COL_WIDTH)
        self._icon_spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # -------------------------------------------------
        # Icon widget (OWNED by SidebarButton; never put in a layout)
        # -------------------------------------------------
        self.icon = QLabel(self)
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.icon.setFixedSize(self._icon_box, self._icon_box)

        # If this row doesn't show icon column, hide icon/spacer
        if not self._show_icon_column:
            self._icon_spacer.hide()
            self.icon.hide()

        # -------------------------------------------------
        # Leading caret (child items)
        # -------------------------------------------------
        self.leading_icon = QLabel(self.button)
        self.leading_icon.setFixedSize(14, 14)
        self.leading_icon.setAlignment(Qt.AlignCenter)
        self.leading_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.leading_icon.hide()

        # -------------------------------------------------
        # Label
        # -------------------------------------------------
        self.label = QLabel(text, self.button)
        self.label.setObjectName("SidebarButtonLabel")
        apply_typography(self.label, "nav")
        self.label.setAttribute(Qt.WA_SetFont, True)
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._label_opacity = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self._label_opacity)
        self._label_opacity.setOpacity(1.0)

        self._fade_anim = QPropertyAnimation(self._label_opacity, b"opacity")
        self._fade_anim.setDuration(110)
        self._fade_anim.finished.connect(self._on_fade_finished)

        # -------------------------------------------------
        # Trailing caret (group expand)
        # -------------------------------------------------
        self.trailing_icon = QLabel(self.button)
        self.trailing_icon.setFixedSize(16, 16)
        self.trailing_icon.setAlignment(Qt.AlignCenter)
        self.trailing_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.trailing_icon.hide()

        # -------------------------------------------------
        # Badge slot (expanded mode inline badge)
        # -------------------------------------------------
        self._badge_slot = QWidget(self.button)
        self._badge_layout = QHBoxLayout(self._badge_slot)
        self._badge_layout.setContentsMargins(0, 0, 0, 0)
        self._badge_layout.setSpacing(0)

        # -------------------------------------------------
        # Assemble button layout
        # -------------------------------------------------
        if self._show_icon_column:
            btn_layout.addWidget(self._icon_spacer)
            btn_layout.addSpacing(LABEL_COL_GAP)

        btn_layout.addWidget(self.leading_icon)
        btn_layout.addSpacing(6)  # matches prior spacing
        btn_layout.addWidget(self.label, 1)

        # Action area: caret + badge slot
        action_col = QWidget(self.button)
        action_col.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        action_col_layout = QHBoxLayout(action_col)
        action_col_layout.setContentsMargins(0, 0, 0, 0)
        action_col_layout.setSpacing(0)

        action_col_layout.addWidget(self.trailing_icon, alignment=Qt.AlignCenter)
        action_col_layout.addWidget(self._badge_slot, alignment=Qt.AlignCenter)

        btn_layout.addWidget(action_col)

        # -------------------------------------------------
        # Outer layout
        # -------------------------------------------------
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.indicator)
        outer.addWidget(self.button, 1)

        # Initial state
        self.set_active(False)
        self._refresh_icon()
        self._refresh_leading_icon()
        self._refresh_trailing_icon()
        self._position_icon()
        self._update_badge_visibility()

    # =================================================
    # Geometry helpers
    # =================================================
    def _position_icon(self):
        if not self._show_icon_column:
            return

        y = (self.height() - self.icon.height()) // 2

        # Anchor to the icon spacer's actual geometry
        spacer_left = self._icon_spacer.mapTo(self, QPoint(0, 0)).x()
        spacer_width = self._icon_spacer.width()

        nudge = 4 if self._collapsed else 0
        x = spacer_left + (spacer_width - self.icon.width()) // 2 + nudge

        self.icon.move(x, y)


    # =================================================
    # Public API
    # =================================================
    @property
    def badge_count(self) -> int:
        return self._badge_count

    def set_badge_count(self, count: int):
        self._badge_count = max(0, count)
        self.badge.set_count(self._badge_count)
        self._update_badge_visibility()

    def _update_badge_visibility(self):
        if self._badge_count <= 0:
            self.badge.hide()
            return

        if self._collapsed:
            # Collapsed: overlay on icon (badge parent = self)
            self.badge.set_compact(True)
            if self.badge.parent() is not self:
                self.badge.setParent(self)
            self.badge.raise_()

            if self._show_icon_column and self.icon.isVisible():
                icon_tl = self.icon.mapTo(self, QPoint(0, 0))
                self.badge.adjustSize()

                x = icon_tl.x() + self.icon.width() - self.badge.width() + 6
                y = icon_tl.y() - 6
                self.badge.move(x, y)
                self.badge.show()
            else:
                self.badge.hide()

        else:
            # Expanded: inline badge (badge parent = _badge_slot)
            self.badge.set_compact(False)
            if self.badge.parent() is not self._badge_slot:
                self.badge.setParent(self._badge_slot)
                self._badge_layout.addWidget(self.badge, alignment=Qt.AlignCenter)
            self.badge.show()

    def set_active(self, is_active: bool):
        self.setProperty("active", is_active)
        self._refresh_icon()
        self._repolish()

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed

        layout = self.button.layout()

        if collapsed:
            self.label.hide()
            self.leading_icon.hide()
            self.trailing_icon.hide()

            # remove indicator from layout flow
            self.indicator.hide()
            self.indicator.setFixedWidth(0)

            # REMOVE ALL BUTTON PADDING
            layout.setContentsMargins(0, 0, 0, 0)
            self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            # icon bigger
            self._icon_box = ICON_BOX_COLLAPSED
            self._icon_glyph = ICON_GLYPH_COLLAPSED
            if self._show_icon_column:
                self.icon.setFixedSize(self._icon_box, self._icon_box)
                self.button.setIconSize(QSize(self._icon_box, self._icon_box))

        else:
            self.label.show()

            if self._show_indicator:
                self.indicator.show()
                self.indicator.setFixedWidth(3)
            else:
                self.indicator.hide()
                self.indicator.setFixedWidth(0)

            if self._trailing_icon_name:
                self.trailing_icon.show()

            layout.setContentsMargins(self._indent, 0, 12, 0)
            self.button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            # icon normal
            self._icon_box = ICON_BOX_EXPANDED
            self._icon_glyph = ICON_GLYPH_EXPANDED
            if self._show_icon_column:
                self.icon.setFixedSize(self._icon_box, self._icon_box)
                self.button.setIconSize(QSize(self._icon_box, self._icon_box))

        self._refresh_icon()
        self._position_icon()
        self._update_badge_visibility()

    def set_icon_active(self, active: bool):
        """
        Activate only the icon (no label, no indicator).
        Used for group parents when a child is active.
        """
        self.setProperty("icon_active", active)
        self._refresh_icon()
        self._repolish()

    def fade_label(self, visible: bool):
        self._fade_anim.stop()

        if visible:
            self.label.setVisible(True)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
        else:
            self._fade_anim.setStartValue(1.0)
            self._fade_anim.setEndValue(0.0)

        self._fade_anim.start()

    # ---------- caret controls ----------
    def set_leading_icon(self, icon_name: str | None, *, muted: bool = True):
        self._leading_icon_name = icon_name
        self._leading_icon_muted = muted
        self._refresh_leading_icon()

    def set_trailing_icon(self, icon_name: str | None, *, muted: bool = True):
        self._trailing_icon_name = icon_name
        self._trailing_icon_muted = muted
        self._refresh_trailing_icon()

    def refresh_theme(self):
        self._refresh_icon()
        self._refresh_leading_icon()
        self._refresh_trailing_icon()
        self._repolish()

    # =================================================
    # Internals
    # =================================================
    def _handle_click(self):
        if self._on_click:
            self._on_click()

    def _on_fade_finished(self):
        if self._label_opacity.opacity() == 0.0:
            self.label.setVisible(False)

    def _repolish(self):
        for w in (self, self.indicator, self.button, self.label):
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def _refresh_icon(self):
        if not self._show_icon_column:
            return

        if not self._icon_name:
            self.icon.clear()
            return

        app = QtWidgets.QApplication.instance()
        tokens = app.property("theme_tokens")

        is_active = bool(self.property("active"))
        is_icon_active = bool(self.property("icon_active"))

        if not tokens:
            color = QColor(128, 128, 128)
        else:
            base = QColor(tokens.text_primary)
            if not (is_active or is_icon_active):
                base.setAlphaF(0.55)
            color = base

        self.icon.setPixmap(
            render_svg(self._icon_name, size=self._icon_glyph, color=color)
        )
        self.icon.show()

    def _refresh_leading_icon(self):
        if not self._leading_icon_name:
            self.leading_icon.hide()
            return

        app = QtWidgets.QApplication.instance()
        tokens = app.property("theme_tokens")

        if not tokens:
            color = QColor(128, 128, 128)
        else:
            base = QColor(tokens.text_primary)
            if self._leading_icon_muted:
                base.setAlphaF(0.55)
            color = base

        self.leading_icon.setPixmap(
            render_svg(self._leading_icon_name, size=12, color=color)
        )
        self.leading_icon.show()

    def _refresh_trailing_icon(self):
        if not self._trailing_icon_name:
            self.trailing_icon.hide()
            return

        app = QtWidgets.QApplication.instance()
        tokens = app.property("theme_tokens")

        if not tokens:
            color = QColor(128, 128, 128)
        else:
            base = QColor(tokens.text_primary)
            if self._trailing_icon_muted:
                base.setAlphaF(0.55)
            color = base

        self.trailing_icon.setPixmap(
            render_svg(self._trailing_icon_name, size=14, color=color)
        )
        self.trailing_icon.show()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_icon()
        self._refresh_leading_icon()
        self._refresh_trailing_icon()
        self._position_icon()
        self._update_badge_visibility()

    # QSS-bound property
    def get_icon_color(self) -> QColor:
        return self._icon_color

    def set_icon_color(self, color):
        self._icon_color = QColor(color)
        self._refresh_icon()

    iconColor = Property(QColor, get_icon_color, set_icon_color)
