from app.strategy_engine.schemas.condition import ConditionNode
from app.strategy_engine.schemas.group import GroupNode
from app.strategy_engine.schemas.operand import IndicatorOperand
from app.strategy_engine.schemas.strategy_definition import StrategyDefinition

class RequirementExtractor:
    def __init__(self):
        self.requirements = set()

    def extract(self, strategy: StrategyDefinition):
        self._walk_node(strategy.long_entry)
        self._walk_node(strategy.long_exit)
        if strategy.short_entry:
            self._walk_node(strategy.short_entry)
        if strategy.short_exit:
            self._walk_node(strategy.short_exit)

        return self.requirements

    def _walk_node(self, node):
        if isinstance(node, ConditionNode):
            self._walk_condition(node)

        elif isinstance(node, GroupNode):
            for child in (node.children):
                self._walk_node(child)

    def _walk_condition(self, condition: ConditionNode):
        self._walk_operand(condition.left)
        self._walk_operand(condition.right)

    def _walk_operand(self,operand):
        if isinstance(operand,IndicatorOperand):
            self.requirements.add((operand.indicator, tuple(sorted(operand.params.items()))))