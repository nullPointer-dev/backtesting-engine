from app.enums.types import PositionSide

from app.strategy_engine.evaluator import Evaluator


class ExecutionEngine:

    def __init__(self, symbol: str, dataframe, strategy, indicator_cache):
        self.dataframe = dataframe
        self.symbol = symbol
        self.strategy = strategy
        self.evaluator = Evaluator(dataframe, indicator_cache)

    def run(self):
        trades = []
        position = None

        for index in range(len(self.dataframe) - 1):
            if position is None:
                if self.evaluator.evaluate(self.strategy.long_entry, index):
                    position = {
                        "symbol": self.symbol,
                        "side": PositionSide.LONG,
                        "entry_time": self.dataframe["datetime"].iloc[index + 1],
                        "entry_price": self.dataframe["open"].iloc[index + 1],
                        "entry_index": index + 1
                    }
                    continue

                if (self.strategy.short_entry and self.evaluator.evaluate(self.strategy.short_entry, index)):
                    position = {
                        "symbol": self.symbol,
                        "side": PositionSide.SHORT,
                        "entry_time": self.dataframe["datetime"].iloc[index + 1],
                        "entry_price": self.dataframe["open"].iloc[index + 1],
                        "entry_index": index + 1
                    }
                    continue

            else:
                if (position["side"]== PositionSide.LONG):
                    if self.evaluator.evaluate(self.strategy.long_exit, index):
                        trades.append(self._close_position(position, index))
                        position = None

                else:
                    if (self.strategy.short_exit and self.evaluator.evaluate(self.strategy.short_exit, index)):
                        trades.append(self._close_position(position, index))
                        position = None

        return trades

    def _close_position(self, position, index):
        exit_time = (self.dataframe["datetime"].iloc[index + 1])
        exit_price = (self.dataframe["open"].iloc[index + 1])

        if (position["side"] == PositionSide.LONG):
            pnl = (exit_price - position["entry_price"])

        else:
            pnl = (position["entry_price"] - exit_price)
        
        duration_bars = index + 1 - position["entry_index"]

        return {
            "symbol": position["symbol"],
            "side": position["side"],
            "entry_time": position["entry_time"],
            "entry_price": position["entry_price"],
            "exit_time": exit_time,
            "exit_price": exit_price,
            "pnl": pnl,
            "duration_bars": duration_bars
        }