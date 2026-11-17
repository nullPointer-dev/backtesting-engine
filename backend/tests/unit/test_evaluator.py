import numpy as np

from app.backtesting.indicator_preloader import IndicatorPreloader
from app.strategy_engine.evaluator import Evaluator
from app.strategy_engine.requirement_extractor import RequirementExtractor
from tests.helpers import cond, group, indicator, make_bars, price, strategy, value


def _evaluator(df, definition):
    return Evaluator(df, IndicatorPreloader(df, definition).preload())


def test_price_and_value_operands():
    df = make_bars([10, 20, 30])
    node = cond(price("close"), ">", value(15))
    definition = strategy(node, node)
    evaluator = _evaluator(df, definition)
    assert [evaluator.evaluate(definition.long_entry, i) for i in range(3)] == [False, True, True]


def test_indicator_without_value_yet_is_false():
    df = make_bars(np.arange(1, 11, dtype=float))
    node = cond(indicator("SMA", period=5), ">", value(0))
    definition = strategy(node, node)
    evaluator = _evaluator(df, definition)
    results = [evaluator.evaluate(definition.long_entry, i) for i in range(10)]
    assert results == [False] * 4 + [True] * 6


def test_crossing_uses_previous_bar():
    df = make_bars([1, 1, 3, 3, 1])
    node = cond(price("close"), "crosses_above", value(2))
    definition = strategy(node, node)
    evaluator = _evaluator(df, definition)
    assert [evaluator.evaluate(definition.long_entry, i) for i in range(5)] == [False, False, True, False, False]


def test_nested_groups():
    df = make_bars([5, 15, 25])
    above_10 = cond(price("close"), ">", value(10))
    below_20 = cond(price("close"), "<", value(20))
    equals_5 = cond(price("close"), "==", value(5))
    node = group("OR", group("AND", above_10, below_20), equals_5)
    definition = strategy(node, node)
    evaluator = _evaluator(df, definition)
    assert [evaluator.evaluate(definition.long_entry, i) for i in range(3)] == [True, True, False]


def test_requirement_extractor_deduplicates_indicators():
    sma20 = indicator("SMA", period=20)
    definition = strategy(
        cond(sma20, "crosses_above", indicator("SMA", period=50)),
        cond(sma20, "crosses_below", indicator("SMA", period=50)),
        cond(indicator("RSI", period=14), "<", value(30)),
        cond(indicator("RSI", period=14), ">", value(70)),
    )
    requirements = RequirementExtractor().extract(definition)
    assert requirements == {
        ("SMA", (("period", 20),)),
        ("SMA", (("period", 50),)),
        ("RSI", (("period", 14),)),
    }
