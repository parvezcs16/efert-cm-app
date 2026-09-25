import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    EmployeeRole,
    EmployeeStatus,
    PasswordState,
    RegistrationStatus,
    StatementFrequency,
    enum_column,
)


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    p_no: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_state: Mapped[PasswordState] = mapped_column(
        enum_column(PasswordState, "password_state"),
        default=PasswordState.MUST_CHANGE,
        nullable=False,
    )

    status: Mapped[EmployeeStatus] = mapped_column(
        enum_column(EmployeeStatus, "employee_status"),
        default=EmployeeStatus.PENDING_ACTIVATION,
        nullable=False,
    )
    role: Mapped[EmployeeRole] = mapped_column(
        enum_column(EmployeeRole, "employee_role"),
        default=EmployeeRole.EMPLOYEE,
        nullable=False,
    )

    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    statement_frequency: Mapped[StatementFrequency] = mapped_column(
        enum_column(StatementFrequency, "statement_frequency"),
        default=StatementFrequency.MONTHLY,
        nullable=False,
    )
    # Drives the in-process statement scheduler (Phase 9): the next time
    # this employee is due a statement email. Advanced after each send.
    next_statement_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    registration: Mapped["EmployeeRegistration | None"] = relationship(
        back_populates="employee", uselist=False, foreign_keys="EmployeeRegistration.employee_id"
    )


class EmployeeRegistration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee_registrations"

    p_no: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))

    status: Mapped[RegistrationStatus] = mapped_column(
        enum_column(RegistrationStatus, "registration_status"),
        default=RegistrationStatus.PENDING,
        nullable=False,
    )

    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    employee: Mapped["Employee | None"] = relationship(
        back_populates="registration", foreign_keys=[employee_id]
    )

    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )
    decision_reason: Mapped[str | None] = mapped_column(String(500))
