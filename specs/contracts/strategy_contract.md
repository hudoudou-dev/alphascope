# Strategy Contract

## 1. BaseStrategy 接口

所有策略必须继承：

```python
BaseStrategy
```

---

## 2. 必须实现的方法

### prepare

```python
prepare(df: pd.DataFrame) -> pd.DataFrame
```

数据准备与预处理，用于：

- 生成技术指标
- 生成因子
- 预处理数据

在评估股票前，策略需要把所有必要的历史数据（K线、财务报表、技术指标等）加载到内存中，并进行清洗或计算（比如计算 5 日均线、MACD 等）。

输入：股票代码列表（ts_code_list）、时间范围（start_date, end_date）、原始行情数据。

输出：无，或返回一个对齐好时间的结构化数据集（如 Pandas DataFrame）。

基本功能：检查数据完整性，剔除停牌、刚上市新股等异常标的。

---

### should_buy

```python
should_buy(code: str, daily_data: pd.Series) -> bool
```

用于：

- 判断是否买入

买入信号触发判定，用于判定满足“择时”的触发条件，判断当前时点是否应该对某只股票发出买入指令。

输入：特定股票代码、当前交易日数据、当前账户的持仓仓位状态。

输出：布尔值 True（买入）/ False（不买），或者包含推荐买入仓位比例的结构体。

基本功能：基类可以实现一些通用风控硬限制。比如：如果当前账户资金不足，或者该股票已经被调出股票池，即使分数再高也直接返回 False。

---


### should_sell

```python
should_sell(
    code: str,
    daily_data: pd.Series,
    position: Dict
) -> bool
```

用于：

- 判断是否卖出

卖出/止损信号触发判定，负责监控已经持有的股票，决定什么时候该落袋为安，或者割肉止损。

输入：当前持仓的股票信息、买入成本价、当前最新价格、持有天数。

输出：布尔值 True（卖出）/ False（继续持有）。

基本功能：基类可以内置全局止损/止盈逻辑。例如：默认实现“回撤超过 8% 强制止损”或“触及 20% 自动止盈”。这样子类策略就算不写卖出逻辑，也自带一套防守机制。

---

### score_stock

```python
score_stock(code: str, daily_data: pd.Series) -> float
```

用于：

- 股票评分

评分范围：

```text
0 ~ 100
```

股票打分/量化评级，选股的核心。策略会给股票池里的每一只股票打分。分数越高，说明该股票越符合当前策略的选股口味，后续就越优先考虑买入。

输入：单只股票或股票池的预处理数据（由 prepare 提供）。

输出：一个字典或 DataFrame，包含 {'股票代码': 分数/权重}（例如：{'000001.SZ': 85.5}）。

基本功能：基类可以提供一个默认的“等权重”或者“随机打分”作为 Baseline。具体的量化因子打分由子类去重写（Override）。


---

## 3. 策略限制

禁止：

- future leakage
- 全局变量
- 文件写入
- 隐式状态

---

## 4. 输出规范

所有评分必须：

- deterministic
- reproducible
- schema stable

## 5. 调用链路

[开始运行] 
   │
   ▼
1. prepare() ──────> 批量下载并洗净 K 线数据
   │
   ▼
2. score_stock() ──> 遍历股票池，算出每只股票的得分，并从高到低排序
   │
   ▼
3. should_buy() ───> 挑选高分股票，结合当前仓位，判断是否触发买入信号
   │
   ▼
4. should_sell() ──> 盘中/盘后监控已有持仓，判断是否触发止损或止盈信号
