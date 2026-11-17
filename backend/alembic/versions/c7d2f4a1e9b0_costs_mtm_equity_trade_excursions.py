"""commission/slippage settings, cost and exposure results, trade excursions

Revision ID: c7d2f4a1e9b0
Revises: b3c1e7a90f21
Create Date: 2026-11-17 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d2f4a1e9b0'
down_revision: Union[str, Sequence[str], None] = 'b3c1e7a90f21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtests', sa.Column('commission_pct', sa.Double(), nullable=False, server_default='0'))
    op.add_column('backtests', sa.Column('slippage_pct', sa.Double(), nullable=False, server_default='0'))
    op.add_column('backtests', sa.Column('total_commission', sa.Double(), nullable=True))
    op.add_column('backtests', sa.Column('exposure_pct', sa.Double(), nullable=True))
    op.add_column('backtests', sa.Column('skipped_trades', sa.Integer(), nullable=True))

    op.add_column('trades', sa.Column('commission', sa.Double(), nullable=True))
    op.add_column('trades', sa.Column('return_pct', sa.Double(), nullable=True))
    op.add_column('trades', sa.Column('mae_pct', sa.Double(), nullable=True))
    op.add_column('trades', sa.Column('mfe_pct', sa.Double(), nullable=True))
    op.add_column('trades', sa.Column('exit_reason', sa.String(20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for column in ('exit_reason', 'mfe_pct', 'mae_pct', 'return_pct', 'commission'):
        op.drop_column('trades', column)
    for column in ('skipped_trades', 'exposure_pct', 'total_commission', 'slippage_pct', 'commission_pct'):
        op.drop_column('backtests', column)
