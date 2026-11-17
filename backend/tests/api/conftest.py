"""Fixtures for API tests against TEST_DB_URL.

The database is migrated to head once per session, seeded with synthetic
market data (no network), and its user data is wiped before every test.
"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from tests.conftest import DEV_DB_URL, TEST_DB_URL

SYMBOL = "TEST.NS"
BARS = 600


def _same_database(a: str, b: str) -> bool:
    url_a, url_b = make_url(a), make_url(b)
    return (url_a.host, url_a.port, url_a.database) == (url_b.host, url_b.port, url_b.database)


def pytest_collection_modifyitems(config, items):
    reason = None
    if not TEST_DB_URL:
        reason = "TEST_DB_URL is not set (see .env.example)"
    elif DEV_DB_URL and _same_database(TEST_DB_URL, DEV_DB_URL):
        reason = "TEST_DB_URL points at the development database; refusing to wipe it"
    if reason:
        skip = pytest.mark.skip(reason=reason)
        for item in items:
            if "tests/api/" in str(item.fspath).replace("\\", "/"):
                item.add_marker(skip)


def synthetic_bars(n=BARS, seed=7):
    """A trending, oscillating series so moving-average strategies trade."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    close = 100 + 0.05 * t + 10 * np.sin(t / 15) + rng.normal(0, 0.5, n)
    open_ = np.concatenate([[close[0]], close[:-1]]) + rng.normal(0, 0.3, n)
    high = np.maximum(open_, close) + rng.uniform(0.1, 1.0, n)
    low = np.minimum(open_, close) - rng.uniform(0.1, 1.0, n)
    dates = pd.bdate_range("2022-01-03", periods=n, tz="UTC")
    return [
        {"symbol": SYMBOL, "timeframe": "1d", "datetime": d.to_pydatetime(), "open": float(o), "high": float(h),
         "low": float(l), "close": float(c), "volume": float(v)}
        for d, o, h, l, c, v in zip(dates, open_, high, low, close, rng.integers(1_000, 50_000, n))
    ]


@pytest.fixture(scope="session")
def database():
    from alembic import command
    from alembic.config import Config

    from tests.conftest import BACKEND_DIR

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")

    engine = create_engine(TEST_DB_URL)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE market_data, users RESTART IDENTITY CASCADE"))
        connection.execute(
            text(
                "INSERT INTO market_data (symbol, timeframe, datetime, open, high, low, close, volume) "
                "VALUES (:symbol, :timeframe, :datetime, :open, :high, :low, :close, :volume)"
            ),
            synthetic_bars(),
        )
    yield engine
    engine.dispose()


@pytest.fixture
def client(database):
    from fastapi.testclient import TestClient

    from app.main import app

    with database.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    def _make(username="alice", password="secret123"):
        response = client.post("/auth/register", json={"username": username, "password": password})
        assert response.status_code == 201, response.text
        token = client.post("/auth/login", json={"username": username, "password": password}).json()
        return {"Authorization": f"Bearer {token['access_token']}"}

    return _make


@pytest.fixture
def auth(make_user):
    return make_user()


SMA_CROSS = {
    "long_entry": {
        "type": "condition",
        "left": {"type": "indicator", "indicator": "SMA", "params": {"period": 10}},
        "operator": "crosses_above",
        "right": {"type": "indicator", "indicator": "SMA", "params": {"period": 30}},
    },
    "long_exit": {
        "type": "condition",
        "left": {"type": "indicator", "indicator": "SMA", "params": {"period": 10}},
        "operator": "crosses_below",
        "right": {"type": "indicator", "indicator": "SMA", "params": {"period": 30}},
    },
}


@pytest.fixture
def strategy_id(client, auth):
    response = client.post("/strategies", json={"name": "SMA 10/30", "strategy_json": SMA_CROSS}, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()["strategy_id"]


def backtest_payload(strategy_id, **overrides):
    payload = {
        "strategy_id": strategy_id,
        "symbol": SYMBOL,
        "timeframe": "1d",
        "start_date": "2022-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100_000,
        "position_sizing_type": "PERCENT_OF_CAPITAL",
        "position_size_percent": 100,
        "commission_pct": 0.05,
        "slippage_pct": 0.02,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def completed_backtest(client, auth, strategy_id):
    created = client.post("/backtests", json=backtest_payload(strategy_id), headers=auth)
    assert created.status_code == 201, created.text
    backtest_id = created.json()["backtest_id"]
    run = client.post(f"/backtests/{backtest_id}/run", headers=auth)
    assert run.status_code == 200, run.text
    result = client.get(f"/backtests/{backtest_id}", headers=auth).json()
    assert result["status"] == "COMPLETED", result["error_message"]
    return result
