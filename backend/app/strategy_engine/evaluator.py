from app.enums.types import LogicalOperator
from app.strategy_engine.operators import evaluate_operator
from app.strategy_engine.schemas.condition import ConditionNode
from app.strategy_engine.schemas.group import GroupNode
from app.strategy_engine.schemas.operand import (
    IndicatorOperand,
    PriceOperand,
    ValueOperand
)
import pandas as pd


class Evaluator:
    def __init__(self, dataframe, indicator_cache):
        self.dataframe = dataframe
        self.cache = indicator_cache

    def evaluate(self, node, index: int):
        if isinstance(node, ConditionNode):
            return self._evaluate_condition(node, index)

        if isinstance(node, GroupNode):
            return self._evaluate_group(node, index)

        raise ValueError(
            "Unknown node type"
        )

    def _evaluate_group(self, group: GroupNode, index: int):
        results = [
            self.evaluate(child, index)
            for child in group.children
        ]

        if group.operator == LogicalOperator.AND:
            return all(results)

        return any(results)

    def _evaluate_condition(self, condition: ConditionNode, index: int):
        left_current = self._resolve_operand(condition.left, index)
        right_current = self._resolve_operand(condition.right, index)

        left_previous = None
        right_previous = None

        if index > 0:

            left_previous = (self._resolve_operand(condition.left, index - 1))
            right_previous = (self._resolve_operand(condition.right, index - 1))

        return evaluate_operator(
            operator=condition.operator,
            left_current=left_current,
            right_current=right_current,
            left_previous=left_previous,
            right_previous=right_previous
        )

    def _resolve_operand(self, operand, index: int):

        if isinstance(operand, ValueOperand):
            return operand.value

        if isinstance(operand, PriceOperand):
            return self.dataframe[
                operand.field
            ].iloc[index]

        if isinstance(operand, IndicatorOperand):
            series = self.cache.get(
                operand.indicator,
                operand.params
            )

            value = series.iloc[index]

            if pd.isna(value):
                return None

            return value

        raise ValueError(
            "Unknown operand type"
        )