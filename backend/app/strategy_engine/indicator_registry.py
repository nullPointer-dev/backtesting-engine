import pandas_ta as ta


INDICATOR_REGISTRY = {

    # -------------------------
    # Moving Averages
    # -------------------------

    "SMA": {
        "function": ta.sma,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "EMA": {
        "function": ta.ema,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "WMA": {
        "function": ta.wma,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "VWMA": {
        "function": ta.vwma,
        "price_columns": [
            "close",
            "volume"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    # -------------------------
    # Momentum
    # -------------------------

    "RSI": {
        "function": ta.rsi,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "ROC": {
        "function": ta.roc,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "MOM": {
        "function": ta.mom,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "CCI": {
        "function": ta.cci,
        "price_columns": [
            "high",
            "low",
            "close"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    # -------------------------
    # MACD
    # -------------------------

    "MACD_LINE": {
        "function": ta.macd,
        "price_columns": ["close"],
        "param_mapping": {
            "fast_period": "fast",
            "slow_period": "slow",
            "signal_period": "signal"
        },
        "column_prefix": "MACD_"
    },

    "MACD_SIGNAL": {
        "function": ta.macd,
        "price_columns": ["close"],
        "param_mapping": {
            "fast_period": "fast",
            "slow_period": "slow",
            "signal_period": "signal"
        },
        "column_prefix": "MACDs_"
    },

    "MACD_HISTOGRAM": {
        "function": ta.macd,
        "price_columns": ["close"],
        "param_mapping": {
            "fast_period": "fast",
            "slow_period": "slow",
            "signal_period": "signal"
        },
        "column_prefix": "MACDh_"
    },

    # -------------------------
    # STOCH
    # -------------------------

    "STOCH_K": {
        "function": ta.stoch,
        "price_columns": [
            "high",
            "low",
            "close"
        ],
        "param_mapping": {
            "k_period": "k",
            "d_period": "d",
            "smooth_period": "smooth_k"
        },
        "column_prefix": "STOCHk_"
    },

    "STOCH_D": {
        "function": ta.stoch,
        "price_columns": [
            "high",
            "low",
            "close"
        ],
        "param_mapping": {
            "k_period": "k",
            "d_period": "d",
            "smooth_period": "smooth_k"
        },
        "column_prefix": "STOCHd_"
    },

    # -------------------------
    # STOCH RSI
    # -------------------------

    "STOCHRSI_K": {
        "function": ta.stochrsi,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": "STOCHRSIk_"
    },

    "STOCHRSI_D": {
        "function": ta.stochrsi,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": "STOCHRSId_"
    },

    # -------------------------
    # Volatility
    # -------------------------

    "ATR": {
        "function": ta.atr,
        "price_columns": [
            "high",
            "low",
            "close"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "BB_UPPER": {
        "function": ta.bbands,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length",
            "std_dev": "std"
        },
        "column_prefix": "BBU_"
    },

    "BB_MIDDLE": {
        "function": ta.bbands,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length",
            "std_dev": "std"
        },
        "column_prefix": "BBM_"
    },

    "BB_LOWER": {
        "function": ta.bbands,
        "price_columns": ["close"],
        "param_mapping": {
            "period": "length",
            "std_dev": "std"
        },
        "column_prefix": "BBL_"
    },

    # -------------------------
    # Trend
    # -------------------------

    "ADX": {
        "function": ta.adx,
        "price_columns": [
            "high",
            "low",
            "close"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": "ADX_"
    },

    "SUPERTREND": {
        "function": ta.supertrend,
        "price_columns": [
            "high",
            "low",
            "close"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": "SUPERT_"
    },

    # -------------------------
    # Volume
    # -------------------------

    "OBV": {
        "function": ta.obv,
        "price_columns": [
            "close",
            "volume"
        ],
        "param_mapping": {},
        "column_prefix": None
    },

    "MFI": {
        "function": ta.mfi,
        "price_columns": [
            "high",
            "low",
            "close",
            "volume"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    },

    "CMF": {
        "function": ta.cmf,
        "price_columns": [
            "high",
            "low",
            "close",
            "volume"
        ],
        "param_mapping": {
            "period": "length"
        },
        "column_prefix": None
    }
}