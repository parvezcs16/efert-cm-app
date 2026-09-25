from typing import Protocol


class NotificationSender(Protocol):
    """Channel-agnostic notification port. Email is the only implementation
    today; SMS/WhatsApp/push can be added later behind the same interface
    without touching callers (see docs/architecture.md)."""

    async def send_email(self, *, to: str, subject: str, body: str) -> None: ...
