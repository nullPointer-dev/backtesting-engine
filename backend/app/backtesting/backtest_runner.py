import logging
import traceback
from datetime import datetime, timezone

from sqlalchemy import delete, select, update

from app.core.database import SessionLocal
from app.enums.types import BacktestStatus
from app.models.backtest import Backtest
from app.models.strategy import Strategy
from app.models.trade import Trade

from app.strategy_engine.validation import validate_strategy
from app.backtesting.market_data_loader import MarketDataLoader
from app.backtesting.indicator_preloader import IndicatorPreloader
from app.backtesting.execution_engine import BacktestCancelled, ExecutionEngine
from app.backtesting.portfolio_engine import PortfolioEngine
from app.backtesting.performance_metrics import PerformanceMetrics
from app.strategy_engine.requirement_extractor import RequirementExtractor
from app.backtesting.errors import summarize_error

logger = logging.getLogger(__name__)


def _describe_indicator(name: str, params: tuple) -> str:
    values = ", ".join(f"{value:g}" if isinstance(value, float) else str(value) for _, value in params)
    return f"{name}({values})" if values else name


def _to_datetime(value):
    return value.to_pydatetime() if hasattr(value, "to_pydatetime") else value


class BacktestRunner:
    def __init__(self, backtest_id: int):
        self.backtest_id = backtest_id

    def _checkpoint(self, stage: str, pct: float, message: str) -> bool:
        """Record progress in its own transaction; return True if the run was cancelled.

        The cancel endpoint and this runner share one row, so progress is only
        written while the backtest is still RUNNING.
        """
        with SessionLocal() as session:
            updated = session.execute(
                update(Backtest)
                .where(
                    Backtest.backtest_id == self.backtest_id,
                    Backtest.status == BacktestStatus.RUNNING,
                )
                .values(progress_pct=round(pct, 1), progress_stage=stage, progress_message=message)
                .returning(Backtest.backtest_id)
            ).first()
            session.commit()
        return updated is None

    def run(self):
        session = SessionLocal()
        try:
            backtest = session.execute(
                select(Backtest).where(Backtest.backtest_id == self.backtest_id)
            ).scalar_one()

            if backtest.status == BacktestStatus.CANCELLED:
                # Cancelled after /run was called but before this job started.
                raise BacktestCancelled()

            backtest.status = BacktestStatus.RUNNING
            backtest.started_at = datetime.now(timezone.utc)
            backtest.completed_at = None
            backtest.error_message = None
            backtest.progress_pct = 0.0
            backtest.progress_stage = "starting"
            backtest.progress_message = "job started"
            # A re-run replaces the trades of any earlier attempt.
            session.execute(delete(Trade).where(Trade.backtest_id == backtest.backtest_id))
            session.commit()

            strategy = session.execute(
                select(Strategy).where(Strategy.strategy_id == backtest.strategy_id)
            ).scalar_one()

            validation = validate_strategy(strategy.strategy_json)
            if not validation.valid:
                raise ValueError("Invalid strategy: " + "; ".join(validation.errors))
            strategy_definition = validation.definition

            span = f"{backtest.start_date:%Y-%m-%d} → {backtest.end_date:%Y-%m-%d}"
            if self._checkpoint(
                "loading", 3, f"loading {backtest.symbol} {backtest.timeframe.value} candles · {span}"
            ):
                raise BacktestCancelled()

            dataframe = MarketDataLoader().load(
                symbol=backtest.symbol,
                timeframe=backtest.timeframe,
                start_date=backtest.start_date,
                end_date=backtest.end_date,
            )
            if dataframe.empty:
                raise ValueError(
                    f"No market data for {backtest.symbol} ({backtest.timeframe.value}) "
                    f"between {backtest.start_date:%Y-%m-%d} and {backtest.end_date:%Y-%m-%d}"
                )

            requirements = RequirementExtractor().extract(strategy_definition)
            indicator_names = ", ".join(sorted(_describe_indicator(n, p) for n, p in requirements))
            if self._checkpoint(
                "indicators", 8,
                f"{len(dataframe)} bars loaded · preloading indicators: {indicator_names or 'none'}",
            ):
                raise BacktestCancelled()

            indicator_cache = IndicatorPreloader(dataframe, strategy_definition).preload()

            def on_bar(index: int, total: int) -> bool:
                pct = 10 + 70 * index / max(total, 1)
                return self._checkpoint("signals", pct, f"evaluating rules · bar {index:,} / {total:,}")

            raw_trades = ExecutionEngine(
                symbol=backtest.symbol,
                dataframe=dataframe,
                strategy=strategy_definition,
                indicator_cache=indicator_cache,
            ).run(checkpoint=on_bar)

            logger.info(
                "Backtest %s: %d bars, %d trades", self.backtest_id, len(dataframe), len(raw_trades)
            )

            if self._checkpoint(
                "portfolio", 82,
                f"{len(raw_trades)} signal trades · simulating portfolio: "
                f"{backtest.commission_pct:g}% commission, {backtest.slippage_pct:g}% slippage",
            ):
                raise BacktestCancelled()

            portfolio = PortfolioEngine(
                initial_capital=backtest.initial_capital,
                position_sizing_type=backtest.position_sizing_type,
                quantity=backtest.quantity,
                position_size_percent=backtest.position_size_percent,
                commission_pct=backtest.commission_pct,
                slippage_pct=backtest.slippage_pct,
            ).run(dataframe, raw_trades)

            if self._checkpoint("metrics", 90, "computing metrics: sharpe, sortino, drawdown, MAE/MFE"):
                raise BacktestCancelled()

            metrics = PerformanceMetrics(
                trades=portfolio["trades"],
                equity=portfolio["equity"],
                timestamps=dataframe["datetime"],
                initial_capital=backtest.initial_capital,
                timeframe=backtest.timeframe,
            ).calculate()

            if self._checkpoint(
                "saving", 96, f"saving {len(portfolio['trades'])} trades and the equity curve"
            ):
                raise BacktestCancelled()

            for trade in portfolio["trades"]:
                session.add(
                    Trade(
                        backtest_id=backtest.backtest_id,
                        symbol=str(trade["symbol"]),
                        side=trade["side"],
                        entry_time=_to_datetime(trade["entry_time"]),
                        entry_price=float(trade["entry_price"]),
                        exit_time=_to_datetime(trade["exit_time"]),
                        exit_price=float(trade["exit_price"]),
                        exit_reason=trade["exit_reason"],
                        quantity=float(trade["quantity"]),
                        duration_bars=int(trade["duration_bars"]),
                        pnl=float(trade["pnl"]),
                        commission=float(trade["commission"]),
                        return_pct=float(trade["return_pct"]),
                        mae_pct=float(trade["mae_pct"]),
                        mfe_pct=float(trade["mfe_pct"]),
                    )
                )

            for key, value in metrics.items():
                setattr(backtest, key, value)

            backtest.equity_curve = portfolio["equity_curve"]
            backtest.total_commission = portfolio["total_commission"]
            backtest.exposure_pct = portfolio["exposure_pct"]
            backtest.skipped_trades = portfolio["skipped_trades"]
            backtest.status = BacktestStatus.COMPLETED
            backtest.progress_pct = 100.0
            backtest.progress_stage = "done"
            backtest.progress_message = "completed"
            backtest.completed_at = datetime.now(timezone.utc)
            session.commit()

            return {"backtest_id": backtest.backtest_id, "metrics": metrics}

        except BacktestCancelled:
            # The cancel endpoint already set status, message and completed_at.
            session.rollback()
            logger.info("Backtest %s cancelled", self.backtest_id)
            return None

        except Exception:
            session.rollback()
            backtest = session.get(Backtest, self.backtest_id)
            if backtest and backtest.status != BacktestStatus.CANCELLED:
                backtest.status = BacktestStatus.FAILED
                backtest.error_message = traceback.format_exc()
                backtest.progress_stage = "failed"
                backtest.progress_message = summarize_error(backtest.error_message)
                backtest.completed_at = datetime.now(timezone.utc)
                session.commit()
            raise

        finally:
            session.close()
