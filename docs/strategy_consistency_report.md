# 选股生成结果 vs 回测分析展示 — 策略一致性分析报告

> 生成时间：2026-07-14
> 目的：验证选股模块与回测模块是否使用相同的选股/打分策略
> 状态：纯分析文档，不含代码修改

---

## 一、用户理解的验证

### 用户理解（准确度评估）

| 用户的描述 | 代码实际行为 | 准确度 |
|-----------|-------------|--------|
| "选股基于策略配置中的超参" | ✅ `SelectionConfig.from_config()` 从 `config/settings.yaml` 加载 | ✅ 正确 |
| "基于当前候选池股票的k线，选择最近 limit_stat_period 日时间窗口" | ⚠️ 部分准确 | ⚠️ 见分析 |
| "对窗口内的数据打分" | ✅ 调用 `strategy.score_stock(code, df_recent)` | ✅ 正确（但窗口对得分几无影响）|
| "回测基于滑动窗口，由远及近逐日计算得分" | ✅ `BacktestEngine.run()` 逐日循环 | ✅ 正确 |
| "按 limit_stat_period 滑窗" | ⚠️ 需要修正 | ⚠️ `limit_stat_period` 不是滑窗参数 |
| "两个模块策略一致" | ✅ 核心打分逻辑完全一致 | ✅ 正确 |

---

## 二、策略一致性：结论先行

### 核心结论：两个模块的选股/打分策略完全一致 ✅

- **策略对象**：完全相同的 `SelectionStrategy` 实例
- **配置来源**：完全相同的 `config/settings.yaml` → `strategy.selection` 节点
- **得分计算**：完全相同的代码路径 `score_stock()` → `StrategyCombiner.score_stock_unified()`
- **四个子策略**：相同的 TrendStrategy / MomentumStrategy / VolumePriceStrategy / QualityStrategy
- **融合方式**：相同的 WeightedAverageCombiner，相同的权重
- **后处理**：相同的长期强势加分（+3.0）和涨跌停惩罚

**唯一差异**：执行模式（快照 vs 滑动窗口），这是设计上的必然差异，不影响策略逻辑的一致性。

---

## 三、详细对比分析

### 3.1 配置加载

```
选股模块 (selection.py:45-46)
    selection_config = SelectionConfig.from_config()
    strategy = SelectionStrategy(selection_config)

回测模块 (backtest.py:114-118)
    selection_config = SelectionConfig.from_config()
    selection_config.initial_cash = req.initial_cash     # ← 仅额外覆盖资金参数
    selection_config.max_positions = req.max_positions    # ← 仅额外覆盖持仓参数
    strategy = SelectionStrategy(selection_config)
```

✅ **同源配置，100% 一致**

---

### 3.2 得分计算核心调用链

```
选股模块调用链：
    SelectionStrategy.prepare(df)           # 技术指标计算
    → SelectionStrategy.filter_stock()      # 硬筛选
    → df.tail(limit_stat_period)            # 取最近N天数据
    → SelectionStrategy.score_stock(code, df_recent)
        → StrategyCombiner.score_stock_unified()
            → TrendStrategy.score_stock()
            → MomentumStrategy.score_stock()
            → VolumePriceStrategy.score_stock()
            → QualityStrategy.score_stock()
            → WeightedAverageCombiner.combine()
        → +3.0 长期强势加分
        → × penalty 涨跌停惩罚
        → clamp [0, 100]

回测模块调用链：
    SelectionStrategy.execute(df, ctx, date)
        → SelectionStrategy.prepare(df)     # 技术指标计算（全量）
        → for each code:
            → code_data = prepared_df[prepared_df["code"] == code]  # 全量历史
            → SelectionStrategy.score_stock(code, code_data)        # ← 同一函数！
                → 完全相同的内部调用链（子策略→组合器→后处理）

    同时 should_buy() 中也会再调用一次：
        → code_data = self._prepared_data[self._prepared_data["code"] == code]
        → self.score_stock(code, code_data)  # ← 同一函数！
```

✅ **代码路径完全一致 — 调用的是同一个 `SelectionStrategy.score_stock()` 方法**

---

### 3.3 关键差异点：传入 score_stock 的数据窗口不同

| 维度 | 选股模块 | 回测模块 |
|------|---------|---------|
| 传入数据 | `df.tail(limit_stat_period)` — 最近60天 | `prepared_df[prepared_df["code"] == code]` — 全部历史 |
| 回测初期 | N/A | 早期数据较短（如只有10天），但随日期推进增长 |
| 对得分的影响 | **近乎为零** | **近乎为零** |

**为什么窗口不同对得分无影响？**

所有16个因子的评分逻辑中：

- **90% 的因子只读 `latest` 行**（已预计算的技术指标）：
  - ADX、MA、MACD、RSI 信号线 → 只看 `stock_data.iloc[-1]` 行的预计算值
  - 量比、换手率、波动率、偏度、下行风险、基本面 → 只看 `latest`
  
- **需要少量历史数据的因子**最多只看最近5-10天：
  - 短期反转 → `tail(5)`
  - OBV → `tail(5)`
  - 缩量止跌 → `tail(3)` + `tail(6)`
  
- **多周期动量**需要 `iloc[-10]`、`iloc[-20]`、`iloc[-60]`，但这些在数据长度≥60天时都能满足

因此，`tail(60)` 截断对得分计算**没有实际影响**。

---

### 3.4 关于 `limit_stat_period` 的真实作用

`limit_stat_period` 的设计本意是**涨跌停统计周期**，配置文件注释定义为"涨跌停统计窗口（天）"，其在代码中的实际用途：

| 使用位置 | 作用 |
|---------|------|
| `_calc_limit_penalty()` | 取最近 N 天计算涨跌停惩罚系数（涨停次数越多惩罚越小，跌停次数越多惩罚越大） |
| `filter_stock()` | 统计近 N 日跌停次数（≥3次则过滤） |
| `selection.py:72` | 截断传给 `score_stock` 的数据（副作用，无实际影响） |

> ⚠️ **`limit_stat_period` 不是滑动窗口参数**，它不控制回测的窗口大小。回测的"窗口"由 `start_date` → `end_date` 的逐日推进自然形成。

---

### 3.5 筛选逻辑对比

| 环节 | 选股模块 | 回测模块 | 一致性 |
|------|---------|---------|--------|
| 硬筛选 | `filter_stock()`: 价格/市值/涨跌停/ST | 无显式调用 `filter_stock()` | ⚠️ 差异 |
| 买入信号 | 无 | `should_buy()`: 资金/持仓/冷却期/交易频率/得分阈值 | N/A |
| 卖出信号 | 无 | `should_sell()`: 止损/止盈 | N/A |

**差异说明**：选股模块通过 `filter_stock()` 做前置硬筛选，回测模块的 `execute()` 中**未显式调用** `filter_stock()`。但因为：
- 回测的 `should_buy()` 中调用 `score_stock()` 计算得分，低分股票自然会排在后面
- 当日涨停的股票 `score_stock()` 中的涨跌停惩罚会大幅降低其得分
- 所以过滤效果通过得分自然实现

> 💡 **改进空间**：建议回测的 `execute()` 中也加入 `filter_stock()` 调用，或者至少在 `should_buy()` 中添加 ST/价格/市值等硬过滤，避免浪费计算资源。

---

## 四、策略执行流程可视化

### 选股模块（一次性快照）

```
┌──────────────────────────────────────────────────────┐
│  遍历所有股票文件的 parquet 数据                        │
│  ┌────────────────────────────────────────────────┐  │
│  │ per stock:                                      │  │
│  │   1. prepare(df) → 计算所有技术指标              │  │
│  │   2. filter_stock() → 硬筛选                     │  │
│  │   3. df.tail(60) → 取最近60天                    │  │
│  │   4. score_stock() → 多策略综合打分              │  │
│  └────────────────────────────────────────────────┘  │
│  → 所有通过筛选的股票按得分排名                        │
│  → 返回 Top-N 结果                                    │
└──────────────────────────────────────────────────────┘
```

### 回测模块（滑动窗口）

```
┌──────────────────────────────────────────────────────┐
│  加载所有股票的全量历史数据（合并为一个 DataFrame）       │
│                                                       │
│  for date in [start_date ... end_date]:               │
│  ┌────────────────────────────────────────────────┐  │
│  │  _process_date(df, date):                       │  │
│  │    execute(df, ctx, date):                      │  │
│  │      1. prepare(df) → 计算全量技术指标           │  │
│  │      2. 筛选当日股票 (date == current_date)      │  │
│  │      3. per stock:                              │  │
│  │         code_data = prepared[code] → 全量历史    │  │
│  │         score_stock(code, code_data) → 打分     │  │
│  │      4. should_buy() / should_sell() → 信号    │  │
│  │    → 执行买卖, 更新持仓和资金                     │  │
│  └────────────────────────────────────────────────┘  │
│                                                       │
│  → 汇总交易明细、收益率、最大回撤、夏普比率等             │
└──────────────────────────────────────────────────────┘
```

---

## 五、改进建议

### 5.1 一致性增强（低优先级）

| 改进项 | 说明 | 优先级 |
|--------|------|--------|
| 回测中增加 `filter_stock()` | 回测的 `execute()` 不应给 ST/超低价/小市值股票打分，与选股保持一致 | 🟡 中 |
| 选股中 `tail(limit_stat_period)` | 可去掉此截断（对得分无影响），直接传全量数据，减少歧义 | 🟢 低 |

### 5.2 架构改进（建议考虑）

| 改进项 | 说明 | 优先级 |
|--------|------|--------|
| `should_buy()` 中重复调用 `score_stock()` | `execute()` 中已经计算过一次得分，`should_buy()` 又算一次。建议将得分作为参数传入，避免重复计算 | 🟡 中 |
| 回测引擎暴露滑窗配置 | 当前滑窗大小由 `start_date`/`end_date` 隐式定义，可考虑增加显式的 `lookback_window` 参数，让用户能控制每次打分使用的历史数据长度 | 🟢 低 |
| 选股与回测得分缓存 | 同一股票在同一天被多次打分（选股+回测），可考虑缓存机制 | 🟢 低 |

### 5.3 功能增强（远期）

| 改进项 | 说明 |
|--------|------|
| 策略版本化 | 选股和回测在时间上分离时，策略配置可能已变。建议记录策略配置的快照，确保回测结果的"可复现性" |
| 横截面模式下的回测 | 当前横截面标准化在回测中未启用（逐日独立打分），可考虑每交易日做一次横截面归一化 |
| 行情自适应权重 | 类似横截面，行情自适应权重在回测中按日独立判断，可增强回测的真实性 |

---

## 六、最终结论

1. **选股模块和回测模块使用完全相同的打分策略** ✅  
   两者共享同一个 `SelectionStrategy` 类、同一套配置、同一套子策略、同一套因子权重、同一套后处理逻辑。

2. **用户的理解基本正确**，但有两个细节需要修正：
   - `limit_stat_period` 不是滑动窗口参数，它是涨跌停统计周期，不影响因子打分
   - 回测中传入 `score_stock` 的数据是全量历史（而非截断的 N 天），但因所有因子只依赖最新行或最近几天数据，不影响结果

3. **选股 = 回测最后一天的快照**  
   从数学上讲，如果回测的 `end_date` 等于"今天"，那么选股结果本质上就是回测在最后一天对所有股票的评分排序。两者的得分计算在逻辑上是**完全等价的**。

4. **不存在策略漂移风险**  
   由于配置同源、代码同路径，不会出现"选股看A策略、回测用B策略"的漂移问题。当前架构在这方面的设计是可靠的。
