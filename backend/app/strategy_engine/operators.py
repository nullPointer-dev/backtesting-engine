from app.enums.types import ComparisonOperator


def evaluate_operator(
    operator: ComparisonOperator,
    left_current,
    right_current,
    left_previous=None,
    right_previous=None
):

    if operator == ComparisonOperator.GT:
        return left_current > right_current

    if operator == ComparisonOperator.LT:
        return left_current < right_current

    if operator == ComparisonOperator.GTE:
        return left_current >= right_current

    if operator == ComparisonOperator.LTE:
        return left_current <= right_current

    if operator == ComparisonOperator.EQ:
        return left_current == right_current

    if operator == ComparisonOperator.NEQ:
        return left_current != right_current

    if operator == ComparisonOperator.CROSSES_ABOVE:
        return (
            left_previous <= right_previous
            and left_current > right_current
        )

    if operator == ComparisonOperator.CROSSES_BELOW:
        return (
            left_previous >= right_previous
            and left_current < right_current
        )

    raise ValueError(
        f"Unsupported operator: {operator}"
    )