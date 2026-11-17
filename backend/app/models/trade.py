from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import Double
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import ENUM

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.enums.types import PositionSide

if TYPE_CHECKING:
    from app.models.backtest import Backtest
from app.models.base import Base


class Trade(Base):

    __tablename__ = "trades"

    trade_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    backtest_id: Mapped[int] = mapped_column(
        ForeignKey(
            "backtests.backtest_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    symbol: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    side: Mapped[PositionSide] = mapped_column(
        ENUM(
            PositionSide,
            name="trade_side"
        ),
        nullable=False
    )

    entry_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    entry_price: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    exit_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    exit_price: Mapped[float | None] = mapped_column(
        Double
    )

    quantity: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    duration_bars: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    pnl: Mapped[float | None] = mapped_column(
        Double
    )

    commission: Mapped[float | None] = mapped_column(Double)

    return_pct: Mapped[float | None] = mapped_column(Double)

    mae_pct: Mapped[float | None] = mapped_column(Double)

    mfe_pct: Mapped[float | None] = mapped_column(Double)

    exit_reason: Mapped[str | None] = mapped_column(String(20))

    backtest: Mapped[Backtest] = relationship(
        back_populates="trades",
        lazy="selectin"
    )