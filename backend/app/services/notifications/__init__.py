from functools import lru_cache

from app.services.notifications.base import NotificationSender
from app.services.notifications.console import ConsoleEmailSender


@lru_cache
def get_notification_sender() -> NotificationSender:
    return ConsoleEmailSender()
