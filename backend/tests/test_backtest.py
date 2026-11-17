import pytest
from datetime import datetime, timezone
import bcrypt

from app.core.database import engine, SessionLocal
from app.models import Base
from app.models.user import User
from app.models.strategy import Strategy
from app.models.backtest import Backtest
from app.models.trade import Trade
from app.models.market_data import MarketData
from app.enums.types import (
    BacktestStatus,
    PositionSizingType,
    TimeFrame
)
from app.backtesting.backtest_runner import BacktestRunner
from app.ingestion.download_market_data import download_and_store


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def load_market_data(setup_database):
    """Load RELIANCE.NS 1d data once per test session."""
    session = SessionLocal()
    try:
        from sqlalchemy import select, func
        count = session.scalar(
            select(func.count())
            .select_from(MarketData)
            .where(MarketData.symbol == "RELIANCE.NS")
            .where(MarketData.timeframe == TimeFrame.ONE_DAY)
        )
        if count == 0:
            print("Loading market data for RELIANCE.NS 1d...")
            download_and_store("RELIANCE.NS", "1d")
        else:
            print(f"Market data already exists: {count} rows")
    finally:
        session.close()


@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def test_user():
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.username == "test123").first()
        if existing:
            return existing

        password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode()
        user = User(
            username="test123",
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc)
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


@pytest.fixture(scope="session")
def sma_crossover_strategy(test_user):
    session = SessionLocal()
    try:
        existing = session.query(Strategy).filter(
            Strategy.user_id == test_user.user_id,
            Strategy.name == "SMA 20/50 Crossover"
        ).first()
        if existing:
            return existing

        strategy_json = {
            "long_entry": {
                "type": "condition",
                "left": {"type": "indicator", "indicator": "SMA", "params": {"period": 20}},
                "operator": "crosses_above",
                "right": {"type": "indicator", "indicator": "SMA", "params": {"period": 50}}
            },
            "long_exit": {
                "type": "condition",
                "left": {"type": "indicator", "indicator": "SMA", "params": {"period": 20}},
                "operator": "crosses_below",
                "right": {"type": "indicator", "indicator": "SMA", "params": {"period": 50}}
            }
        }
        strategy = Strategy(
            user_id=test_user.user_id,
            name="SMA 20/50 Crossover",
            strategy_json=strategy_json,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(strategy)
        session.commit()
        session.refresh(strategy)
        return strategy
    finally:
        session.close()


@pytest.fixture(scope="function")
def backtest_config(db_session, sma_crossover_strategy):
    backtest = Backtest(
        strategy_id=sma_crossover_strategy.strategy_id,
        status=BacktestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        initial_capital=100000,
        symbol="RELIANCE.NS",
        timeframe=TimeFrame.ONE_DAY,
        position_sizing_type=PositionSizingType.FIXED_QUANTITY,
        quantity=100
    )
    db_session.add(backtest)
    db_session.commit()
    db_session.refresh(backtest)

    runner = BacktestRunner(backtest_id=backtest.backtest_id)
    runner.run()

    db_session.refresh(backtest)
    return backtest


def test_user_creation(test_user):
    assert test_user.username == "test123"
    assert bcrypt.checkpw(b"test123", test_user.password_hash.encode())


def test_data_exists(db_session):
    count = db_session.query(MarketData).filter(
        MarketData.symbol == "RELIANCE.NS",
        MarketData.timeframe == TimeFrame.ONE_DAY
    ).count()
    assert count > 0, "No market data found. Run 'python main.py' first to load data."


def test_backtest_runs(backtest_config, db_session):
    assert backtest_config.status == BacktestStatus.COMPLETED
    assert backtest_config.total_trades is not None
    assert backtest_config.total_trades >= 0
    assert backtest_config.started_at is not None
    assert backtest_config.completed_at is not None


def test_trades_saved(backtest_config, db_session):
    trades = db_session.query(Trade).filter(
        Trade.backtest_id == backtest_config.backtest_id
    ).all()

    assert len(trades) == backtest_config.total_trades

    for trade in trades:
        assert trade.symbol == "RELIANCE.NS"
        assert trade.side in ("LONG", "SHORT")
        assert trade.entry_price > 0
        assert trade.exit_price > 0
        assert trade.quantity == 100


def test_metrics_calculated(backtest_config, db_session):
    db_session.refresh(backtest_config)

    assert backtest_config.total_return is not None
    assert backtest_config.net_profit is not None
    assert backtest_config.sharpe_ratio is not None
    assert backtest_config.max_drawdown is not None
    assert backtest_config.win_rate is not None
    assert backtest_config.profit_factor is not None
    assert backtest_config.expectancy is not None