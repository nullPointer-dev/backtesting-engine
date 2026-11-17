import pytest

from app.backtesting.execution_engine import ExecutionEngine
from app.backtesting.indicator_preloader import IndicatorPreloader
from app.backtesting.portfolio_engine import PortfolioEngine
from app.enums.types import PositionSide, PositionSizingType
from tests.helpers import cond, make_bars, price, strategy, value

CLOSE = [10, 10, 12, 12, 9, 9, 11, 11]
OPEN = [10, 10, 11, 12, 11, 9, 10, 11]
DEFINITION = strategy(
    cond(price("close"), ">", value(10.5)),
    cond(price("close"), "<", value(10)),
    cond(price("close"), "<", value(9.5)),
    cond(price("close"), ">", value(10)),
)


@pytest.fixture
def bars():
    return make_bars(CLOSE, open_=OPEN)


@pytest.fixture
def raw_trades(bars):
    cache = IndicatorPreloader(bars, DEFINITION).preload()
    return ExecutionEngine("TEST", bars, DEFINITION, cache).run()


def _engine(sizing=PositionSizingType.FIXED_QUANTITY, **kwargs):
    kwargs.setdefault("quantity", 10 if sizing == PositionSizingType.FIXED_QUANTITY else None)
    return PortfolioEngine(initial_capital=1000, position_sizing_type=sizing, **kwargs)


def test_fixed_quantity_with_commission(bars, raw_trades):
    result = _engine(commission_pct=0.1).run(bars, raw_trades)
    trades = result["trades"]

    # Long 10 @ 12 -> 9: -30, commission 0.12 + 0.09
    assert trades[0]["side"] == PositionSide.LONG
    assert trades[0]["pnl"] == pytest.approx(-30.21)
    assert trades[0]["commission"] == pytest.approx(0.21)
    assert trades[0]["return_pct"] == pytest.approx(-30.21 / 120 * 100)
    # Short 10 @ 9 -> 11: -20, commission 0.09 + 0.11
    assert trades[1]["pnl"] == pytest.approx(-20.20)
    # Long 10 @ 11, closed at the final close of 11: commission only
    assert trades[2]["pnl"] == pytest.approx(-0.22)

    expected_equity = [1000, 1000, 1000, 999.88, 969.88, 969.70, 949.70, 949.37]
    assert result["equity"].tolist() == pytest.approx(expected_equity)
    assert result["final_capital"] == pytest.approx(949.37)
    assert result["total_commission"] == pytest.approx(0.63)
    assert result["exposure_pct"] == pytest.approx(5 / 8 * 100)
    assert result["skipped_trades"] == 0


def test_equity_curve_has_a_timestamp_per_bar(bars, raw_trades):
    curve = _engine().run(bars, raw_trades)["equity_curve"]
    assert len(curve) == len(bars)
    assert curve[0] == {"time": bars["datetime"].iloc[0].isoformat(), "equity": 1000.0}


def test_slippage_moves_fills_against_the_trader(bars, raw_trades):
    trades = _engine(slippage_pct=1).run(bars, raw_trades)["trades"]
    long_trade, short_trade = trades[0], trades[1]
    assert long_trade["entry_price"] == pytest.approx(12 * 1.01)   # buy higher
    assert long_trade["exit_price"] == pytest.approx(9 * 0.99)     # sell lower
    assert short_trade["entry_price"] == pytest.approx(9 * 0.99)   # sell lower
    assert short_trade["exit_price"] == pytest.approx(11 * 1.01)   # buy back higher


def test_fixed_quantity_is_capped_by_available_equity(bars, raw_trades):
    trades = _engine(quantity=1000).run(bars, raw_trades[:1])["trades"]
    assert trades[0]["quantity"] == pytest.approx(1000 / 12)


def test_percent_of_capital_uses_current_equity(bars, raw_trades):
    result = _engine(PositionSizingType.PERCENT_OF_CAPITAL, position_size_percent=50).run(bars, raw_trades)
    first, second = result["trades"][0], result["trades"][1]
    assert first["quantity"] == pytest.approx(500 / 12)
    equity_after_first = 1000 + first["pnl"]
    assert second["quantity"] == pytest.approx(equity_after_first * 0.5 / 9)


def test_excursions(bars, raw_trades):
    trades = _engine().run(bars, raw_trades)["trades"]
    # Long from 12 held over bars 3-4: lowest low 8.5, highest high 12.5
    assert trades[0]["mae_pct"] == pytest.approx((8.5 / 12 - 1) * 100)
    assert trades[0]["mfe_pct"] == pytest.approx((12.5 / 12 - 1) * 100)
    # Short from 9 held over bars 5-6: highest high 11.5 hurts, lowest low 8.5 helps
    assert trades[1]["mae_pct"] == pytest.approx((1 - 11.5 / 9) * 100)
    assert trades[1]["mfe_pct"] == pytest.approx((1 - 8.5 / 9) * 100)
    for trade in trades:
        assert trade["mae_pct"] <= 0 <= trade["mfe_pct"]


def test_trades_are_skipped_once_equity_is_gone():
    bars = make_bars([10, 10, 1, 1, 1], open_=[10, 10, 10, 0.5, 1])
    raw = [
        {"symbol": "T", "side": PositionSide.SHORT, "entry_index": 1, "entry_price": 10.0, "exit_index": 2,
         "exit_price": 30.0, "exit_reason": "SIGNAL", "duration_bars": 1,
         "entry_time": bars["datetime"].iloc[1], "exit_time": bars["datetime"].iloc[2]},
        {"symbol": "T", "side": PositionSide.LONG, "entry_index": 3, "entry_price": 0.5, "exit_index": 4,
         "exit_price": 1.0, "exit_reason": "SIGNAL", "duration_bars": 1,
         "entry_time": bars["datetime"].iloc[3], "exit_time": bars["datetime"].iloc[4]},
    ]
    result = _engine(PositionSizingType.PERCENT_OF_CAPITAL, position_size_percent=100).run(bars, raw)
    assert result["final_capital"] < 0
    assert len(result["trades"]) == 1
    assert result["skipped_trades"] == 1


def test_missing_sizing_parameter_is_rejected():
    with pytest.raises(ValueError):
        PortfolioEngine(1000, PositionSizingType.FIXED_QUANTITY)
    with pytest.raises(ValueError):
        PortfolioEngine(1000, PositionSizingType.PERCENT_OF_CAPITAL)
