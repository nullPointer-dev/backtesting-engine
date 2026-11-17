import math

import numpy as np
import pandas as pd
import pytest

from app.backtesting.performance_metrics import BARS_PER_YEAR, PerformanceMetrics
from app.enums.types import TimeFrame


def _metrics(equity, trades=(), timeframe=TimeFrame.ONE_DAY, initial=100.0, start="2024-01-01", freq="D"):
    times = pd.Series(pd.date_range(start, periods=len(equity), freq=freq, tz="UTC"))
    return PerformanceMetrics(list(trades), np.asarray(equity, dtype=float), times, initial, timeframe).calculate()


def _trade(pnl, bars=1):
    return {"pnl": pnl, "duration_bars": bars}


def test_flat_equity():
    m = _metrics([100.0] * 10)
    assert m["total_return"] == 0 and m["max_drawdown"] == 0 and m["max_drawdown_duration"] == 0
    assert m["sharpe_ratio"] is None and m["sortino_ratio"] is None
    assert m["total_trades"] == 0 and m["win_rate"] is None and m["profit_factor"] is None


def test_drawdown_and_duration():
    #             peak 120, trough 90 -> -25%; underwater for 4 bars
    m = _metrics([110, 120, 100, 90, 100, 110, 130])
    assert m["max_drawdown"] == pytest.approx(-25.0)
    assert m["max_drawdown_duration"] == 4
    assert m["recovery_factor"] == pytest.approx(30 / 30)
    assert m["final_capital"] == 130 and m["net_profit"] == 30 and m["total_return"] == pytest.approx(30.0)


def test_starting_capital_counts_as_first_peak():
    m = _metrics([90, 95, 100])
    assert m["max_drawdown"] == pytest.approx(-10.0)


def test_cagr_over_actual_span():
    # Doubling over exactly one (365.25-day) year of daily bars -> 100%.
    m = _metrics(np.linspace(100, 200, 2), start="2023-01-01", freq="365D6h")
    assert m["cagr"] == pytest.approx(100.0)


def test_cagr_when_capital_is_lost():
    assert _metrics([100, 50, -10])["cagr"] == -100.0


def test_sharpe_and_sortino_are_annualised_by_timeframe():
    equity = [100, 101, 100, 102, 101, 103]
    path = np.array([100.0] + equity)
    returns = np.diff(path) / path[:-1]
    daily = _metrics(equity, timeframe=TimeFrame.ONE_DAY)
    weekly = _metrics(equity, timeframe=TimeFrame.ONE_WEEK, freq="7D")

    expected_daily = returns.mean() / returns.std(ddof=1) * math.sqrt(252)
    assert daily["sharpe_ratio"] == pytest.approx(expected_daily)
    assert weekly["sharpe_ratio"] == pytest.approx(expected_daily * math.sqrt(52 / 252))

    downside = math.sqrt(np.mean(np.minimum(returns, 0) ** 2))
    assert daily["sortino_ratio"] == pytest.approx(returns.mean() / downside * math.sqrt(252))


def test_bars_per_year_covers_every_timeframe():
    assert set(BARS_PER_YEAR) == set(TimeFrame)


def test_trade_statistics():
    trades = [_trade(10, 2), _trade(5, 4), _trade(0, 1), _trade(-4, 3), _trade(-6, 5), _trade(8, 1)]
    m = _metrics([100, 105], trades=trades)
    assert m["total_trades"] == 6
    assert m["win_rate"] == pytest.approx(50.0)
    assert m["loss_rate"] == pytest.approx(100 / 3)
    assert m["profit_factor"] == pytest.approx(23 / 10)
    assert m["expectancy"] == pytest.approx(13 / 6)
    assert m["max_consecutive_wins"] == 2
    assert m["max_consecutive_losses"] == 2
    assert m["avg_trade_duration"] == pytest.approx(16 / 6)


def test_profit_factor_without_losses_is_undefined():
    assert _metrics([100, 110], trades=[_trade(5), _trade(5)])["profit_factor"] is None


def test_results_are_plain_finite_values():
    m = _metrics([100, 0, 0])
    for key, value in m.items():
        assert value is None or isinstance(value, (int, float)), key
        assert value is None or math.isfinite(value), key
