import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.backtesting.job_queue import submit_backtest
from app.core.database import get_db
from app.enums.types import BacktestStatus
from app.models.backtest import Backtest
from app.models.market_data import MarketData
from app.models.strategy import Strategy
from app.models.trade import Trade
from app.models.user import User
from app.schemas.backtest import (
    BacktestCreate,
    BacktestListResponse,
    BacktestResponse,
    BacktestRunResponse,
    BacktestStatusResponse,
    CompareRequest,
    CompareResponse,
    DashboardSummary,
    DrawdownPoint,
    DrawdownResponse,
    EquityCurveResponse,
    normalize_equity_curve,
    HistogramBucket,
    PeriodReturn,
    ReturnsBreakdownResponse,
    TradeAnalysisResponse,
)
from app.schemas.trade import TradeListResponse

router = APIRouter(prefix="/backtests", tags=["backtests"])

RUNNABLE_STATUSES = {BacktestStatus.PENDING, BacktestStatus.FAILED, BacktestStatus.CANCELLED}


def _user_backtests(db: Session, user: User):
    return db.query(Backtest).join(Strategy).filter(Strategy.user_id == user.user_id)


def _get_owned_backtest(db: Session, user: User, backtest_id: int) -> Backtest:
    backtest = _user_backtests(db, user).filter(Backtest.backtest_id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")
    return backtest


def _closed_trades(db: Session, backtest_id: int) -> list[Trade]:
    return (
        db.query(Trade)
        .filter(Trade.backtest_id == backtest_id, Trade.exit_time.isnot(None))
        .order_by(Trade.exit_time.asc(), Trade.trade_id.asc())
        .all()
    )


def _histogram(values: list[float], bins: int, integer: bool = False) -> list[HistogramBucket]:
    counts, edges = np.histogram(np.asarray(values, dtype=float), bins=bins)
    fmt = (lambda x: f"{int(round(x))}") if integer else (lambda x: f"{x:.2f}")
    return [
        HistogramBucket(range=f"{fmt(edges[i])} to {fmt(edges[i + 1])}", count=int(counts[i]))
        for i in range(len(counts))
    ]


def _period_returns_from_equity(points, initial_capital: float, fmt: str) -> list[PeriodReturn]:
    """Return per calendar period, measured from the equity at the previous period's end."""
    period_end: dict[str, float] = {}
    for point in points:
        period_end[point.time.strftime(fmt)] = point.equity

    periods = []
    previous = initial_capital
    for period, equity in period_end.items():
        pnl = equity - previous
        return_pct = (pnl / previous) * 100 if previous > 0 else 0.0
        periods.append(PeriodReturn(period=period, pnl=pnl, return_pct=return_pct))
        previous = equity
    return periods


def _average_excursions(trades: list[Trade]) -> dict[str, float]:
    mae = [t.mae_pct for t in trades if t.mae_pct is not None]
    mfe = [t.mfe_pct for t in trades if t.mfe_pct is not None]
    return {
        "avg_mae": float(np.mean(mae)) if mae else 0.0,
        "avg_mfe": float(np.mean(mfe)) if mfe else 0.0,
    }


# --------------------------------------------------------------------------
# Collection routes
# --------------------------------------------------------------------------

@router.post("", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
def create_backtest(
    backtest_in: BacktestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == backtest_in.strategy_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    has_data = db.query(MarketData.market_data_id).filter(
        MarketData.symbol == backtest_in.symbol,
        MarketData.timeframe == backtest_in.timeframe,
        MarketData.datetime >= backtest_in.start_date,
        MarketData.datetime <= backtest_in.end_date,
    ).first()
    if not has_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No market data for {backtest_in.symbol} ({backtest_in.timeframe.value}) "
                "in the selected date range"
            ),
        )

    backtest = Backtest(
        **backtest_in.model_dump(),
        status=BacktestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db.add(backtest)
    db.commit()
    db.refresh(backtest)
    return backtest


@router.get("", response_model=BacktestListResponse)
def list_backtests(
    strategy_id: Optional[int] = Query(None),
    status_filter: Optional[BacktestStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = _user_backtests(db, current_user)
    if strategy_id is not None:
        query = query.filter(Backtest.strategy_id == strategy_id)
    status_counts = {
        status.value: count
        for status, count in query.with_entities(Backtest.status, func.count()).group_by(Backtest.status)
    }
    if status_filter is not None:
        query = query.filter(Backtest.status == status_filter)
    total = query.count()
    backtests = query.order_by(Backtest.created_at.desc()).offset(skip).limit(limit).all()
    return BacktestListResponse(
        backtests=backtests,
        total=total,
        status_counts={status.value: status_counts.get(status.value, 0) for status in BacktestStatus},
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    counts = dict(
        _user_backtests(db, current_user)
        .with_entities(Backtest.status, func.count())
        .group_by(Backtest.status)
        .all()
    )
    best, worst, average = (
        _user_backtests(db, current_user)
        .filter(Backtest.status == BacktestStatus.COMPLETED)
        .with_entities(
            func.max(Backtest.total_return),
            func.min(Backtest.total_return),
            func.avg(Backtest.total_return),
        )
        .one()
    )
    total_strategies = db.query(Strategy).filter(Strategy.user_id == current_user.user_id).count()
    recent = _user_backtests(db, current_user).order_by(Backtest.created_at.desc()).limit(5).all()

    return DashboardSummary(
        total_backtests=sum(counts.values()),
        completed_backtests=counts.get(BacktestStatus.COMPLETED, 0),
        running_backtests=counts.get(BacktestStatus.RUNNING, 0),
        failed_backtests=counts.get(BacktestStatus.FAILED, 0),
        pending_backtests=counts.get(BacktestStatus.PENDING, 0),
        cancelled_backtests=counts.get(BacktestStatus.CANCELLED, 0),
        total_strategies=total_strategies,
        best_return=float(best) if best is not None else None,
        worst_return=float(worst) if worst is not None else None,
        avg_return=float(average) if average is not None else None,
        recent_backtests=recent,
    )


@router.post("/compare", response_model=CompareResponse)
def compare_backtests(
    request: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtests = _user_backtests(db, current_user).filter(
        Backtest.backtest_id.in_(request.backtest_ids),
        Backtest.status == BacktestStatus.COMPLETED,
    ).all()
    if not backtests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed backtests found for comparison",
        )
    order = {backtest_id: index for index, backtest_id in enumerate(request.backtest_ids)}
    backtests.sort(key=lambda bt: order[bt.backtest_id])
    return CompareResponse(comparison=backtests)


# --------------------------------------------------------------------------
# Single-backtest routes
# --------------------------------------------------------------------------

@router.get("/{backtest_id}", response_model=BacktestResponse)
def get_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_backtest(db, current_user, backtest_id)


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    if backtest.status == BacktestStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running backtest; cancel it first",
        )
    db.delete(backtest)
    db.commit()
    return None


@router.post("/{backtest_id}/run", response_model=BacktestRunResponse)
def run_backtest(
    backtest_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    if backtest.status == BacktestStatus.RUNNING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backtest already running")
    if backtest.status not in RUNNABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest already completed. Create a new backtest to run again.",
        )

    backtest.status = BacktestStatus.RUNNING
    backtest.started_at = datetime.now(timezone.utc)
    backtest.completed_at = None
    backtest.error_message = None
    backtest.progress_pct = 0.0
    backtest.progress_stage = "queued"
    backtest.progress_message = "queued for a worker"
    db.commit()

    submit_backtest(backtest_id, background_tasks)

    return BacktestRunResponse(
        backtest_id=backtest_id,
        status=BacktestStatus.RUNNING,
        message="Backtest started in background",
    )


@router.post("/{backtest_id}/cancel", response_model=BacktestStatusResponse)
def cancel_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    if backtest.status not in (BacktestStatus.RUNNING, BacktestStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or running backtests can be cancelled",
        )
    backtest.status = BacktestStatus.CANCELLED
    backtest.error_message = "Cancelled by user"
    backtest.progress_stage = "cancelled"
    backtest.progress_message = "cancelled by user; nothing was saved"
    backtest.completed_at = datetime.now(timezone.utc)
    db.commit()
    return backtest


@router.get("/{backtest_id}/status", response_model=BacktestStatusResponse)
def get_backtest_status(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_backtest(db, current_user, backtest_id)


@router.get("/{backtest_id}/trades", response_model=TradeListResponse)
def get_backtest_trades(
    backtest_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_backtest(db, current_user, backtest_id)
    query = db.query(Trade).filter(Trade.backtest_id == backtest_id)
    total = query.count()
    trades = query.order_by(Trade.entry_time.asc(), Trade.trade_id.asc()).offset(skip).limit(limit).all()
    return TradeListResponse(trades=trades, total=total)


@router.get("/{backtest_id}/equity-curve", response_model=EquityCurveResponse)
def get_equity_curve(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    return EquityCurveResponse(
        backtest_id=backtest_id,
        initial_capital=backtest.initial_capital,
        equity_curve=normalize_equity_curve(backtest.equity_curve),
    )


@router.get("/{backtest_id}/drawdown", response_model=DrawdownResponse)
def get_drawdown(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    points = [p for p in normalize_equity_curve(backtest.equity_curve) if p.equity is not None]
    if not points:
        return DrawdownResponse(backtest_id=backtest_id, drawdown=[], max_drawdown=0.0)

    equity = np.asarray([p.equity for p in points], dtype=float)
    running_max = np.maximum.accumulate(np.maximum(equity, backtest.initial_capital))
    drawdowns = np.where(running_max > 0, (equity - running_max) / running_max * 100, 0.0)
    return DrawdownResponse(
        backtest_id=backtest_id,
        drawdown=[DrawdownPoint(time=p.time, drawdown=float(d)) for p, d in zip(points, drawdowns)],
        max_drawdown=float(drawdowns.min()),
    )


@router.get("/{backtest_id}/returns-breakdown", response_model=ReturnsBreakdownResponse)
def get_returns_breakdown(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    points = [
        p for p in normalize_equity_curve(backtest.equity_curve)
        if p.time is not None and p.equity is not None
    ]
    if points:
        return ReturnsBreakdownResponse(
            backtest_id=backtest_id,
            monthly_returns=_period_returns_from_equity(points, backtest.initial_capital, "%Y-%m"),
            yearly_returns=_period_returns_from_equity(points, backtest.initial_capital, "%Y"),
        )

    # Legacy backtests without timestamped equity: approximate from closed trades.
    trades = _closed_trades(db, backtest_id)

    monthly = defaultdict(float)
    yearly = defaultdict(float)
    for trade in trades:
        monthly[trade.exit_time.strftime("%Y-%m")] += trade.pnl or 0.0
        yearly[trade.exit_time.strftime("%Y")] += trade.pnl or 0.0

    def to_periods(totals: dict[str, float]) -> list[PeriodReturn]:
        # Each period's return is measured against the capital at its start.
        periods = []
        capital = backtest.initial_capital
        for period, pnl in sorted(totals.items()):
            return_pct = (pnl / capital) * 100 if capital else 0.0
            periods.append(PeriodReturn(period=period, pnl=pnl, return_pct=return_pct))
            capital += pnl
        return periods

    return ReturnsBreakdownResponse(
        backtest_id=backtest_id,
        monthly_returns=to_periods(monthly),
        yearly_returns=to_periods(yearly),
    )


@router.get("/{backtest_id}/trade-analysis", response_model=TradeAnalysisResponse)
def get_trade_analysis(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_backtest(db, current_user, backtest_id)
    trades = _closed_trades(db, backtest_id)
    if not trades:
        return TradeAnalysisResponse(
            backtest_id=backtest_id,
            win_loss_distribution={"wins": 0, "losses": 0, "breakeven": 0},
            pnl_distribution=[],
            duration_distribution=[],
            mae_mfe={"avg_mae": 0.0, "avg_mfe": 0.0},
            consecutive={"max_wins": 0, "max_losses": 0},
        )

    pnls = [trade.pnl or 0.0 for trade in trades]
    wins = sum(1 for pnl in pnls if pnl > 0)
    losses = sum(1 for pnl in pnls if pnl < 0)

    max_wins = max_losses = current_wins = current_losses = 0
    for pnl in pnls:
        if pnl > 0:
            current_wins, current_losses = current_wins + 1, 0
        elif pnl < 0:
            current_wins, current_losses = 0, current_losses + 1
        else:
            current_wins = current_losses = 0
        max_wins = max(max_wins, current_wins)
        max_losses = max(max_losses, current_losses)

    return TradeAnalysisResponse(
        backtest_id=backtest_id,
        win_loss_distribution={"wins": wins, "losses": losses, "breakeven": len(pnls) - wins - losses},
        pnl_distribution=_histogram(pnls, bins=min(20, max(1, len(pnls)))),
        duration_distribution=_histogram(
            [trade.duration_bars for trade in trades], bins=min(20, max(1, len(trades))), integer=True
        ),
        mae_mfe=_average_excursions(trades),
        consecutive={"max_wins": max_wins, "max_losses": max_losses},
    )


@router.get("/{backtest_id}/export")
def export_backtest(
    backtest_id: int,
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = _get_owned_backtest(db, current_user, backtest_id)
    trades = (
        db.query(Trade)
        .filter(Trade.backtest_id == backtest_id)
        .order_by(Trade.entry_time.asc(), Trade.trade_id.asc())
        .all()
    )

    trade_columns = [
        "trade_id", "symbol", "side", "entry_time", "entry_price",
        "exit_time", "exit_price", "exit_reason", "quantity", "duration_bars",
        "pnl", "commission", "return_pct", "mae_pct", "mfe_pct",
    ]

    def trade_row(trade: Trade) -> dict:
        return {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "side": trade.side.value,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "entry_price": trade.entry_price,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "exit_price": trade.exit_price,
            "exit_reason": trade.exit_reason,
            "quantity": trade.quantity,
            "duration_bars": trade.duration_bars,
            "pnl": trade.pnl,
            "commission": trade.commission,
            "return_pct": trade.return_pct,
            "mae_pct": trade.mae_pct,
            "mfe_pct": trade.mfe_pct,
        }

    if format == "json":
        payload = {
            "backtest": BacktestResponse.model_validate(backtest).model_dump(mode="json"),
            "trades": [trade_row(trade) for trade in trades],
        }
        return StreamingResponse(
            io.BytesIO(json.dumps(payload, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}.json"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=trade_columns)
    writer.writeheader()
    for trade in trades:
        writer.writerow(trade_row(trade))

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}_trades.csv"},
    )
