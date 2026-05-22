# Backtest Engine 使用示例

本文档展示如何使用 AlphaScope 的回测引擎模块。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 基本使用

### 1. 创建策略

```python
from src.strategy.base_strategy import BaseStrategy, StrategyContext
from src.indicators.technical_indicators import TechnicalIndicators

class MyStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__(strategy_name="MyStrategy")
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        return indicators.add_all_indicators(df)
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        indicators = TechnicalIndicators()
        return indicators.calculate_composite_score(code_df)
```

### 2. 运行回测

```python
from src.backtest.backtest_engine import BacktestEngine

# 初始化回测引擎
engine = BacktestEngine(
    strategy=MyStrategy(),
    initial_cash=1000000.0,
    commission_rate=0.0003,
    stamp_duty_rate=0.001,
)

# 运行回测
result = engine.run(stock_data)

# 查看结果
print(f"总收益率: {result.total_return:.2f}%")
print(f"年化收益率: {result.annual_return:.2f}%")
print(f"最大回撤: {result.max_drawdown:.2f}%")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
```

### 3. 保存交易记录

```python
# 保存交易历史
engine.save_transaction_history("./logs/transaction_history.parquet")

# 保存资产曲线
engine.save_portfolio_states("./logs/portfolio_states.parquet")
```

## 回测指标

### 总收益率 (Total Return)
```
总收益率 = (期末资产 - 期初资产) / 期初资产 * 100%
```

### 年化收益率 (Annualized Return)
```
年化收益率 = (期末资产 / 期初资产)^(252/天数) - 1 * 100%
```

### 最大回撤 (Maximum Drawdown)
```
最大回撤 = max((峰值 - 当前值) / 峰值)
```

### 夏普比率 (Sharpe Ratio)
```
夏普比率 = 平均收益率 / 收益率标准差 * sqrt(252)
```

### 胜率 (Win Rate)
```
胜率 = 盈利交易次数 / 总交易次数 * 100%
```

## 交易成本

回测引擎自动计算交易成本：

- **佣金**: 默认 0.03%，最低 5 元
- **印花税**: 默认 0.1%（仅卖出）

```python
engine = BacktestEngine(
    strategy=strategy,
    commission_rate=0.0003,  # 0.03%
    stamp_duty_rate=0.001,   # 0.1%
    min_commission=5.0,      # 最低 5 元
)
```

## 完整示例

```python
from datetime import datetime
import pandas as pd
from src.backtest.backtest_engine import BacktestEngine
from src.strategy.base_strategy import BaseStrategy
from src.indicators.technical_indicators import TechnicalIndicators

class TrendStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__(strategy_name="TrendStrategy")
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        df = indicators.add_ma(df, periods=[5, 20])
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        latest = code_df.iloc[-1]
        
        score = 50.0
        
        if latest["close_price"] > latest["ma5"] > latest["ma20"]:
            score = 75.0
        elif latest["close_price"] < latest["ma5"] < latest["ma20"]:
            score = 25.0
        
        return score

# 准备数据
stock_data = pd.DataFrame({
    "date": pd.date_range(start="2024-01-01", periods=60, freq="D"),
    "open_price": [10.0 + i * 0.05 for i in range(60)],
    "high_price": [10.3 + i * 0.05 for i in range(60)],
    "low_price": [9.7 + i * 0.05 for i in range(60)],
    "close_price": [10.1 + i * 0.05 for i in range(60)],
    "volume": [1000000.0 for _ in range(60)],
    "amount": [10000000.0 for _ in range(60)],
    "code": ["600000.SH" for _ in range(60)],
})

# 运行回测
engine = BacktestEngine(strategy=TrendStrategy(), initial_cash=1000000.0)
result = engine.run(stock_data)

# 输出结果
print(f"总收益率: {result.total_return:.2f}%")
print(f"年化收益率: {result.annual_return:.2f}%")
print(f"最大回撤: {result.max_drawdown:.2f}%")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"胜率: {result.win_rate:.2f}%")
print(f"总交易次数: {result.total_trades}")
```

## 注意事项

1. **时间顺序**: 回测严格按照时间顺序执行
2. **未来数据**: 系统会自动拒绝未来日期的数据
3. **交易成本**: 自动计算佣金和印花税
4. **风控**: 策略内置止损止盈逻辑
5. **可复现**: 回测结果可复现

## 配置

所有回测参数可以通过 YAML 配置：

```yaml
# config/settings.yaml
backtest:
  initial_cash: 1000000.0
  commission_rate: 0.0003
  stamp_duty_rate: 0.001
  min_commission: 5.0
```