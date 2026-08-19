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


def full_load():

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


def incremental_update():

    for symbol in (
        SUPPORTED_SYMBOLS
    ):

        print(
            f"\n{symbol}"
        )

        for timeframe in (
            SUPPORTED_TIMEFRAMES
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

                if inserted > 0:
                    delete_oldest_rows(symbol, timeframe, inserted)
                    print(f"    Inserted {inserted} new rows, deleted {inserted} oldest rows")

                print(
                    f"[OK] {timeframe}"
                )

            except Exception as error:

                print(f"[ERROR]{timeframe}")

                print(
                    f"      {error}"
                )
