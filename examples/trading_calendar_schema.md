# Trading Calendar Parquet Schema

This document describes the parquet schema used in AlphaScope for storing trading calendar data.

## Schema Definition

```
message schema {
  REQUIRED INT64 date (TIMESTAMP(MILLIS, false));
  REQUIRED BOOLEAN is_trading_day;
  OPTIONAL BYTE_STRING exchange (STRING);
}
```

## Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| date | timestamp | Yes | Calendar date (datetime64[ns]) |
| is_trading_day | boolean | Yes | Whether it's a trading day |
| exchange | string | No | Exchange code (e.g., SSE, SZSE) |

## Compression

- Algorithm: Snappy
- Optimized for: Fast read/write performance

## File Location

Trading calendar data is stored at:
- Path: `data/calendar/trading_days.parquet`
- Format: Single parquet file containing all trading days

## Example Data

```python
import pandas as pd
import pyarrow.parquet as pq

# Read trading calendar
table = pq.read_table("data/calendar/trading_days.parquet")
df = table.to_pandas()

print(df.head())
```

Output:
```
        date  is_trading_day exchange
0 2024-01-02            True      SSE
1 2024-01-03            True      SSE
2 2024-01-04            True      SSE
3 2024-01-05            True      SSE
4 2024-01-06           False      SSE
```

## Data Validation Rules

1. **No future dates**: All dates must be <= current date
2. **No missing values**: date and is_trading_day cannot be null
3. **No duplicate dates**: Each date must be unique
4. **Sorted by date**: Data must be sorted chronologically

## Timezone

All timestamps are in `Asia/Shanghai` timezone.

## Market Hours

A-share market trading hours:
- Morning session: 09:30 - 11:30
- Lunch break: 11:30 - 13:00
- Afternoon session: 13:00 - 15:00

## Usage

```python
from src.calendar.trading_calendar import TradingCalendarService

# Initialize service
calendar_service = TradingCalendarService()

# Download trading days
calendar_service.download_trading_days("1991-12-19", "2024-12-31")

# Check if today is a trading day
is_trading = calendar_service.is_trading_day(datetime.now())

# Get previous trading day
prev_day = calendar_service.previous_trading_day(datetime.now())

# Get next trading day
next_day = calendar_service.next_trading_day(datetime.now())

# Get trading days in a range
trading_days = calendar_service.get_trading_days("2024-01-01", "2024-01-31")

# Check if market is open
is_open = calendar_service.is_market_open(datetime.now())

# Get latest closed trading day
latest_closed = calendar_service.latest_closed_trading_day()
```

## Data Sources

Trading calendar data can be downloaded from:
1. **AKShare**: `akshare.tool_trade_date_hist_sina()`
2. **BaoStock**: `baostock.query_trade_dates()`

## Historical Coverage

- Start date: 1991-12-19 (Shanghai Stock Exchange establishment)
- End date: Current date
- Coverage: SSE and SZSE trading days