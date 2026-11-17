"""Set up the database schema and load market data.

    python main.py                                  # migrate, then download full history for every symbol
    python main.py --update                         # migrate, then fetch only new bars
    python main.py --symbols RELIANCE.NS,TCS.NS --timeframes 1d,1wk   # just these
    python main.py --migrate-only                   # apply migrations and stop
"""
import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.ingestion.assets import SUPPORTED_SYMBOLS, SUPPORTED_TIMEFRAMES
from app.ingestion.download_market_data import full_load, incremental_update


def migrate():
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    command.upgrade(config, "head")


def csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up the database and load market data")
    parser.add_argument("--update", action="store_true", help="Incremental update of market data")
    parser.add_argument("--migrate-only", action="store_true", help="Apply migrations and exit")
    parser.add_argument("--symbols", type=csv_list, help="Comma-separated symbols (default: all supported)")
    parser.add_argument("--timeframes", type=csv_list, help="Comma-separated timeframes, e.g. 1d,1wk (default: all)")
    args = parser.parse_args()

    for symbol in args.symbols or []:
        if symbol not in SUPPORTED_SYMBOLS:
            parser.error(f"unsupported symbol {symbol!r}; see app/ingestion/assets.py")
    for timeframe in args.timeframes or []:
        if timeframe not in SUPPORTED_TIMEFRAMES:
            parser.error(f"unsupported timeframe {timeframe!r}; choose from {', '.join(SUPPORTED_TIMEFRAMES)}")

    migrate()
    print("Database schema is up to date.")

    if args.migrate_only:
        pass
    elif args.update:
        incremental_update(args.symbols, args.timeframes)
        print("\nIncremental market data update complete.")
    else:
        full_load(args.symbols, args.timeframes)
        print("\nMarket data load complete.")
