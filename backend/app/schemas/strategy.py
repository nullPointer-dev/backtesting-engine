from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strategy_json: dict


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    strategy_json: Optional[dict] = None


class StrategyResponse(BaseModel):
    strategy_id: int
    user_id: int
    name: str
    strategy_json: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    strategies: list[StrategyResponse]
    total: int