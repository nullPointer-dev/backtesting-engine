from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

from app.enums.types import (
    BacktestStatus,
    PositionSizingType,
    TimeFrame,
)


class BacktestCreate(BaseModel):
    strategy_id: int
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(..., gt=0)
    symbol: str = Field(..., min_length=1, max_length=30)
    timeframe: TimeFrame
    position_sizing_type: PositionSizingType
    quantity: Optional[float] = Field(None, gt=0)
    position_size_percent: Optional[float] = Field(None, gt=0, le=100)


class BacktestResponse(BaseModel):
    backtest_id: int
    strategy_id: int
    status: BacktestStatus
    start_date: datetime
    end_date: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    initial_capital: float
    symbol: str
    timeframe: TimeFrame
    position_sizing_type: PositionSizingType
    quantity: Optional[float]
    position_size_percent: Optional[float]
    final_capital: Optional[float]
    total_return: Optional[float]
    net_profit: Optional[float]
    cagr: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    recovery_factor: Optional[float]
    max_drawdown: Optional[float]
    max_drawdown_duration: Optional[int]
    ulcer_index: Optional[float]
    win_rate: Optional[float]
    loss_rate: Optional[float]
    max_consecutive_wins: Optional[int]
    max_consecutive_losses: Optional[int]
    avg_trade_duration: Optional[float]
    profit_factor: Optional[float]
    total_trades: Optional[int]
    expectancy: Optional[float]
    equity_curve: Optional[list[float]]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class BacktestListResponse(BaseModel):
    backtests: list[BacktestResponse]
    total: int


class BacktestRunResponse(BaseModel):
    backtest_id: int
    status: BacktestStatus
    message: str