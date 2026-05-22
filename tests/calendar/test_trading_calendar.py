from datetime import datetime, date, time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.calendar.trading_calendar import TradingCalendarService


@pytest.fixture
def temp_calendar_path(tmp_path: Path) -> Path:
    return tmp_path / "calendar" / "trading_days.parquet"


@pytest.fixture
def sample_trading_days() -> pd.DataFrame:
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    
    trading_dates = []
    for i, d in enumerate(dates):
        if d.weekday() < 5:
            trading_dates.append({
                "date": d,
                "is_trading_day": True,
                "exchange": "SSE",
            })
    
    return pd.DataFrame(trading_dates)


@pytest.fixture
def mock_akshare_calendar() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range(start="2024-01-02", periods=5, freq="D"),
        "is_trading_day": [True, True, True, True, True],
        "exchange": ["SSE", "SSE", "SSE", "SSE", "SSE"],
    })


@pytest.fixture
def mock_baostock_calendar_data() -> list[list]:
    return [
        ["2024-01-02", "1"],
        ["2024-01-03", "1"],
        ["2024-01-04", "1"],
        ["2024-01-05", "1"],
        ["2024-01-06", "0"],
    ]


class TestTradingCalendarService:
    
    def test_init(self, temp_calendar_path: Path):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        assert service.calendar_path == temp_calendar_path
        assert service.timezone == "Asia/Shanghai"
        assert service.MARKET_OPEN_TIME == time(9, 30)
        assert service.MARKET_CLOSE_TIME == time(15, 0)
    
    def test_validate_trading_days(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        result = service._validate_trading_days(sample_trading_days)
        
        assert not result.empty
        assert "date" in result.columns
        assert "is_trading_day" in result.columns
    
    def test_validate_empty_dataframe(self, temp_calendar_path: Path):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        with pytest.raises(ValueError, match="Trading days DataFrame is empty"):
            service._validate_trading_days(pd.DataFrame())
    
    def test_validate_missing_fields(self, temp_calendar_path: Path):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        df = pd.DataFrame({"date": [datetime.now()]})
        
        with pytest.raises(ValueError, match="Missing required fields"):
            service._validate_trading_days(df)
    
    def test_validate_future_dates(self, temp_calendar_path: Path):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        future_dates = pd.DataFrame({
            "date": [datetime.now() + pd.Timedelta(days=10)],
            "is_trading_day": [True],
        })
        
        result = service._validate_trading_days(future_dates)
        
        assert result.empty
    
    def test_save_and_load_parquet(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        service._save_to_parquet(sample_trading_days)
        
        assert temp_calendar_path.exists()
        
        loaded = service._load_from_parquet()
        
        assert not loaded.empty
        assert len(loaded) == len(sample_trading_days)
    
    @patch("akshare.tool_trade_date_hist_sina")
    def test_download_from_akshare(self, mock_akshare, temp_calendar_path: Path):
        mock_akshare.return_value = pd.DataFrame({
            "date": pd.date_range(start="2024-01-01", periods=5, freq="D"),
        })
        
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        df = service._download_from_akshare("2024-01-01", "2024-01-05")
        
        assert not df.empty
        assert "date" in df.columns
        assert "is_trading_day" in df.columns
    
    @patch("baostock.login")
    @patch("baostock.query_trade_dates")
    @patch("baostock.logout")
    def test_download_from_baostock(
        self, mock_logout, mock_query, mock_login, temp_calendar_path: Path
    ):
        mock_login.return_value = MagicMock(error_code="0")
        
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.next = MagicMock(side_effect=[True, True, True, False])
        mock_rs.get_row_data = MagicMock(side_effect=[
            ["2024-01-02", "1"],
            ["2024-01-03", "1"],
            ["2024-01-04", "0"],
        ])
        
        mock_query.return_value = mock_rs
        mock_logout.return_value = None
        
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        df = service._download_from_baostock("2024-01-02", "2024-01-04")
        
        assert not df.empty
        assert len(df) == 2
    
    def test_is_trading_day(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        trading_date = sample_trading_days["date"].iloc[0].date()
        
        assert service.is_trading_day(trading_date) is True
    
    def test_is_trading_day_not_trading(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        weekend = date(2024, 1, 6)
        
        assert service.is_trading_day(weekend) is False
    
    def test_previous_trading_day(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        check_date = sample_trading_days["date"].iloc[2].date()
        
        prev_day = service.previous_trading_day(check_date)
        
        assert prev_day < check_date
    
    def test_next_trading_day(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        check_date = sample_trading_days["date"].iloc[0].date()
        
        next_day = service.next_trading_day(check_date)
        
        assert next_day > check_date
    
    def test_get_trading_days(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        start = sample_trading_days["date"].min().date()
        end = sample_trading_days["date"].max().date()
        
        trading_days = service.get_trading_days(start, end)
        
        assert len(trading_days) > 0
        assert all(isinstance(d, date) for d in trading_days)
    
    def test_is_market_open(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        trading_date = sample_trading_days["date"].iloc[0].date()
        
        morning_time = datetime.combine(trading_date, time(10, 0))
        
        assert service.is_market_open(morning_time) is True
    
    def test_is_market_closed(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        trading_date = sample_trading_days["date"].iloc[0].date()
        
        night_time = datetime.combine(trading_date, time(20, 0))
        
        assert service.is_market_closed(night_time) is True
    
    def test_latest_closed_trading_day(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        trading_date = sample_trading_days["date"].iloc[0].date()
        
        after_close = datetime.combine(trading_date, time(16, 0))
        
        latest = service.latest_closed_trading_day(after_close)
        
        assert latest == trading_date
    
    def test_get_trading_days_count(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        start = sample_trading_days["date"].min().date()
        end = sample_trading_days["date"].max().date()
        
        count = service.get_trading_days_count(start, end)
        
        assert count == len(sample_trading_days)
    
    def test_get_all_trading_days(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        service._trading_days = sample_trading_days
        
        all_days = service.get_all_trading_days()
        
        assert len(all_days) == len(sample_trading_days)
        assert all(isinstance(d, date) for d in all_days)
    
    def test_update_trading_days(self, temp_calendar_path: Path, sample_trading_days: pd.DataFrame):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        service._save_to_parquet(sample_trading_days)
        service._trading_days = sample_trading_days
        
        end_date = datetime.now()
        
        with patch.object(service, "download_trading_days") as mock_download:
            mock_download.return_value = pd.DataFrame({
                "date": pd.date_range(start="2024-01-11", periods=2, freq="D"),
                "is_trading_day": [True, True],
                "exchange": ["SSE", "SSE"],
            })
            
            result = service.update_trading_days(end_date)
            
            assert not result.empty
    
    def test_update_trading_days_already_uptodate(self, temp_calendar_path: Path):
        service = TradingCalendarService(calendar_path=temp_calendar_path)
        
        future_data = pd.DataFrame({
            "date": [datetime.now() + pd.Timedelta(days=10)],
            "is_trading_day": [True],
            "exchange": ["SSE"],
        })
        
        service._trading_days = future_data
        
        end_date = datetime.now()
        
        result = service.update_trading_days(end_date)
        
        assert len(result) == len(future_data)