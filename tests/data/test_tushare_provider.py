from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.providers.tushare_provider import TushareProvider


class TestTushareProvider:
    
    def test_init_with_token(self, temp_storage_path: Path):
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        assert provider.provider_name == "tushare"
        assert provider.storage_path == temp_storage_path
    
    def test_init_without_token(self, temp_storage_path: Path):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Tushare token is required"):
                TushareProvider(storage_path=temp_storage_path)
    
    def test_init_with_env_token(self, temp_storage_path: Path):
        with patch.dict("os.environ", {"TUSHARE_TOKEN": "env_token"}):
            with patch("tushare.set_token"):
                with patch("tushare.pro_api"):
                    provider = TushareProvider(storage_path=temp_storage_path)
                    assert provider is not None
    
    def test_to_ts_code(self, temp_storage_path: Path):
        with patch("tushare.set_token"):
            with patch("tushare.pro_api"):
                provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
                
                assert provider._to_ts_code("600000") == "600000.SH"
                assert provider._to_ts_code("000001") == "000001.SZ"
                assert provider._to_ts_code("600000.SH") == "600000.SH"
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_fetch_daily_data_no_adjust(self, mock_pro_api, mock_set_token, temp_storage_path: Path, mock_tushare_data: pd.DataFrame):
        mock_pro = MagicMock()
        mock_pro.daily.return_value = mock_tushare_data
        mock_pro_api.return_value = mock_pro
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        
        df = provider.fetch_daily_data("600000.SH", start_date, end_date, adjust="none")
        
        assert not df.empty
        assert "date" in df.columns
        assert "open_price" in df.columns
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_fetch_daily_data_with_adjust(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro = MagicMock()
        
        daily_data = pd.DataFrame({
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
        
        adj_factor_data = pd.DataFrame({
            "trade_date": ["20240101", "20240102", "20240103"],
            "adj_factor": [1.0, 1.1, 1.2],
        })
        
        mock_pro.daily.return_value = daily_data
        mock_pro.adj_factor.return_value = adj_factor_data
        mock_pro_api.return_value = mock_pro
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        df = provider.fetch_daily_data("600000.SH", datetime(2024, 1, 1), datetime(2024, 1, 3), adjust="qfq")
        
        assert not df.empty
        assert "date" in df.columns
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_fetch_daily_data_empty(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro = MagicMock()
        mock_pro.daily.return_value = pd.DataFrame()
        mock_pro_api.return_value = mock_pro
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        df = provider.fetch_daily_data("600000.SH", datetime(2024, 1, 1), datetime(2024, 1, 5), adjust="none")
        
        assert df.empty
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_normalize_columns(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro_api.return_value = MagicMock()
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        df = pd.DataFrame({
            "trade_date": ["20240101", "20240102"],
            "open": [10.0, 10.1],
            "high": [10.5, 10.6],
            "low": [9.5, 9.6],
            "close": [10.2, 10.3],
            "vol": [1000000, 1100000],
            "amount": [10000000, 11000000],
        })
        
        result = provider._normalize_columns(df, "600000.SH")
        
        assert "date" in result.columns
        assert "open_price" in result.columns
        assert "code" in result.columns
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_get_stock_list(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro = MagicMock()
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["600000.SH", "000001.SZ", "300750.SZ"],
            "symbol": ["600000", "000001", "300750"],
            "name": ["浦发银行", "平安银行", "宁德时代"],
        })
        mock_pro_api.return_value = mock_pro
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        stock_list = provider.get_stock_list()
        
        assert len(stock_list) == 3
        assert "600000.SH" in stock_list
        assert "000001.SZ" in stock_list
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_get_trade_calendar(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro = MagicMock()
        mock_pro.trade_cal.return_value = pd.DataFrame({
            "cal_date": ["20240101", "20240102", "20240103"],
        })
        mock_pro_api.return_value = mock_pro
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        trade_dates = provider.get_trade_calendar(datetime(2024, 1, 1), datetime(2024, 1, 3))
        
        assert len(trade_dates) == 3
        assert "20240101" in trade_dates
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_get_daily_basic(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro = MagicMock()
        mock_pro.daily_basic.return_value = pd.DataFrame({
            "ts_code": ["600000.SH"],
            "trade_date": ["20240101"],
            "close": [10.5],
            "pe": [5.5],
            "pb": [0.8],
        })
        mock_pro_api.return_value = mock_pro
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        data = provider.get_daily_basic("600000.SH", datetime(2024, 1, 1))
        
        assert data["ts_code"] == "600000.SH"
        assert data["close"] == 10.5
    
    @patch("tushare.set_token")
    @patch("tushare.pro_api")
    def test_apply_adjust(self, mock_pro_api, mock_set_token, temp_storage_path: Path):
        mock_pro_api.return_value = MagicMock()
        
        provider = TushareProvider(token="test_token", storage_path=temp_storage_path)
        
        df = pd.DataFrame({
            "open": [10.0, 10.1, 10.2],
            "high": [10.5, 10.6, 10.7],
            "low": [9.5, 9.6, 9.7],
            "close": [10.2, 10.3, 10.4],
            "adj_factor": [1.2, 1.1, 1.0],
        })
        
        result = provider._apply_adjust(df, "qfq")
        
        assert "adj_factor" in result.columns
        assert result["adj_factor"].iloc[0] == 1.0
