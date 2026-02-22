# FILE: C:\Users\snooo\Desktop\src\studiohub\src\studiohub\ui\widgets\notifications_drawer.py

"""Notifications drawer widget."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from studiohub.constants import UIConstants
from studiohub.style.typography.rules import apply_typography
from studiohub.services.notifications.notification_service import Notification, NotificationAction
from studiohub.ui.icons import render_svg


class NotificationActionButton(QtWidgets.QPushButton):
    """Button for notification actions."""
    
    def __init__(self, action: NotificationAction, parent=None, close_drawer_callback=None):
        super().__init__(action.label, parent)
        self.action = action
        self.close_drawer_callback = close_drawer_callback
        self.setObjectName("NotificationAction")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        
        if action.icon:
            self._update_icon()
    
    def _update_icon(self):
        """Update button icon based on current theme."""
        app = QtWidgets.QApplication.instance()
        tokens = app.property("theme_tokens") if app else None
        
        if tokens:
            color = QtGui.QColor(tokens.text_primary)
        else:
            color = QtGui.QColor(200, 200, 200)
        
        pixmap = render_svg(self.action.icon, size=14, color=color)
        if pixmap and not pixmap.isNull():
            self.setIcon(QtGui.QIcon(pixmap))
            self.setIconSize(QtCore.QSize(14, 14))
    
    def mousePressEvent(self, event):
        """Handle click - execute action and close drawer."""
        super().mousePressEvent(event)
        if self.action.callback:
            self.action.callback()
        if self.close_drawer_callback:
            self.close_drawer_callback()
    
    def showEvent(self, event):
        """Update icon when shown."""
        super().showEvent(event)
        self._update_icon()


class NotificationRow(QtWidgets.QWidget):
    """Enhanced notification row with actions."""
    
    dismissed = QtCore.Signal(str)  # notification key
    
    def __init__(self, notification: Notification, parent=None, close_drawer_callback=None):
        super().__init__(parent)
        self.notification = notification
        self.close_drawer_callback = close_drawer_callback
        self.setObjectName("NotificationRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header with level indicator and timestamp
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(8)
        
        # Level indicator (colored dot)
        level_dot = QtWidgets.QLabel("●")
        level_dot.setObjectName(f"NotificationLevel_{self.notification.level}")
        level_dot.setFixedSize(8, 8)
        level_dot.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QtWidgets.QLabel(self.notification.title)
        title.setProperty("role", "notification-title")
        title.setWordWrap(True)
        apply_typography(title, "h5")
        
        # Timestamp
        timestamp = QtWidgets.QLabel(
            self.notification.timestamp.strftime("%I:%M %p")
        )
        timestamp.setObjectName("NotificationTimestamp")
        apply_typography(timestamp, "small")
        timestamp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header.addWidget(level_dot)
        header.addWidget(title, 1)
        header.addWidget(timestamp)
        
        layout.addLayout(header)
        
        # Message body
        if self.notification.message:
            body = QtWidgets.QLabel(self.notification.message)
            body.setWordWrap(True)
            body.setObjectName("NotificationBody")
            apply_typography(body, "body-small")
            layout.addWidget(body)
        
        # Action buttons
        if self.notification.actions:
            actions_row = QtWidgets.QHBoxLayout()
            actions_row.setSpacing(8)
            actions_row.addStretch(1)
            
            for action in self.notification.actions:
                if action.label == "Dismiss":
                    btn = NotificationActionButton(action, close_drawer_callback=None)
                    btn.clicked.connect(lambda checked, key=self.notification.key: self.dismissed.emit(key))
                    btn.setProperty("action", "dismiss")
                    actions_row.addWidget(btn)
                else:
                    btn = NotificationActionButton(
                        action, 
                        close_drawer_callback=self.close_drawer_callback
                    )
                    btn.clicked.connect(lambda checked, key=self.notification.key: self.dismissed.emit(key))
                    actions_row.addWidget(btn)
            
            layout.addLayout(actions_row)
    
    def refresh_theme(self):
        """Refresh theme-dependent elements."""
        # Update action button icons
        for child in self.findChildren(NotificationActionButton):
            child._update_icon()


class NotificationsDrawer(QtWidgets.QFrame):
    """
    Slide-out drawer for displaying notifications.
    
    Animates in from the right side of the window and displays
    a list of notifications with title and message.
    """
    
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        """
        Initialize notifications drawer.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._is_open = False
        self._notifications: dict[str, NotificationRow] = {}
        self._dismiss_timers: dict[str, QtCore.QTimer] = {}
        
        self._setup_ui()
        self._setup_animation()
        self.hide()
    
    def _setup_ui(self) -> None:
        """Setup the UI components."""
        self.setObjectName("NotificationsDrawer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(400)  # Wider for actions
        
        # Root layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Content
        content = self._create_content()
        layout.addWidget(content)
        
        self.refresh_theme()
    
    def _setup_animation(self) -> None:
        """Configure slide animation."""
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
    
    def _create_header(self) -> QtWidgets.QFrame:
        """
        Create the drawer header.
        
        Returns:
            Configured header widget
        """
        header = QtWidgets.QFrame()
        header.setObjectName("NotificationsHeader")
        header.setAttribute(Qt.WA_StyledBackground, True)
        header.setFixedHeight(56)
        
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)
        
        title = QtWidgets.QLabel("Notifications")
        title.setProperty("role", "view-title")
        apply_typography(title, "h1")
        
        # Clear all button
        self.clear_all_btn = QtWidgets.QPushButton("Clear All")
        self.clear_all_btn.setObjectName("NotificationAction")
        self.clear_all_btn.setCursor(Qt.PointingHandCursor)
        self.clear_all_btn.setFixedHeight(28)
        self.clear_all_btn.hide()  # Hide by default
        self.clear_all_btn.clicked.connect(self._clear_all)
        
        layout.addWidget(title, 1)
        layout.addWidget(self.clear_all_btn)
        
        return header
    
    def _create_content(self) -> QtWidgets.QWidget:
        """
        Create the content area.
        
        Returns:
            Configured content widget
        """
        content = QtWidgets.QWidget()
        content.setAttribute(Qt.WA_StyledBackground, False)
        
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Scroll area for notifications
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setObjectName("NotificationsScroll")
        
        # Container for notifications
        self.container = QtWidgets.QWidget()
        self.container.setAttribute(Qt.WA_StyledBackground, False)
        self._list = QtWidgets.QVBoxLayout(self.container)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(1)  # 1px for divider
        self._list.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        # Empty state
        self._empty_label = QtWidgets.QLabel("No notifications")
        self._empty_label.setObjectName("NotificationEmpty")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setFixedHeight(100)
        self._list.addWidget(self._empty_label)
        
        return content
    
    @property
    def is_open(self) -> bool:
        """Check if drawer is currently open."""
        return self._is_open
    
    @is_open.setter
    def is_open(self, value: bool) -> None:
        """Set drawer open state."""
        self._is_open = value
    
    def refresh_theme(self) -> None:
        """Refresh the widget theme."""
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        
        # Update all notification rows
        for row in self._notifications.values():
            row.refresh_theme()
    
    def add_notification(self, notification: Notification) -> None:
        """
        Add a notification to the drawer.
        
        Args:
            notification: Notification to add
        """
        # Remove existing if present
        if notification.key in self._notifications:
            self._remove_notification_row(notification.key)
        
        self._empty_label.hide()
        self.clear_all_btn.show()
        
        # Create and add new notification at top
        row = NotificationRow(
            notification, 
            close_drawer_callback=self._safe_close
        )
        row.dismissed.connect(self._on_notification_dismissed)
        
        # Insert at beginning (position 0)
        self._list.insertWidget(0, row)
        self._notifications[notification.key] = row
        
        # Add divider after new notification (position 1)
        divider = self._create_divider()
        self._list.insertWidget(1, divider)
        
        # Set auto-dismiss timer if specified
        if notification.auto_dismiss_seconds:
            self._schedule_dismiss(notification.key, notification.auto_dismiss_seconds)
    
    def _safe_close(self):
        """Safely close the drawer."""
        main_window = self.window()
        if main_window and hasattr(main_window, '_toggle_notifications'):
            if self.is_open:
                main_window._toggle_notifications()
    
    def _create_divider(self) -> QtWidgets.QFrame:
        """Create a divider frame."""
        divider = QtWidgets.QFrame()
        divider.setObjectName("NotificationDivider")
        divider.setFixedHeight(1)
        divider.setAttribute(Qt.WA_StyledBackground, True)
        return divider
    
    def _schedule_dismiss(self, key: str, seconds: int):
        """Schedule automatic dismissal of a notification."""
        # Cancel existing timer if any
        if key in self._dismiss_timers:
            self._dismiss_timers[key].stop()
        
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._auto_dismiss_notification(key))
        timer.start(seconds * 1000)
        
        self._dismiss_timers[key] = timer
    
    def _auto_dismiss_notification(self, key: str):
        """Automatically dismiss a notification."""
        if key in self._dismiss_timers:
            del self._dismiss_timers[key]
        self._on_notification_dismissed(key)
    
    def _on_notification_dismissed(self, key: str):
        """Handle notification dismissal."""
        self._remove_notification_row(key)
        
        # Cancel any pending timer
        if key in self._dismiss_timers:
            self._dismiss_timers[key].stop()
            del self._dismiss_timers[key]
        
        # Update empty state
        if not self._notifications:
            self._empty_label.show()
            self.clear_all_btn.hide()
        
        # Update badge count in sidebar
        self._update_badge_count()
    
    def _update_badge_count(self):
        """Update the notification badge count in the sidebar."""
        main_window = self.window()
        if main_window and hasattr(main_window, '_sidebar'):
            sidebar = main_window._sidebar
            if sidebar and sidebar._notifications_button:
                sidebar._notifications_button.set_badge_count(len(self._notifications))
    
    def _remove_notification_row(self, key: str):
        """Remove a notification row and its divider."""
        if key not in self._notifications:
            return
        
        row = self._notifications[key]
        
        # Find and remove the row and its divider
        for i in range(self._list.count()):
            widget = self._list.itemAt(i).widget()
            if widget == row:
                # Remove the row
                self._list.takeAt(i)
                row.deleteLater()
                
                # Remove the following divider if it exists
                if i < self._list.count():
                    next_widget = self._list.itemAt(i).widget()
                    if next_widget and next_widget.objectName() == "NotificationDivider":
                        self._list.takeAt(i)
                        next_widget.deleteLater()
                break
        
        del self._notifications[key]
    
    def _clear_all(self):
        """Clear all notifications."""
        # Dismiss all notifications
        keys = list(self._notifications.keys())
        for key in keys:
            self._on_notification_dismissed(key)
    
    def remove_notification(self, key: str):
        """Remove a specific notification."""
        self._on_notification_dismissed(key)