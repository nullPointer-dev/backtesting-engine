"""Performance statistics computed from a per-bar equity series.

Conventions:
- Percentages are expressed as percent (12.5 means 12.5%).
- ``max_drawdown`` is negative (e.g. -18.2) and ``max_drawdown_duration`` is
  the longest stretch, in bars, spent below a previous equity peak.
- Sharpe and Sortino use a zero risk-free rate and are annualised with the
  number of bars per year for the timeframe.
- Ratios that would be infinite or undefined (e.g. profit factor with no
  losing trades) are returned as None.
"""

import math

import numpy as np
import pandas as pd

from app.enums.types import TimeFrame

# NSE trades 09:15-15:30 (375 minutes) on roughly 252 days a year. Yahoo's
# 30m and 60m bars start at 09:15, giving 13 and 7 bars per session.
TRADING_DAYS_PER_YEAR = 252
BARS_PER_YEAR = {
    TimeFrame.ONE_MINUTE: 375 * TRADING_DAYS_PER_YEAR,
    TimeFrame.FIVE_MINUTES: 75 * TRADING_DAYS_PER_YEAR,
    TimeFrame.FIFTEEN_MINUTES: 25 * TRADING_DAYS_PER_YEAR,
    TimeFrame.THIRTY_MINUTES: 13 * TRADING_DAYS_PER_YEAR,
    TimeFrame.ONE_HOUR: 7 * TRADING_DAYS_PER_YEAR,
    TimeFrame.ONE_DAY: TRADING_DAYS_PER_YEAR,
    TimeFrame.ONE_WEEK: 52,
}


class PerformanceMetrics:

    def __init__(
        self,
        trades: list[dict],
        equity: np.ndarray,
        timestamps: pd.Series,
        initial_capital: float,
        timeframe: TimeFrame,
    ):
        self.trades = trades
        self.equity = np.asarray(equity, dtype=float)
        self.timestamps = pd.to_datetime(timestamps, utc=True)
        self.initial_capital = float(initial_capital)
        self.bars_per_year = BARS_PER_YEAR[TimeFrame(timeframe)]

    def calculate(self) -> dict:
        final_capital = float(self.equity[-1]) if self.equity.size else self.initial_capital
        net_profit = final_capital - self.initial_capital

        # Prepend the starting capital so the first bar's move counts as a return.
        path = np.concatenate([[self.initial_capital], self.equity])
        returns = _safe_returns(path)
        drawdowns = _drawdowns(path)

        max_drawdown = float(drawdowns.min() * 100) if drawdowns.size else 0.0
        cagr = self._cagr(final_capital)
        largest_drawdown_amount = float((np.maximum.accumulate(path) - path).max()) if path.size else 0.0

        metrics = {
            "final_capital": final_capital,
            "net_profit": net_profit,
            "total_return": (net_profit / self.initial_capital) * 100,
            "cagr": cagr,
            "sharpe_ratio": self._sharpe(returns),
            "sortino_ratio": self._sortino(returns),
            "calmar_ratio": (cagr / abs(max_drawdown)) if max_drawdown < 0 and cagr is not None else None,
            "recovery_factor": (net_profit / largest_drawdown_amount) if largest_drawdown_amount > 0 else None,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": _longest_underwater(drawdowns),
            "ulcer_index": float(math.sqrt(np.mean((drawdowns * 100) ** 2))) if drawdowns.size else 0.0,
            **self._trade_metrics(),
        }
        return {key: _clean(value) for key, value in metrics.items()}

    # ------------------------------------------------------------------

    def _cagr(self, final_capital: float) -> float | None:
        if len(self.timestamps) < 2:
            return None
        years = (self.timestamps.iloc[-1] - self.timestamps.iloc[0]).total_seconds() / (365.25 * 86400)
        if years <= 0:
            return None
        if final_capital <= 0:
            return -100.0
        return ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100

    def _sharpe(self, returns: np.ndarray) -> float | None:
        if returns.size < 2:
            return None
        std = returns.std(ddof=1)
        if std == 0:
            return None
        return float(returns.mean() / std * math.sqrt(self.bars_per_year))

    def _sortino(self, returns: np.ndarray) -> float | None:
        if returns.size < 2:
            return None
        downside_deviation = math.sqrt(np.mean(np.minimum(returns, 0.0) ** 2))
        if downside_deviation == 0:
            return None
        return float(returns.mean() / downside_deviation * math.sqrt(self.bars_per_year))

    def _trade_metrics(self) -> dict:
        total = len(self.trades)
        if total == 0:
            return {
                "total_trades": 0,
                "win_rate": None,
                "loss_rate": None,
                "profit_factor": None,
                "expectancy": None,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "avg_trade_duration": None,
            }

        pnls = [trade["pnl"] for trade in self.trades]
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = -sum(p for p in pnls if p < 0)
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)

        max_wins = max_losses = current_wins = current_losses = 0
        for pnl in pnls:
            if pnl > 0:
                current_wins, current_losses = current_wins + 1, 0
            elif pnl < 0:
                current_wins, current_losses = 0, current_losses + 1
            else:
                current_wins = current_losses = 0
            max_wins = max(max_wins, current_wins)
            max_losses = max(max_losses, current_losses)

        return {
            "total_trades": total,
            "win_rate": wins / total * 100,
            "loss_rate": losses / total * 100,
            "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
            "expectancy": sum(pnls) / total,
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
            "avg_trade_duration": float(np.mean([trade["duration_bars"] for trade in self.trades])),
        }


def _safe_returns(path: np.ndarray) -> np.ndarray:
    if path.size < 2:
        return np.array([])
    previous = path[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        returns = np.where(previous > 0, np.diff(path) / previous, 0.0)
    return returns[np.isfinite(returns)]


def _drawdowns(path: np.ndarray) -> np.ndarray:
    """Fractional drawdown from the running peak at each point (<= 0)."""
    if path.size == 0:
        return np.array([])
    peaks = np.maximum.accumulate(path)
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdowns = np.where(peaks > 0, (path - peaks) / peaks, 0.0)
    return np.maximum(drawdowns, -1.0)


def _longest_underwater(drawdowns: np.ndarray) -> int:
    longest = current = 0
    for value in drawdowns:
        current = current + 1 if value < 0 else 0
        longest = max(longest, current)
    return longest


def _clean(value):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    return value
