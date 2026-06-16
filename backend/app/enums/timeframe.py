from enum import Enum


class TimeFrame(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "60m"
    ONE_DAY = "1d"
    ONE_WEEK = "1wk"