from pandas import Series


class IndicatorCache:
    def __init__(self):
        self._cache = {}

    @staticmethod
    def build_key(indicator: str,params: dict) -> str:
        parameter_string = "|".join(
            f"{key}={value}"
            for key, value in sorted(
                params.items()
            )
        )

        return (
            f"{indicator}|"
            f"{parameter_string}"
        )

    def get(self,indicator: str, params: dict):

        key = self.build_key(indicator, params)
        return self._cache.get(key)

    def set(self, indicator: str, params: dict, series: Series):
        key = self.build_key(indicator, params)
        self._cache[key] = series

    def exists(self,indicator: str, params: dict) -> bool:
        key = self.build_key(indicator, params) 
        return key in self._cache