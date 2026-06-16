from app.strategy_engine.indicator_cache import IndicatorCache
from app.strategy_engine.indicator_registry import INDICATOR_REGISTRY
from app.strategy_engine.requirement_extractor import RequirementExtractor
from app.strategy_engine.schemas.strategy_definition import StrategyDefinition


class IndicatorPreloader:
    def __init__(
        self,
        dataframe,
        strategy: StrategyDefinition
    ):
        self.dataframe = dataframe
        self.strategy = strategy

    def preload(self):
        cache = IndicatorCache()
        requirements = (RequirementExtractor().extract(self.strategy))
        for indicator, params_tuple in requirements:
            params = dict(params_tuple)
            metadata = (INDICATOR_REGISTRY[indicator])
            function = metadata["function"]
            translated_params = (
                self._translate_params(
                    params,
                    metadata["param_mapping"]
                )
            )

            result = (self._compute_indicator(metadata, function, translated_params))
            cache.set(
                indicator=indicator,
                params=params,
                series=result
            )

        return cache

    def _translate_params(
        self,
        params,
        mapping
    ):

        translated = {}
        for key, value in (params.items()):
            translated[mapping.get(key, key)] = value

        return translated

    def _compute_indicator(
        self,
        metadata,
        function,
        params
    ):

        arguments = []
        for column in (metadata["price_columns"]):
            arguments.append(self.dataframe[column])

        result = function(*arguments,**params)
        column_prefix = (metadata["column_prefix"])

        if column_prefix is None:
            return result

        for column in (result.columns):

            if column.startswith(column_prefix):
                return result[column]

        raise ValueError(
            f"Could not find column "
            f"starting with "
            f"{column_prefix}"
        )