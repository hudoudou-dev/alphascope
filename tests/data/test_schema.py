from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.data.schema import DataValidator


class TestDataValidator:
    
    def test_validate_happy_path(self, sample_bar_data: pd.DataFrame):
        validator = DataValidator()
        result = validator.validate(sample_bar_data)
        
        assert not result.empty
        assert len(result) == 10
        assert "date" in result.columns
        assert "code" in result.columns
    
    def test_validate_missing_required_fields(self):
        validator = DataValidator()
        df = pd.DataFrame({
            "date": [datetime.now()],
            "open_price": [10.0],
        })
        
        with pytest.raises(ValueError, match="Missing required fields"):
            validator.validate(df)
    
    def test_validate_negative_price(self, invalid_data_negative_price: pd.DataFrame):
        validator = DataValidator(check_negative_price=True)
        
        with pytest.raises(ValueError, match="contains non-positive values"):
            validator.validate(invalid_data_negative_price)
    
    def test_validate_future_date(self, invalid_data_future_date: pd.DataFrame):
        validator = DataValidator(check_future_date=True)
        
        with pytest.raises(ValueError, match="future dates"):
            validator.validate(invalid_data_future_date)
    
    def test_validate_duplicate_date(self, invalid_data_duplicate_date: pd.DataFrame):
        validator = DataValidator(check_duplicate_date=True)
        
        with pytest.raises(ValueError, match="duplicate dates"):
            validator.validate(invalid_data_duplicate_date)
    
    def test_validate_price_logic(self):
        validator = DataValidator()
        df = pd.DataFrame({
            "date": [datetime.now()],
            "open_price": [10.0],
            "high_price": [9.0],
            "low_price": [10.5],
            "close_price": [10.2],
            "volume": [1000000.0],
            "amount": [10000000.0],
            "code": ["600000.SH"],
        })
        
        with pytest.raises(ValueError, match="high_price must be >= low_price"):
            validator.validate(df)
    
    def test_cast_dtypes(self, sample_bar_data: pd.DataFrame):
        validator = DataValidator()
        result = validator.cast_dtypes(sample_bar_data)
        
        assert result["date"].dtype == "datetime64[ns]"
        assert result["open_price"].dtype == "float64"
        assert result["code"].dtype == "object"
    
    def test_validate_empty_dataframe(self):
        validator = DataValidator()
        df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="DataFrame is empty"):
            validator.validate(df)
    
    def test_validate_missing_values(self):
        validator = DataValidator(check_missing_values=True)
        df = pd.DataFrame({
            "date": [datetime.now(), None],
            "open_price": [10.0, 10.1],
            "high_price": [10.5, 10.6],
            "low_price": [9.5, 9.6],
            "close_price": [10.2, 10.3],
            "volume": [1000000.0, 1100000.0],
            "amount": [10000000.0, 11000000.0],
            "code": ["600000.SH", "600000.SH"],
        })
        
        with pytest.raises(ValueError, match="contains missing values"):
            validator.validate(df)
