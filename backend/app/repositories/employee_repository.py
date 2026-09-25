import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee, EmployeeRegistration
from app.models.enums import EmployeeRole, EmployeeStatus


class EmployeeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, employee_id: uuid.UUID) -> Employee | None:
        return await self.db.get(Employee, employee_id)

    async def get_by_p_no(self, p_no: str) -> Employee | None:
        result = await self.db.execute(select(Employee).where(Employee.p_no == p_no))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Employee | None:
        result = await self.db.execute(select(Employee).where(Employee.email == email))
        return result.scalar_one_or_none()

    async def search(
        self, *, q: str | None = None, roles: list[EmployeeRole] | None = None, limit: int = 50
    ) -> list[Employee]:
        """Directory lookup for admin screens (e.g. picking a location
        manager) -- matches p_no or name (case-insensitive, substring)."""
        query = select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
        if roles:
            query = query.where(Employee.role.in_(roles))
        if q:
            pattern = f"%{q}%"
            query = query.where(Employee.p_no.ilike(pattern) | Employee.name.ilike(pattern))
        query = query.order_by(Employee.name).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_due_for_statement(self, now: datetime) -> list[Employee]:
        result = await self.db.execute(
            select(Employee).where(
                Employee.status == EmployeeStatus.ACTIVE,
                Employee.next_statement_due_at.is_not(None),
                Employee.next_statement_due_at <= now,
            )
        )
        return list(result.scalars().all())

    def add(self, employee: Employee) -> None:
        self.db.add(employee)

    async def flush(self) -> None:
        await self.db.flush()


class EmployeeRegistrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, registration_id: uuid.UUID) -> EmployeeRegistration | None:
        return await self.db.get(EmployeeRegistration, registration_id)

    async def get_pending_by_p_no(self, p_no: str) -> EmployeeRegistration | None:
        result = await self.db.execute(
            select(EmployeeRegistration).where(
                EmployeeRegistration.p_no == p_no,
                EmployeeRegistration.status == "PENDING",
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self) -> list[EmployeeRegistration]:
        result = await self.db.execute(
            select(EmployeeRegistration)
            .where(EmployeeRegistration.status == "PENDING")
            .order_by(EmployeeRegistration.created_at)
        )
        return list(result.scalars().all())

    def add(self, registration: EmployeeRegistration) -> None:
        self.db.add(registration)

    async def flush(self) -> None:
        await self.db.flush()
