"""Notifications drawer widget."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from studiohub.constants import UIConstants
from studiohub.style.styles.typography import apply_typography
from studiohub.services.notifications.notification_service import Notification


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
        self._setup_ui()
        self._setup_animation()
        self.hide()
    
    def _setup_ui(self) -> None:
        """Setup the UI components."""
        self.setObjectName("NotificationsDrawer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(UIConstants.NOTIFICATION_DRAWER_WIDTH)
        
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
        self._anim.setDuration(UIConstants.NOTIFICATION_ANIMATION_DURATION)
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
        header.setFixedHeight(UIConstants.NOTIFICATION_HEADER_HEIGHT)
        
        layout = QtWidgets.QVBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        title = QtWidgets.QLabel("Notifications")
        title.setProperty("role", "view-title")
        apply_typography(title, "h1")
        
        layout.addWidget(title)
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Notification list
        self._list = QtWidgets.QVBoxLayout()
        self._list.setSpacing(8)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setAlignment(Qt.AlignTop)
        
        self._list_container = QtWidgets.QWidget()
        self._list_container.setContentsMargins(0, 0, 0, 0)
        self._list_container.setLayout(self._list)
        self._list_container.setAttribute(Qt.WA_StyledBackground, False)
        
        layout.addWidget(self._list_container)
        layout.addStretch(1)
        
        # Empty state
        self._empty_label = QtWidgets.QLabel("No notifications yet")
        self._empty_label.setObjectName("Muted")
        self._empty_label.setAlignment(Qt.AlignCenter)
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
    
    def add_notification(self, notification: Notification) -> None:
        """
        Add a notification to the drawer.
        
        Args:
            notification: Notification to add
        """
        self._empty_label.hide()
        
        row = self._create_notification_row(notification)
        self._list.addWidget(row)
        
        # Add divider
        divider = QtWidgets.QFrame()
        divider.setObjectName("NotificationDivider")
        divider.setFixedHeight(1)
        divider.setAttribute(Qt.WA_StyledBackground, True)
        self._list.addWidget(divider)
    
    def _create_notification_row(
        self, 
        notification: Notification
    ) -> QtWidgets.QWidget:
        """
        Create a notification row widget.
        
        Args:
            notification: Notification data
            
        Returns:
            Configured notification row
        """
        row = QtWidgets.QWidget()
        row.setObjectName("NotificationRow")
        row.setAttribute(Qt.WA_StyledBackground, True)
        
        layout = QtWidgets.QVBoxLayout(row)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title
        title = QtWidgets.QLabel(notification.title)
        title.setProperty("role", "notification-title")
        apply_typography(title, "h5")
        
        # Body
        body = QtWidgets.QLabel(notification.message)
        body.setWordWrap(True)
        apply_typography(body, "body-small")
        
        layout.addWidget(title)
        layout.addWidget(body)
        
        return row
