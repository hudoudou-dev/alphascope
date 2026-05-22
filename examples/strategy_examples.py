from datetime import datetime
from typing import Any

import pandas as pd

from src.indicators.technical_indicators import TechnicalIndicators
from src.strategy.base_strategy import BaseStrategy, StrategyContext


class SimpleMAStrategy(BaseStrategy):
    
    def __init__(self, strategy_name: str | None = None):
        super().__init__(strategy_name or "SimpleMAStrategy")
        
        self.ma_short_period = 5
        self.ma_long_period = 20
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        
        df = indicators.add_ma(df, periods=[self.ma_short_period, self.ma_long_period])
        df = indicators.add_rsi(df)
        df = indicators.add_volume_indicators(df)
        
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty or len(code_df) < self.ma_long_period:
            return 50.0
        
        latest = code_df.iloc[-1]
        score = 50.0
        
        ma_short = latest.get(f"ma{self.ma_short_period}")
        ma_long = latest.get(f"ma{self.ma_long_period}")
        close_price = latest.get("close_price")
        
        if ma_short and ma_long and close_price:
            if close_price > ma_short > ma_long:
                score += 20
            elif close_price > ma_short:
                score += 10
            elif close_price < ma_short < ma_long:
                score -= 20
        
        rsi = latest.get("rsi")
        if rsi:
            if rsi < 30:
                score += 15
            elif rsi > 70:
                score -= 15
        
        volume_ratio = latest.get("volume_ratio")
        if volume_ratio and volume_ratio > 1.5:
            score += 10
        
        return max(0, min(100, score))
    
    def _check_sell_signal(
        self,
        code: str,
        daily_data: pd.Series,
        position: Any,
        ctx: StrategyContext,
    ) -> bool:
        if self._prepared_data is None:
            return False
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty:
            return False
        
        latest = code_df.iloc[-1]
        
        ma_short = latest.get(f"ma{self.ma_short_period}")
        ma_long = latest.get(f"ma{self.ma_long_period}")
        close_price = latest.get("close_price")
        
        if ma_short and ma_long and close_price:
            if close_price < ma_short < ma_long:
                return True
        
        return False


class RSIReversalStrategy(BaseStrategy):
    
    def __init__(self, strategy_name: str | None = None):
        super().__init__(strategy_name or "RSIReversalStrategy")
        
        self.rsi_oversold = 30
        self.rsi_overbought = 70
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        
        df = indicators.add_rsi(df, period=14)
        df = indicators.add_ma(df, periods=[5, 10])
        df = indicators.add_bollinger_bands(df)
        
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty:
            return 50.0
        
        latest = code_df.iloc[-1]
        score = 50.0
        
        rsi = latest.get("rsi")
        
        if rsi:
            if rsi < self.rsi_oversold:
                score = 80.0
            elif rsi < 40:
                score = 70.0
            elif rsi > self.rsi_overbought:
                score = 20.0
            elif rsi > 60:
                score = 30.0
        
        bb_lower = latest.get("bb_lower")
        close_price = latest.get("close_price")
        
        if bb_lower and close_price and close_price < bb_lower:
            score += 10
        
        return max(0, min(100, score))
    
    def _check_sell_signal(
        self,
        code: str,
        daily_data: pd.Series,
        position: Any,
        ctx: StrategyContext,
    ) -> bool:
        if self._prepared_data is None:
            return False
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty:
            return False
        
        latest = code_df.iloc[-1]
        rsi = latest.get("rsi")
        
        if rsi and rsi > self.rsi_overbought:
            return True
        
        return False


def create_example_strategy_usage():
    print("\n" + "="*60)
    print("策略引擎使用示例")
    print("="*60)
    
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    
    data = []
    for i, date in enumerate(dates):
        base_price = 10.0 + i * 0.1
        data.append({
            "date": date,
            "open_price": base_price,
            "high_price": base_price + 0.5,
            "low_price": base_price - 0.5,
            "close_price": base_price + 0.2,
            "volume": 1000000.0 + i * 10000,
            "amount": 10000000.0 + i * 100000,
            "code": "600000.SH",
        })
    
    df = pd.DataFrame(data)
    
    strategy = SimpleMAStrategy()
    
    ctx = StrategyContext(
        date=datetime(2024, 1, 30),
        available_cash=100000.0,
        positions={},
        total_assets=100000.0,
    )
    
    result = strategy.execute(df, ctx)
    
    print(f"\n策略名称: {strategy.strategy_name}")
    print(f"买入信号: {result['buy_signals']}")
    print(f"卖出信号: {result['sell_signals']}")
    print(f"股票评分: {result['scores']}")
    
    print("\n" + "-"*60)


if __name__ == "__main__":
    create_example_strategy_usage()