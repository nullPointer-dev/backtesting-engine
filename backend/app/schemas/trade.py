from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.enums.types import PositionSide


class TradeResponse(BaseModel):
    trade_id: int
    backtest_id: int
    symbol: str
    side: PositionSide
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    exit_reason: Optional[str] = None
    quantity: float
    duration_bars: int
    pnl: float
    commission: Optional[float] = None
    return_pct: Optional[float] = None
    mae_pct: Optional[float] = None
    mfe_pct: Optional[float] = None

    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int