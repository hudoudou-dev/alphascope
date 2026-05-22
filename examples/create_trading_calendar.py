from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def create_example_trading_calendar(output_path: str | Path = "examples/calendar/trading_days.parquet") -> None:
    dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="D")
    
    trading_days = []
    for d in dates:
        if d.weekday() < 5:
            trading_days.append({
                "date": d,
                "is_trading_day": True,
                "exchange": "SSE",
            })
        else:
            trading_days.append({
                "date": d,
                "is_trading_day": False,
                "exchange": "SSE",
            })
    
    df = pd.DataFrame(trading_days)
    
    df["date"] = pd.to_datetime(df["date"])
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df, preserve_index=False)
    
    pq.write_table(
        table,
        output_path,
        compression="snappy",
    )
    
    print(f"Example trading calendar created: {output_path}")
    print(f"\nSchema:")
    print(table.schema)
    print(f"\nData preview:")
    print(df.head(10))
    print(f"\nTrading days count: {df[df['is_trading_day']].shape[0]}")


def inspect_trading_calendar(file_path: str | Path) -> None:
    file_path = Path(file_path)
    
    table = pq.read_table(file_path)
    
    print(f"File: {file_path}")
    print(f"\nSchema:")
    print(table.schema)
    
    df = table.to_pandas()
    print(f"\nShape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nData types:")
    print(df.dtypes)
    print(f"\nTrading days: {df[df['is_trading_day']].shape[0]}")
    print(f"\nNon-trading days: {df[~df['is_trading_day']].shape[0]}")
    print(f"\nFirst 10 rows:")
    print(df.head(10))


if __name__ == "__main__":
    create_example_trading_calendar()