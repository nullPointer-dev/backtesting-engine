"""initial migration

Creates the original schema (users, strategies, backtests, trades, market_data).
Columns added later (backtests.created_at, equity_curve, error_message) come
from the follow-up revisions.

Revision ID: 426b09fbb703
Revises:
Create Date: 2026-08-19 17:36:42.425603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '426b09fbb703'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


backtest_status = postgresql.ENUM(
    'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='backtest_status', create_type=False
)
timeframe_type = postgresql.ENUM(
    '1m', '5m', '15m', '30m', '60m', '1d', '1wk', name='timeframe_type', create_type=False
)
position_sizing_type = postgresql.ENUM(
    'FIXED_QUANTITY', 'PERCENT_OF_CAPITAL', name='position_sizing_type', create_type=False
)
trade_side = postgresql.ENUM('LONG', 'SHORT', name='trade_side', create_type=False)

ENUMS = (backtest_status, timeframe_type, position_sizing_type, trade_side)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'strategies',
        sa.Column('strategy_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('strategy_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'backtests',
        sa.Column('backtest_id', sa.Integer(), primary_key=True),
        sa.Column('strategy_id', sa.Integer(), sa.ForeignKey('strategies.strategy_id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', backtest_status, nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('initial_capital', sa.Double(), nullable=False),
        sa.Column('symbol', sa.String(30), nullable=False),
        sa.Column('timeframe', timeframe_type, nullable=False),
        sa.Column('position_sizing_type', position_sizing_type, nullable=False),
        sa.Column('quantity', sa.Double()),
        sa.Column('position_size_percent', sa.Double()),
        sa.Column('final_capital', sa.Double()),
        sa.Column('total_return', sa.Double()),
        sa.Column('net_profit', sa.Double()),
        sa.Column('cagr', sa.Double()),
        sa.Column('sharpe_ratio', sa.Double()),
        sa.Column('sortino_ratio', sa.Double()),
        sa.Column('calmar_ratio', sa.Double()),
        sa.Column('recovery_factor', sa.Double()),
        sa.Column('max_drawdown', sa.Double()),
        sa.Column('max_drawdown_duration', sa.Integer()),
        sa.Column('ulcer_index', sa.Double()),
        sa.Column('win_rate', sa.Double()),
        sa.Column('loss_rate', sa.Double()),
        sa.Column('max_consecutive_wins', sa.Integer()),
        sa.Column('max_consecutive_losses', sa.Integer()),
        sa.Column('avg_trade_duration', sa.Double()),
        sa.Column('profit_factor', sa.Double()),
        sa.Column('total_trades', sa.Integer()),
        sa.Column('expectancy', sa.Double()),
    )

    op.create_table(
        'trades',
        sa.Column('trade_id', sa.Integer(), primary_key=True),
        sa.Column('backtest_id', sa.Integer(), sa.ForeignKey('backtests.backtest_id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(30), nullable=False),
        sa.Column('side', trade_side, nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_price', sa.Double(), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True)),
        sa.Column('exit_price', sa.Double()),
        sa.Column('quantity', sa.Double(), nullable=False),
        sa.Column('duration_bars', sa.Integer(), nullable=False),
        sa.Column('pnl', sa.Double()),
    )

    op.create_table(
        'market_data',
        sa.Column('market_data_id', sa.Integer(), primary_key=True),
        sa.Column('symbol', sa.String(30), nullable=False),
        sa.Column('timeframe', timeframe_type, nullable=False),
        sa.Column('datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Double(), nullable=False),
        sa.Column('high', sa.Double(), nullable=False),
        sa.Column('low', sa.Double(), nullable=False),
        sa.Column('close', sa.Double(), nullable=False),
        sa.Column('volume', sa.Double(), nullable=False),
        sa.UniqueConstraint('symbol', 'timeframe', 'datetime', name='unique_market_data'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('market_data')
    op.drop_table('trades')
    op.drop_table('backtests')
    op.drop_table('strategies')
    op.drop_table('users')
    bind = op.get_bind()
    for enum in reversed(ENUMS):
        enum.drop(bind, checkfirst=True)
