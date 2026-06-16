from __future__ import annotations
from typing import Union, Literal
from pydantic import BaseModel
from pydantic import Field

from app.enums.types import LogicalOperator

from app.strategy_engine.schemas.condition import ConditionNode


class GroupNode(BaseModel):

    type: Literal["group"] = "group"
    operator: LogicalOperator
    children: list[
        Union[
            ConditionNode,
            "GroupNode"
        ]
    ]

GroupNode.model_rebuild()