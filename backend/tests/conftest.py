"""Shared test setup.

Unit tests (tests/unit) need no database. API tests (tests/api) run against
TEST_DB_URL, which is wiped between tests. To guarantee nothing touches the
development database, DB_URL is pointed at TEST_DB_URL *before* the app is
imported.
"""
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

_env = {**dotenv_values(BACKEND_DIR / ".env"), **os.environ}
DEV_DB_URL = _env.get("DB_URL")
TEST_DB_URL = _env.get("TEST_DB_URL")

if TEST_DB_URL:
    os.environ["DB_URL"] = TEST_DB_URL
else:
    # Unit tests never connect, but the app's config requires a value.
    os.environ.setdefault("DB_URL", "postgresql://unused@localhost/unused")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ["BACKTEST_WORKERS"] = "0"  # run backtests inline so tests can assert on results
os.environ["SQL_ECHO"] = "false"
os.environ["BCRYPT_ROUNDS"] = "4"  # fast password hashing
