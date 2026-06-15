from enum import Enum


class TradeSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"