<!--
 * @Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
 * @Date: 2026-05-21 16:36:15
 * @LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
 * @LastEditTime: 2026-06-25 15:58:42
 * @FilePath: /alphascope/specs/contracts/backtest_contract.md
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
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
    'amount': float  # 总成交金额
}
```

---

## 4. 回测指标

必须输出：

- total_return
- annual_return
- max_drawdown
- sharpe_ratio
- win_rate

---

## 5. 回测限制

禁止：

- 使用未来数据
- 修改原始数据
- 跳过交易日