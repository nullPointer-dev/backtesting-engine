from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.enums.types import BacktestStatus
from app.models.backtest import Backtest
from app.models.strategy import Strategy
from app.models.trade import Trade

from app.strategy_engine.schemas.strategy_definition import StrategyDefinition
from app.backtesting.market_data_loader import MarketDataLoader
from app.backtesting.indicator_preloader import IndicatorPreloader
from app.backtesting.execution_engine import ExecutionEngine
from app.backtesting.portfolio_engine import PortfolioEngine
from app.backtesting.performance_metrics import PerformanceMetrics

class BacktestRunner:
    def __init__(self, backtest_id: int):
        self.backtest_id = backtest_id

    def run(self):
        session = SessionLocal()
        try:
            backtest = (session.execute(select(Backtest).where(Backtest.backtest_id == self.backtest_id)).scalar_one())
            backtest.status = (BacktestStatus.RUNNING)
            backtest.started_at = (datetime.now(timezone.utc))

            session.commit()

            strategy = (session.execute(select(Strategy).where(Strategy.strategy_id == backtest.strategy_id)).scalar_one())

            strategy_definition = (StrategyDefinition.model_validate(strategy.strategy_json))

            dataframe = (MarketDataLoader().load(
                    symbol=backtest.symbol,
                    timeframe=backtest.timeframe,
                    start_date=backtest.start_date,
                    end_date=backtest.end_date
                )
            )

            indicator_cache = (IndicatorPreloader(
                    dataframe,
                    strategy_definition
                ).preload()
            )

            raw_trades = (ExecutionEngine(
                    symbol=backtest.symbol,
                    dataframe=dataframe,
                    strategy=strategy_definition,
                    indicator_cache=indicator_cache).run()
            )

            print("Rows:", len(dataframe))
            print("Trades generated:", len(raw_trades))

            portfolio_result = (
                PortfolioEngine(
                    initial_capital=backtest.initial_capital,
                    position_sizing_type=backtest.position_sizing_type,
                    quantity=backtest.quantity,
                    position_size_percent=backtest.position_size_percent
                ).process_trades(raw_trades)
            )

            metrics = (
                PerformanceMetrics(
                    trades=portfolio_result["trades"],
                    equity_curve=portfolio_result["equity_curve"],
                    initial_capital=backtest.initial_capital,
                    final_capital=portfolio_result["final_capital"],
                    start_date=backtest.start_date,
                    end_date=backtest.end_date
                ).calculate()
            )

            for trade in portfolio_result["trades"]:
                session.add(
                    Trade(
                        backtest_id=backtest.backtest_id,
                        symbol=str(trade["symbol"]),
                        side=trade["side"],
                        entry_time=trade["entry_time"].to_pydatetime()
                        if hasattr(trade["entry_time"], "to_pydatetime")
                        else trade["entry_time"],
                        entry_price=float(trade["entry_price"]),
                        exit_time=trade["exit_time"].to_pydatetime()
                        if hasattr(trade["exit_time"], "to_pydatetime")
                        else trade["exit_time"],
                        exit_price=float(trade["exit_price"]),
                        quantity=float(trade["quantity"]),
                        duration_bars=int(trade["duration_bars"]),
                        pnl=float(trade["pnl"])
                    )
                )

            for key, value in (metrics.items()):
                setattr(backtest, key, value)

            backtest.status = (BacktestStatus.COMPLETED)
            backtest.completed_at = (datetime.now(timezone.utc))
            session.commit()

            return {
                "backtest_id": backtest.backtest_id,
                "metrics": metrics
            }

        except Exception:

            session.rollback()
            backtest = (session.get(Backtest, self.backtest_id))

            if backtest:
                backtest.status = (BacktestStatus.FAILED)
                session.commit()

            raise

        finally:
            session.close()