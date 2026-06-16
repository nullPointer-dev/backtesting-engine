import pandas as pd

from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal

from app.models.market_data import (
    MarketData
)

from app.enums.timeframe import (
    TimeFrame
)


def load_market_data(
    dataframe: pd.DataFrame,
    symbol: str,
    timeframe: str
):

    if dataframe.empty:
        return

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
        return

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

        statement = insert(
            MarketData
        ).values(
            records
        )

        statement = (
            statement
            .on_conflict_do_nothing(
                constraint="unique_market_data"
            )
        )

        session.execute(
            statement
        )

        session.commit()

    finally:

        session.close()