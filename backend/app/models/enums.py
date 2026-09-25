import enum

from sqlalchemy import Enum as SAEnum


def enum_column(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """A Postgres-native enum column type storing each member's `.value`."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class EmployeeRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    SERVER = "SERVER"
    KITCHEN_OPERATOR = "KITCHEN_OPERATOR"
    LOCATION_MANAGER = "LOCATION_MANAGER"
    SYSTEM_MANAGER = "SYSTEM_MANAGER"
    FINANCE_ADMIN = "FINANCE_ADMIN"
    SYSTEM_ADMINISTRATOR = "SYSTEM_ADMINISTRATOR"


class EmployeeStatus(str, enum.Enum):
    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class PasswordState(str, enum.Enum):
    MUST_CHANGE = "MUST_CHANGE"
    OK = "OK"


class RegistrationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class OtpPurpose(str, enum.Enum):
    ACTIVATION = "ACTIVATION"
    PASSWORD_RESET = "PASSWORD_RESET"
    LOGIN_STEP_UP = "LOGIN_STEP_UP"


class ActiveStatus(str, enum.Enum):
    """Shared simple lifecycle status for reference/catalog entities
    (locations, kitchen stations, menu categories/items) that don't need
    more than an on/off state."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OrderType(str, enum.Enum):
    DINE_IN = "DINE_IN"
    TAKEAWAY = "TAKEAWAY"
    BOOK_FOR_LATER = "BOOK_FOR_LATER"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"
    CANCELLED = "CANCELLED"


class CustomerType(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    GUEST = "GUEST"


class GuestType(str, enum.Enum):
    PRIVATE = "PRIVATE"
    OFFICIAL = "OFFICIAL"


class GuestSessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class IngredientStatus(str, enum.Enum):
    """Only meaningful for BOOK_FOR_LATER orders (null otherwise). Gates the
    PENDING -> CONFIRMED kitchen transition for booked orders specifically
    (see docs/kitchen.md "Booked Orders", docs/business-rules.md)."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DELAYED = "DELAYED"


class ConsumptionStatus(str, enum.Enum):
    VALIDATED = "VALIDATED"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"


class LedgerAccountType(str, enum.Enum):
    """Private guest charges post to the host's EMPLOYEE_PERSONAL account
    (tagged via LedgerEntry.source_type=PRIVATE_GUEST), not a separate
    account -- only employees and official-guest billing get their own
    account (docs/billing.md "Accounts")."""

    EMPLOYEE_PERSONAL = "EMPLOYEE_PERSONAL"
    OFFICIAL = "OFFICIAL"


class LedgerSourceType(str, enum.Enum):
    """A correction/adjustment entry keeps the SAME source_type as the
    charge it adjusts (identified instead by a non-null reversal_of_id) so
    that filtering a bill by source_type -- e.g. "personal bill" vs
    "private guest bill" (docs/billing.md) -- naturally includes its
    corrections instead of losing them into an undifferentiated bucket."""

    PERSONAL_CONSUMPTION = "PERSONAL_CONSUMPTION"
    PRIVATE_GUEST = "PRIVATE_GUEST"
    OFFICIAL_GUEST = "OFFICIAL_GUEST"


class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class StatementFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"


class ReviewType(str, enum.Enum):
    OVERALL = "OVERALL"
    ORDER = "ORDER"


class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"


class NotificationStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"
