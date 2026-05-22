from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def temp_storage_path(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def sample_bar_data() -> pd.DataFrame:
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    
    data = {
        "date": dates,
        "open_price": [10.0 + i * 0.1 for i in range(10)],
        "high_price": [10.5 + i * 0.1 for i in range(10)],
        "low_price": [9.5 + i * 0.1 for i in range(10)],
        "close_price": [10.2 + i * 0.1 for i in range(10)],
        "volume": [1000000.0 for _ in range(10)],
        "amount": [10000000.0 for _ in range(10)],
        "code": ["600000.SH" for _ in range(10)],
        "name": ["浦发银行" for _ in range(10)],
        "pct_chg": [1.0 + i * 0.1 for i in range(10)],
        "turn": [2.5 for _ in range(10)],
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_stock_list() -> list[str]:
    return [
        "600000.SH",
        "000001.SZ",
        "300750.SZ",
        "688001.SH",
    ]


@pytest.fixture
def mock_akshare_data() -> pd.DataFrame:
    dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
    
    data = {
        "日期": dates,
        "开盘": [10.0, 10.1, 10.2, 10.3, 10.4],
        "收盘": [10.2, 10.3, 10.4, 10.5, 10.6],
        "最高": [10.5, 10.6, 10.7, 10.8, 10.9],
        "最低": [9.5, 9.6, 9.7, 9.8, 9.9],
        "成交量": [1000000, 1100000, 1200000, 1300000, 1400000],
        "成交额": [10000000, 11000000, 12000000, 13000000, 14000000],
        "涨跌幅": [1.0, 1.1, 1.2, 1.3, 1.4],
        "换手率": [2.5, 2.6, 2.7, 2.8, 2.9],
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_baostock_data() -> list[list[Any]]:
    return [
        ["2024-01-01", "sh.600000", "10.0", "10.5", "9.5", "10.2", "1000000", "10000000", "2.5", "1.0"],
        ["2024-01-02", "sh.600000", "10.1", "10.6", "9.6", "10.3", "1100000", "11000000", "2.6", "1.1"],
        ["2024-01-03", "sh.600000", "10.2", "10.7", "9.7", "10.4", "1200000", "12000000", "2.7", "1.2"],
    ]


@pytest.fixture
def mock_tushare_data() -> pd.DataFrame:
    return pd.DataFrame({
        "ts_code": ["600000.SH", "600000.SH", "600000.SH"],
        "trade_date": ["20240101", "20240102", "20240103"],
        "open": [10.0, 10.1, 10.2],
        "high": [10.5, 10.6, 10.7],
        "low": [9.5, 9.6, 9.7],
        "close": [10.2, 10.3, 10.4],
        "vol": [1000000, 1100000, 1200000],
        "amount": [10000000, 11000000, 12000000],
        "pct_chg": [1.0, 1.1, 1.2],
    })


@pytest.fixture
def invalid_data_negative_price() -> pd.DataFrame:
    dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
    
    data = {
        "date": dates,
        "open_price": [-10.0, 10.1, 10.2, 10.3, 10.4],
        "high_price": [10.5, 10.6, 10.7, 10.8, 10.9],
        "low_price": [9.5, 9.6, 9.7, 9.8, 9.9],
        "close_price": [10.2, 10.3, 10.4, 10.5, 10.6],
        "volume": [1000000.0 for _ in range(5)],
        "amount": [10000000.0 for _ in range(5)],
        "code": ["600000.SH" for _ in range(5)],
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def invalid_data_future_date() -> pd.DataFrame:
    future_dates = pd.date_range(start=datetime.now() + timedelta(days=1), periods=5, freq="D")
    
    data = {
        "date": future_dates,
        "open_price": [10.0 + i * 0.1 for i in range(5)],
        "high_price": [10.5 + i * 0.1 for i in range(5)],
        "low_price": [9.5 + i * 0.1 for i in range(5)],
        "close_price": [10.2 + i * 0.1 for i in range(5)],
        "volume": [1000000.0 for _ in range(5)],
        "amount": [10000000.0 for _ in range(5)],
        "code": ["600000.SH" for _ in range(5)],
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def invalid_data_duplicate_date() -> pd.DataFrame:
    dates = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"])
    
    data = {
        "date": dates,
        "open_price": [10.0, 10.1, 10.2],
        "high_price": [10.5, 10.6, 10.7],
        "low_price": [9.5, 9.6, 9.7],
        "close_price": [10.2, 10.3, 10.4],
        "volume": [1000000.0, 1100000.0, 1200000.0],
        "amount": [10000000.0, 11000000.0, 12000000.0],
        "code": ["600000.SH", "600000.SH", "600000.SH"],
    }
    
    return pd.DataFrame(data)
