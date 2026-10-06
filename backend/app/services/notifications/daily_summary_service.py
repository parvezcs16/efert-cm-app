import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.consumption import ConsumptionRecord
from app.models.enums import InAppNotificationType
from app.models.guest import GuestSession
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem
from app.repositories.in_app_notification_repository import InAppNotificationRepository
from app.services.notifications.in_app_service import InAppNotificationService

logger = get_logger("notifications.daily_summary")


def business_timezone() -> timezone:
    return timezone(timedelta(minutes=get_settings().business_utc_offset_minutes))


def business_today(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(business_timezone()).date()


@dataclass
class _ServedTally:
    """What was served for one bucket (the employee's own orders, or their
    guests' orders) over the day. Quantities only -- prices are never shown
    to employees (CLAUDE.md principle 9)."""

    order_ids: set[uuid.UUID] = field(default_factory=set)
    items: Counter[str] = field(default_factory=Counter)

    @property
    def item_count(self) -> int:
        return sum(self.items.values())


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _describe(tally: _ServedTally) -> str:
    breakdown = ", ".join(f"{name} x{qty}" for name, qty in tally.items.most_common())
    return (
        f"{_plural(len(tally.order_ids), 'order')} "
        f"({_plural(tally.item_count, 'item')}: {breakdown})"
    )


class DailySummaryService:
    """Builds the end-of-day "what was served to you today" notification for
    every employee who had something served -- their own orders plus, kept
    separate, orders by guests they hosted. Based on ConsumptionRecord
    (actual served quantity, not ordered quantity -- CLAUDE.md "Served
    quantity ... determines consumption"). Invoked by
    app/workers/daily_summary_scheduler.py."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.inbox = InAppNotificationService(db)
        self.notifications = InAppNotificationRepository(db)

    async def send_for_day(self, day: date) -> int:
        """Idempotent per (employee, day): re-running only fills in
        employees who don't have that day's summary yet."""
        tz = business_timezone()
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = start + timedelta(days=1)

        result = await self.db.execute(
            select(
                Order.id,
                Order.employee_id,
                GuestSession.host_employee_id,
                MenuItem.name,
                ConsumptionRecord.served_quantity,
            )
            .join(OrderItem, ConsumptionRecord.order_item_id == OrderItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .outerjoin(GuestSession, Order.guest_session_id == GuestSession.id)
            .where(
                ConsumptionRecord.served_at >= start,
                ConsumptionRecord.served_at < end,
                ConsumptionRecord.served_quantity > 0,
            )
        )

        personal: dict[uuid.UUID, _ServedTally] = {}
        guests: dict[uuid.UUID, _ServedTally] = {}
        for order_id, employee_id, host_employee_id, item_name, quantity in result.all():
            if employee_id is not None:
                tally = personal.setdefault(employee_id, _ServedTally())
            elif host_employee_id is not None:
                tally = guests.setdefault(host_employee_id, _ServedTally())
            else:
                continue
            tally.order_ids.add(order_id)
            tally.items[item_name] += quantity

        recipients = set(personal) | set(guests)
        keys = {
            employee_id: f"daily-served:{employee_id}:{day.isoformat()}"
            for employee_id in recipients
        }
        already_sent = await self.notifications.existing_dedupe_keys(list(keys.values()))

        sent = 0
        for employee_id in recipients:
            if keys[employee_id] in already_sent:
                continue
            lines = []
            if employee_id in personal:
                lines.append(f"Served to you: {_describe(personal[employee_id])}.")
            if employee_id in guests:
                lines.append(f"Served to your guests: {_describe(guests[employee_id])}.")
            total_orders = len(personal.get(employee_id, _ServedTally()).order_ids) + len(
                guests.get(employee_id, _ServedTally()).order_ids
            )
            await self.inbox.notify(
                employee_id=employee_id,
                type=InAppNotificationType.DAILY_SERVED_SUMMARY,
                title=f"Today's summary: {_plural(total_orders, 'order')} served",
                body="\n".join(lines),
                link="/orders",
                dedupe_key=keys[employee_id],
            )
            sent += 1

        if sent:
            logger.info("Sent %d daily served summary notification(s) for %s", sent, day)
        return sent
