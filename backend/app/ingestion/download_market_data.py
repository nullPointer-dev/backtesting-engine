from app.ingestion.assets import (
    SUPPORTED_SYMBOLS,
    SUPPORTED_TIMEFRAMES
)
from app.ingestion.yfinance_client import (
    fetch_data
)

from app.ingestion.loader import (
    load_market_data
)


def download_and_store(
    symbol: str,
    timeframe: str
):

    dataframe = fetch_data(
        symbol=symbol,
        timeframe=timeframe
    )

    if dataframe.empty:

        print(
            f"    No data available"
        )

        return

    load_market_data(
        dataframe=dataframe,
        symbol=symbol,
        timeframe=timeframe
    )


if __name__ == "__main__":

    total = len(
        SUPPORTED_SYMBOLS
    )

    for index, symbol in enumerate(
        SUPPORTED_SYMBOLS,
        start=1
    ):

        print(
            f"\n[{index}/{total}] {symbol}"
        )

        for timeframe in (
            SUPPORTED_TIMEFRAMES
        ):

            try:

                download_and_store(
                    symbol=symbol,
                    timeframe=timeframe
                )

                print(
                    f"[OK] {timeframe}"
                )

            except Exception as error:

                print(f"[ERROR]{timeframe}")

                print(
                    f"      {error}"
                )