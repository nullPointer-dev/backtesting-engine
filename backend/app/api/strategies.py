from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import SessionLocal
from app.api.auth import get_current_user
from app.models.user import User
from app.models.strategy import Strategy
from app.strategy_engine.schemas.strategy_definition import StrategyDefinition
from app.schemas.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyListResponse,
    StrategyValidateRequest,
    StrategyValidateResponse,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy(
    strategy_in: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = Strategy(
        user_id=current_user.user_id,
        name=strategy_in.name,
        strategy_json=strategy_in.strategy_json,
        created_at=datetime.now(),
        updated_at=datetime.now(),
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


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: int,
    strategy_in: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    if strategy_in.name is not None:
        strategy.name = strategy_in.name
    if strategy_in.strategy_json is not None:
        strategy.strategy_json = strategy_in.strategy_json
    strategy.updated_at = datetime.now()
    db.commit()
    db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id,
        Strategy.user_id == current_user.user_id,
    ).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    db.delete(strategy)
    db.commit()
    return None


@router.post("/validate", response_model=StrategyValidateResponse)
def validate_strategy(
    strategy_in: StrategyValidateRequest,
    current_user: User = Depends(get_current_user),
):
    errors = []
    warnings = []
    
    try:
        StrategyDefinition.model_validate(strategy_in.strategy_json)
    except Exception as e:
        errors.append(str(e))
    
    if not errors:
        strategy_json = strategy_in.strategy_json
        required_keys = ["long_entry", "long_exit"]
        for key in required_keys:
            if key not in strategy_json:
                errors.append(f"Missing required key: {key}")
        
        for key in ["short_entry", "short_exit"]:
            if key in strategy_json and strategy_json[key] is not None:
                pass
            elif key in strategy_json and strategy_json[key] is None:
                warnings.append(f"Optional key {key} is null")
    
    return StrategyValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )