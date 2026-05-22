from typing import Any

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger


class TechnicalIndicators:
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.config = config_loader.get("indicators", {})
    
    def add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        
        df = df.copy()
        
        df = self.add_ma(df)
        df = self.add_rsi(df)
        df = self.add_macd(df)
        df = self.add_bollinger_bands(df)
        df = self.add_volume_indicators(df)
        df = self.add_price_indicators(df)
        
        return df
    
    def add_ma(self, df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
        if periods is None:
            periods = self.config.get("ma", {}).get("periods", [5, 10, 20, 60])
        
        df = df.copy()
        
        for period in periods:
            df[f"ma{period}"] = df["close_price"].rolling(window=period, min_periods=1).mean()
        
        return df
    
    def add_rsi(self, df: pd.DataFrame, period: int | None = None) -> pd.DataFrame:
        if period is None:
            period = self.config.get("rsi", {}).get("period", 14)
        
        df = df.copy()
        
        delta = df["close_price"].diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        
        return df
    
    def add_macd(
        self,
        df: pd.DataFrame,
        fast_period: int | None = None,
        slow_period: int | None = None,
        signal_period: int | None = None,
    ) -> pd.DataFrame:
        macd_config = self.config.get("macd", {})
        
        if fast_period is None:
            fast_period = macd_config.get("fast_period", 12)
        if slow_period is None:
            slow_period = macd_config.get("slow_period", 26)
        if signal_period is None:
            signal_period = macd_config.get("signal_period", 9)
        
        df = df.copy()
        
        ema_fast = df["close_price"].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df["close_price"].ewm(span=slow_period, adjust=False).mean()
        
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        
        return df
    
    def add_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int | None = None,
        std_dev: float | None = None,
    ) -> pd.DataFrame:
        bb_config = self.config.get("bollinger_bands", {})
        
        if period is None:
            period = bb_config.get("period", 20)
        if std_dev is None:
            std_dev = bb_config.get("std_dev", 2.0)
        
        df = df.copy()
        
        df["bb_middle"] = df["close_price"].rolling(window=period, min_periods=1).mean()
        rolling_std = df["close_price"].rolling(window=period, min_periods=1).std()
        
        df["bb_upper"] = df["bb_middle"] + (rolling_std * std_dev)
        df["bb_lower"] = df["bb_middle"] - (rolling_std * std_dev)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        
        return df
    
    def add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df["volume_ma5"] = df["volume"].rolling(window=5, min_periods=1).mean()
        df["volume_ma10"] = df["volume"].rolling(window=10, min_periods=1).mean()
        
        df["volume_ratio"] = df["volume"] / df["volume_ma5"]
        
        return df
    
    def add_price_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df["price_change"] = df["close_price"].pct_change() * 100
        
        if "high_price" in df.columns and "low_price" in df.columns:
            df["high_low_pct"] = (df["high_price"] - df["low_price"]) / df["close_price"] * 100
        
        if "open_price" in df.columns:
            df["open_close_pct"] = abs(df["close_price"] - df["open_price"]) / df["open_price"] * 100
        
        return df
    
    def calculate_ma_score(self, df: pd.DataFrame) -> float:
        if df.empty or len(df) < 20:
            return 50.0
        
        latest = df.iloc[-1]
        score = 50.0
        
        if "ma5" in latest and "ma10" in latest:
            if latest["close_price"] > latest["ma5"] > latest["ma10"]:
                score += 10
            elif latest["close_price"] < latest["ma5"] < latest["ma10"]:
                score -= 10
        
        if "ma20" in latest:
            if latest["close_price"] > latest["ma20"]:
                score += 5
            else:
                score -= 5
        
        return max(0, min(100, score))
    
    def calculate_rsi_score(self, df: pd.DataFrame) -> float:
        if df.empty or "rsi" not in df.columns:
            return 50.0
        
        rsi_config = self.config.get("rsi", {})
        oversold = rsi_config.get("oversold", 30)
        overbought = rsi_config.get("overbought", 70)
        
        latest_rsi = df.iloc[-1]["rsi"]
        
        if pd.isna(latest_rsi):
            return 50.0
        
        if latest_rsi < oversold:
            return 70.0
        elif latest_rsi > overbought:
            return 30.0
        else:
            return 50.0 + (50 - latest_rsi) * 0.5
    
    def calculate_macd_score(self, df: pd.DataFrame) -> float:
        if df.empty or "macd" not in df.columns:
            return 50.0
        
        latest = df.iloc[-1]
        
        if pd.isna(latest["macd"]) or pd.isna(latest["macd_signal"]):
            return 50.0
        
        score = 50.0
        
        if latest["macd"] > latest["macd_signal"]:
            score += 15
        
        if "macd_hist" in latest and latest["macd_hist"] > 0:
            score += 10
        
        return max(0, min(100, score))
    
    def calculate_volume_score(self, df: pd.DataFrame) -> float:
        if df.empty or "volume_ratio" not in df.columns:
            return 50.0
        
        latest = df.iloc[-1]
        volume_ratio = latest.get("volume_ratio", 1.0)
        
        if pd.isna(volume_ratio):
            return 50.0
        
        if volume_ratio > 2.0:
            return 70.0
        elif volume_ratio > 1.5:
            return 60.0
        elif volume_ratio < 0.5:
            return 40.0
        else:
            return 50.0
    
    def calculate_composite_score(
        self,
        df: pd.DataFrame,
        weights: dict[str, float] | None = None,
    ) -> float:
        if weights is None:
            weights_config = self.config.get("weights", {})
            weights = {
                "ma": weights_config.get("ma", 0.3),
                "rsi": weights_config.get("rsi", 0.25),
                "macd": weights_config.get("macd", 0.25),
                "volume": weights_config.get("volume", 0.2),
            }
        
        ma_score = self.calculate_ma_score(df)
        rsi_score = self.calculate_rsi_score(df)
        macd_score = self.calculate_macd_score(df)
        volume_score = self.calculate_volume_score(df)
        
        composite_score = (
            ma_score * weights.get("ma", 0.3) +
            rsi_score * weights.get("rsi", 0.25) +
            macd_score * weights.get("macd", 0.25) +
            volume_score * weights.get("volume", 0.2)
        )
        
        return max(0, min(100, composite_score))