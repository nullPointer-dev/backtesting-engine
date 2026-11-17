"""Turns strategy rules into a list of signal-level trades.

Rules are evaluated on each bar's close and orders fill at the next bar's
open, so a decision never uses information from the bar it trades on.
Only one position is held at a time. When a position exits, the opposite
side's entry rule is checked on the same bar, so a strategy can reverse
from long to short (or back) without waiting a bar.

Prices here are raw market prices; sizing, slippage and commission are
applied later by the PortfolioEngine.
"""

from app.enums.types import PositionSide
from app.strategy_engine.evaluator import Evaluator


class BacktestCancelled(Exception):
    """Raised when a running backtest is cancelled by the user."""


EXIT_SIGNAL = "SIGNAL"
EXIT_END_OF_DATA = "END_OF_DATA"


class ExecutionEngine:

    def __init__(self, symbol: str, dataframe, strategy, indicator_cache):
        self.symbol = symbol
        self.dataframe = dataframe
        self.strategy = strategy
        self.evaluator = Evaluator(dataframe, indicator_cache)
        self._open_prices = dataframe["open"].to_numpy()
        self._close_prices = dataframe["close"].to_numpy()

    def run(self, checkpoint=None, check_every: int = 250) -> list[dict]:
        """Evaluate the rules bar by bar.

        ``checkpoint(index, bar_count)`` is called every ``check_every`` bars to
        report progress; returning True cancels the run.
        """
        trades = []
        position = None
        bar_count = len(self.dataframe)

        for index in range(bar_count - 1):
            if checkpoint is not None and index % check_every == 0 and checkpoint(index, bar_count):
                raise BacktestCancelled()

            if position is not None:
                if self._exit_signal(position["side"], index):
                    trades.append(self._close(position, exit_index=index + 1, reason=EXIT_SIGNAL))
                    closed_side = position["side"]
                    position = None
                    # Allow an immediate reversal into the opposite side.
                    opposite = PositionSide.SHORT if closed_side == PositionSide.LONG else PositionSide.LONG
                    if self._entry_signal(opposite, index):
                        position = self._open_position(opposite, index + 1)
                continue

            for side in (PositionSide.LONG, PositionSide.SHORT):
                if self._entry_signal(side, index):
                    position = self._open_position(side, index + 1)
                    break

        if position is not None:
            trades.append(self._close(position, exit_index=bar_count - 1, reason=EXIT_END_OF_DATA))

        return trades

    def _entry_signal(self, side: PositionSide, index: int) -> bool:
        rule = self.strategy.long_entry if side == PositionSide.LONG else self.strategy.short_entry
        return rule is not None and bool(self.evaluator.evaluate(rule, index))

    def _exit_signal(self, side: PositionSide, index: int) -> bool:
        rule = self.strategy.long_exit if side == PositionSide.LONG else self.strategy.short_exit
        return rule is not None and bool(self.evaluator.evaluate(rule, index))

    def _open_position(self, side: PositionSide, entry_index: int) -> dict:
        return {
            "side": side,
            "entry_index": entry_index,
            "entry_price": float(self._open_prices[entry_index]),
        }

    def _close(self, position: dict, exit_index: int, reason: str) -> dict:
        if reason == EXIT_END_OF_DATA:
            # Marked out at the final close; the last bar is fully held.
            exit_price = float(self._close_prices[exit_index])
            duration = exit_index - position["entry_index"] + 1
        else:
            exit_price = float(self._open_prices[exit_index])
            duration = exit_index - position["entry_index"]

        return {
            "symbol": self.symbol,
            "side": position["side"],
            "entry_index": position["entry_index"],
            "entry_time": self.dataframe["datetime"].iloc[position["entry_index"]],
            "entry_price": position["entry_price"],
            "exit_index": exit_index,
            "exit_time": self.dataframe["datetime"].iloc[exit_index],
            "exit_price": exit_price,
            "exit_reason": reason,
            "duration_bars": duration,
        }
