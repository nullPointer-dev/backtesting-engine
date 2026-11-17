from enum import Enum

class ComparisonOperator(str, Enum):
    GT = ">"
    LT = "<"

    GTE = ">="
    LTE = "<="

    EQ = "=="
    NEQ = "!="

    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"

class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"

class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class PositionSizingType(str, Enum):
    FIXED_QUANTITY = "FIXED_QUANTITY"
    PERCENT_OF_CAPITAL = "PERCENT_OF_CAPITAL"

class TimeFrame(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "60m"
    ONE_DAY = "1d"
    ONE_WEEK = "1wk"

class BacktestStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"