"""Set up the database schema and load market data.

    python main.py            # migrate, then download full history for every symbol
    python main.py --update   # migrate, then fetch only new bars
"""
import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.ingestion.download_market_data import full_load, incremental_update


def migrate():
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    command.upgrade(config, "head")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up the database and load market data")
    parser.add_argument("--update", action="store_true", help="Incremental update of market data")
    parser.add_argument("--migrate-only", action="store_true", help="Apply migrations and exit")
    args = parser.parse_args()

    migrate()
    print("Database schema is up to date.")

    if args.migrate_only:
        pass
    elif args.update:
        incremental_update()
        print("\nIncremental market data update complete.")
    else:
        full_load()
        print("\nMarket data seeding complete.")
