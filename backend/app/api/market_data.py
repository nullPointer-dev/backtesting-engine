from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.enums.types import TimeFrame
from app.models.market_data import MarketData
from app.models.user import User

router = APIRouter(prefix="/market-data", tags=["market-data"])


class Candle(BaseModel):
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SymbolCoverage(BaseModel):
    timeframe: TimeFrame
    first: datetime
    last: datetime
    bars: int


class SymbolInfo(BaseModel):
    symbol: str
    timeframes: list[SymbolCoverage]


class SymbolsResponse(BaseModel):
    symbols: list[SymbolInfo]


class HistoryResponse(BaseModel):
    symbol: str
    timeframe: TimeFrame
    data: list[Candle]


class LatestResponse(Candle):
    symbol: str
    timeframe: TimeFrame


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.get("/symbols", response_model=SymbolsResponse)
def get_symbols(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every symbol with data, and the date range available for each timeframe."""
    rows = (
        db.query(
            MarketData.symbol,
            MarketData.timeframe,
            func.min(MarketData.datetime),
            func.max(MarketData.datetime),
            func.count(),
        )
        .group_by(MarketData.symbol, MarketData.timeframe)
        .order_by(MarketData.symbol)
        .all()
    )
    timeframe_order = {timeframe: index for index, timeframe in enumerate(TimeFrame)}
    grouped: dict[str, list[SymbolCoverage]] = {}
    for symbol, timeframe, first, last, bars in rows:
        grouped.setdefault(symbol, []).append(
            SymbolCoverage(timeframe=timeframe, first=first, last=last, bars=bars)
        )
    return SymbolsResponse(
        symbols=[
            SymbolInfo(symbol=symbol, timeframes=sorted(coverage, key=lambda c: timeframe_order[c.timeframe]))
            for symbol, coverage in grouped.items()
        ]
    )


@router.get("/{symbol}/history", response_model=HistoryResponse)
def get_symbol_history(
    symbol: str,
    timeframe: TimeFrame = Query(TimeFrame.ONE_DAY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Price bars in chronological order.

    With a start_date, returns up to `limit` bars from that date forward;
    otherwise returns the latest `limit` bars (up to end_date, if given).
    """
    symbol = symbol.upper()
    query = db.query(MarketData).filter(
        MarketData.symbol == symbol,
        MarketData.timeframe == timeframe,
    )
    if start_date is not None:
        query = query.filter(MarketData.datetime >= _as_utc(start_date))
    if end_date is not None:
        query = query.filter(MarketData.datetime <= _as_utc(end_date))

    if start_date is not None:
        rows = query.order_by(MarketData.datetime.asc()).limit(limit).all()
    else:
        rows = query.order_by(MarketData.datetime.desc()).limit(limit).all()[::-1]
    return HistoryResponse(
        symbol=symbol,
        timeframe=timeframe,
        data=[Candle.model_validate(row, from_attributes=True) for row in rows],
    )


@router.get("/{symbol}/latest", response_model=LatestResponse)
def get_latest_price(
    symbol: str,
    timeframe: TimeFrame = Query(TimeFrame.ONE_DAY),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    row = (
        db.query(MarketData)
        .filter(MarketData.symbol == symbol, MarketData.timeframe == timeframe)
        .order_by(MarketData.datetime.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for {symbol} {timeframe.value}",
        )
    return LatestResponse(
        symbol=symbol,
        timeframe=timeframe,
        datetime=row.datetime,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
    )
