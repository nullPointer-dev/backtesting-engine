import pytest

from app.enums.types import ComparisonOperator as Op
from app.strategy_engine.operators import evaluate_operator


@pytest.mark.parametrize("op, left, right, expected", [
    (Op.GT, 2, 1, True), (Op.GT, 1, 1, False),
    (Op.LT, 1, 2, True), (Op.LT, 2, 2, False),
    (Op.GTE, 2, 2, True), (Op.GTE, 1, 2, False),
    (Op.LTE, 2, 2, True), (Op.LTE, 3, 2, False),
    (Op.EQ, 2, 2, True), (Op.EQ, 2, 3, False),
    (Op.NEQ, 2, 3, True), (Op.NEQ, 2, 2, False),
])
def test_simple_comparisons(op, left, right, expected):
    assert evaluate_operator(op, left, right) is expected


@pytest.mark.parametrize("op", list(Op))
def test_missing_current_value_is_false(op):
    assert evaluate_operator(op, None, 1, 0, 0) is False
    assert evaluate_operator(op, 1, None, 0, 0) is False


@pytest.mark.parametrize("prev_left, prev_right, left, right, expected", [
    (1, 2, 3, 2, True),    # from below to above
    (2, 2, 3, 2, True),    # from touching to above
    (3, 2, 4, 2, False),   # already above
    (1, 2, 2, 2, False),   # only touches
])
def test_crosses_above(prev_left, prev_right, left, right, expected):
    assert evaluate_operator(Op.CROSSES_ABOVE, left, right, prev_left, prev_right) is expected


@pytest.mark.parametrize("prev_left, prev_right, left, right, expected", [
    (3, 2, 1, 2, True),
    (2, 2, 1, 2, True),
    (1, 2, 0, 2, False),
    (3, 2, 2, 2, False),
])
def test_crosses_below(prev_left, prev_right, left, right, expected):
    assert evaluate_operator(Op.CROSSES_BELOW, left, right, prev_left, prev_right) is expected


@pytest.mark.parametrize("op", [Op.CROSSES_ABOVE, Op.CROSSES_BELOW])
def test_cross_needs_previous_values(op):
    assert evaluate_operator(op, 3, 2, None, 2) is False
    assert evaluate_operator(op, 3, 2, 1, None) is False
