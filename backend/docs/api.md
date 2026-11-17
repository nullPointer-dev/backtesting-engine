# Backtesting Engine API

Base URL: `http://localhost:8000`. Interactive docs are served at `/docs` (Swagger UI) and `/redoc`.

- [Conventions](#conventions)
- [Auth](#auth)
- [Reference data](#reference-data)
- [Strategies](#strategies)
- [Strategy definition format](#strategy-definition-format)
- [Backtests](#backtests)
- [Backtest results and analytics](#backtest-results-and-analytics)
- [Market data](#market-data)
- [Metric definitions](#metric-definitions)

---

## Conventions

**Authentication.** Every endpoint except `/auth/register`, `/auth/login`, `/auth/token`, `/indicators` and `/health` needs a bearer token from `/auth/login`:

```
Authorization: Bearer <access_token>
```

Tokens are valid for 7 days. Users only ever see their own strategies and backtests; anything else returns 404.

**Times** are ISO 8601 with a UTC offset. Request dates without an offset are treated as UTC.

**Percentages** are in percent units: `12.5` means 12.5%.

**Errors** use FastAPI's shape:

| Status | When | Body |
|---|---|---|
| 400 | Request is valid JSON but not allowed (e.g. running a completed backtest) | `{"detail": "message"}` |
| 401 | Missing, invalid or expired token | `{"detail": "Could not validate credentials"}` |
| 404 | Resource does not exist or belongs to another user | `{"detail": "Backtest not found"}` |
| 422 | Body failed validation | `{"detail": [ {"loc": [...], "msg": "...", ...} ]}`, or for strategies `{"detail": {"message", "errors", "warnings"}}` |

---

## Auth

### `POST /auth/register`

```json
{ "username": "alice", "password": "secret123" }
```

Username 3–50 characters, password 6–100. Returns **201**:

```json
{ "user_id": 1, "username": "alice", "created_at": "2026-11-17T10:00:00+00:00" }
```

400 if the username is taken.

### `POST /auth/login`

JSON body `{ "username", "password" }`. Returns:

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

### `POST /auth/token`

Same as login but takes form fields (`username`, `password`). This is what the **Authorize** button in `/docs` uses.

### `GET /auth/me`

Returns the current user (same shape as register).

---

## Reference data

### `GET /indicators`

No auth. Everything a client needs to build a strategy:

```json
{
  "indicators": [
    {
      "name": "SMA",
      "label": "Simple Moving Average",
      "category": "Moving Averages",
      "inputs": ["close"],
      "params": [
        { "name": "period", "type": "int", "default": 10, "min": 1, "max": 1000,
          "description": "Lookback length in bars" }
      ]
    }
  ],
  "comparison_operators": [
    { "value": "crosses_above", "label": "crosses above",
      "description": "left was <= right on the previous bar and is > right now" }
  ],
  "logical_operators": ["AND", "OR"],
  "price_fields": ["open", "high", "low", "close", "volume"],
  "timeframes": ["1m", "5m", "15m", "30m", "60m", "1d", "1wk"],
  "position_sizing_types": ["FIXED_QUANTITY", "PERCENT_OF_CAPITAL"]
}
```

Available indicators:

| Category | Indicators | Parameters (default) |
|---|---|---|
| Moving averages | `SMA`, `EMA`, `WMA`, `VWMA` | `period` (10) |
| Momentum | `RSI` | `period` (14) |
| | `ROC`, `MOM` | `period` (10) |
| | `CCI` | `period` (14) |
| MACD | `MACD_LINE`, `MACD_SIGNAL`, `MACD_HISTOGRAM` | `fast_period` (12), `slow_period` (26), `signal_period` (9) |
| Stochastics | `STOCH_K`, `STOCH_D` | `k_period` (14), `d_period` (3), `smooth_period` (3) |
| | `STOCHRSI_K`, `STOCHRSI_D` | `period` (14), `rsi_period` (14), `k_period` (3), `d_period` (3) |
| Volatility | `ATR` | `period` (14) |
| | `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER` | `period` (5), `std_dev` (2.0) |
| Trend | `ADX` | `period` (14) |
| | `SUPERTREND` | `period` (7), `multiplier` (3.0) |
| Volume | `OBV` | none |
| | `MFI` | `period` (14) |
| | `CMF` | `period` (20) |

Omitted parameters use the default.

### `GET /health`

`{"status": "ok"}`.

---

## Strategies

A strategy is a name plus a [strategy definition](#strategy-definition-format) stored as JSON. It is validated on create and update.

### `POST /strategies`

```json
{ "name": "SMA 20/50 crossover", "strategy_json": { "long_entry": {...}, "long_exit": {...} } }
```

Returns **201** with the strategy. An invalid definition returns **422**:

```json
{
  "detail": {
    "message": "Invalid strategy",
    "errors": [
      "long_entry.left.indicator: unknown indicator 'SMAX'. Available: ADX, ATR, ...",
      "short_exit: required when short_entry is set, otherwise short positions never close"
    ],
    "warnings": []
  }
}
```

### `GET /strategies?skip=0&limit=100`

```json
{ "strategies": [ { "strategy_id": 1, "user_id": 1, "name": "...", "strategy_json": {...},
                    "created_at": "...", "updated_at": "..." } ],
  "total": 1 }
```

Newest first.

### `GET /strategies/{strategy_id}`

### `PUT /strategies/{strategy_id}`

Either or both of `name` and `strategy_json`. Existing backtests keep their results.

### `DELETE /strategies/{strategy_id}`

**204**. Also deletes its backtests and their trades.

### `POST /strategies/validate`

```json
{ "strategy_json": {...} }
```

Always 200:

```json
{ "valid": false, "errors": ["..."], "warnings": ["long_exit: compares two constant values, so it never changes"] }
```

Checks: structure; indicator names; parameter names, types and ranges; empty groups; a `short_entry` must have a `short_exit`. Warnings flag things that are allowed but probably unintended.

---

## Strategy definition format

```json
{
  "long_entry":  <node>,          // required
  "long_exit":   <node>,          // required
  "short_entry": <node> | null,   // optional
  "short_exit":  <node> | null    // required if short_entry is set
}
```

A **node** is a condition or a group.

**Condition** compares two operands:

```json
{ "type": "condition", "left": <operand>, "operator": "crosses_above", "right": <operand> }
```

Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `crosses_above`, `crosses_below`. The crossing operators compare the current bar with the previous one.

**Group** combines nodes with `AND` or `OR` and can be nested:

```json
{ "type": "group", "operator": "AND", "children": [ <node>, <node>, ... ] }
```

**Operands:**

```json
{ "type": "indicator", "indicator": "RSI", "params": { "period": 14 } }
{ "type": "price", "field": "close" }        // open | high | low | close | volume
{ "type": "value", "value": 30 }
```

A condition involving an indicator that has no value yet (e.g. a 50-bar SMA on bar 10) is false.

**Example** — buy when the 20 SMA crosses above the 50 SMA while RSI is below 70; sell on the opposite cross or when RSI goes above 80:

```json
{
  "long_entry": {
    "type": "group", "operator": "AND", "children": [
      { "type": "condition",
        "left":  { "type": "indicator", "indicator": "SMA", "params": { "period": 20 } },
        "operator": "crosses_above",
        "right": { "type": "indicator", "indicator": "SMA", "params": { "period": 50 } } },
      { "type": "condition",
        "left":  { "type": "indicator", "indicator": "RSI", "params": { "period": 14 } },
        "operator": "<",
        "right": { "type": "value", "value": 70 } }
    ]
  },
  "long_exit": {
    "type": "group", "operator": "OR", "children": [
      { "type": "condition",
        "left":  { "type": "indicator", "indicator": "SMA", "params": { "period": 20 } },
        "operator": "crosses_below",
        "right": { "type": "indicator", "indicator": "SMA", "params": { "period": 50 } } },
      { "type": "condition",
        "left":  { "type": "indicator", "indicator": "RSI", "params": { "period": 14 } },
        "operator": ">",
        "right": { "type": "value", "value": 80 } }
    ]
  }
}
```

### How a strategy is executed

- Rules are evaluated on each bar's **close**; orders fill at the **next bar's open**. No decision uses data from the bar it trades on.
- One position at a time. While flat, `long_entry` is checked before `short_entry`.
- While in a position only its exit rule is checked. When it fires and the *opposite* entry rule is also true on that bar, the position reverses at the same open.
- A position still open on the last bar is closed at that bar's close (`exit_reason: "END_OF_DATA"`).
- Fills are moved against you by `slippage_pct`; `commission_pct` of the traded value is charged on entry and exit.
- Position size is capped so a position never costs more than current equity. Entry signals that cannot be funded (equity ≤ 0) are skipped and counted in `skipped_trades`.

---

## Backtests

Lifecycle: `PENDING` → `RUNNING` → `COMPLETED` | `FAILED` | `CANCELLED`. Failed and cancelled backtests can be run again; completed ones cannot (create a new one).

### `POST /backtests`

```json
{
  "strategy_id": 1,
  "symbol": "RELIANCE.NS",
  "timeframe": "1d",
  "start_date": "2015-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 100000,
  "position_sizing_type": "PERCENT_OF_CAPITAL",
  "position_size_percent": 50,
  "quantity": null,
  "commission_pct": 0.05,
  "slippage_pct": 0.02
}
```

| Field | Rules |
|---|---|
| `symbol` | Upper-cased. There must be market data for it in the range (400 otherwise); see [`/market-data/symbols`](#get-market-datasymbols). |
| `end_date` | After `start_date`. |
| `initial_capital` | > 0 |
| `position_sizing_type` | `FIXED_QUANTITY` needs `quantity` > 0. `PERCENT_OF_CAPITAL` needs `position_size_percent` in (0, 100] — the share of *current* equity put into each trade. |
| `commission_pct` | 0–10, default 0. Per side. |
| `slippage_pct` | 0–10, default 0. Per fill. |

Returns **201** with the backtest in `PENDING`. It does not run until you call `/run`.

### `POST /backtests/{backtest_id}/run`

Queues the backtest and returns immediately:

```json
{ "backtest_id": 7, "status": "RUNNING", "message": "Backtest started in background" }
```

Poll `/status` until it leaves `RUNNING`. 400 if it is already running or completed.

Backtests run in separate worker processes (`BACKTEST_WORKERS`, default 2). If the server stops mid-run, the backtest is marked `FAILED` on the next start.

### `GET /backtests/{backtest_id}/status`

```json
{ "backtest_id": 7, "status": "FAILED", "started_at": "...", "completed_at": "...",
  "error_message": "Traceback (most recent call last): ..." }
```

### `POST /backtests/{backtest_id}/cancel`

Cancels a `PENDING` or `RUNNING` backtest. A running job stops at its next check (every 250 bars) and saves nothing. Returns the status object with `"status": "CANCELLED"`.

### `GET /backtests`

Query: `strategy_id`, `status`, `skip` (0), `limit` (100, max 1000). Newest first. Returns summaries (no equity curve):

```json
{
  "backtests": [
    {
      "backtest_id": 7, "strategy_id": 1, "strategy_name": "SMA 20/50 crossover",
      "status": "COMPLETED", "created_at": "...", "start_date": "...", "end_date": "...",
      "started_at": "...", "completed_at": "...",
      "symbol": "RELIANCE.NS", "timeframe": "1d", "initial_capital": 100000,
      "position_sizing_type": "PERCENT_OF_CAPITAL", "quantity": null, "position_size_percent": 50,
      "commission_pct": 0.05, "slippage_pct": 0.02,
      "final_capital": 164471.9, "total_return": 64.47, "net_profit": 64471.9, "cagr": 5.69,
      "sharpe_ratio": 0.84, "max_drawdown": -15.12, "win_rate": 64.29, "profit_factor": 2.62,
      "total_trades": 28
    }
  ],
  "total": 1
}
```

### `GET /backtests/{backtest_id}`

The summary fields plus every metric, cost totals and the equity curve:

```json
{
  "...": "summary fields",
  "sortino_ratio": 1.31, "calmar_ratio": 0.38, "recovery_factor": 2.5,
  "max_drawdown_duration": 740, "ulcer_index": 5.49, "loss_rate": 35.71,
  "max_consecutive_wins": 5, "max_consecutive_losses": 2,
  "avg_trade_duration": 26.3, "expectancy": 2302.6,
  "total_commission": 1994.37, "exposure_pct": 33.1, "skipped_trades": 0,
  "equity_curve": [ { "time": "2015-01-02T00:00:00+05:30", "equity": 100000.0 }, ... ],
  "error_message": null
}
```

Backtests created before per-bar equity existed return points with `"time": null`.

### `DELETE /backtests/{backtest_id}`

**204**. 400 while running (cancel first).

---

## Backtest results and analytics

### `GET /backtests/{backtest_id}/trades?skip=0&limit=1000`

Oldest first. `limit` max 5000.

```json
{
  "trades": [
    {
      "trade_id": 1, "backtest_id": 7, "symbol": "RELIANCE.NS", "side": "LONG",
      "entry_time": "2015-04-28T00:00:00+05:30", "entry_price": 425.31,
      "exit_time": "2015-06-10T00:00:00+05:30", "exit_price": 431.02,
      "exit_reason": "SIGNAL", "quantity": 117.5, "duration_bars": 30,
      "pnl": 621.4, "commission": 50.3, "return_pct": 1.24,
      "mae_pct": -3.1, "mfe_pct": 4.8
    }
  ],
  "total": 28
}
```

`entry_price`/`exit_price` are fill prices after slippage. `pnl` is net of commission. `return_pct` is `pnl` over the entry cost. `mae_pct`/`mfe_pct` are the worst/best unrealised move while open, relative to the entry fill. `exit_reason` is `SIGNAL` or `END_OF_DATA`.

### `GET /backtests/{backtest_id}/equity-curve`

```json
{ "backtest_id": 7, "initial_capital": 100000,
  "equity_curve": [ { "time": "...", "equity": 100000.0 }, ... ] }
```

One point per bar, marked to market at the close.

### `GET /backtests/{backtest_id}/drawdown`

```json
{ "backtest_id": 7, "max_drawdown": -15.12,
  "drawdown": [ { "time": "...", "drawdown": -0.57 }, ... ] }
```

Percent below the running equity peak (the starting capital counts as the first peak).

### `GET /backtests/{backtest_id}/returns-breakdown`

```json
{ "backtest_id": 7,
  "monthly_returns": [ { "period": "2015-01", "pnl": 0.0, "return_pct": 0.0 }, ... ],
  "yearly_returns":  [ { "period": "2015", "pnl": 5906.39, "return_pct": 5.91 }, ... ] }
```

Each period's return is the change in equity over the period, relative to equity at the end of the previous period.

### `GET /backtests/{backtest_id}/trade-analysis`

```json
{
  "backtest_id": 7,
  "win_loss_distribution": { "wins": 18, "losses": 10, "breakeven": 0 },
  "pnl_distribution": [ { "range": "-3120.55 to -2510.10", "count": 1 }, ... ],
  "duration_distribution": [ { "range": "3 to 9", "count": 4 }, ... ],
  "mae_mfe": { "avg_mae": -4.42, "avg_mfe": 7.32 },
  "consecutive": { "max_wins": 5, "max_losses": 2 }
}
```

Histograms have up to 20 buckets.

### `GET /backtests/{backtest_id}/export?format=json|csv`

Download. `json` contains the full backtest and all trades; `csv` contains the trades.

### `GET /backtests/dashboard/summary`

```json
{
  "total_backtests": 12, "completed_backtests": 10, "running_backtests": 0, "failed_backtests": 1,
  "total_strategies": 3,
  "best_return": 64.47, "worst_return": -8.2, "avg_return": 21.3,
  "recent_backtests": [ { "...": "summary" } ]
}
```

Returns are over completed backtests; `recent_backtests` holds the latest five.

### `POST /backtests/compare`

```json
{ "backtest_ids": [7, 8, 9] }
```

1–20 IDs. Returns `{ "comparison": [ <full backtest>, ... ] }` for those that are completed and yours, in the order requested. 404 if none are.

---

## Market data

### `GET /market-data/symbols`

Every symbol with data and what is available for each timeframe:

```json
{
  "symbols": [
    { "symbol": "RELIANCE.NS",
      "timeframes": [ { "timeframe": "1d", "first": "1996-01-01T00:00:00+05:30",
                        "last": "2026-08-19T00:00:00+05:30", "bars": 7689 } ] }
  ]
}
```

### `GET /market-data/{symbol}/history`

Query: `timeframe` (default `1d`), `start_date`, `end_date`, `limit` (1000, max 10000).

With `start_date`, returns up to `limit` bars from that date forward; otherwise the latest `limit` bars (up to `end_date` if given). Always chronological:

```json
{ "symbol": "RELIANCE.NS", "timeframe": "1d",
  "data": [ { "datetime": "...", "open": 1290.0, "high": 1312.4, "low": 1285.1,
              "close": 1311.0, "volume": 10234567 } ] }
```

### `GET /market-data/{symbol}/latest?timeframe=1d`

The most recent bar: `{ "symbol", "timeframe", "datetime", "open", "high", "low", "close", "volume" }`. 404 if there is no data.

---

## Metric definitions

Computed from the per-bar equity series (starting capital prepended) and the closed trades. Ratios that are undefined — no trades, no losing trades, zero volatility — are `null`.

| Metric | Definition |
|---|---|
| `total_return` | `(final_capital − initial_capital) / initial_capital × 100` |
| `cagr` | Compound annual growth over the time between the first and last bar traded |
| `sharpe_ratio` | Mean bar return ÷ standard deviation of bar returns × √(bars per year). Risk-free rate 0. |
| `sortino_ratio` | Mean bar return ÷ downside deviation × √(bars per year) |
| `max_drawdown` | Largest fall from a running equity peak, in percent (negative) |
| `max_drawdown_duration` | Longest stretch, in bars, spent below a previous peak |
| `ulcer_index` | Root-mean-square of the percent drawdown at every bar |
| `calmar_ratio` | `cagr / |max_drawdown|` |
| `recovery_factor` | Net profit ÷ the largest peak-to-trough fall in currency |
| `win_rate`, `loss_rate` | Share of trades with positive / negative P&L (breakeven trades count as neither) |
| `profit_factor` | Gross profit ÷ gross loss |
| `expectancy` | Average P&L per trade |
| `avg_trade_duration` | Average bars held |
| `exposure_pct` | Share of bars with an open position |
| `total_commission` | Commission paid across all trades |

Bars per year: `1d` 252, `1wk` 52, and NSE session lengths for intraday — `60m` 7×252, `30m` 13×252, `15m` 25×252, `5m` 75×252, `1m` 375×252.
