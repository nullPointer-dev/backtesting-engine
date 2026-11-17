"""Checks a strategy JSON document before it is saved or run."""

from dataclasses import dataclass, field

from pydantic import ValidationError

from app.strategy_engine.indicator_registry import INDICATOR_REGISTRY
from app.strategy_engine.schemas.condition import ConditionNode
from app.strategy_engine.schemas.group import GroupNode
from app.strategy_engine.schemas.operand import IndicatorOperand, ValueOperand
from app.strategy_engine.schemas.strategy_definition import StrategyDefinition


@dataclass
class StrategyValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    definition: StrategyDefinition | None = None

    @property
    def valid(self) -> bool:
        return not self.errors


def _format_pydantic_error(error: ValidationError) -> list[str]:
    messages = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "strategy"
        messages.append(f"{location}: {item['msg']}")
    return messages


def validate_strategy(strategy_json: dict) -> StrategyValidationResult:
    result = StrategyValidationResult()

    try:
        definition = StrategyDefinition.model_validate(strategy_json)
    except ValidationError as error:
        result.errors.extend(_format_pydantic_error(error))
        return result

    for rule in ("long_entry", "long_exit", "short_entry", "short_exit"):
        node = getattr(definition, rule)
        if node is not None:
            _check_node(node, rule, result)

    if definition.short_entry is not None and definition.short_exit is None:
        result.errors.append(
            "short_exit: required when short_entry is set, otherwise short positions never close"
        )
    if definition.short_exit is not None and definition.short_entry is None:
        result.warnings.append("short_exit: ignored because there is no short_entry")

    if result.valid:
        result.definition = definition
    return result


def _check_node(node, path: str, result: StrategyValidationResult):
    if isinstance(node, GroupNode):
        for index, child in enumerate(node.children):
            _check_node(child, f"{path}.children.{index}", result)
        return

    if isinstance(node, ConditionNode):
        _check_operand(node.left, f"{path}.left", result)
        _check_operand(node.right, f"{path}.right", result)
        if isinstance(node.left, ValueOperand) and isinstance(node.right, ValueOperand):
            result.warnings.append(f"{path}: compares two constant values, so it never changes")


def _check_operand(operand, path: str, result: StrategyValidationResult):
    if not isinstance(operand, IndicatorOperand):
        return

    indicator = INDICATOR_REGISTRY.get(operand.indicator)
    if indicator is None:
        result.errors.append(
            f"{path}.indicator: unknown indicator '{operand.indicator}'. "
            f"Available: {', '.join(sorted(INDICATOR_REGISTRY))}"
        )
        return

    for name, value in operand.params.items():
        spec = indicator.params.get(name)
        if spec is None:
            allowed = ", ".join(indicator.params) or "none"
            result.errors.append(
                f"{path}.params.{name}: unknown parameter for {operand.indicator} (allowed: {allowed})"
            )
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            result.errors.append(f"{path}.params.{name}: must be a number")
            continue

        if spec.type is int and float(value) != int(value):
            result.errors.append(f"{path}.params.{name}: must be a whole number")
            continue

        if spec.min is not None and value < spec.min:
            result.errors.append(f"{path}.params.{name}: must be at least {spec.min}")
        if spec.max is not None and value > spec.max:
            result.errors.append(f"{path}.params.{name}: must be at most {spec.max}")

    params = operand.params
    if "fast_period" in indicator.params:
        fast = params.get("fast_period", indicator.params["fast_period"].default)
        slow = params.get("slow_period", indicator.params["slow_period"].default)
        if isinstance(fast, (int, float)) and isinstance(slow, (int, float)) and fast >= slow:
            result.warnings.append(f"{path}.params: fast_period should be smaller than slow_period")
