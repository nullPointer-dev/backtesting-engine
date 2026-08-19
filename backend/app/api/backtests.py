from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

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