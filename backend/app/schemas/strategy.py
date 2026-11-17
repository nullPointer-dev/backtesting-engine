from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(from_attributes=True)


class StrategyListResponse(BaseModel):
    strategies: list[StrategyResponse]
    total: int


class StrategyValidateRequest(BaseModel):
    strategy_json: dict


class StrategyValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []