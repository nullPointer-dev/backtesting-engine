"""Runs backtests outside the API process.

The bar loop is CPU-bound Python, so running it in the API's thread pool
would hold the GIL and slow every other request. Instead each backtest runs
in a separate worker process (``BACKTEST_WORKERS`` of them).

Setting ``BACKTEST_WORKERS=0`` runs backtests in-process as FastAPI
background tasks, which is simpler for tests and debugging.
"""

import logging
import multiprocessing
from concurrent.futures import Future, ProcessPoolExecutor
from datetime import datetime, timezone

from fastapi import BackgroundTasks

from app.core.config import BACKTEST_WORKERS

logger = logging.getLogger(__name__)

_executor: ProcessPoolExecutor | None = None


def run_backtest_job(backtest_id: int) -> None:
    # Imported here so worker processes only load the engine when they need it.
    from app.backtesting.backtest_runner import BacktestRunner

    try:
        BacktestRunner(backtest_id=backtest_id).run()
    except Exception:
        # The runner has already marked the backtest FAILED and stored the
        # traceback; log it here rather than crash the worker or request.
        logger.exception("Backtest %s failed", backtest_id)


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(
            max_workers=BACKTEST_WORKERS,
            # "spawn" gives each worker a clean interpreter, so it opens its own
            # database connections instead of sharing the parent's.
            mp_context=multiprocessing.get_context("spawn"),
        )
    return _executor


def _log_failure(backtest_id: int, future: Future) -> None:
    error = future.exception()
    if error is not None:
        # Only reached if the worker process itself broke (e.g. it was killed).
        logger.error("Backtest %s worker error: %r", backtest_id, error)


def submit_backtest(backtest_id: int, background_tasks: BackgroundTasks) -> None:
    if BACKTEST_WORKERS <= 0:
        background_tasks.add_task(run_backtest_job, backtest_id)
        return

    future = _get_executor().submit(run_backtest_job, backtest_id)
    future.add_done_callback(lambda f: _log_failure(backtest_id, f))


def shutdown() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


def fail_interrupted_backtests() -> int:
    """Mark backtests left RUNNING by a previous server process as failed.

    Jobs live only as long as the server process, so anything still RUNNING
    at startup can never finish. Assumes a single API process.
    """
    from app.core.database import SessionLocal
    from app.enums.types import BacktestStatus
    from app.models.backtest import Backtest

    with SessionLocal() as session:
        stuck = session.query(Backtest).filter(Backtest.status == BacktestStatus.RUNNING).all()
        for backtest in stuck:
            backtest.status = BacktestStatus.FAILED
            backtest.error_message = "Interrupted: the server stopped while this backtest was running"
            backtest.completed_at = datetime.now(timezone.utc)
        session.commit()
        return len(stuck)
