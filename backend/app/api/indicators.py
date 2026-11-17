from fastapi import APIRouter
from pydantic import BaseModel

from app.enums.types import ComparisonOperator, LogicalOperator, PositionSizingType, TimeFrame
from app.strategy_engine.indicator_registry import describe_registry

router = APIRouter(tags=["reference"])


class IndicatorParam(BaseModel):
    name: str
    type: str
    default: int | float
    min: int | float | None
    max: int | float | None
    description: str


class IndicatorInfo(BaseModel):
    name: str
    label: str
    category: str
    inputs: list[str]
    params: list[IndicatorParam]


class OperatorInfo(BaseModel):
    value: str
    label: str
    description: str


class ReferenceResponse(BaseModel):
    indicators: list[IndicatorInfo]
    comparison_operators: list[OperatorInfo]
    logical_operators: list[str]
    price_fields: list[str]
    timeframes: list[str]
    position_sizing_types: list[str]


_OPERATOR_INFO = {
    ComparisonOperator.GT: ("greater than", "left > right on the current bar"),
    ComparisonOperator.LT: ("less than", "left < right on the current bar"),
    ComparisonOperator.GTE: ("greater than or equal", "left >= right on the current bar"),
    ComparisonOperator.LTE: ("less than or equal", "left <= right on the current bar"),
    ComparisonOperator.EQ: ("equal", "left == right on the current bar"),
    ComparisonOperator.NEQ: ("not equal", "left != right on the current bar"),
    ComparisonOperator.CROSSES_ABOVE: (
        "crosses above", "left was <= right on the previous bar and is > right now"
    ),
    ComparisonOperator.CROSSES_BELOW: (
        "crosses below", "left was >= right on the previous bar and is < right now"
    ),
}


@router.get("/indicators", response_model=ReferenceResponse)
def get_reference():
    """Everything a client needs to build a strategy: indicators with their
    parameters, operators, price fields, timeframes and sizing types."""
    return ReferenceResponse(
        indicators=describe_registry(),
        comparison_operators=[
            OperatorInfo(value=op.value, label=label, description=description)
            for op, (label, description) in _OPERATOR_INFO.items()
        ],
        logical_operators=[op.value for op in LogicalOperator],
        price_fields=["open", "high", "low", "close", "volume"],
        timeframes=[tf.value for tf in TimeFrame],
        position_sizing_types=[ps.value for ps in PositionSizingType],
    )
