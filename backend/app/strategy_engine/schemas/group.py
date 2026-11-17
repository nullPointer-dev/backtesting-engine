from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from app.enums.types import LogicalOperator
from app.strategy_engine.schemas.condition import ConditionNode


class GroupNode(BaseModel):
    type: Literal["group"] = "group"
    operator: LogicalOperator
    children: list[
        Annotated[Union[ConditionNode, "GroupNode"], Field(discriminator="type")]
    ] = Field(min_length=1)


GroupNode.model_rebuild()
