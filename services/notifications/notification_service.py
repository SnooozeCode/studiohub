from dataclasses import dataclass
from datetime import datetime
from typing import List, Callable

@dataclass
class Notification:
    key: str              # unique key (prevents duplicates)
    level: str            # info | warning | error
    title: str
    message: str
    timestamp: datetime


class NotificationService:
    def __init__(self):
        self._notifications: List[Notification] = []
        self._listeners: list[Callable[[Notification], None]] = []

    def add_listener(self, fn: Callable[[Notification], None]):
        self._listeners.append(fn)

    def emit(self, notification: Notification):
        # Prevent duplicates
        if any(n.key == notification.key for n in self._notifications):
            return

        self._notifications.append(notification)

        for fn in self._listeners:
            fn(notification)

    def all(self) -> List[Notification]:
        return list(self._notifications)

    def clear(self, key: str):
        self._notifications = [
            n for n in self._notifications if n.key != key
        ]
