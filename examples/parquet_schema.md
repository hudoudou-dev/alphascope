# Example Parquet Schema

This document describes the parquet schema used in AlphaScope for storing stock market data.

## Schema Definition

```
message schema {
  REQUIRED INT64 date (TIMESTAMP(MILLIS, false));
  REQUIRED DOUBLE open_price;
  REQUIRED DOUBLE high_price;
  REQUIRED DOUBLE low_price;
  REQUIRED DOUBLE close_price;
  REQUIRED DOUBLE volume;
  REQUIRED DOUBLE amount;
  REQUIRED BYTE_STRING code (STRING);
  OPTIONAL BYTE_STRING name (STRING);
  OPTIONAL DOUBLE pct_chg;
  OPTIONAL DOUBLE turn;
}
```

## Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| date | timestamp | Yes | Trading date (datetime64[ns]) |
| open_price | float64 | Yes | Opening price |
| high_price | float64 | Yes | Highest price |
| low_price | float64 | Yes | Lowest price |
| close_price | float64 | Yes | Closing price |
| volume | float64 | Yes | Trading volume |
| amount | float64 | Yes | Trading amount |
| code | string | Yes | Stock code (format: XXXXXX.EXCHANGE) |
| name | string | No | Stock name |
| pct_chg | float64 | No | Price change percentage |
| turn | float64 | No | Turnover rate |

## Compression

- Algorithm: Snappy
- Optimized for: Fast read/write performance

## File Naming Convention

Files are named by stock code:
- Format: `{CODE}.parquet`
- Example: `600000.SH.parquet`, `000001.SZ.parquet`

## Example Data

```python
import pandas as pd
import pyarrow.parquet as pq

# Read parquet file
table = pq.read_table("600000.SH.parquet")
df = table.to_pandas()

print(df.head())
```

Output:
```
        date  open_price  high_price  low_price  close_price    volume      amount       code   name  pct_chg  turn
0 2024-01-01       10.00       10.50       9.50        10.20  1000000.0  10000000.0  600000.SH  浦发银行     1.00   2.5
1 2024-01-02       10.10       10.60       9.60        10.30  1010000.0  10100000.0  600000.SH  浦发银行     1.10   2.6
2 2024-01-03       10.20       10.70       9.70        10.40  1020000.0  10200000.0  600000.SH  浦发银行     1.20   2.7
```

## Data Validation Rules

1. **No future dates**: All dates must be <= current date
2. **No negative prices**: All price fields must be > 0
3. **No duplicate dates**: Each (code, date) combination must be unique
4. **Price logic**: high_price >= low_price, high_price >= open_price, high_price >= close_price
5. **No missing values**: Required fields cannot have null values

## Timezone

All timestamps are in `Asia/Shanghai` timezone.

## Adjust Types

Data can be stored with different adjustment types:
- `none`: No adjustment (raw prices)
- `qfq`: Forward adjustment (前复权)
- `hfq`: Backward adjustment (后复权)
