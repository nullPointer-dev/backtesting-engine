from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import io
import csv
import json

from app.core.database import SessionLocal
from app.api.auth import get_current_user
from app.models.user import User
from app.models.strategy import Strategy
from app.models.backtest import Backtest
from app.models.trade import Trade
from app.enums.types import BacktestStatus
from app.backtesting.backtest_runner import BacktestRunner
from app.schemas.backtest import (
    BacktestCreate,
    BacktestResponse,
    BacktestListResponse,
    BacktestRunResponse,
)
from app.schemas.trade import TradeResponse, TradeListResponse

router = APIRouter(prefix="/backtests", tags=["backtests"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_backtest_background(backtest_id: int):
    """Background task to run backtest."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        runner = BacktestRunner(backtest_id=backtest_id)
        runner.run()
    finally:
        db.close()


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    if backtest_in.position_sizing_type.value == "FIXED_QUANTITY" and backtest_in.quantity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity is required for FIXED_QUANTITY position sizing",
        )
    if backtest_in.position_sizing_type.value == "PERCENT_OF_CAPITAL" and backtest_in.position_size_percent is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="position_size_percent is required for PERCENT_OF_CAPITAL position sizing",
        )

    backtest = Backtest(
        strategy_id=backtest_in.strategy_id,
        status=BacktestStatus.PENDING,
        created_at=datetime.now(),
        start_date=backtest_in.start_date,
        end_date=backtest_in.end_date,
        initial_capital=backtest_in.initial_capital,
        symbol=backtest_in.symbol,
        timeframe=backtest_in.timeframe,
        position_sizing_type=backtest_in.position_sizing_type,
        quantity=backtest_in.quantity,
        position_size_percent=backtest_in.position_size_percent,
    )
    db.add(backtest)
    db.commit()
    db.refresh(backtest)
    return backtest


@router.get("", response_model=BacktestListResponse)
def list_backtests(
    strategy_id: Optional[int] = Query(None),
    status: Optional[BacktestStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Backtest).join(Strategy).filter(Strategy.user_id == current_user.user_id)
    if strategy_id:
        query = query.filter(Backtest.strategy_id == strategy_id)
    if status:
        query = query.filter(Backtest.status == status)
    total = query.count()
    backtests = query.order_by(Backtest.created_at.desc()).offset(skip).limit(limit).all()
    return BacktestListResponse(backtests=backtests, total=total)


@router.get("/{backtest_id}", response_model=BacktestResponse)
def get_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    return backtest


@router.post("/{backtest_id}/run", response_model=BacktestRunResponse)
def run_backtest(
    backtest_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    if backtest.status == BacktestStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest already running",
        )
    if backtest.status == BacktestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest already completed. Create a new backtest to run again.",
        )

    backtest.status = BacktestStatus.RUNNING
    backtest.started_at = datetime.now()
    db.commit()

    background_tasks.add_task(run_backtest_background, backtest_id)

    return BacktestRunResponse(
        backtest_id=backtest_id,
        status=BacktestStatus.RUNNING,
        message="Backtest started in background",
    )


@router.get("/{backtest_id}/trades", response_model=TradeListResponse)
def get_backtest_trades(
    backtest_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    query = db.query(Trade).filter(Trade.backtest_id == backtest_id)
    total = query.count()
    trades = query.order_by(Trade.entry_time.desc()).offset(skip).limit(limit).all()
    return TradeListResponse(trades=trades, total=total)


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    if backtest.status == BacktestStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running backtest",
        )
    db.delete(backtest)
    db.commit()
    return None


@router.get("/{backtest_id}/equity-curve")
def get_equity_curve(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    return {
        "backtest_id": backtest_id,
        "equity_curve": backtest.equity_curve or [],
        "initial_capital": backtest.initial_capital,
    }


@router.get("/{backtest_id}/drawdown")
def get_drawdown(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    
    equity_curve = backtest.equity_curve or []
    if not equity_curve:
        return {"backtest_id": backtest_id, "drawdown": [], "max_drawdown": 0}
    
    import numpy as np
    equity_array = np.array(equity_curve)
    running_max = np.maximum.accumulate(equity_array)
    drawdowns = ((equity_array - running_max) / running_max * 100).tolist()
    max_drawdown = min(drawdowns) if drawdowns else 0
    
    return {
        "backtest_id": backtest_id,
        "drawdown": drawdowns,
        "max_drawdown": max_drawdown,
    }


@router.get("/{backtest_id}/returns-breakdown")
def get_returns_breakdown(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    
    trades = db.query(Trade).filter(Trade.backtest_id == backtest_id).all()
    if not trades:
        return {"backtest_id": backtest_id, "monthly_returns": [], "yearly_returns": []}
    
    from collections import defaultdict
    monthly_pnl = defaultdict(float)
    yearly_pnl = defaultdict(float)
    
    for trade in trades:
        if trade.exit_time:
            month_key = trade.exit_time.strftime("%Y-%m")
            year_key = trade.exit_time.strftime("%Y")
            monthly_pnl[month_key] += trade.pnl
            yearly_pnl[year_key] += trade.pnl
    
    monthly_returns = [
        {"period": k, "pnl": v, "return_pct": (v / backtest.initial_capital) * 100}
        for k, v in sorted(monthly_pnl.items())
    ]
    yearly_returns = [
        {"period": k, "pnl": v, "return_pct": (v / backtest.initial_capital) * 100}
        for k, v in sorted(yearly_pnl.items())
    ]
    
    return {
        "backtest_id": backtest_id,
        "monthly_returns": monthly_returns,
        "yearly_returns": yearly_returns,
    }


@router.get("/{backtest_id}/trade-analysis")
def get_trade_analysis(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    
    trades = db.query(Trade).filter(Trade.backtest_id == backtest_id).all()
    if not trades:
        return {
            "backtest_id": backtest_id,
            "win_loss_distribution": {"wins": 0, "losses": 0},
            "pnl_distribution": [],
            "duration_distribution": [],
            "mae_mfe": {"avg_mae": 0, "avg_mfe": 0},
            "consecutive": {"max_wins": 0, "max_losses": 0},
        }
    
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    
    pnl_values = [t.pnl for t in trades]
    durations = [t.duration_bars for t in trades]
    
    import numpy as np
    pnl_array = np.array(pnl_values)
    duration_array = np.array(durations)
    
    pnl_hist, pnl_bins = np.histogram(pnl_array, bins=20)
    duration_hist, duration_bins = np.histogram(duration_array, bins=20)
    
    pnl_distribution = [
        {"range": f"{pnl_bins[i]:.2f} to {pnl_bins[i+1]:.2f}", "count": int(pnl_hist[i])}
        for i in range(len(pnl_hist))
    ]
    duration_distribution = [
        {"range": f"{int(duration_bins[i])} to {int(duration_bins[i+1])}", "count": int(duration_hist[i])}
        for i in range(len(duration_hist))
    ]
    
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0
    for trade in trades:
        if trade.pnl > 0:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        elif trade.pnl < 0:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)
    
    return {
        "backtest_id": backtest_id,
        "win_loss_distribution": {"wins": len(wins), "losses": len(losses)},
        "pnl_distribution": pnl_distribution,
        "duration_distribution": duration_distribution,
        "mae_mfe": {"avg_mae": 0, "avg_mfe": 0},
        "consecutive": {"max_wins": max_consecutive_wins, "max_losses": max_consecutive_losses},
    }


@router.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func
    
    total_backtests = db.query(Backtest).join(Strategy).filter(
        Strategy.user_id == current_user.user_id
    ).count()
    
    completed_backtests = db.query(Backtest).join(Strategy).filter(
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.COMPLETED
    ).count()
    
    running_backtests = db.query(Backtest).join(Strategy).filter(
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.RUNNING
    ).count()
    
    failed_backtests = db.query(Backtest).join(Strategy).filter(
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.FAILED
    ).count()
    
    total_strategies = db.query(Strategy).filter(
        Strategy.user_id == current_user.user_id
    ).count()
    
    best_return = db.query(func.max(Backtest.total_return)).join(Strategy).filter(
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.COMPLETED
    ).scalar()
    
    worst_return = db.query(func.min(Backtest.total_return)).join(Strategy).filter(
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.COMPLETED
    ).scalar()
    
    avg_return = db.query(func.avg(Backtest.total_return)).join(Strategy).filter(
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.COMPLETED
    ).scalar()
    
    recent_backtests = db.query(Backtest).join(Strategy).filter(
        Strategy.user_id == current_user.user_id
    ).order_by(Backtest.created_at.desc()).limit(5).all()
    
    return {
        "total_backtests": total_backtests,
        "completed_backtests": completed_backtests,
        "running_backtests": running_backtests,
        "failed_backtests": failed_backtests,
        "total_strategies": total_strategies,
        "best_return": float(best_return) if best_return else None,
        "worst_return": float(worst_return) if worst_return else None,
        "avg_return": float(avg_return) if avg_return else None,
        "recent_backtests": recent_backtests,
    }


@router.post("/compare")
def compare_backtests(
    backtest_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtests = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id.in_(backtest_ids),
        Strategy.user_id == current_user.user_id,
        Backtest.status == BacktestStatus.COMPLETED
    ).all()
    
    if not backtests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed backtests found for comparison",
        )
    
    comparison = []
    for bt in backtests:
        comparison.append({
            "backtest_id": bt.backtest_id,
            "strategy_id": bt.strategy_id,
            "symbol": bt.symbol,
            "timeframe": bt.timeframe.value if bt.timeframe else None,
            "start_date": bt.start_date,
            "end_date": bt.end_date,
            "initial_capital": bt.initial_capital,
            "final_capital": bt.final_capital,
            "total_return": bt.total_return,
            "net_profit": bt.net_profit,
            "cagr": bt.cagr,
            "sharpe_ratio": bt.sharpe_ratio,
            "sortino_ratio": bt.sortino_ratio,
            "calmar_ratio": bt.calmar_ratio,
            "max_drawdown": bt.max_drawdown,
            "win_rate": bt.win_rate,
            "profit_factor": bt.profit_factor,
            "total_trades": bt.total_trades,
            "expectancy": bt.expectancy,
        })
    
    return {"comparison": comparison}


@router.get("/{backtest_id}/export")
def export_backtest(
    backtest_id: int,
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    
    trades = db.query(Trade).filter(Trade.backtest_id == backtest_id).all()
    
    if format == "json":
        data = {
            "backtest": {
                "backtest_id": backtest.backtest_id,
                "strategy_id": backtest.strategy_id,
                "status": backtest.status.value,
                "start_date": backtest.start_date.isoformat() if backtest.start_date else None,
                "end_date": backtest.end_date.isoformat() if backtest.end_date else None,
                "initial_capital": backtest.initial_capital,
                "symbol": backtest.symbol,
                "timeframe": backtest.timeframe.value if backtest.timeframe else None,
                "final_capital": backtest.final_capital,
                "total_return": backtest.total_return,
                "net_profit": backtest.net_profit,
                "cagr": backtest.cagr,
                "sharpe_ratio": backtest.sharpe_ratio,
                "sortino_ratio": backtest.sortino_ratio,
                "calmar_ratio": backtest.calmar_ratio,
                "max_drawdown": backtest.max_drawdown,
                "win_rate": backtest.win_rate,
                "profit_factor": backtest.profit_factor,
                "total_trades": backtest.total_trades,
                "equity_curve": backtest.equity_curve,
            },
            "trades": [
                {
                    "trade_id": t.trade_id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "entry_price": t.entry_price,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "duration_bars": t.duration_bars,
                    "pnl": t.pnl,
                }
                for t in trades
            ],
        }
        return StreamingResponse(
            io.BytesIO(json.dumps(data, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}.json"}
        )
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["trade_id", "symbol", "side", "entry_time", "entry_price", "exit_time", "exit_price", "quantity", "duration_bars", "pnl"])
    for t in trades:
        writer.writerow([
            t.trade_id, t.symbol, t.side,
            t.entry_time.isoformat() if t.entry_time else "",
            t.entry_price,
            t.exit_time.isoformat() if t.exit_time else "",
            t.exit_price, t.quantity, t.duration_bars, t.pnl
        ])
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}_trades.csv"}
    )


@router.get("/{backtest_id}/status")
def get_backtest_status(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    
    return {
        "backtest_id": backtest_id,
        "status": backtest.status.value,
        "started_at": backtest.started_at.isoformat() if backtest.started_at else None,
        "completed_at": backtest.completed_at.isoformat() if backtest.completed_at else None,
        "error_message": backtest.error_message,
    }


@router.post("/{backtest_id}/cancel")
def cancel_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    backtest = db.query(Backtest).join(Strategy).filter(
        Backtest.backtest_id == backtest_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )
    
    if backtest.status != BacktestStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel running backtests",
        )
    
    backtest.status = BacktestStatus.FAILED
    backtest.error_message = "Cancelled by user"
    backtest.completed_at = datetime.now()
    db.commit()
    
    return {"backtest_id": backtest_id, "status": BacktestStatus.FAILED.value, "message": "Backtest cancelled"}