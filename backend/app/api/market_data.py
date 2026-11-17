from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import SessionLocal
from app.api.auth import get_current_user
from app.models.user import User
from app.models.market_data import MarketData
from app.enums.types import TimeFrame

router = APIRouter(prefix="/market-data", tags=["market-data"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/symbols")
def get_symbols(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    symbols = db.query(MarketData.symbol).distinct().all()
    return {"symbols": [s[0] for s in symbols]}


@router.get("/{symbol}/history")
def get_symbol_history(
    symbol: str,
    timeframe: TimeFrame = Query(TimeFrame.ONE_DAY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(MarketData).filter(
        MarketData.symbol == symbol.upper(),
        MarketData.timeframe == timeframe
    )
    
    if start_date:
        query = query.filter(MarketData.timestamp >= start_date)
    if end_date:
        query = query.filter(MarketData.timestamp <= end_date)
    
    data = query.order_by(MarketData.timestamp.desc()).limit(limit).all()
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.value,
        "data": [
            {
                "timestamp": d.timestamp.isoformat(),
                "open": d.open,
                "high": d.high,
                "low": d.low,
                "close": d.close,
                "volume": d.volume,
            }
            for d in reversed(data)
        ],
    }


@router.get("/{symbol}/latest")
def get_latest_price(
    symbol: str,
    timeframe: TimeFrame = Query(TimeFrame.ONE_DAY),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = db.query(MarketData).filter(
        MarketData.symbol == symbol.upper(),
        MarketData.timeframe == timeframe
    ).order_by(MarketData.timestamp.desc()).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for {symbol} {timeframe.value}",
        )
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.value,
        "timestamp": data.timestamp.isoformat(),
        "open": data.open,
        "high": data.high,
        "low": data.low,
        "close": data.close,
        "volume": data.volume,
    }