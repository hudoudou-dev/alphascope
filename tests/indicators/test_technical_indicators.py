from datetime import datetime

import pandas as pd
import pytest

from src.indicators.technical_indicators import TechnicalIndicators


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
    
    data = []
    for i, date in enumerate(dates):
        base_price = 10.0 + i * 0.05
        data.append({
            "date": date,
            "open_price": base_price,
            "high_price": base_price + 0.3,
            "low_price": base_price - 0.3,
            "close_price": base_price + 0.1,
            "volume": 1000000.0 + i * 5000,
            "amount": 10000000.0 + i * 50000,
        })
    
    return pd.DataFrame(data)


class TestTechnicalIndicators:
    
    def test_init(self):
        indicators = TechnicalIndicators()
        assert indicators is not None
    
    def test_add_all_indicators(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_all_indicators(sample_price_data)
        
        assert not result.empty
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert "ma20" in result.columns
        assert "rsi" in result.columns
        assert "macd" in result.columns
        assert "bb_upper" in result.columns
    
    def test_add_ma(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_ma(sample_price_data, periods=[5, 10, 20])
        
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert "ma20" in result.columns
        
        assert not result["ma5"].isna().all()
        assert not result["ma10"].isna().all()
    
    def test_add_rsi(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_rsi(sample_price_data, period=14)
        
        assert "rsi" in result.columns
        assert result["rsi"].iloc[-1] >= 0
        assert result["rsi"].iloc[-1] <= 100
    
    def test_add_macd(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_macd(sample_price_data)
        
        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_hist" in result.columns
    
    def test_add_bollinger_bands(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_bollinger_bands(sample_price_data)
        
        assert "bb_middle" in result.columns
        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns
        assert "bb_width" in result.columns
        
        assert result["bb_upper"].iloc[-1] > result["bb_middle"].iloc[-1]
        assert result["bb_lower"].iloc[-1] < result["bb_middle"].iloc[-1]
    
    def test_add_volume_indicators(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_volume_indicators(sample_price_data)
        
        assert "volume_ma5" in result.columns
        assert "volume_ma10" in result.columns
        assert "volume_ratio" in result.columns
    
    def test_add_price_indicators(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        result = indicators.add_price_indicators(sample_price_data)
        
        assert "price_change" in result.columns
        assert "high_low_pct" in result.columns
        assert "open_close_pct" in result.columns
    
    def test_calculate_ma_score(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        df_with_indicators = indicators.add_ma(sample_price_data)
        
        score = indicators.calculate_ma_score(df_with_indicators)
        
        assert 0 <= score <= 100
    
    def test_calculate_rsi_score(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        df_with_indicators = indicators.add_rsi(sample_price_data)
        
        score = indicators.calculate_rsi_score(df_with_indicators)
        
        assert 0 <= score <= 100
    
    def test_calculate_macd_score(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        df_with_indicators = indicators.add_macd(sample_price_data)
        
        score = indicators.calculate_macd_score(df_with_indicators)
        
        assert 0 <= score <= 100
    
    def test_calculate_volume_score(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        df_with_indicators = indicators.add_volume_indicators(sample_price_data)
        
        score = indicators.calculate_volume_score(df_with_indicators)
        
        assert 0 <= score <= 100
    
    def test_calculate_composite_score(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        df_with_indicators = indicators.add_all_indicators(sample_price_data)
        
        score = indicators.calculate_composite_score(df_with_indicators)
        
        assert 0 <= score <= 100
    
    def test_calculate_composite_score_with_weights(self, sample_price_data: pd.DataFrame):
        indicators = TechnicalIndicators()
        
        df_with_indicators = indicators.add_all_indicators(sample_price_data)
        
        weights = {
            "ma": 0.4,
            "rsi": 0.3,
            "macd": 0.2,
            "volume": 0.1,
        }
        
        score = indicators.calculate_composite_score(df_with_indicators, weights=weights)
        
        assert 0 <= score <= 100
    
    def test_empty_dataframe_handling(self):
        indicators = TechnicalIndicators()
        
        empty_df = pd.DataFrame()
        
        result = indicators.add_all_indicators(empty_df)
        
        assert result.empty
    
    def test_short_dataframe_handling(self):
        indicators = TechnicalIndicators()
        
        short_df = pd.DataFrame({
            "date": [datetime(2024, 1, 1)],
            "close_price": [10.0],
            "volume": [1000000.0],
        })
        
        result = indicators.add_all_indicators(short_df)
        
        assert not result.empty