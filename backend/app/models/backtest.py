from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import Double
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.enums.types import BacktestStatus
from app.enums.types import PositionSizingType, TimeFrame
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.strategy import Strategy
    from app.models.trade import Trade


class Backtest(Base):

    __tablename__ = "backtests"

    backtest_id: Mapped[int] = mapped_column(primary_key=True)

    strategy_id: Mapped[int] = mapped_column(
        ForeignKey(
            "strategies.strategy_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    status: Mapped[BacktestStatus] = mapped_column(
        ENUM(
            BacktestStatus,
            name="backtest_status"
        ),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    initial_capital: Mapped[float] = mapped_column(Double, nullable=False)

    symbol: Mapped[str] = mapped_column(String(30), nullable=False)

    timeframe: Mapped[TimeFrame] = mapped_column(
        ENUM(
            TimeFrame,
            values_callable=lambda x: [e.value for e in x],
            name="timeframe_type"
        ),
        nullable=False
    )

    position_sizing_type: Mapped[
        PositionSizingType
    ] = mapped_column(
        ENUM(
            PositionSizingType,
            name="position_sizing_type"
        ),
        nullable=False
    )

    quantity: Mapped[float | None] = mapped_column(Double)

    position_size_percent: Mapped[float | None] = mapped_column(Double)

    commission_pct: Mapped[float] = mapped_column(Double, nullable=False, default=0.0, server_default="0")

    slippage_pct: Mapped[float] = mapped_column(Double, nullable=False, default=0.0, server_default="0")

    final_capital: Mapped[float | None] = mapped_column(Double)

    total_return: Mapped[float | None] = mapped_column(Double)

    net_profit: Mapped[float | None] = mapped_column(Double)

    cagr: Mapped[float | None] = mapped_column(Double)

    sharpe_ratio: Mapped[float | None] = mapped_column(Double)

    sortino_ratio: Mapped[float | None] = mapped_column(Double)

    calmar_ratio: Mapped[float | None] = mapped_column(Double)

    recovery_factor: Mapped[float | None] = mapped_column(Double)

    max_drawdown: Mapped[float | None] = mapped_column(Double)

    max_drawdown_duration: Mapped[int | None] = mapped_column(Integer)

    ulcer_index: Mapped[float | None] = mapped_column(Double)

    win_rate: Mapped[float | None] = mapped_column(Double)

    loss_rate: Mapped[float | None] = mapped_column(Double)

    max_consecutive_wins: Mapped[int | None] = mapped_column(Integer)

    max_consecutive_losses: Mapped[int | None] = mapped_column(Integer)

    avg_trade_duration: Mapped[float | None] = mapped_column(Double)

    profit_factor: Mapped[float | None] = mapped_column(Double)

    total_trades: Mapped[int | None] = mapped_column(Integer)

    expectancy: Mapped[float | None] = mapped_column(Double)

    total_commission: Mapped[float | None] = mapped_column(Double)

    exposure_pct: Mapped[float | None] = mapped_column(Double)

    skipped_trades: Mapped[int | None] = mapped_column(Integer)

    # List of {"time": ISO-8601, "equity": float}, one per bar. Backtests run
    # before per-bar equity was introduced hold a plain list of floats.
    equity_curve: Mapped[list | None] = mapped_column(JSONB)

    error_message: Mapped[str | None] = mapped_column(Text)

    # Live progress while RUNNING: 0-100, a short stage key and a log line.
    progress_pct: Mapped[float | None] = mapped_column(Double)

    progress_stage: Mapped[str | None] = mapped_column(String(32))

    progress_message: Mapped[str | None] = mapped_column(Text)

    strategy: Mapped[Strategy] = relationship(
        back_populates="backtests",
        lazy="selectin"
    )

    trades: Mapped[list[Trade]] = relationship(
        back_populates="backtest",
        cascade="all, delete-orphan",
        lazy="selectin"
    )