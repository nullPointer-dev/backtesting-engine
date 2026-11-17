"""add CANCELLED backtest status

Revision ID: b3c1e7a90f21
Revises: add_equity_curve_error_message
Create Date: 2026-11-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b3c1e7a90f21'
down_revision: Union[str, Sequence[str], None] = 'add_equity_curve_error_message'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE backtest_status ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres cannot drop a value from an enum type; move rows off it and
    # leave the label in place.
    op.execute("UPDATE backtests SET status = 'FAILED' WHERE status = 'CANCELLED'")
