import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal

from app.models.market_data import (
    MarketData
)

from app.enums.types import (
    TimeFrame
)


def load_market_data(
    dataframe: pd.DataFrame,
    symbol: str,
    timeframe: str
) -> int:

    if dataframe.empty:
        return 0

    dataframe = dataframe.reset_index()

    dataframe.columns = [
        str(column)
        .lower()
        .replace(" ", "_")
        for column in dataframe.columns
    ]

    if "adj_close" in dataframe.columns:
        dataframe.drop(
            columns=["adj_close"],
            inplace=True
        )

    if "date" in dataframe.columns:
        dataframe.rename(
            columns={
                "date": "datetime"
            },
            inplace=True
        )

    dataframe.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close",
            "volume"
        ],
        inplace=True
    )

    if dataframe.empty:
        return 0

    dataframe["symbol"] = symbol
    dataframe["timeframe"] = timeframe

    records = []

    for record in dataframe.to_dict(
        orient="records"
    ):

        records.append(
            {
                "symbol": record["symbol"],
                "timeframe": TimeFrame(
                    record["timeframe"]
                ),

                "datetime": record[
                    "datetime"
                ],

                "open": float(
                    record["open"]
                ),

                "high": float(
                    record["high"]
                ),

                "low": float(
                    record["low"]
                ),

                "close": float(
                    record["close"]
                ),

                "volume": float(
                    record["volume"]
                )
            }
        )

    session = SessionLocal()

    try:
        count_before = session.scalar(
            select(func.count())
            .select_from(MarketData)
            .where(MarketData.symbol == symbol)
            .where(MarketData.timeframe == TimeFrame(timeframe))
        )

        statement = insert(
            MarketData
        ).values(
            records
        )

        statement = (
            statement
            .on_conflict_do_update(
                constraint="unique_market_data",
                set_={
                    "open": statement.excluded.open,
                    "high": statement.excluded.high,
                    "low": statement.excluded.low,
                    "close": statement.excluded.close,
                    "volume": statement.excluded.volume
                }
            )
        )

        session.execute(
            statement
        )

        session.commit()

        count_after = session.scalar(
            select(func.count())
            .select_from(MarketData)
            .where(MarketData.symbol == symbol)
            .where(MarketData.timeframe == TimeFrame(timeframe))
        )

        return max(0, count_after - count_before)

    finally:

        session.close()


def delete_oldest_rows(
    symbol: str,
    timeframe: str,
    count: int
):
    if count <= 0:
        return

    session = SessionLocal()

    try:
        subquery = (
            select(MarketData.market_data_id)
            .where(MarketData.symbol == symbol)
            .where(MarketData.timeframe == TimeFrame(timeframe))
            .order_by(MarketData.datetime.asc())
            .limit(count)
        )

        stmt = delete(MarketData).where(
            MarketData.market_data_id.in_(subquery)
        )

        session.execute(stmt)
        session.commit()

    finally:
        session.close()