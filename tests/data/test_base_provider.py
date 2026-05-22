from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.providers.base_data_provider import BaseDataProvider


class ConcreteDataProvider(BaseDataProvider):
    
    def fetch_daily_data(self, code: str, start_date, end_date, adjust: str = "qfq") -> pd.DataFrame:
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        data = {
            "date": dates,
            "open_price": [10.0 + i * 0.1 for i in range(len(dates))],
            "high_price": [10.5 + i * 0.1 for i in range(len(dates))],
            "low_price": [9.5 + i * 0.1 for i in range(len(dates))],
            "close_price": [10.2 + i * 0.1 for i in range(len(dates))],
            "volume": [1000000.0 for _ in range(len(dates))],
            "amount": [10000000.0 for _ in range(len(dates))],
            "code": [code for _ in range(len(dates))],
        }
        return pd.DataFrame(data)
    
    def get_stock_list(self) -> list[str]:
        return ["600000.SH", "000001.SZ"]


class TestBaseDataProvider:
    
    def test_init(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        assert provider.storage_path == temp_storage_path
        assert provider.compression == "snappy"
        assert provider.retry_times == 3
        assert provider.timezone == "Asia/Shanghai"
    
    def test_normalize_code(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        assert provider._normalize_code("600000") == "600000.SH"
        assert provider._normalize_code("000001") == "000001.SZ"
        assert provider._normalize_code("300750") == "300750.SZ"
        assert provider._normalize_code("688001") == "688001.SH"
        assert provider._normalize_code("600000.SH") == "600000.SH"
    
    def test_download_and_save(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        df = provider.download_and_save("600000.SH", start_date, end_date)
        
        assert not df.empty
        assert len(df) == 10
        assert "date" in df.columns
        assert "code" in df.columns
        
        parquet_file = temp_storage_path / "600000.SH.parquet"
        assert parquet_file.exists()
    
    def test_load_from_parquet(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        provider.download_and_save("600000.SH", start_date, end_date)
        
        loaded_df = provider._load_from_parquet("600000.SH")
        
        assert not loaded_df.empty
        assert len(loaded_df) == 10
    
    def test_incremental_update(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        provider.download_and_save("600000.SH", start_date, end_date)
        
        new_end_date = datetime(2024, 1, 15)
        updated_df = provider.incremental_update("600000.SH", new_end_date)
        
        assert not updated_df.empty
        assert len(updated_df) == 15
    
    def test_incremental_update_already_uptodate(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        provider.download_and_save("600000.SH", start_date, end_date)
        
        updated_df = provider.incremental_update("600000.SH", end_date)
        
        assert len(updated_df) == 10
    
    def test_delete_data(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        provider.download_and_save("600000.SH", start_date, end_date)
        
        parquet_file = temp_storage_path / "600000.SH.parquet"
        assert parquet_file.exists()
        
        provider.delete_data("600000.SH")
        
        assert not parquet_file.exists()
    
    def test_list_available_codes(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        provider.download_and_save("600000.SH", start_date, end_date)
        provider.download_and_save("000001.SZ", start_date, end_date)
        
        codes = provider.list_available_codes()
        
        assert len(codes) == 2
        assert "600000.SH" in codes
        assert "000001.SZ" in codes
    
    def test_get_available_data(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        provider.download_and_save("600000.SH", start_date, end_date)
        
        df = provider.get_available_data("600000.SH")
        
        assert not df.empty
        assert len(df) == 10
    
    def test_get_available_data_not_exists(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        df = provider.get_available_data("999999.SH")
        
        assert df.empty
    
    def test_retry_on_failure(self, temp_storage_path: Path):
        provider = ConcreteDataProvider(storage_path=temp_storage_path)
        
        call_count = [0]
        
        def failing_fetch(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return pd.DataFrame({
                "date": [datetime.now()],
                "open_price": [10.0],
                "high_price": [10.5],
                "low_price": [9.5],
                "close_price": [10.2],
                "volume": [1000000.0],
                "amount": [10000000.0],
                "code": ["600000.SH"],
            })
        
        provider.fetch_daily_data = failing_fetch
        
        df = provider.download_and_save("600000.SH", datetime.now(), datetime.now())
        
        assert not df.empty
        assert call_count[0] == 3
