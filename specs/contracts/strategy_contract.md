# Strategy Contract

## 1. BaseStrategy 接口

所有策略必须继承：

```python
BaseStrategy
```

---

## 2. 基类已提供的公共能力

### prepare

```python
prepare(df: pd.DataFrame, compute_turn: bool = False) -> pd.DataFrame
```

统一为所有子策略计算全量技术指标（按股票分组，避免跨边界污染）。
`compute_turn=True` 时额外计算换手率近似值。

子类只需调用 `super().prepare(df, compute_turn=True)` 或在 `compute_turn` 不同的场景下覆盖。

---

### score_stock

```python
score_stock(code: str, stock_data: pd.DataFrame) -> float
```

模板方法，流程为：
1. 空数据/价格校验 → 中性 50.0
2. 调用 `build_factor_scores()` 获取因子字典 + 权重
3. 调用 `_redistribute_scores()` 处理缺失因子再分配
4. 记录 completeness + debug 日志
5. 返回 `finalize_score()` 结果

评分范围：0 ~ 100

---

### build_factor_scores（子类必须实现）

```python
build_factor_scores(
    self, code: str, stock_data: pd.DataFrame
) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]
```

返回：
- factor_scores: `{因子名: (得分, 是否缺失)}`
- weights: `{因子名: 权重}`

---

### finalize_score

```python
finalize_score(
    factor_scores: dict[str, tuple[float, bool]],
    weights: dict[str, float]
) -> float
```

统一处理缺失再分配 + completeness + debug 日志，返回最终 0-100 分。

---

## 3. 选股门面（SelectionStrategy）

作为对外唯一入口，持有 `StrategyCombiner` + 4 套子策略：

- `TrendStrategy` — 趋势跟踪（ADX + MA排列 + MACD + 回调买点）
- `MomentumStrategy` — 动量反转（短期反转 + 多周期动量 + RSI）
- `VolumePriceStrategy` — 量价共振（量比 + 换手率 + 量价相关 + OBV + 缩量止跌）
- `QualityStrategy` — 低波质量（波动率 + 偏度 + 下行风险 + 基本面）

门面核心方法：

```python
score_stock(code, stock_data) -> float
score_universe(stock_dfs, breadth, avg_vol) -> dict   # 横截面两阶段评分
filter_stock(daily_data, df) -> bool                   # 筛选：价格/市值/涨跌停/风控
update_market_filter(all_data) -> None
update_st_list(st_codes) -> None
```

---

## 4. 缺失数据处理

由 `base_strategy.py` 中的 `_redistribute_scores()` 统一处理，模式由 `strategy.missing_data.mode` 控制：

| 模式 | 行为 |
|------|------|
| redistribute（默认） | 缺失因子剔除，剩余权重归一化 |
| neutral | 缺失因子按 50 分计入 |
| penalize | 缺失因子按 30 分计入 |
| exclude | 任一因子缺失 → 该策略对该股标记 incomplete |

---

## 5. 策略限制

禁止：

- future leakage
- 全局变量
- 文件写入
- 隐式状态

---

## 6. 输出规范

所有评分必须：

- deterministic
- reproducible
- schema stable

---

## 7. 调用链路

```
[开始运行]
   │
   ▼
1. prepare() ──────> 统一技术指标计算（按股票分组）
   │
   ▼
2. score_stock() ──> 调用 StrategyCombiner → 4 子策略并行评分 → 加权融合
   │
   ▼
3. filter_stock() ──> 价格/市值/涨跌停/ST/风控多维度过滤
   │
   ▼
4. score_universe() ──> [可选] 横截面标准化 + 行情自适应权重
   │
   ▼
5. Top-N 排序 ──────> 输出最终候选股票清单
```
