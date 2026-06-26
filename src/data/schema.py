from datetime import datetime
from typing import Any

import pandas as pd


class DataValidator:
    
    REQUIRED_FIELDS = [
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "amount",
        "code",
    ]
    
    DTYPES = {
        "date": "datetime64[ns]",
        "open_price": "float64",
        "high_price": "float64",
        "low_price": "float64",
        "close_price": "float64",
        "volume": "float64",
        "amount": "float64",
        "code": "string",
    }
    
    def __init__(
        self,
        check_future_date: bool = True,
        check_negative_price: bool = True,
        check_duplicate_date: bool = True,
        check_missing_values: bool = True,
    ):
        self.check_future_date = check_future_date
        self.check_negative_price = check_negative_price
        self.check_duplicate_date = check_duplicate_date
        self.check_missing_values = check_missing_values
    
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError("DataFrame is empty")
        
        self._validate_required_fields(df)
        
        if self.check_missing_values:
            self._validate_missing_values(df)
        
        if self.check_negative_price:
            self._validate_negative_price(df)
        
        if self.check_future_date:
            self._validate_future_date(df)
        
        if self.check_duplicate_date:
            self._validate_duplicate_date(df)
        
        self._validate_price_logic(df)
        
        return df
    
    def _validate_required_fields(self, df: pd.DataFrame) -> None:
        missing_fields = [field for field in self.REQUIRED_FIELDS if field not in df.columns]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
    
    def _validate_missing_values(self, df: pd.DataFrame) -> None:
        for field in self.REQUIRED_FIELDS:
            if df[field].isna().any():
                raise ValueError(f"Field {field} contains missing values")
    
    def _validate_negative_price(self, df: pd.DataFrame) -> None:
        price_fields = ["open_price", "high_price", "low_price", "close_price"]
        for field in price_fields:
            if (df[field] <= 0).any():
                raise ValueError(f"Field {field} contains non-positive values")
    
    def _validate_future_date(self, df: pd.DataFrame) -> None:
        now = datetime.now()
        future_dates = df["date"] > now
        if future_dates.any():
            raise ValueError(f"Found {future_dates.sum()} future dates")
    
    def _validate_duplicate_date(self, df: pd.DataFrame) -> None:
        if "code" in df.columns:
            duplicates = df.duplicated(subset=["code", "date"])
        else:
            duplicates = df.duplicated(subset=["date"])
        
        if duplicates.any():
            raise ValueError(f"Found {duplicates.sum()} duplicate dates")
    
    def _validate_price_logic(self, df: pd.DataFrame) -> None:
        if (df["high_price"] < df["low_price"]).any():
            raise ValueError("high_price must be >= low_price")
        
        if (df["high_price"] < df["open_price"]).any():
            raise ValueError("high_price must be >= open_price")
        
        if (df["high_price"] < df["close_price"]).any():
            raise ValueError("high_price must be >= close_price")
        
        if (df["low_price"] > df["open_price"]).any():
            raise ValueError("low_price must be <= open_price")
        
        if (df["low_price"] > df["close_price"]).any():
            raise ValueError("low_price must be <= close_price")
    
    def cast_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        for field, dtype in self.DTYPES.items():
            if field in df.columns:
                if dtype == "datetime64[ns]":
                    df[field] = pd.to_datetime(df[field])
                elif dtype == "string":
                    df[field] = df[field].astype(str)
                else:
                    df[field] = df[field].astype(dtype)
        
        return df
