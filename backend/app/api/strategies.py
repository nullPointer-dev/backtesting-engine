from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.strategy import Strategy
from app.models.user import User
from app.schemas.strategy import (
    StrategyCreate,
    StrategyListResponse,
    StrategyResponse,
    StrategyUpdate,
    StrategyValidateRequest,
    StrategyValidateResponse,
)
from app.strategy_engine.validation import validate_strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _require_valid(strategy_json: dict) -> None:
    result = validate_strategy(strategy_json)
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Invalid strategy", "errors": result.errors, "warnings": result.warnings},
        )


def _get_owned_strategy(db: Session, user: User, strategy_id: int) -> Strategy:
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id,
        Strategy.user_id == user.user_id,
    ).first()
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return strategy


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy(
    strategy_in: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_valid(strategy_in.strategy_json)
    now = datetime.now(timezone.utc)
    strategy = Strategy(
        user_id=current_user.user_id,
        name=strategy_in.name,
        strategy_json=strategy_in.strategy_json,
        created_at=now,
        updated_at=now,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("", response_model=StrategyListResponse)
def list_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Strategy).filter(Strategy.user_id == current_user.user_id)
    total = query.count()
    strategies = query.order_by(Strategy.created_at.desc()).offset(skip).limit(limit).all()
    return StrategyListResponse(strategies=strategies, total=total)


@router.post("/validate", response_model=StrategyValidateResponse)
def validate_strategy_endpoint(
    strategy_in: StrategyValidateRequest,
    current_user: User = Depends(get_current_user),
):
    result = validate_strategy(strategy_in.strategy_json)
    return StrategyValidateResponse(valid=result.valid, errors=result.errors, warnings=result.warnings)


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_strategy(db, current_user, strategy_id)


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: int,
    strategy_in: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = _get_owned_strategy(db, current_user, strategy_id)
    if strategy_in.name is not None:
        strategy.name = strategy_in.name
    if strategy_in.strategy_json is not None:
        _require_valid(strategy_in.strategy_json)
        strategy.strategy_json = strategy_in.strategy_json
    strategy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = _get_owned_strategy(db, current_user, strategy_id)
    db.delete(strategy)
    db.commit()
    return None
