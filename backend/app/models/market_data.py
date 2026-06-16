from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum
from sqlalchemy import Double
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.enums.timeframe import TimeFrame
from app.models.base import Base


class MarketData(Base):

    __tablename__ = "market_data"

    market_data_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    symbol: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    timeframe: Mapped[TimeFrame] = mapped_column(
        Enum(
            TimeFrame,
            values_callable=lambda x: [e.value for e in x],
            name="timeframe_type",
            create_type=False
        ),
        nullable=False
    )

    datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    open: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    high: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    low: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    close: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    volume: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )