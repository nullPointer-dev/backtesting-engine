import pandas as pd
import yfinance as yf


def fetch_data(
    symbol: str,
    timeframe: str
) -> pd.DataFrame:

    ticker = yf.Ticker(symbol)

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