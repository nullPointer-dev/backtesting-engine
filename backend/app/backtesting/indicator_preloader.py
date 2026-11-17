import numpy as np
import pandas as pd

from app.strategy_engine.indicator_cache import IndicatorCache
from app.strategy_engine.indicator_registry import (
    INDICATOR_REGISTRY,
    resolve_params,
    to_function_kwargs,
)
from app.strategy_engine.requirement_extractor import RequirementExtractor
from app.strategy_engine.schemas.strategy_definition import StrategyDefinition


class IndicatorPreloader:
    """Computes every indicator a strategy needs once, over the whole price series."""

    def __init__(self, dataframe: pd.DataFrame, strategy: StrategyDefinition):
        self.dataframe = dataframe
        self.strategy = strategy

    def preload(self) -> IndicatorCache:
        cache = IndicatorCache()
        requirements = RequirementExtractor().extract(self.strategy)

        for name, params_tuple in requirements:
            params = dict(params_tuple)
            indicator = INDICATOR_REGISTRY.get(name)
            if indicator is None:
                raise ValueError(f"Unknown indicator '{name}'")

            kwargs = to_function_kwargs(indicator, resolve_params(indicator, params))
            series = self._compute(indicator, kwargs)
            cache.set(indicator=name, params=params, series=series)

        return cache

    def _compute(self, indicator, kwargs) -> pd.Series:
        arguments = [self.dataframe[column] for column in indicator.price_columns]
        result = indicator.function(*arguments, **kwargs)

        # pandas_ta returns None when there are fewer bars than the lookback
        # needs. Treat that as "no value yet" on every bar.
        if result is None:
            return pd.Series(np.nan, index=self.dataframe.index)

        if indicator.column_prefix is None:
            return result.reindex(self.dataframe.index)

        for column in result.columns:
            if column.startswith(indicator.column_prefix):
                return result[column].reindex(self.dataframe.index)

        raise ValueError(f"Could not find column starting with {indicator.column_prefix}")
