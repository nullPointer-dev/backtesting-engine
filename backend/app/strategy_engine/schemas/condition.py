from typing import Union, Literal

from pydantic import BaseModel
from pydantic import Field

from app.enums.types import (
    ComparisonOperator
)

from app.strategy_engine.schemas.operand import (
    IndicatorOperand,
    PriceOperand,
    ValueOperand
)

Operand = Union[IndicatorOperand, PriceOperand,ValueOperand]

class ConditionNode(BaseModel):

    type: Literal["condition"] = "condition"
    left: Operand
    operator: ComparisonOperator
    right: Operand