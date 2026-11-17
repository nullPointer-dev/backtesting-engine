from datetime import timedelta

from sqlalchemy import func
from sqlalchemy import select

from app.core.database import SessionLocal

from app.ingestion.assets import (
    SUPPORTED_SYMBOLS,
    SUPPORTED_TIMEFRAMES
)
from app.ingestion.yfinance_client import (
    fetch_data
)

from app.ingestion.loader import (
    load_market_data,
    delete_oldest_rows
)

from app.models.market_data import (
    MarketData
)

from app.enums.types import (
    TimeFrame
)


SLIDING_WINDOW_TIMEFRAMES = {"1m", "5m", "15m", "30m", "60m"}


def download_and_store(
    symbol: str,
    timeframe: str,
    start: str | None = None
) -> int:

    dataframe = fetch_data(
        symbol=symbol,
        timeframe=timeframe,
        start=start
    )

    if dataframe.empty:

        print(
            f"    No data available"
        )

        return 0

    inserted_count = load_market_data(
        dataframe=dataframe,
        symbol=symbol,
        timeframe=timeframe
    )

    return inserted_count


def latest_datetime(
    symbol: str,
    timeframe: str
) -> object | None:

    session = SessionLocal()

    try:

        return session.scalar(
            select(
                func.max(
                    MarketData.datetime
                )
            ).where(
                MarketData.symbol == symbol,
                MarketData.timeframe == TimeFrame(
                    timeframe
                )
            )
        )

    finally:

        session.close()


def full_load(
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None
):

    symbols = symbols or sorted(SUPPORTED_SYMBOLS)
    timeframes = timeframes or SUPPORTED_TIMEFRAMES

    total = len(
        symbols
    )

    for index, symbol in enumerate(
        symbols,
        start=1
    ):

        print(
            f"\n[{index}/{total}] {symbol}"
        )

        for timeframe in (
            timeframes
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


def incremental_update(
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None
):

    symbols = symbols or sorted(SUPPORTED_SYMBOLS)
    timeframes = timeframes or SUPPORTED_TIMEFRAMES

    for symbol in (
        symbols
    ):

        print(
            f"\n{symbol}"
        )

        for timeframe in (
            timeframes
        ):

            try:

                last = latest_datetime(
                    symbol=symbol,
                    timeframe=timeframe
                )

                if last is None:

                    inserted = download_and_store(
                        symbol=symbol,
                        timeframe=timeframe
                    )

                else:

                    start = (
                        last - timedelta(days=2)
                    ).date().isoformat()

                    inserted = download_and_store(
                        symbol=symbol,
                        timeframe=timeframe,
                        start=start
                    )

                if inserted > 0 and timeframe in SLIDING_WINDOW_TIMEFRAMES:
                    # Intraday data is kept as a fixed-size window: Yahoo only
                    # serves recent intraday bars, so the table would otherwise
                    # grow without bound. Daily/weekly history is never deleted.
                    delete_oldest_rows(symbol, timeframe, inserted)
                    print(f"    Inserted {inserted} new rows, deleted {inserted} oldest rows")
                elif inserted > 0:
                    print(f"    Inserted {inserted} new rows")

                print(
                    f"[OK] {timeframe}"
                )

            except Exception as error:

                print(f"[ERROR]{timeframe}")

                print(
                    f"      {error}"
                )
