"""Catalogue of the technical indicators a strategy can use.

Each entry describes how to compute the indicator with pandas_ta:

- ``function``: the pandas_ta function to call.
- ``price_columns``: DataFrame columns passed positionally, in order.
- ``params``: the parameters a strategy may set, keyed by the name used in the
  strategy JSON. Each ``Param`` names the pandas_ta keyword argument(s) it maps
  to, its type, default (pandas_ta's own default) and bounds.
- ``column_prefix``: for functions that return several columns, the prefix of
  the column to use. ``None`` means the function returns a single Series.
"""

from dataclasses import dataclass, field

import pandas_ta as ta


@dataclass(frozen=True)
class Param:
    arg: str | tuple[str, ...]
    type: type
    default: float
    min: float | None = None
    max: float | None = None
    description: str = ""

    @property
    def args(self) -> tuple[str, ...]:
        return (self.arg,) if isinstance(self.arg, str) else self.arg


@dataclass(frozen=True)
class Indicator:
    label: str
    category: str
    function: object
    price_columns: list[str]
    params: dict[str, Param] = field(default_factory=dict)
    column_prefix: str | None = None


def _period(default: int, description: str = "Lookback length in bars") -> Param:
    return Param("length", int, default, min=1, max=1000, description=description)


_MACD_PARAMS = {
    "fast_period": Param("fast", int, 12, min=1, max=1000, description="Fast EMA length"),
    "slow_period": Param("slow", int, 26, min=1, max=1000, description="Slow EMA length"),
    "signal_period": Param("signal", int, 9, min=1, max=1000, description="Signal EMA length"),
}

_STOCH_PARAMS = {
    "k_period": Param("k", int, 14, min=1, max=1000, description="%K lookback"),
    "d_period": Param("d", int, 3, min=1, max=1000, description="%D smoothing"),
    "smooth_period": Param("smooth_k", int, 3, min=1, max=1000, description="%K smoothing"),
}

_STOCHRSI_PARAMS = {
    "period": _period(14, "Stochastic lookback"),
    "rsi_period": Param("rsi_length", int, 14, min=1, max=1000, description="RSI length"),
    "k_period": Param("k", int, 3, min=1, max=1000, description="%K smoothing"),
    "d_period": Param("d", int, 3, min=1, max=1000, description="%D smoothing"),
}

_BBANDS_PARAMS = {
    "period": _period(5),
    "std_dev": Param(
        ("lower_std", "upper_std"), float, 2.0, min=0.1, max=10,
        description="Band width in standard deviations",
    ),
}

_HLC = ["high", "low", "close"]
_HLCV = ["high", "low", "close", "volume"]


INDICATOR_REGISTRY: dict[str, Indicator] = {
    # Moving averages
    "SMA": Indicator("Simple Moving Average", "Moving Averages", ta.sma, ["close"], {"period": _period(10)}),
    "EMA": Indicator("Exponential Moving Average", "Moving Averages", ta.ema, ["close"], {"period": _period(10)}),
    "WMA": Indicator("Weighted Moving Average", "Moving Averages", ta.wma, ["close"], {"period": _period(10)}),
    "VWMA": Indicator("Volume Weighted Moving Average", "Moving Averages", ta.vwma, ["close", "volume"], {"period": _period(10)}),

    # Momentum
    "RSI": Indicator("Relative Strength Index", "Momentum", ta.rsi, ["close"], {"period": _period(14)}),
    "ROC": Indicator("Rate of Change", "Momentum", ta.roc, ["close"], {"period": _period(10)}),
    "MOM": Indicator("Momentum", "Momentum", ta.mom, ["close"], {"period": _period(10)}),
    "CCI": Indicator("Commodity Channel Index", "Momentum", ta.cci, _HLC, {"period": _period(14)}),

    # MACD
    "MACD_LINE": Indicator("MACD Line", "MACD", ta.macd, ["close"], _MACD_PARAMS, "MACD_"),
    "MACD_SIGNAL": Indicator("MACD Signal", "MACD", ta.macd, ["close"], _MACD_PARAMS, "MACDs_"),
    "MACD_HISTOGRAM": Indicator("MACD Histogram", "MACD", ta.macd, ["close"], _MACD_PARAMS, "MACDh_"),

    # Stochastics
    "STOCH_K": Indicator("Stochastic %K", "Stochastics", ta.stoch, _HLC, _STOCH_PARAMS, "STOCHk_"),
    "STOCH_D": Indicator("Stochastic %D", "Stochastics", ta.stoch, _HLC, _STOCH_PARAMS, "STOCHd_"),
    "STOCHRSI_K": Indicator("Stochastic RSI %K", "Stochastics", ta.stochrsi, ["close"], _STOCHRSI_PARAMS, "STOCHRSIk_"),
    "STOCHRSI_D": Indicator("Stochastic RSI %D", "Stochastics", ta.stochrsi, ["close"], _STOCHRSI_PARAMS, "STOCHRSId_"),

    # Volatility
    "ATR": Indicator("Average True Range", "Volatility", ta.atr, _HLC, {"period": _period(14)}),
    "BB_UPPER": Indicator("Bollinger Band Upper", "Volatility", ta.bbands, ["close"], _BBANDS_PARAMS, "BBU_"),
    "BB_MIDDLE": Indicator("Bollinger Band Middle", "Volatility", ta.bbands, ["close"], _BBANDS_PARAMS, "BBM_"),
    "BB_LOWER": Indicator("Bollinger Band Lower", "Volatility", ta.bbands, ["close"], _BBANDS_PARAMS, "BBL_"),

    # Trend
    "ADX": Indicator("Average Directional Index", "Trend", ta.adx, _HLC, {"period": _period(14)}, "ADX_"),
    "SUPERTREND": Indicator(
        "Supertrend", "Trend", ta.supertrend, _HLC,
        {
            "period": _period(7, "ATR length"),
            "multiplier": Param("multiplier", float, 3.0, min=0.1, max=20, description="ATR multiplier"),
        },
        "SUPERT_",
    ),

    # Volume
    "OBV": Indicator("On-Balance Volume", "Volume", ta.obv, ["close", "volume"]),
    "MFI": Indicator("Money Flow Index", "Volume", ta.mfi, _HLCV, {"period": _period(14)}),
    "CMF": Indicator("Chaikin Money Flow", "Volume", ta.cmf, _HLCV, {"period": _period(20)}),
}


def resolve_params(indicator: Indicator, params: dict) -> dict:
    """Fill in defaults and return the full, typed parameter set for an indicator."""
    resolved = {}
    for name, spec in indicator.params.items():
        value = params.get(name, spec.default)
        resolved[name] = spec.type(value)
    return resolved


def to_function_kwargs(indicator: Indicator, resolved_params: dict) -> dict:
    """Translate strategy parameter names into pandas_ta keyword arguments."""
    kwargs = {}
    for name, value in resolved_params.items():
        for arg in indicator.params[name].args:
            kwargs[arg] = value
    return kwargs


def describe_registry() -> list[dict]:
    """JSON-friendly description of every indicator, for the API and UI."""
    return [
        {
            "name": name,
            "label": indicator.label,
            "category": indicator.category,
            "inputs": indicator.price_columns,
            "params": [
                {
                    "name": param_name,
                    "type": spec.type.__name__,
                    "default": spec.default,
                    "min": spec.min,
                    "max": spec.max,
                    "description": spec.description,
                }
                for param_name, spec in indicator.params.items()
            ],
        }
        for name, indicator in INDICATOR_REGISTRY.items()
    ]
