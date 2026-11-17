import numpy as np
import pandas as pd

from app.strategy_engine.schemas.strategy_definition import StrategyDefinition


def make_bars(close, open_=None, high=None, low=None, volume=None, start="2024-01-01", freq="D"):
    """Build an OHLCV DataFrame like MarketDataLoader returns."""
    close = np.asarray(close, dtype=float)
    open_ = close.copy() if open_ is None else np.asarray(open_, dtype=float)
    high = np.maximum(open_, close) + 0.5 if high is None else np.asarray(high, dtype=float)
    low = np.minimum(open_, close) - 0.5 if low is None else np.asarray(low, dtype=float)
    volume = np.full(len(close), 1000.0) if volume is None else np.asarray(volume, dtype=float)
    return pd.DataFrame({
        "datetime": pd.date_range(start, periods=len(close), freq=freq, tz="UTC"),
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })


def random_walk(n=300, seed=0, start=100.0):
    rng = np.random.default_rng(seed)
    close = start + rng.standard_normal(n).cumsum()
    open_ = np.concatenate([[start], close[:-1]]) + rng.normal(0, 0.2, n)
    return make_bars(close, open_=open_, volume=rng.integers(100, 10_000, n))


def price(field="close"):
    return {"type": "price", "field": field}


def value(v):
    return {"type": "value", "value": v}


def indicator(name, **params):
    return {"type": "indicator", "indicator": name, "params": params}


def cond(left, op, right):
    return {"type": "condition", "left": left, "operator": op, "right": right}


def group(op, *children):
    return {"type": "group", "operator": op, "children": list(children)}


def strategy(long_entry, long_exit, short_entry=None, short_exit=None):
    return StrategyDefinition.model_validate({
        "long_entry": long_entry, "long_exit": long_exit,
        "short_entry": short_entry, "short_exit": short_exit,
    })
