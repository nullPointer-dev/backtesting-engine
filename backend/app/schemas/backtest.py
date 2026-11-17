from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.enums.types import BacktestStatus, PositionSizingType, TimeFrame


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

    @field_validator("start_date", "end_date")
    @classmethod
    def assume_utc(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def check_consistency(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.position_sizing_type == PositionSizingType.FIXED_QUANTITY and self.quantity is None:
            raise ValueError("quantity is required for FIXED_QUANTITY position sizing")
        if (
            self.position_sizing_type == PositionSizingType.PERCENT_OF_CAPITAL
            and self.position_size_percent is None
        ):
            raise ValueError("position_size_percent is required for PERCENT_OF_CAPITAL position sizing")
        return self


class BacktestSummary(BaseModel):
    """Lightweight view used in lists (no equity curve or traceback)."""

    model_config = ConfigDict(from_attributes=True)

    backtest_id: int
    strategy_id: int
    strategy_name: Optional[str] = None
    status: BacktestStatus
    created_at: datetime
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
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    total_trades: Optional[int]

    @model_validator(mode="before")
    @classmethod
    def add_strategy_name(cls, data):
        strategy = getattr(data, "strategy", None)
        if strategy is not None and not isinstance(data, dict):
            fields = {name: getattr(data, name, None) for name in cls.model_fields if name != "strategy_name"}
            fields["strategy_name"] = strategy.name
            return fields
        return data


class BacktestResponse(BacktestSummary):
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    recovery_factor: Optional[float]
    max_drawdown_duration: Optional[int]
    ulcer_index: Optional[float]
    loss_rate: Optional[float]
    max_consecutive_wins: Optional[int]
    max_consecutive_losses: Optional[int]
    avg_trade_duration: Optional[float]
    expectancy: Optional[float]
    equity_curve: Optional[list[float]]
    error_message: Optional[str]


class BacktestListResponse(BaseModel):
    backtests: list[BacktestSummary]
    total: int


class BacktestRunResponse(BaseModel):
    backtest_id: int
    status: BacktestStatus
    message: str


class BacktestStatusResponse(BaseModel):
    backtest_id: int
    status: BacktestStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class EquityCurveResponse(BaseModel):
    backtest_id: int
    initial_capital: float
    equity_curve: list[float]


class DrawdownResponse(BaseModel):
    backtest_id: int
    drawdown: list[float]
    max_drawdown: float


class PeriodReturn(BaseModel):
    period: str
    pnl: float
    return_pct: float


class ReturnsBreakdownResponse(BaseModel):
    backtest_id: int
    monthly_returns: list[PeriodReturn]
    yearly_returns: list[PeriodReturn]


class HistogramBucket(BaseModel):
    range: str
    count: int


class TradeAnalysisResponse(BaseModel):
    backtest_id: int
    win_loss_distribution: dict[str, int]
    pnl_distribution: list[HistogramBucket]
    duration_distribution: list[HistogramBucket]
    mae_mfe: dict[str, float]
    consecutive: dict[str, int]


class DashboardSummary(BaseModel):
    total_backtests: int
    completed_backtests: int
    running_backtests: int
    failed_backtests: int
    total_strategies: int
    best_return: Optional[float]
    worst_return: Optional[float]
    avg_return: Optional[float]
    recent_backtests: list[BacktestSummary]


class CompareRequest(BaseModel):
    backtest_ids: list[int] = Field(..., min_length=1, max_length=20)


class CompareResponse(BaseModel):
    comparison: list[BacktestResponse]
