from app.enums.types import PositionSizingType


class PortfolioEngine:

    def __init__(
        self,
        initial_capital: float,
        position_sizing_type: PositionSizingType,
        quantity: float | None = None,
        position_size_percent: float | None = None
    ):

        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position_sizing_type = (position_sizing_type)
        self.quantity = quantity
        self.position_size_percent = (position_size_percent)
        self.equity_curve = [initial_capital]

    def _python_scalar(self, value):
        if hasattr(value, "item"):
            return value.item()

        return value
    
    def process_trades(self, trades: list[dict]):
        processed_trades = []

        for trade in trades:
            trade_quantity = (self._python_scalar(self._calculate_quantity(trade)))
            total_pnl = (self._python_scalar(trade["pnl"] * trade_quantity))
            self.current_capital += total_pnl

            processed_trades.append(
                {
                    **trade,
                    "quantity": trade_quantity,
                    "pnl": total_pnl
                }
            )

            self.equity_curve.append(self.current_capital)

        return {
            "trades": processed_trades,
            "final_capital": float(self.current_capital),
            "total_return": float(((self.current_capital - self.initial_capital) / self.initial_capital) * 100),
            "equity_curve": [self._python_scalar(x) for x in self.equity_curve]
        }

    def _calculate_quantity(self, trade):
        if (self.position_sizing_type ==PositionSizingType.FIXED_QUANTITY):
            if self.quantity is None:
                raise ValueError("Quantity must be provided for FIXED_QUANTITY position sizing type")
            return float(self.quantity)

        if (self.position_sizing_type == PositionSizingType.PERCENT_OF_CAPITAL):
            if self.position_size_percent is None:
                raise ValueError("Position size percent must be provided for PERCENT_OF_CAPITAL position sizing type")

            capital_to_use = (self.current_capital * (self.position_size_percent / 100))
            return (capital_to_use / trade["entry_price"])

        raise ValueError(f"Unsupported position sizing type: {self.position_sizing_type}")