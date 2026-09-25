import asyncio

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.services.billing.statement_service import StatementService

logger = get_logger("workers.statement_scheduler")

CHECK_INTERVAL_SECONDS = 3600


async def run_statement_scheduler() -> None:
    """In-process periodic loop that emails every employee currently due a
    statement (Employee.next_statement_due_at <= now). Single-process only
    -- like the kitchen WebSocket manager, this would double-send under
    multiple worker processes without a shared lock/queue, which this app
    doesn't have. Started as an asyncio task from app.main's lifespan and
    cancelled on shutdown (task.cancel(), not a shared flag, so repeated
    app startups within one process -- e.g. across tests -- each get a
    clean loop)."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await StatementService(db).send_due_statements()
                await db.commit()
                if count:
                    logger.info("Sent %d due statement(s)", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Statement scheduler iteration failed")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
