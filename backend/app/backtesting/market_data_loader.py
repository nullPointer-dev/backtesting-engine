import pandas as pd
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.market_data import MarketData


class MarketDataLoader:
    @staticmethod
    def load(
        symbol: str,
        timeframe: str,
        start_date=None,
        end_date=None
    ) -> pd.DataFrame:

        session = SessionLocal()

        try:
            statement = (
                select(MarketData)
                .where(MarketData.symbol == symbol)
                .where(MarketData.timeframe == timeframe)
            )

            if start_date is not None:
                statement = statement.where(MarketData.datetime >= start_date)

            if end_date is not None:
                statement = statement.where(MarketData.datetime <= end_date)

            statement = statement.order_by(MarketData.datetime)
            rows = session.execute(statement).scalars().all()

            dataframe = pd.DataFrame(
                [
                    {
                        "datetime": row.datetime,
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "volume": row.volume
                    }
                    for row in rows
                ]
            )
            return dataframe

        finally:
            session.close()