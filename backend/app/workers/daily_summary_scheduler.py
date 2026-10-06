import asyncio
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.services.notifications.daily_summary_service import (
    DailySummaryService,
    business_timezone,
)

logger = get_logger("workers.daily_summary_scheduler")

CHECK_INTERVAL_SECONDS = 600


async def run_daily_summary_scheduler() -> None:
    """Once local time passes `daily_summary_hour`, posts each employee's
    "served today" summary to their in-app inbox. Checks every few minutes
    rather than sleeping until the exact hour, so a restart after the hour
    still catches up; DailySummaryService is idempotent per employee/day, so
    repeat checks are harmless. Same single-process caveat and
    cancel-on-shutdown lifecycle as app/workers/statement_scheduler.py."""
    while True:
        try:
            local_now = datetime.now(UTC).astimezone(business_timezone())
            if local_now.hour >= get_settings().daily_summary_hour:
                async with AsyncSessionLocal() as db:
                    await DailySummaryService(db).send_for_day(local_now.date())
                    await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Daily summary scheduler iteration failed")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
