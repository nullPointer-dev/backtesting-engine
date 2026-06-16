import math
import numpy as np


class PerformanceMetrics:
    def __init__(
        self,
        trades,
        equity_curve,
        initial_capital,
        final_capital,
        start_date,
        end_date
    ):

        self.trades = trades
        self.equity_curve = np.array(equity_curve, dtype=float)
        self.initial_capital = (initial_capital)
        self.final_capital = (final_capital)
        self.start_date = start_date
        self.end_date = end_date

    def _python_scalar(self, value):
        if hasattr(value, "item"):
            return value.item()

        return value

    def calculate(self):
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        net_profit = (self.final_capital - self.initial_capital)
        total_return = (net_profit / self.initial_capital) * 100
        cagr = self._cagr()
        max_drawdown = (self._max_drawdown())
        max_drawdown_duration = (self._max_drawdown_duration())
        ulcer_index = (self._ulcer_index())
        sharpe_ratio = (self._sharpe_ratio(returns))
        sortino_ratio = (self._sortino_ratio(returns))
        calmar_ratio = ((cagr/abs(max_drawdown)) if max_drawdown != 0 else 0)
        drawdown_amt = self.initial_capital * abs(max_drawdown) / 100
        recovery_factor = ((net_profit / drawdown_amt) if drawdown_amt != 0 else 0)

        metrics = {
            "final_capital": self.final_capital,
            "total_return": total_return,
            "net_profit": net_profit,
            "cagr": cagr,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "recovery_factor": recovery_factor,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_drawdown_duration,
            "ulcer_index": ulcer_index,
            **self._trade_metrics()
        }

        return {
            key: self._python_scalar(value)
            for key, value in metrics.items()
        }

    def _cagr(self):
        years = ((self.end_date - self.start_date).days / 365.25)
        if years <= 0:
            return 0
        return ((self.final_capital / self.initial_capital) ** ( 1 / years) - 1) * 100

    def _max_drawdown(self):
        running_max = np.maximum.accumulate(self.equity_curve)
        drawdowns = (self.equity_curve - running_max) / running_max
        return (drawdowns.min() * 100)

    def _max_drawdown_duration(self):
        peak = self.equity_curve[0]
        duration = 0
        max_duration = 0
        for value in (self.equity_curve):
            if value >= peak:
                peak = value
                duration = 0
            else:
                duration += 1
                max_duration = max(max_duration, duration)

        return max_duration

    def _ulcer_index(self):
        running_max = np.maximum.accumulate(self.equity_curve)
        drawdowns = ((self.equity_curve - running_max) / running_max) * 100
        return math.sqrt(np.mean(drawdowns ** 2))

    def _sharpe_ratio(self, returns):
        if len(returns) == 0:
            return 0

        std = np.std(returns)

        if std == 0:
            return 0

        return (np.mean(returns)/std) * np.sqrt(len(returns))

    def _sortino_ratio(self, returns):

        downside = returns[returns < 0]

        if len(downside) == 0:
            return 0

        downside_std = np.std(downside)

        if downside_std == 0:
            return 0

        return (np.mean(returns) / downside_std) * np.sqrt(len(returns))

    def _trade_metrics(self):
        total_trades = len(self.trades)
        if total_trades == 0:
            return {
                "win_rate": 0,
                "loss_rate": 0,
                "profit_factor": 0,
                "expectancy": 0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "avg_trade_duration": 0,
                "total_trades": 0
            }

        wins = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] < 0]
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))

        return {
            "win_rate":(len(wins)/total_trades) * 100,
            "loss_rate":(len(losses)/total_trades) *100,
            "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else 0,
            "expectancy": (sum(t["pnl"] for t in self.trades) / total_trades) if total_trades > 0 else 0,
            "max_consecutive_wins": self._max_streak(True),
            "max_consecutive_losses": self._max_streak(False),
            "avg_trade_duration": np.mean([t["duration_bars"] for t in self.trades]),
            "total_trades":total_trades
        }

    def _max_streak(self, wins):
        best = 0
        current = 0
        for trade in (self.trades):
            condition = (trade["pnl"] > 0)
            if condition == wins:
                current += 1
                best = max(best, current)
            else:
                current = 0
        return best