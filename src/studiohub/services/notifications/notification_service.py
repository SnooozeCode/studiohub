# FILE: C:\Users\snooo\Desktop\src\studiohub\src\studiohub\services\notifications\notification_service.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Callable, Optional

@dataclass
class NotificationAction:
    """Action that can be taken on a notification."""
    label: str
    callback: Callable[[], None]
    icon: Optional[str] = None


@dataclass
class Notification:
    key: str              # unique key (prevents duplicates)
    level: str            # info | warning | error | success
    title: str
    message: str
    timestamp: datetime
    actions: List[NotificationAction] = field(default_factory=list)
    auto_dismiss_seconds: Optional[int] = None  # Auto-dismiss after N seconds (None = persistent)


class NotificationService:
    def __init__(self):
        self._notifications: List[Notification] = []
        self._listeners: list[Callable[[Notification], None]] = []
        self._dismiss_timers: dict[str, any] = {}  # QTimer references

    def add_listener(self, fn: Callable[[Notification], None]):
        self._listeners.append(fn)

    def emit(self, notification: Notification):
        # Remove existing notification with same key
        self.clear(notification.key)

        self._notifications.append(notification)

        for fn in self._listeners:
            fn(notification)

    def all(self) -> List[Notification]:
        return list(self._notifications)

    def clear(self, key: str):
        """Remove notification completely."""
        # Cancel any pending dismiss timer
        if key in self._dismiss_timers:
            try:
                self._dismiss_timers[key].stop()
            except:
                pass
            del self._dismiss_timers[key]

        self._notifications = [
            n for n in self._notifications if n.key != key
        ]