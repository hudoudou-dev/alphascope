# Strategy Engine 使用示例

本文档展示如何使用 AlphaScope 的策略引擎模块。

## 安装依赖

```bash
pip install -r requirements.txt
```

## BaseStrategy 基类

### 1. 创建自定义策略

```python
from src.strategy.base_strategy import BaseStrategy, StrategyContext
from src.indicators.technical_indicators import TechnicalIndicators
import pandas as pd

class MyStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__(strategy_name="MyStrategy")
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        # 添加技术指标
        indicators = TechnicalIndicators()
        df = indicators.add_all_indicators(df)
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        # 实现评分逻辑
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        # 使用技术指标计算评分
        indicators = TechnicalIndicators()
        score = indicators.calculate_composite_score(code_df)
        
        return score

# 使用策略
strategy = MyStrategy()

# 创建上下文
ctx = StrategyContext(
    date=datetime.now(),
    available_cash=100000.0,
    positions={},
    total_assets=100000.0,
)

# 执行策略
result = strategy.execute(stock_data, ctx)
```

### 2. 使用内置风控

BaseStrategy 提供了内置的风控功能：

```python
# 自动止损止盈
strategy.stop_loss_pct = -8.0  # 8% 止损
strategy.take_profit_pct = 20.0  # 20% 止盈

# 仓位限制
strategy.max_position_pct = 30.0  # 单只股票最大仓位 30%
strategy.max_positions = 10  # 最大持仓数量 10 只

# 评分阈值
strategy.min_score_threshold = 60.0  # 最低评分 60 分
```

## 技术指标模块

### 1. 添加技术指标

```python
from src.indicators.technical_indicators import TechnicalIndicators

indicators = TechnicalIndicators()

# 添加所有指标
df = indicators.add_all_indicators(df)

# 添加单个指标
df = indicators.add_ma(df, periods=[5, 10, 20])
df = indicators.add_rsi(df, period=14)
df = indicators.add_macd(df)
df = indicators.add_bollinger_bands(df)
```

### 2. 计算评分

```python
# 计算综合评分
score = indicators.calculate_composite_score(df)

# 计算单个指标评分
ma_score = indicators.calculate_ma_score(df)
rsi_score = indicators.calculate_rsi_score(df)
macd_score = indicators.calculate_macd_score(df)
volume_score = indicators.calculate_volume_score(df)

# 自定义权重
weights = {
    "ma": 0.4,
    "rsi": 0.3,
    "macd": 0.2,
    "volume": 0.1,
}
score = indicators.calculate_composite_score(df, weights=weights)
```

## 完整示例

```python
from datetime import datetime
from src.strategy.base_strategy import BaseStrategy, StrategyContext
from src.indicators.technical_indicators import TechnicalIndicators
import pandas as pd

class TrendFollowingStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__(strategy_name="TrendFollowing")
        self.ma_short = 5
        self.ma_long = 20
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        df = indicators.add_ma(df, periods=[self.ma_short, self.ma_long])
        df = indicators.add_rsi(df)
        df = indicators.add_volume_indicators(df)
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        latest = code_df.iloc[-1]
        
        score = 50.0
        
        # MA 趋势判断
        if latest["close_price"] > latest[f"ma{self.ma_short}"] > latest[f"ma{self.ma_long}"]:
            score += 20
        
        # RSI 判断
        if latest["rsi"] < 30:
            score += 15
        elif latest["rsi"] > 70:
            score -= 15
        
        # 成交量判断
        if latest["volume_ratio"] > 1.5:
            score += 10
        
        return max(0, min(100, score))

# 使用策略
strategy = TrendFollowingStrategy()

# 准备数据
stock_data = pd.DataFrame({
    "date": pd.date_range(start="2024-01-01", periods=30, freq="D"),
    "open_price": [10.0 + i * 0.1 for i in range(30)],
    "high_price": [10.5 + i * 0.1 for i in range(30)],
    "low_price": [9.5 + i * 0.1 for i in range(30)],
    "close_price": [10.2 + i * 0.1 for i in range(30)],
    "volume": [1000000.0 for _ in range(30)],
    "amount": [10000000.0 for _ in range(30)],
    "code": ["600000.SH" for _ in range(30)],
})

# 创建上下文
ctx = StrategyContext(
    date=datetime(2024, 1, 30),
    available_cash=100000.0,
    positions={},
    total_assets=100000.0,
)

# 执行策略
result = strategy.execute(stock_data, ctx)

print(f"买入信号: {result['buy_signals']}")
print(f"卖出信号: {result['sell_signals']}")
print(f"股票评分: {result['scores']}")
```

## 策略配置

所有策略参数可以通过 YAML 配置：

```yaml
# config/settings.yaml
strategy:
  stop_loss_pct: -8.0
  take_profit_pct: 20.0
  max_position_pct: 30.0
  max_positions: 10
  min_score_threshold: 60.0
  
  indicators:
    ma_periods: [5, 10, 20, 60]
    rsi_period: 14
    macd_fast: 12
    macd_slow: 26
    macd_signal: 9
    
  weights:
    ma: 0.3
    rsi: 0.25
    macd: 0.25
    volume: 0.2
```

## 注意事项

1. **未来数据检查**: 系统会自动拒绝未来日期的数据
2. **评分范围**: 所有评分必须在 0-100 之间
3. **风控优先**: 风控逻辑优先级高于买入信号
4. **无状态**: score_stock 方法必须保持无状态
5. **可复现**: 所有评分必须可复现