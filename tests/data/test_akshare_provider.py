from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.providers.akshare_provider import AKShareProvider


class TestAKShareProvider:
    
    def test_init(self, temp_storage_path: Path):
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        assert provider.provider_name == "akshare"
        assert provider.storage_path == temp_storage_path
    
    @patch("akshare.stock_zh_a_hist")
    def test_fetch_daily_data(self, mock_hist, temp_storage_path: Path, mock_akshare_data: pd.DataFrame):
        mock_hist.return_value = mock_akshare_data
        
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        df = provider.fetch_daily_data("600000.SH", start_date, end_date, adjust="qfq")
        
        assert not df.empty
        assert "date" in df.columns
        assert "open_price" in df.columns
        assert "code" in df.columns
        
        mock_hist.assert_called_once()
    
    @patch("akshare.stock_zh_a_hist")
    def test_fetch_daily_data_empty(self, mock_hist, temp_storage_path: Path):
        mock_hist.return_value = pd.DataFrame()
        
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        df = provider.fetch_daily_data("600000.SH", start_date, end_date)
        
        assert df.empty
    
    @patch("akshare.stock_zh_a_hist")
    def test_fetch_daily_data_error(self, mock_hist, temp_storage_path: Path):
        mock_hist.side_effect = Exception("Network error")
        
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        with pytest.raises(Exception, match="Network error"):
            provider.fetch_daily_data("600000.SH", datetime(2024, 1, 1), datetime(2024, 1, 5))
    
    def test_normalize_columns(self, temp_storage_path: Path, mock_akshare_data: pd.DataFrame):
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        df = provider._normalize_columns(mock_akshare_data, "600000.SH")
        
        assert "date" in df.columns
        assert "open_price" in df.columns
        assert "high_price" in df.columns
        assert "low_price" in df.columns
        assert "close_price" in df.columns
        assert "volume" in df.columns
        assert "amount" in df.columns
        assert "code" in df.columns
    
    @patch("akshare.stock_info_a_code_name")
    def test_get_stock_list(self, mock_list, temp_storage_path: Path):
        mock_list.return_value = pd.DataFrame({
            "code": ["600000", "000001", "300750"],
        })
        
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        stock_list = provider.get_stock_list()
        
        assert len(stock_list) == 3
        assert "600000.SH" in stock_list
        assert "000001.SZ" in stock_list
        assert "300750.SZ" in stock_list
    
    @patch("akshare.stock_zh_a_spot_em")
    def test_get_realtime_data(self, mock_realtime, temp_storage_path: Path):
        mock_realtime.return_value = pd.DataFrame({
            "代码": ["600000"],
            "名称": ["浦发银行"],
            "最新价": [10.5],
            "涨跌幅": [1.5],
            "成交量": [1000000],
            "成交额": [10000000],
        })
        
        provider = AKShareProvider(storage_path=temp_storage_path)
        
        data = provider.get_realtime_data("600000.SH")
        
        assert data["code"] == "600000.SH"
        assert data["name"] == "浦发银行"
        assert data["price"] == 10.5
    
    def test_download_and_save_integration(self, temp_storage_path: Path, mock_akshare_data: pd.DataFrame):
        with patch("akshare.stock_zh_a_hist", return_value=mock_akshare_data):
            provider = AKShareProvider(storage_path=temp_storage_path)
            
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 5)
            
            df = provider.download_and_save("600000.SH", start_date, end_date)
            
            assert not df.empty
            
            parquet_file = temp_storage_path / "600000.SH.parquet"
            assert parquet_file.exists()
