import csv
import io

import pytest

from tests.api.conftest import SYMBOL, backtest_payload


def _create(client, auth, strategy_id, **overrides):
    return client.post("/backtests", json=backtest_payload(strategy_id, **overrides), headers=auth)


# ---------------------------------------------------------------- creation

@pytest.mark.parametrize("overrides, status, fragment", [
    ({"symbol": "NOPE.NS"}, 400, "No market data"),
    ({"start_date": "2030-01-01", "end_date": "2031-01-01"}, 400, "No market data"),
    ({"end_date": "2021-01-01"}, 422, "end_date must be after start_date"),
    ({"position_sizing_type": "FIXED_QUANTITY"}, 422, "quantity is required"),
    ({"position_size_percent": None}, 422, "position_size_percent is required"),
    ({"initial_capital": 0}, 422, "greater than 0"),
    ({"commission_pct": 11}, 422, "less than or equal to 10"),
])
def test_create_rejects_bad_input(client, auth, strategy_id, overrides, status, fragment):
    response = _create(client, auth, strategy_id, **overrides)
    assert response.status_code == status
    assert fragment in response.text


def test_create_normalises_symbol_and_starts_pending(client, auth, strategy_id):
    response = _create(client, auth, strategy_id, symbol=SYMBOL.lower())
    assert response.status_code == 201
    body = response.json()
    assert body["symbol"] == SYMBOL and body["status"] == "PENDING"
    assert body["strategy_name"] == "SMA 10/30"
    assert body["commission_pct"] == 0.05 and body["slippage_pct"] == 0.02


def test_cannot_backtest_someone_elses_strategy(client, make_user, strategy_id):
    other = make_user("mallory")
    assert _create(client, other, strategy_id).status_code == 404


# ---------------------------------------------------------------- running

def test_run_produces_results(client, auth, completed_backtest):
    bt = completed_backtest
    assert bt["total_trades"] > 0
    assert bt["started_at"] and bt["completed_at"] and bt["error_message"] is None
    assert bt["final_capital"] == pytest.approx(bt["initial_capital"] + bt["net_profit"])
    assert bt["equity_curve"][-1]["equity"] == pytest.approx(bt["final_capital"])
    assert bt["max_drawdown"] <= 0
    assert bt["total_commission"] > 0
    assert 0 < bt["exposure_pct"] <= 100
    for key in ("sharpe_ratio", "sortino_ratio", "cagr", "win_rate", "ulcer_index"):
        assert bt[key] is not None, key


def test_trades_match_summary(client, auth, completed_backtest):
    bt = completed_backtest
    body = client.get(f"/backtests/{bt['backtest_id']}/trades", headers=auth).json()
    trades = body["trades"]
    assert body["total"] == bt["total_trades"] == len(trades)
    assert sum(t["pnl"] for t in trades) == pytest.approx(bt["net_profit"])
    assert sum(t["commission"] for t in trades) == pytest.approx(bt["total_commission"])
    entry_times = [t["entry_time"] for t in trades]
    assert entry_times == sorted(entry_times)
    for trade in trades:
        assert trade["exit_reason"] in ("SIGNAL", "END_OF_DATA")
        assert trade["mae_pct"] <= 0 <= trade["mfe_pct"]


def test_completed_backtest_cannot_rerun_or_cancel(client, auth, completed_backtest):
    backtest_id = completed_backtest["backtest_id"]
    assert client.post(f"/backtests/{backtest_id}/run", headers=auth).status_code == 400
    assert client.post(f"/backtests/{backtest_id}/cancel", headers=auth).status_code == 400


def test_cancel_pending_then_rerun(client, auth, strategy_id):
    backtest_id = _create(client, auth, strategy_id).json()["backtest_id"]

    cancelled = client.post(f"/backtests/{backtest_id}/cancel", headers=auth).json()
    assert cancelled["status"] == "CANCELLED" and cancelled["error_message"] == "Cancelled by user"

    assert client.post(f"/backtests/{backtest_id}/run", headers=auth).status_code == 200
    status = client.get(f"/backtests/{backtest_id}/status", headers=auth).json()
    assert status["status"] == "COMPLETED" and status["error_message"] is None


def test_runner_respects_cancel_recorded_before_it_starts(client, auth, strategy_id):
    from app.backtesting.backtest_runner import BacktestRunner

    backtest_id = _create(client, auth, strategy_id).json()["backtest_id"]
    client.post(f"/backtests/{backtest_id}/cancel", headers=auth)
    assert BacktestRunner(backtest_id).run() is None
    assert client.get(f"/backtests/{backtest_id}/status", headers=auth).json()["status"] == "CANCELLED"


def test_failure_is_recorded(client, auth, strategy_id, database):
    from sqlalchemy import text

    backtest_id = _create(client, auth, strategy_id).json()["backtest_id"]
    # Corrupt the strategy behind the API's back so the run fails.
    with database.begin() as connection:
        connection.execute(text("UPDATE strategies SET strategy_json = '{}'::jsonb"))

    assert client.post(f"/backtests/{backtest_id}/run", headers=auth).status_code == 200
    status = client.get(f"/backtests/{backtest_id}/status", headers=auth).json()
    assert status["status"] == "FAILED"
    assert "Invalid strategy" in status["error_message"]


# ---------------------------------------------------------------- analytics

def test_equity_and_drawdown(client, auth, completed_backtest):
    backtest_id = completed_backtest["backtest_id"]
    equity = client.get(f"/backtests/{backtest_id}/equity-curve", headers=auth).json()
    points = equity["equity_curve"]
    assert len(points) > 100 and all(p["time"] for p in points)

    drawdown = client.get(f"/backtests/{backtest_id}/drawdown", headers=auth).json()
    assert len(drawdown["drawdown"]) == len(points)
    assert drawdown["max_drawdown"] == pytest.approx(completed_backtest["max_drawdown"])
    assert all(p["drawdown"] <= 0 for p in drawdown["drawdown"])


def test_returns_breakdown_compounds_to_total(client, auth, completed_backtest):
    body = client.get(f"/backtests/{completed_backtest['backtest_id']}/returns-breakdown", headers=auth).json()
    growth = 1.0
    for period in body["yearly_returns"]:
        growth *= 1 + period["return_pct"] / 100
    assert (growth - 1) * 100 == pytest.approx(completed_backtest["total_return"])
    assert sum(p["pnl"] for p in body["monthly_returns"]) == pytest.approx(completed_backtest["net_profit"])


def test_trade_analysis(client, auth, completed_backtest):
    body = client.get(f"/backtests/{completed_backtest['backtest_id']}/trade-analysis", headers=auth).json()
    distribution = body["win_loss_distribution"]
    assert sum(distribution.values()) == completed_backtest["total_trades"]
    assert sum(b["count"] for b in body["pnl_distribution"]) == completed_backtest["total_trades"]
    assert body["mae_mfe"]["avg_mae"] <= 0 <= body["mae_mfe"]["avg_mfe"]
    assert body["consecutive"]["max_wins"] == completed_backtest["max_consecutive_wins"]


def test_exports(client, auth, completed_backtest):
    backtest_id = completed_backtest["backtest_id"]
    as_json = client.get(f"/backtests/{backtest_id}/export?format=json", headers=auth)
    assert "attachment" in as_json.headers["content-disposition"]
    payload = as_json.json()
    assert payload["backtest"]["backtest_id"] == backtest_id
    assert len(payload["trades"]) == completed_backtest["total_trades"]

    as_csv = client.get(f"/backtests/{backtest_id}/export?format=csv", headers=auth)
    rows = list(csv.DictReader(io.StringIO(as_csv.text)))
    assert len(rows) == completed_backtest["total_trades"]
    assert {"side", "pnl", "mae_pct", "exit_reason"} <= set(rows[0])

    assert client.get(f"/backtests/{backtest_id}/export?format=xml", headers=auth).status_code == 422


def test_list_dashboard_and_compare(client, auth, strategy_id, completed_backtest):
    _create(client, auth, strategy_id)  # a second, pending backtest

    listing = client.get("/backtests", headers=auth).json()
    assert listing["total"] == 2
    assert "equity_curve" not in listing["backtests"][0]
    completed = client.get("/backtests?status=COMPLETED", headers=auth).json()
    assert [b["backtest_id"] for b in completed["backtests"]] == [completed_backtest["backtest_id"]]

    dashboard = client.get("/backtests/dashboard/summary", headers=auth)
    assert dashboard.status_code == 200
    summary = dashboard.json()
    assert summary["total_backtests"] == 2 and summary["completed_backtests"] == 1
    assert summary["best_return"] == pytest.approx(completed_backtest["total_return"])
    assert "password" not in dashboard.text

    compare = client.post(
        "/backtests/compare", json={"backtest_ids": [completed_backtest["backtest_id"], 999]}, headers=auth
    ).json()
    assert [b["backtest_id"] for b in compare["comparison"]] == [completed_backtest["backtest_id"]]


def test_delete(client, auth, completed_backtest):
    backtest_id = completed_backtest["backtest_id"]
    assert client.delete(f"/backtests/{backtest_id}", headers=auth).status_code == 204
    assert client.get(f"/backtests/{backtest_id}", headers=auth).status_code == 404
    assert client.get(f"/backtests/{backtest_id}/trades", headers=auth).status_code == 404


def test_backtests_are_private(client, make_user, auth, completed_backtest):
    other = make_user("mallory")
    backtest_id = completed_backtest["backtest_id"]
    for path in ("", "/status", "/trades", "/equity-curve", "/drawdown", "/returns-breakdown",
                 "/trade-analysis", "/export"):
        assert client.get(f"/backtests/{backtest_id}{path}", headers=other).status_code == 404, path
    assert client.post(f"/backtests/{backtest_id}/cancel", headers=other).status_code == 404
    assert client.delete(f"/backtests/{backtest_id}", headers=other).status_code == 404
    assert client.get("/backtests/dashboard/summary", headers=other).json()["total_backtests"] == 0
