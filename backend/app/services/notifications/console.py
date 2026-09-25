from app.core.logging import get_logger

logger = get_logger("notifications.email")


class ConsoleEmailSender:
    """Development stand-in for a real email provider: logs instead of
    sending. Swap for an SMTP/provider-backed implementation in Phase 9
    without changing any caller of NotificationSender."""

    async def send_email(self, *, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL to=%s subject=%r body=%r", to, subject, body)
