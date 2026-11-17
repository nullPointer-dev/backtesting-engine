import pytest

from app.backtesting.execution_engine import (
    EXIT_END_OF_DATA,
    EXIT_SIGNAL,
    BacktestCancelled,
    ExecutionEngine,
)
from app.backtesting.indicator_preloader import IndicatorPreloader
from app.enums.types import PositionSide
from tests.helpers import cond, make_bars, price, strategy, value

# Bars:     0   1   2   3   4  5   6   7
CLOSE = [10, 10, 12, 12, 9, 9, 11, 11]
OPEN = [10, 10, 11, 12, 11, 9, 10, 11]

LONG_ENTRY = cond(price("close"), ">", value(10.5))
LONG_EXIT = cond(price("close"), "<", value(10))
SHORT_ENTRY = cond(price("close"), "<", value(9.5))
SHORT_EXIT = cond(price("close"), ">", value(10))


def _run(definition, close=CLOSE, open_=OPEN, **kwargs):
    df = make_bars(close, open_=open_)
    cache = IndicatorPreloader(df, definition).preload()
    return ExecutionEngine("TEST", df, definition, cache).run(**kwargs)


def _summary(trades):
    return [
        (t["side"], t["entry_index"], t["entry_price"], t["exit_index"], t["exit_price"], t["exit_reason"], t["duration_bars"])
        for t in trades
    ]


def test_long_only_fills_at_next_open_and_closes_at_end():
    trades = _run(strategy(LONG_ENTRY, LONG_EXIT))
    assert _summary(trades) == [
        # signal on bar 2 close -> buy bar 3 open; exit signal bar 4 -> sell bar 5 open
        (PositionSide.LONG, 3, 12.0, 5, 9.0, EXIT_SIGNAL, 2),
        # signal on bar 6 -> buy bar 7 open; still open at the end -> closed at bar 7 close
        (PositionSide.LONG, 7, 11.0, 7, 11.0, EXIT_END_OF_DATA, 1),
    ]


def test_reversal_on_the_same_bar():
    trades = _run(strategy(LONG_ENTRY, LONG_EXIT, SHORT_ENTRY, SHORT_EXIT))
    assert _summary(trades) == [
        (PositionSide.LONG, 3, 12.0, 5, 9.0, EXIT_SIGNAL, 2),
        (PositionSide.SHORT, 5, 9.0, 7, 11.0, EXIT_SIGNAL, 2),
        (PositionSide.LONG, 7, 11.0, 7, 11.0, EXIT_END_OF_DATA, 1),
    ]


def test_signal_on_last_bar_is_not_traded():
    # Close only exceeds 10.5 on the final bar: there is no next bar to fill on.
    trades = _run(strategy(LONG_ENTRY, LONG_EXIT), close=[10, 10, 10, 12], open_=[10, 10, 10, 10])
    assert trades == []


def test_long_entry_takes_priority_over_short_entry():
    always = cond(price("close"), ">", value(0))
    never = cond(price("close"), "<", value(0))
    trades = _run(strategy(always, never, always, never), close=[1, 2, 3], open_=[1, 2, 3])
    assert [t["side"] for t in trades] == [PositionSide.LONG]


def test_no_signals_no_trades():
    never = cond(price("close"), "<", value(0))
    assert _run(strategy(never, never)) == []


def test_cancellation_is_checked_during_the_loop():
    calls = []

    def should_stop():
        calls.append(1)
        return len(calls) > 1

    with pytest.raises(BacktestCancelled):
        _run(strategy(LONG_ENTRY, LONG_EXIT), should_stop=should_stop, check_every=2)
