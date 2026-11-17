from typing import Literal

from pydantic import BaseModel

from app.enums.types import ComparisonOperator
from app.strategy_engine.schemas.operand import Operand


class ConditionNode(BaseModel):
    type: Literal["condition"] = "condition"
    left: Operand
    operator: ComparisonOperator
    right: Operand
