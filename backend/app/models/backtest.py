from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Double
from sqlalchemy import ForeignKey
from sqlalchemy import Integer

from sqlalchemy.dialects.postgresql import ENUM

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.enums.backtest_status import BacktestStatus
from app.models.base import Base


class Backtest(Base):

    __tablename__ = "backtests"

    backtest_id: Mapped[int] = mapped_column(
        primary_key=True
    )

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
            name="backtest_status",
            create_type=False
        ),
        nullable=False
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    initial_capital: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    final_capital: Mapped[float | None] = mapped_column(
        Double
    )

    total_return: Mapped[float | None] = mapped_column(
        Double
    )

    sharpe_ratio: Mapped[float | None] = mapped_column(
        Double
    )

    max_drawdown: Mapped[float | None] = mapped_column(
        Double
    )

    win_rate: Mapped[float | None] = mapped_column(
        Double
    )

    profit_factor: Mapped[float | None] = mapped_column(
        Double
    )

    total_trades: Mapped[int | None] = mapped_column(
        Integer
    )

    strategy: Mapped[Strategy] = relationship(
        back_populates="backtests",
        lazy="selectin"
    )

    trades: Mapped[list[Trade]] = relationship(
        back_populates="backtest",
        cascade="all, delete-orphan",
        lazy="selectin"
    )