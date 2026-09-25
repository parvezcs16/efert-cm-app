from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.exceptions import AppError

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped database session.

    Commits on clean exit. Also commits on a handled AppError (4xx): these
    represent expected business outcomes (e.g. a failed login) whose side
    effects -- a failed-attempt counter, an audit log entry -- must persist
    even though the request itself returns an error response. Only an
    unexpected exception rolls back, so a half-finished operation can't be
    partially committed. Individual services own the transaction boundaries
    for multi-step business operations.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except AppError:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
