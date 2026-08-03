import argparse

from app.core.database import engine
from app.models import Base
from app.ingestion.download_market_data import (
    full_load,
    incremental_update
)


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Setup DB and load market data"
    )

    parser.add_argument(
        "--update",
        action="store_true",
        help="Incremental daily update of market data"
    )

    args = parser.parse_args()

    init_db()
    print("Database tables created.")

    if args.update:

        incremental_update()
        print("\nIncremental market data update complete.")

    else:

        full_load()
        print("\nMarket data seeding complete.")
