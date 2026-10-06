"""in-app notifications

Revision ID: c3e8a1f45b20
Revises: b14cd2457e16
Create Date: 2026-10-05 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e8a1f45b20'
down_revision: Union[str, None] = 'b14cd2457e16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('in_app_notifications',
    sa.Column('employee_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.Enum('DAILY_SERVED_SUMMARY', 'GUEST_REOPEN_REQUEST', name='in_app_notification_type'), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.String(length=2000), nullable=False),
    sa.Column('link', sa.String(length=300), nullable=True),
    sa.Column('dedupe_key', sa.String(length=200), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dedupe_key')
    )
    op.create_index('ix_in_app_notifications_employee_created', 'in_app_notifications', ['employee_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_in_app_notifications_employee_created', table_name='in_app_notifications')
    op.drop_table('in_app_notifications')
    sa.Enum(name='in_app_notification_type').drop(op.get_bind(), checkfirst=True)
