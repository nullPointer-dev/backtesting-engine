"""live progress fields on backtests

Revision ID: d4e8a2c6b1f3
Revises: c7d2f4a1e9b0
Create Date: 2026-11-17 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8a2c6b1f3'
down_revision: Union[str, Sequence[str], None] = 'c7d2f4a1e9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtests', sa.Column('progress_pct', sa.Double(), nullable=True))
    op.add_column('backtests', sa.Column('progress_stage', sa.String(32), nullable=True))
    op.add_column('backtests', sa.Column('progress_message', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for column in ('progress_message', 'progress_stage', 'progress_pct'):
        op.drop_column('backtests', column)
