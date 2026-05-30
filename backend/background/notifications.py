import logging
import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    message: str = ""
    level: NotificationLevel = NotificationLevel.INFO
    source: str = ""
    action_id: str = ""
    read: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "source": self.source,
            "action_id": self.action_id,
            "read": self.read,
            "created_at": self.created_at,
        }


class NotificationManager:
    def __init__(self, max_history: int = 200):
        self._notifications: list = []
        self._max_history = max_history
        self._callbacks: list = []

    def on_notification(self, callback):
        self._callbacks.append(callback)

    def notify(self, title: str, message: str = "",
               level: NotificationLevel = NotificationLevel.INFO,
               source: str = "", action_id: str = "") -> str:
        notification = Notification(
            title=title,
            message=message,
            level=level,
            source=source,
            action_id=action_id,
        )
        self._notifications.append(notification)
        if len(self._notifications) > self._max_history:
            self._notifications = self._notifications[-self._max_history:]
        for cb in self._callbacks:
            try:
                cb(notification)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
        logger.info(f"Notification [{level.value}]: {title} - {message}")
        return notification.id

    def info(self, title: str, message: str = "", source: str = ""):
        return self.notify(title, message, NotificationLevel.INFO, source)

    def warning(self, title: str, message: str = "", source: str = ""):
        return self.notify(title, message, NotificationLevel.WARNING, source)

    def error(self, title: str, message: str = "", source: str = ""):
        return self.notify(title, message, NotificationLevel.ERROR, source)

    def success(self, title: str, message: str = "", source: str = ""):
        return self.notify(title, message, NotificationLevel.SUCCESS, source)

    def mark_read(self, notification_id: str) -> bool:
        for n in self._notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False

    def mark_all_read(self):
        for n in self._notifications:
            n.read = True

    def get_notifications(self, limit: int = 50, unread_only: bool = False) -> list:
        notifications = self._notifications
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        return [n.to_dict() for n in notifications[-limit:]]

    def get_unread_count(self) -> int:
        return sum(1 for n in self._notifications if not n.read)

    def clear(self):
        self._notifications = []
