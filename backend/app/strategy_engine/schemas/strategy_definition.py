from typing import Annotated
from typing import Union

from pydantic import BaseModel
from pydantic import Field

from app.strategy_engine.schemas.condition import ConditionNode
from app.strategy_engine.schemas.group import GroupNode

Node = Annotated[Union[ConditionNode, GroupNode],Field(discriminator="type")]

class StrategyDefinition(BaseModel):
    long_entry: Node
    long_exit: Node
    short_entry: Node | None = None
    short_exit: Node | None = None