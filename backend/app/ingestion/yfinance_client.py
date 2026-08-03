import pandas as pd
import yfinance as yf


def fetch_data(
    symbol: str,
    timeframe: str,
    start: str | None = None
) -> pd.DataFrame:

    ticker = yf.Ticker(symbol)

    if start is not None:

        dataframe = ticker.history(
            start=start,
            interval=timeframe,
            auto_adjust=False
        )

    else:

        dataframe = ticker.history(
            period="max",
            interval=timeframe,
            auto_adjust=False
        )

    if dataframe.empty:
        return dataframe

    if isinstance(
        dataframe.columns,
        pd.MultiIndex
    ):
        dataframe.columns = (
            dataframe.columns
            .get_level_values(0)
        )

    return dataframe