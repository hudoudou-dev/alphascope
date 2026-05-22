from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.app import SimpleMAStrategy, generate_sample_data


class TestWebApp:
    
    def test_simple_ma_strategy_init(self):
        strategy = SimpleMAStrategy(ma_short=5, ma_long=20)
        
        assert strategy.ma_short == 5
        assert strategy.ma_long == 20
        assert strategy.strategy_name == "SimpleMAStrategy"
    
    def test_simple_ma_strategy_prepare(self):
        strategy = SimpleMAStrategy()
        
        df = pd.DataFrame({
            "date": pd.date_range(start="2024-01-01", periods=30, freq="D"),
            "open_price": [10.0 + i * 0.1 for i in range(30)],
            "high_price": [10.5 + i * 0.1 for i in range(30)],
            "low_price": [9.5 + i * 0.1 for i in range(30)],
            "close_price": [10.2 + i * 0.1 for i in range(30)],
            "volume": [1000000.0 for _ in range(30)],
            "amount": [10000000.0 for _ in range(30)],
            "code": ["600000.SH" for _ in range(30)],
        })
        
        result = strategy.prepare(df)
        
        assert "ma5" in result.columns
        assert "ma20" in result.columns
    
    def test_simple_ma_strategy_score_stock(self):
        strategy = SimpleMAStrategy()
        
        df = pd.DataFrame({
            "date": pd.date_range(start="2024-01-01", periods=30, freq="D"),
            "open_price": [10.0 + i * 0.1 for i in range(30)],
            "high_price": [10.5 + i * 0.1 for i in range(30)],
            "low_price": [9.5 + i * 0.1 for i in range(30)],
            "close_price": [10.2 + i * 0.1 for i in range(30)],
            "volume": [1000000.0 for _ in range(30)],
            "amount": [10000000.0 for _ in range(30)],
            "code": ["600000.SH" for _ in range(30)],
        })
        
        prepared_df = strategy.prepare(df)
        strategy._prepared_data = prepared_df
        
        latest_data = prepared_df.iloc[-1]
        score = strategy.score_stock("600000.SH", latest_data)
        
        assert 0 <= score <= 100
    
    def test_generate_sample_data(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        df = generate_sample_data(start_date, end_date)
        
        assert not df.empty
        assert "date" in df.columns
        assert "open_price" in df.columns
        assert "close_price" in df.columns
        assert "code" in df.columns
    
    def test_generate_sample_data_date_range(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        df = generate_sample_data(start_date, end_date)
        
        assert len(df) == 10
    
    def test_generate_sample_data_columns(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        df = generate_sample_data(start_date, end_date)
        
        required_columns = [
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "amount",
            "code",
        ]
        
        for col in required_columns:
            assert col in df.columns