from datetime import datetime

import pandas as pd

from src.backtest.backtest_engine import BacktestEngine
from src.indicators.technical_indicators import TechnicalIndicators
from src.strategy.base_strategy import BaseStrategy, StrategyContext


class TrendFollowingStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__(strategy_name="TrendFollowing")
        self.ma_short = 5
        self.ma_long = 20
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        df = indicators.add_ma(df, periods=[self.ma_short, self.ma_long])
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty or len(code_df) < self.ma_long:
            return 50.0
        
        latest = code_df.iloc[-1]
        score = 50.0
        
        ma_short = latest.get(f"ma{self.ma_short}")
        ma_long = latest.get(f"ma{self.ma_long}")
        close_price = latest.get("close_price")
        
        if ma_short and ma_long and close_price:
            if close_price > ma_short > ma_long:
                score = 75.0
            elif close_price > ma_short:
                score = 60.0
            elif close_price < ma_short < ma_long:
                score = 25.0
        
        return score


def create_example_backtest():
    print("\n" + "="*60)
    print("回测引擎使用示例")
    print("="*60)
    
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
            "volume": 1000000.0,
            "amount": 10000000.0,
            "code": "600000.SH",
        })
    
    df = pd.DataFrame(data)
    
    strategy = TrendFollowingStrategy()
    
    engine = BacktestEngine(
        strategy=strategy,
        initial_cash=1000000.0,
        commission_rate=0.0003,
        stamp_duty_rate=0.001,
    )
    
    result = engine.run(df)
    
    print(f"\n回测结果:")
    print(f"  总收益率: {result.total_return:.2f}%")
    print(f"  年化收益率: {result.annual_return:.2f}%")
    print(f"  最大回撤: {result.max_drawdown:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  胜率: {result.win_rate:.2f}%")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利交易: {result.winning_trades}")
    print(f"  亏损交易: {result.losing_trades}")
    
    print(f"\n交易明细:")
    for i, trans in enumerate(result.transactions[:5], 1):
        print(f"  {i}. {trans.date.strftime('%Y-%m-%d')} {trans.action} {trans.code} "
              f"{trans.shares}股 @ {trans.price:.2f}")
    
    print("\n" + "-"*60)


if __name__ == "__main__":
    create_example_backtest()