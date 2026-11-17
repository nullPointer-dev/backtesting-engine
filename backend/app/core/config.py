import os

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DB_URL = os.getenv("DB_URL")
TEST_DB_URL = os.getenv("TEST_DB_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Log every SQL statement (very noisy; useful only when debugging queries).
SQL_ECHO = _bool("SQL_ECHO", False)

# Comma-separated list of origins allowed to call the API from a browser.
CORS_ORIGINS = _list("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# Number of worker processes used to run backtests.
BACKTEST_WORKERS = int(os.getenv("BACKTEST_WORKERS", "2"))

if not DB_URL:
    raise RuntimeError("DB_URL is not set. Copy .env.example to .env and fill it in.")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set. Copy .env.example to .env and fill it in.")
