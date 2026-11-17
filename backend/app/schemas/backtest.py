from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.backtesting.errors import summarize_error
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
    commission_pct: float = Field(0.0, ge=0, le=10, description="Commission per side, % of traded value")
    slippage_pct: float = Field(0.0, ge=0, le=10, description="Price slippage per fill, %")

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


class EquityPoint(BaseModel):
    time: Optional[datetime] = None
    equity: Optional[float]


def normalize_equity_curve(raw) -> list[EquityPoint]:
    """Accept both the per-bar format and the legacy list of floats."""
    points = []
    for item in raw or []:
        if isinstance(item, dict):
            points.append(EquityPoint(time=item.get("time"), equity=item.get("equity")))
        else:
            points.append(EquityPoint(time=None, equity=item))
    return points


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
    commission_pct: float = 0.0
    slippage_pct: float = 0.0
    final_capital: Optional[float]
    total_return: Optional[float]
    net_profit: Optional[float]
    cagr: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    total_trades: Optional[int]
    progress_pct: Optional[float] = None
    progress_stage: Optional[str] = None
    error_summary: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def add_derived_fields(cls, data):
        """From an ORM row: add the strategy name and a one-line error summary."""
        if isinstance(data, dict):
            return data
        derived = {"strategy_name", "error_summary"}
        fields = {name: getattr(data, name, None) for name in cls.model_fields if name not in derived}
        strategy = getattr(data, "strategy", None)
        fields["strategy_name"] = strategy.name if strategy is not None else None
        fields["error_summary"] = summarize_error(getattr(data, "error_message", None))
        return fields


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
    total_commission: Optional[float] = None
    exposure_pct: Optional[float] = None
    skipped_trades: Optional[int] = None
    equity_curve: list[EquityPoint] = []
    error_message: Optional[str]

    @field_validator("equity_curve", mode="before")
    @classmethod
    def parse_equity_curve(cls, value):
        return normalize_equity_curve(value)


class BacktestListResponse(BaseModel):
    backtests: list[BacktestSummary]
    total: int
    # Backtests per status for the same strategy filter, ignoring the status filter.
    status_counts: dict[str, int] = {}


class BacktestRunResponse(BaseModel):
    backtest_id: int
    status: BacktestStatus
    message: str


class BacktestStatusResponse(BaseModel):
    backtest_id: int
    status: BacktestStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_pct: Optional[float] = None
    progress_stage: Optional[str] = None
    progress_message: Optional[str] = None
    error_message: Optional[str]
    error_summary: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def add_error_summary(cls, data):
        if isinstance(data, dict):
            return data
        fields = {name: getattr(data, name, None) for name in cls.model_fields if name != "error_summary"}
        fields["error_summary"] = summarize_error(fields.get("error_message"))
        return fields


class EquityCurveResponse(BaseModel):
    backtest_id: int
    initial_capital: float
    equity_curve: list[EquityPoint]


class DrawdownPoint(BaseModel):
    time: Optional[datetime] = None
    drawdown: float


class DrawdownResponse(BaseModel):
    backtest_id: int
    drawdown: list[DrawdownPoint]
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
    pending_backtests: int = 0
    cancelled_backtests: int = 0
    total_strategies: int
    best_return: Optional[float]
    worst_return: Optional[float]
    avg_return: Optional[float]
    recent_backtests: list[BacktestSummary]


class CompareRequest(BaseModel):
    backtest_ids: list[int] = Field(..., min_length=1, max_length=20)


class CompareResponse(BaseModel):
    comparison: list[BacktestResponse]
