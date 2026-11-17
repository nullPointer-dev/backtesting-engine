"""add equity_curve and error_message to backtest

Revision ID: add_equity_curve_error_message
Revises: d817e0a8aa2a
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_equity_curve_error_message'
down_revision: Union[str, Sequence[str], None] = 'd817e0a8aa2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtests', sa.Column('equity_curve', JSONB, nullable=True))
    op.add_column('backtests', sa.Column('error_message', sa.Text, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('backtests', 'equity_curve')
    op.drop_column('backtests', 'error_message')