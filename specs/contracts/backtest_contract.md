# Backtest Contract

## 1. 回测原则

回测必须：

- chronological execution
- deterministic replay
- no future leakage

---

## 2. PortfolioState

```python
PortfolioState = {    # 每日账户状态
    'date': datetime,  # 日期
    'capital': float,  # 可用资金
    'positions_value': float,  # 持仓总市值
    'positions': dict,  # 当前持仓字典 {ts_code: quantity}
    'total_value': float,  # 账户总资产 = 现金 + 市值
}
```

---

## 3. Transaction Schema

```python
Transaction = {
    'date': datetime,  # 交易日期
    'code': str,  # 股票代码
    'action': str,  # 交易操作（BUY/SELL）
    'price': float,  # 交易价格
    'shares': int,  # 交易数量
    'commission': float,  # 交易手续费
    'amount': float,  # 总成交金额
    'reason': str,   # 交易原因
}
```

---

## 4. 回测指标

必须输出：

- total_return — 总收益率
- annual_return — 年化收益率（252 交易日）
- max_drawdown — 最大回撤
- sharpe_ratio — 夏普比率
- win_rate — 胜率

---

## 5. 增强能力

- 交易日历过滤（自动跳过非交易日）
- 滑点模拟（支持固定/成交量滑点模型）
- 基准对比

---

## 6. 回测限制

禁止：

- 使用未来数据
- 修改原始数据
- 跳过交易日
