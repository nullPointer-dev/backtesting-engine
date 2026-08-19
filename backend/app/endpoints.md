# Backtesting Engine API Endpoints

Base URL: `http://localhost:8000`

## Authentication

All endpoints (except `/auth/*` and `/health`) require JWT Bearer token:
```
Authorization: Bearer <access_token>
```

---

## Auth

### Register User
**POST** `/auth/register`

**Request:**
```json
{
  "username": "testuser",
  "password": "testpass123"
}
```

**Response:** 201 Created
```json
{
  "user_id": 1,
  "username": "testuser",
  "created_at": "2026-08-19T17:44:05.635260+05:30"
}
```

---

### Login
**POST** `/auth/login`

**Request:**
```json
{
  "username": "testuser",
  "password": "testpass123"
}
```

**Response:** 200 OK
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### Get Current User
**GET** `/auth/me`

**Headers:** `Authorization: Bearer <token>`

**Response:** 200 OK
```json
{
  "user_id": 1,
  "username": "testuser",
  "created_at": "2026-08-19T17:44:05.635260+05:30"
}
```

---

## Strategies

### Create Strategy
**POST** `/strategies`

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "name": "SMA 20/50 Crossover",
  "strategy_json": {
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
}
```

**Response:** 201 Created
```json
{
  "strategy_id": 1,
  "user_id": 1,
  "name": "SMA 20/50 Crossover",
  "strategy_json": {...},
  "created_at": "2026-08-19T17:44:05.635260+05:30",
  "updated_at": "2026-08-19T17:44:05.635260+05:30"
}
```

---

### List Strategies
**GET** `/strategies?skip=0&limit=100`

**Headers:** `Authorization: Bearer <token>`

**Query Params:**
- `skip` (int, default 0)
- `limit` (int, default 100, max 1000)

**Response:** 200 OK
```json
{
  "strategies": [...],
  "total": 5
}
```

---

### Get Strategy
**GET** `/strategies/{strategy_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** 200 OK

---

### Update Strategy
**PUT** `/strategies/{strategy_id}`

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "name": "Updated Name",
  "strategy_json": {...}
}
```

**Response:** 200 OK

---

### Delete Strategy
**DELETE** `/strategies/{strategy_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** 204 No Content

---

## Backtests

### Create Backtest
**POST** `/backtests`

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "strategy_id": 1,
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2024-01-01T00:00:00Z",
  "initial_capital": 100000,
  "symbol": "RELIANCE.NS",
  "timeframe": "1d",
  "position_sizing_type": "FIXED_QUANTITY",
  "quantity": 100
}
```

**Note:** For `PERCENT_OF_CAPITAL`, provide `position_size_percent` instead of `quantity`.

**Response:** 201 Created
```json
{
  "backtest_id": 1,
  "strategy_id": 1,
  "status": "PENDING",
  "start_date": "2023-01-01T05:30:00+05:30",
  "end_date": "2024-01-01T05:30:00+05:30",
  "started_at": null,
  "completed_at": null,
  "initial_capital": 100000,
  "symbol": "RELIANCE.NS",
  "timeframe": "1d",
  "position_sizing_type": "FIXED_QUANTITY",
  "quantity": 100,
  "position_size_percent": null,
  "final_capital": null,
  "total_return": null,
  "net_profit": null,
  "cagr": null,
  "sharpe_ratio": null,
  ...
}
```

---

### List Backtests
**GET** `/backtests?strategy_id=1&status=COMPLETED&skip=0&limit=100`

**Headers:** `Authorization: Bearer <token>`

**Query Params:**
- `strategy_id` (int, optional)
- `status` (enum: PENDING, RUNNING, COMPLETED, FAILED)
- `skip` (int, default 0)
- `limit` (int, default 100, max 1000)

**Response:** 200 OK
```json
{
  "backtests": [...],
  "total": 10
}
```

---

### Get Backtest
**GET** `/backtests/{backtest_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** 200 OK (includes all metrics when COMPLETED)

---

### Run Backtest
**POST** `/backtests/{backtest_id}/run`

**Headers:** `Authorization: Bearer <token>`

**Response:** 200 OK
```json
{
  "backtest_id": 1,
  "status": "RUNNING",
  "message": "Backtest started in background"
}
```

**Note:** Runs as background task. Poll `/backtests/{id}` for status.

---

### Get Backtest Trades
**GET** `/backtests/{backtest_id}/trades?skip=0&limit=1000`

**Headers:** `Authorization: Bearer <token>`

**Query Params:**
- `skip` (int, default 0)
- `limit` (int, default 1000, max 5000)

**Response:** 200 OK
```json
{
  "trades": [
    {
      "trade_id": 1,
      "backtest_id": 1,
      "symbol": "RELIANCE.NS",
      "side": "LONG",
      "entry_time": "2023-05-02T00:00:00+05:30",
      "entry_price": 1124.31,
      "exit_time": "2023-09-07T00:00:00+05:30",
      "exit_price": 1210.85,
      "quantity": 100,
      "duration_bars": 90,
      "pnl": 8654.41
    }
  ],
  "total": 1
}
```

---

### Delete Backtest
**DELETE** `/backtests/{backtest_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** 204 No Content

**Note:** Cannot delete RUNNING backtests.

---

## Health Check

**GET** `/health`

**Response:** 200 OK
```json
{"status": "ok"}
```

---

## Strategy Definition Format

### Operands
```json
// Price operand
{"type": "price", "field": "close"}

// Value operand
{"type": "value", "value": 50}

// Indicator operand
{"type": "indicator", "indicator": "SMA", "params": {"period": 20}}
```

**Available indicators:** SMA, EMA, WMA, VWMA, RSI, ROC, MOM, CCI, MACD_LINE, MACD_SIGNAL, MACD_HISTOGRAM, STOCH_K, STOCH_D, STOCHRSI_K, STOCHRSI_D, ATR, BB_UPPER, BB_MIDDLE, BB_LOWER, ADX, SUPERTREND, OBV, MFI, CMF

### Operators
- `>`, `<`, `>=`, `<=`, `==`, `!=`
- `crosses_above`, `crosses_below`

### Logical Operators (for groups)
- `AND`, `OR`

### Condition Node
```json
{
  "type": "condition",
  "left": {...operand...},
  "operator": ">",
  "right": {...operand...}
}
```

### Group Node
```json
{
  "type": "group",
  "operator": "AND",
  "children": [
    {...condition...},
    {...group...}
  ]
}
```

### Full Strategy JSON
```json
{
  "long_entry": {...node...},
  "long_exit": {...node...},
  "short_entry": {...node...},
  "short_exit": {...node...}
}
```

---

## Timeframes
- `1m`, `5m`, `15m`, `30m`, `60m`, `1d`, `1wk`

---

## Position Sizing Types
- `FIXED_QUANTITY` — requires `quantity`
- `PERCENT_OF_CAPITAL` — requires `position_size_percent` (1-100)

---

## Error Responses

```json
// 400 Bad Request
{"detail": "quantity is required for FIXED_QUANTITY position sizing"}

// 401 Unauthorized
{"detail": "Could not validate credentials"}

// 404 Not Found
{"detail": "Strategy not found"}
```