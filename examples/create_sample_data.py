from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def create_example_parquet(output_path: str | Path = "examples/data/600000.SH.parquet") -> None:
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    
    data = {
        "date": dates,
        "open_price": [10.0 + i * 0.1 for i in range(10)],
        "high_price": [10.5 + i * 0.1 for i in range(10)],
        "low_price": [9.5 + i * 0.1 for i in range(10)],
        "close_price": [10.2 + i * 0.1 for i in range(10)],
        "volume": [1000000.0 + i * 10000 for i in range(10)],
        "amount": [10000000.0 + i * 100000 for i in range(10)],
        "code": ["600000.SH" for _ in range(10)],
        "name": ["浦发银行" for _ in range(10)],
        "pct_chg": [1.0 + i * 0.1 for i in range(10)],
        "turn": [2.5 + i * 0.1 for i in range(10)],
    }
    
    df = pd.DataFrame(data)
    
    df["date"] = pd.to_datetime(df["date"])
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df, preserve_index=False)
    
    pq.write_table(
        table,
        output_path,
        compression="snappy",
    )
    
    print(f"Example parquet file created: {output_path}")
    print(f"\nSchema:")
    print(table.schema)
    print(f"\nData preview:")
    print(df.head())


def inspect_parquet(file_path: str | Path) -> None:
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
    print(f"\nFirst 5 rows:")
    print(df.head())


if __name__ == "__main__":
    create_example_parquet()
