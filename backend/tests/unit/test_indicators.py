import numpy as np
import pandas as pd
import pytest

from app.backtesting.indicator_preloader import IndicatorPreloader
from app.strategy_engine.indicator_registry import INDICATOR_REGISTRY, describe_registry
from tests.helpers import cond, indicator, make_bars, random_walk, strategy, value


def _compute(df, name, **params):
    operand = indicator(name, **params)
    definition = strategy(cond(operand, ">", value(0)), cond(operand, "<", value(0)))
    return IndicatorPreloader(df, definition).preload().get(name, params)


@pytest.mark.parametrize("name", sorted(INDICATOR_REGISTRY))
def test_every_indicator_computes_aligned_series(name):
    df = random_walk(300)
    series = _compute(df, name)
    assert isinstance(series, pd.Series)
    assert len(series) == len(df)
    assert series.index.equals(df.index)
    assert series.notna().sum() > 200, f"{name} produced mostly NaN"


def test_defaults_match_explicit_parameters():
    df = random_walk(100)
    pd.testing.assert_series_equal(_compute(df, "SMA"), _compute(df, "SMA", period=10), check_names=False)


def test_sma_values():
    df = make_bars([1, 2, 3, 4, 5])
    series = _compute(df, "SMA", period=3)
    assert series.isna().tolist()[:2] == [True, True]
    assert series.iloc[2:].tolist() == pytest.approx([2.0, 3.0, 4.0])


def test_bollinger_std_dev_is_applied():
    df = random_walk(100)
    narrow = _compute(df, "BB_UPPER", period=20, std_dev=1)
    wide = _compute(df, "BB_UPPER", period=20, std_dev=3)
    middle = _compute(df, "BB_MIDDLE", period=20)
    gap_narrow = (narrow - middle).dropna()
    gap_wide = (wide - middle).dropna()
    assert np.allclose(gap_wide, gap_narrow * 3)


def test_too_little_data_gives_all_nan():
    df = make_bars([1, 2, 3])
    series = _compute(df, "SMA", period=50)
    assert len(series) == 3 and series.isna().all()


def test_registry_description_is_complete():
    described = {item["name"]: item for item in describe_registry()}
    assert set(described) == set(INDICATOR_REGISTRY)
    macd = described["MACD_LINE"]
    assert [p["name"] for p in macd["params"]] == ["fast_period", "slow_period", "signal_period"]
    assert macd["params"][0]["default"] == 12 and macd["params"][0]["type"] == "int"
