"""Bar-by-bar portfolio simulation.

Takes the signal-level trades from the ExecutionEngine and works out what
actually happens to an account:

- position size (fixed quantity or a percent of current equity), capped so
  a position never costs more than the equity available;
- slippage: every fill is moved against the trader by ``slippage_pct``;
- commission: ``commission_pct`` of the traded value on entry and on exit;
- equity marked to market at every bar's close;
- per-trade MAE/MFE: the worst and best unrealised move while the trade was
  open, as a percent of the entry fill.
"""

import math

import numpy as np
import pandas as pd

from app.enums.types import PositionSide, PositionSizingType
from app.backtesting.execution_engine import EXIT_END_OF_DATA


class PortfolioEngine:

    def __init__(
        self,
        initial_capital: float,
        position_sizing_type: PositionSizingType,
        quantity: float | None = None,
        position_size_percent: float | None = None,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
    ):
        if position_sizing_type == PositionSizingType.FIXED_QUANTITY and quantity is None:
            raise ValueError("Quantity must be provided for FIXED_QUANTITY position sizing type")
        if position_sizing_type == PositionSizingType.PERCENT_OF_CAPITAL and position_size_percent is None:
            raise ValueError(
                "Position size percent must be provided for PERCENT_OF_CAPITAL position sizing type"
            )

        self.initial_capital = float(initial_capital)
        self.position_sizing_type = position_sizing_type
        self.quantity = quantity
        self.position_size_percent = position_size_percent
        self.commission_rate = (commission_pct or 0.0) / 100
        self.slippage_rate = (slippage_pct or 0.0) / 100

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, dataframe: pd.DataFrame, trades: list[dict]) -> dict:
        bar_count = len(dataframe)
        high = dataframe["high"].to_numpy(dtype=float)
        low = dataframe["low"].to_numpy(dtype=float)
        close = dataframe["close"].to_numpy(dtype=float)

        entries_at = {trade["entry_index"]: trade for trade in trades}
        signal_exits_at = {
            trade["exit_index"]: trade for trade in trades if trade["exit_reason"] != EXIT_END_OF_DATA
        }
        end_of_data_exits_at = {
            trade["exit_index"]: trade for trade in trades if trade["exit_reason"] == EXIT_END_OF_DATA
        }

        cash = self.initial_capital
        position = None  # {"trade", "side", "quantity", "entry_fill", "entry_commission"}
        equity = np.empty(bar_count, dtype=float)
        in_market = np.zeros(bar_count, dtype=bool)
        processed = []
        skipped = 0
        total_commission = 0.0

        for bar in range(bar_count):
            # 1. Exits that fill at this bar's open.
            if position is not None and bar in signal_exits_at:
                cash, record = self._exit(position, cash, high, low)
                total_commission += record["commission"] - position["entry_commission"]
                processed.append(record)
                position = None

            # 2. Entries that fill at this bar's open.
            if position is None and bar in entries_at:
                trade = entries_at[bar]
                opened = self._enter(trade, cash)
                if opened is None:
                    skipped += 1
                else:
                    cash, position = opened
                    total_commission += position["entry_commission"]

            # 3. Mark to market at the close.
            if position is not None:
                in_market[bar] = True
                position_value = position["quantity"] * close[bar]
                if position["side"] == PositionSide.LONG:
                    equity[bar] = cash + position_value
                else:
                    equity[bar] = cash - position_value
            else:
                equity[bar] = cash

            # 4. A position still open on the last bar is closed at its close.
            if position is not None and bar in end_of_data_exits_at:
                cash, record = self._exit(position, cash, high, low)
                total_commission += record["commission"] - position["entry_commission"]
                processed.append(record)
                position = None
                equity[bar] = cash

        times = dataframe["datetime"]
        equity_curve = [
            {"time": _iso(times.iloc[i]), "equity": _finite(equity[i])} for i in range(bar_count)
        ]

        return {
            "trades": processed,
            "skipped_trades": skipped,
            "final_capital": float(equity[-1]) if bar_count else self.initial_capital,
            "equity": equity,
            "equity_curve": equity_curve,
            "exposure_pct": float(in_market.mean() * 100) if bar_count else 0.0,
            "total_commission": total_commission,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fill_price(self, price: float, buying: bool) -> float:
        return price * (1 + self.slippage_rate) if buying else price * (1 - self.slippage_rate)

    def _enter(self, trade: dict, cash: float):
        side = trade["side"]
        buying = side == PositionSide.LONG
        fill = self._fill_price(trade["entry_price"], buying)
        if fill <= 0:
            return None

        # Cash equals equity whenever we are flat, which is the only time we enter.
        equity = cash
        if equity <= 0:
            return None

        cost_per_unit = fill * (1 + self.commission_rate)
        max_quantity = equity / cost_per_unit

        if self.position_sizing_type == PositionSizingType.FIXED_QUANTITY:
            quantity = min(float(self.quantity), max_quantity)
        else:
            quantity = (equity * self.position_size_percent / 100) / cost_per_unit

        if quantity <= 0:
            return None

        notional = quantity * fill
        commission = notional * self.commission_rate
        cash = cash - notional - commission if buying else cash + notional - commission

        return cash, {
            "trade": trade,
            "side": side,
            "quantity": quantity,
            "entry_fill": fill,
            "entry_commission": commission,
        }

    def _exit(self, position: dict, cash: float, high: np.ndarray, low: np.ndarray):
        trade = position["trade"]
        side = position["side"]
        quantity = position["quantity"]
        entry_fill = position["entry_fill"]

        selling = side == PositionSide.LONG
        exit_fill = self._fill_price(trade["exit_price"], buying=not selling)
        notional = quantity * exit_fill
        exit_commission = notional * self.commission_rate
        cash = cash + notional - exit_commission if selling else cash - notional - exit_commission

        direction = 1 if side == PositionSide.LONG else -1
        commission = position["entry_commission"] + exit_commission
        pnl = direction * (exit_fill - entry_fill) * quantity - commission
        cost_basis = entry_fill * quantity

        mae_pct, mfe_pct = self._excursions(trade, side, entry_fill, exit_fill, high, low)

        record = {
            **{k: v for k, v in trade.items() if k not in ("entry_price", "exit_price")},
            "entry_price": entry_fill,
            "exit_price": exit_fill,
            "quantity": quantity,
            "commission": commission,
            "pnl": pnl,
            "return_pct": (pnl / cost_basis) * 100 if cost_basis else 0.0,
            "mae_pct": mae_pct,
            "mfe_pct": mfe_pct,
        }
        return cash, record

    @staticmethod
    def _excursions(trade, side, entry_fill, exit_fill, high, low):
        start = trade["entry_index"]
        if trade["exit_reason"] == EXIT_END_OF_DATA:
            last_held = trade["exit_index"]
        else:
            # Filled at the exit bar's open, so only bars before it were held.
            last_held = max(start, trade["exit_index"] - 1)

        highest = max(float(high[start:last_held + 1].max()), entry_fill, exit_fill)
        lowest = min(float(low[start:last_held + 1].min()), entry_fill, exit_fill)

        if side == PositionSide.LONG:
            mae = (lowest / entry_fill - 1) * 100
            mfe = (highest / entry_fill - 1) * 100
        else:
            mae = (1 - highest / entry_fill) * 100
            mfe = (1 - lowest / entry_fill) * 100
        return min(mae, 0.0), max(mfe, 0.0)


def _iso(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _finite(value: float) -> float | None:
    value = float(value)
    return value if math.isfinite(value) else None
