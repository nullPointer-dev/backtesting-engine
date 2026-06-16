from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class IndicatorOperand(BaseModel):
    type: Literal["indicator"] = ("indicator")
    indicator: str
    params: dict = Field(default_factory=dict)


class PriceOperand(BaseModel):
    type: Literal["price"] = ("price")

    field: Literal[
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]


class ValueOperand(BaseModel):
    type: Literal["value"] = ("value")
    value: float