import asyncio
import os
import re
from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.employee import Employee
from app.models.enums import EmployeeRole, EmployeeStatus, PasswordState
from app.models.review import DEFAULT_REVIEW_CATEGORIES, ReviewCategory
from app.services.notifications import get_notification_sender

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://mess:mess@localhost:5432/mess_test"
)

# NullPool: connections must not be reused across the different event loops
# that pytest-asyncio spins up per test function, or asyncpg breaks.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    async def _reset() -> None:
        setup_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with setup_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        setup_session = async_sessionmaker(bind=setup_engine, expire_on_commit=False)
        async with setup_session() as session:
            for name in DEFAULT_REVIEW_CATEGORIES:
                session.add(ReviewCategory(location_id=None, name=name, is_manager_defined=False))
            await session.commit()

        await setup_engine.dispose()

    asyncio.run(_reset())


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncGenerator[None, None]:
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == "review_categories":
                # Keep the seeded global defaults (location_id IS NULL);
                # only clear per-test, location-specific ones -- otherwise
                # the locations cleanup below would hit a FK violation from
                # a test-created category still referencing that location.
                await conn.execute(table.delete().where(table.c.location_id.is_not(None)))
                continue
            await conn.execute(table.delete())


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
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

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Captures emails sent via the (process-wide) notification singleton so
    tests can pull OTP codes out of them instead of reading the DB, which
    only ever stores a hash."""
    sent: list[dict[str, str]] = []

    async def _fake_send_email(*, to: str, subject: str, body: str) -> None:
        sent.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr(get_notification_sender(), "send_email", _fake_send_email)
    return sent


def extract_otp(body: str) -> str:
    match = re.search(r"\b(\d{6})\b", body)
    assert match, f"No 6-digit OTP found in: {body!r}"
    return match.group(1)


SeedEmployee = Callable[..., Awaitable[tuple[Employee, str]]]


@pytest.fixture
def seed_active_employee() -> SeedEmployee:
    """Directly inserts an ACTIVE employee with a known password, bypassing
    the registration/activation flow, for tests that need an authenticated
    actor (e.g. an admin approving someone else's registration)."""

    async def _seed(
        *,
        p_no: str,
        email: str,
        name: str = "Test Employee",
        role: EmployeeRole = EmployeeRole.EMPLOYEE,
        password: str = "Passw0rd1",
    ) -> tuple[Employee, str]:
        async with TestSessionLocal() as session:
            employee = Employee(
                p_no=p_no,
                name=name,
                email=email,
                department=None,
                password_hash=hash_password(password),
                password_state=PasswordState.OK,
                status=EmployeeStatus.ACTIVE,
                role=role,
            )
            session.add(employee)
            await session.commit()
            await session.refresh(employee)
            return employee, password

    return _seed
