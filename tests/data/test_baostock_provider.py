from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.providers.baostock_provider import BaoStockProvider


class TestBaoStockProvider:
    
    def test_init(self, temp_storage_path: Path):
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        assert provider.provider_name == "baostock"
        assert provider.storage_path == temp_storage_path
    
    def test_to_bs_code(self, temp_storage_path: Path):
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        assert provider._to_bs_code("600000.SH") == "sh.600000"
        assert provider._to_bs_code("000001.SZ") == "sz.000001"
        assert provider._to_bs_code("600000") == "sh.600000"
        assert provider._to_bs_code("000001") == "sz.000001"
    
    @patch("baostock.login")
    def test_login(self, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="0")
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        provider._login()
        
        assert provider._logged_in is True
        mock_login.assert_called_once()
    
    @patch("baostock.login")
    def test_login_failure(self, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="1", error_msg="Login failed")
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        with pytest.raises(ConnectionError, match="BaoStock login failed"):
            provider._login()
    
    @patch("baostock.login")
    @patch("baostock.logout")
    def test_context_manager(self, mock_logout, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="0")
        mock_logout.return_value = None
        
        with BaoStockProvider(storage_path=temp_storage_path) as provider:
            assert provider._logged_in is True
        
        mock_login.assert_called_once()
        mock_logout.assert_called_once()
    
    @patch("baostock.login")
    @patch("baostock.query_history_k_data_plus")
    def test_fetch_daily_data(self, mock_query, mock_login, temp_storage_path: Path, mock_baostock_data: list):
        mock_login.return_value = MagicMock(error_code="0")
        
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["date", "code", "open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]
        mock_rs.next = MagicMock(side_effect=[True, True, True, False])
        mock_rs.get_row_data = MagicMock(side_effect=mock_baostock_data + [[]])
        
        mock_query.return_value = mock_rs
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        
        df = provider.fetch_daily_data("600000.SH", start_date, end_date)
        
        assert not df.empty
        assert "date" in df.columns
        assert "open_price" in df.columns
    
    @patch("baostock.login")
    @patch("baostock.query_history_k_data_plus")
    def test_fetch_daily_data_empty(self, mock_query, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="0")
        
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.next = MagicMock(return_value=False)
        
        mock_query.return_value = mock_rs
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        df = provider.fetch_daily_data("600000.SH", datetime(2024, 1, 1), datetime(2024, 1, 5))
        
        assert df.empty
    
    @patch("baostock.login")
    def test_normalize_columns(self, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="0")
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "open": ["10.0"],
            "high": ["10.5"],
            "low": ["9.5"],
            "close": ["10.2"],
            "volume": ["1000000"],
            "amount": ["10000000"],
        })
        
        result = provider._normalize_columns(df, "600000.SH")
        
        assert "date" in result.columns
        assert "open_price" in result.columns
        assert "code" in result.columns
    
    @patch("baostock.login")
    @patch("baostock.query_stock_basic")
    def test_get_stock_list(self, mock_query, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="0")
        
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["code", "type"]
        mock_rs.next = MagicMock(side_effect=[True, True, True, False])
        mock_rs.get_row_data = MagicMock(side_effect=[
            ["sh.600000", "1"],
            ["sz.000001", "1"],
            ["sh.688001", "2"],
        ])
        
        mock_query.return_value = mock_rs
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        stock_list = provider.get_stock_list()
        
        assert len(stock_list) == 2
        assert "600000.SH" in stock_list
        assert "000001.SZ" in stock_list
    
    @patch("baostock.login")
    @patch("baostock.query_trade_dates")
    def test_get_trade_calendar(self, mock_query, mock_login, temp_storage_path: Path):
        mock_login.return_value = MagicMock(error_code="0")
        
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.next = MagicMock(side_effect=[True, True, False])
        mock_rs.get_row_data = MagicMock(side_effect=[
            ["2024-01-01", "1"],
            ["2024-01-02", "1"],
        ])
        
        mock_query.return_value = mock_rs
        
        provider = BaoStockProvider(storage_path=temp_storage_path)
        
        trade_dates = provider.get_trade_calendar(datetime(2024, 1, 1), datetime(2024, 1, 2))
        
        assert len(trade_dates) == 2
        assert "2024-01-01" in trade_dates
