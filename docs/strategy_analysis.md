# AlphaScope 选股策略架构分析 & 优化建议

> 生成时间：2026-07-10（重写版）
> 适用范围：`SelectionStrategy` 多策略组合架构（`src/strategy/`）。
>
> ⚠️ 说明：此前的 `docs/strategy_analysis.md`（2026-07-09）描述的是**重构前的单策略设计**（1 个 `SelectionStrategy` + 3 个高度共线的均线维度，且基本面/风控/组合器均未接入）。当前代码已演进为「4 子策略 + 加权融合 + 门面风控」架构，旧文档已过时。本文档基于**当前源码**重新梳理，并给出策略 / 超参 / 代码精简三维度优化建议。

---

## 第一部分：当前选股策略架构清单

### 1. 总体分层

```
数据源 (parquet)
   │
   ▼
TechnicalIndicators.add_all_indicators(df)   ← 统一指标层（MA/RSI/MACD/BOLL/量/ADX/ATR/波动率/偏度/OBV/量价相关/高低/路径）
   │
   ▼
SelectionStrategy.prepare(df)                ← 门面：按 code 分组算指标 + turn（换手率）
   │
   ▼
StrategyCombiner.score_stock_unified(code, df)
   ├─ TrendStrategy         (融合权重 30%)  4 因子
   ├─ MomentumStrategy      (融合权重 25%)  3 因子
   ├─ VolumePriceStrategy   (融合权重 25%)  5 因子
   └─ QualityStrategy       (融合权重 20%)  4 因子
   │  （各子策略内部：因子评分 → _redistribute_scores 缺失再分配 → 0~100 分）
   ▼
WeightedAverageCombiner.combine()            ← 4 个子策略得分按权重加权
   │
   ▼
SelectionStrategy.score_stock()              ← 门面收尾：长期强势 +3 / 涨跌停惩罚 ×系数
   │
   ▼
filter_stock() + RiskControl + MarketFilter   ← 价格/市值/涨跌停/ST 过滤
   │
   ▼
API (/api/selection/run) → Web 展示
```

**调用入口**：`SelectionStrategy` 是唯一对外门面；内部通过 `StrategyCombiner` 持有并调度 4 套子策略。所有超参集中在 `config/settings.yaml` 的 `strategy.sub_strategies.*` 与 `strategy.selection.*`。

### 2. 四套子策略因子清单

#### 策略 A：TrendStrategy（趋势跟踪，融合权重 30%）

| 因子 | 权重 | 输入指标 | 评分逻辑 |
|------|------|----------|----------|
| `adx` | 0.30 | `adx` / `pdi` / `mdi` | ADX 强度 + 方向：强趋势且 PDI>MDI 高分，弱势中性 50 |
| `ma` | 0.30 | `ma5/10/20/60` + `close` | 多头/空头排列分级评分（完美多头 85，完美空头 25） |
| `macd` | 0.20 | `macd` / `macd_signal` / `macd_hist` | 金叉加分、死叉按牛熊折扣减分、柱正负微调 |
| `pullback` | 0.20 | `ma5/10/20/60` + `close` | 多头排列中的回调买点（强牛回调 75，跌破 MA60 30） |

**适配场景**：单边趋势市。

#### 策略 B：MomentumStrategy（动量反转，融合权重 25%）

| 因子 | 权重 | 输入指标 | 评分逻辑 |
|------|------|----------|----------|
| `short_reversal` | 0.35 | `pct_chg`（5 日累计） | 短期超跌→高分（严重超卖 78，过热 22） |
| `multi_momentum` | 0.35 | `close` | 10/20/60 日动量三层加权（缺失周期自动再分配） |
| `rsi` | 0.30 | `rsi` | RSI 区间评分（超卖回升 75，超买 25） |

**适配场景**：震荡市 / 超跌反弹。

#### 策略 C：VolumePriceStrategy（量价共振，融合权重 25%）

| 因子 | 权重 | 输入指标 | 评分逻辑 |
|------|------|----------|----------|
| `vol_ratio` | 0.30 | `volume_ratio` | 量比分级（>2.5 放量 75，<0.5 极度缩量 35） |
| `turnover` | 0.15 | `turn`（换手率） | 3%~10% 适中 70，>20% 极端 30 |
| `vp_corr` | 0.20 | `vp_corr` + `pct_chg` | 量价正相关且上涨高分，负相关下跌高分 |
| `obv` | 0.20 | `obv` / `obv_ma5` | OBV 在均线上方 65，下方 40 |
| `shrink_stop` | 0.15 | `close` / `volume` | 缩量止跌（价稳量缩 72，无明显信号 48） |

**适配场景**：放量突破 / 缩量企稳。

#### 策略 D：QualityStrategy（低波动质量，融合权重 20%）

| 因子 | 权重 | 输入指标 | 评分逻辑 |
|------|------|----------|----------|
| `volatility` | 0.30 | `hist_vol` | 年化波动率越低分越高（极低 78，极高 25） |
| `skewness` | 0.20 | `ret_skew` | 正偏度高分（强正偏 72，强负偏 28） |
| `downside` | 0.20 | `down_vol` | 下行波动率越低分越高（极低 75，极高 22） |
| `fundamental` | 0.30 | `pe_ttm` / `pb` / `roe` / `debt_to_equity` | 见下方「关键缺口」 |

**适配场景**：防御性配置（熊市 / 震荡）。

### 3. 缺失数据处理（四模式）

统一由 `_redistribute_scores(factor_scores, weights, ...)` 处理，模式由 `strategy.missing_data.mode` 控制：

| 模式 | 行为 | 适用 |
|------|------|------|
| `redistribute`（默认） | 缺失因子剔除，剩余因子权重归一化 | 推荐，不惩罚数据不全的股票 |
| `neutral` | 缺失因子按 50 分计入 | 中性 |
| `penalize` | 缺失因子按 30 分计入 | 惩罚数据不全者 |
| `exclude` | 任一因子缺失 → 该策略对该股标记 incomplete | 严格 |

子策略通过 `get_score_completeness()` 暴露 `{completeness, missing_factors}`，门面在 `_collect_completeness()` 中汇总并发 warning。

### 4. 门面层（SelectionStrategy）附加逻辑

- **长期强势股加分**：`close > ma20 > ma60 > 0` 时综合分 +3.0。
- **涨跌停惩罚**：`_calc_limit_penalty()` 按近 `limit_stat_period` 日跌停次数 ×0.05 扣减（最多 0.4），涨停 >3 次额外扣减；最终系数乘到综合分（下限 0.4）。
- **筛选 `filter_stock()`**：价格区间、涨跌停次数、市值区间（`total_mv`）、`RiskControl.check_buy()`（涨停 / ST）四类过滤。
- **风控组件**：`RiskControl`（涨停不可买 / ST / 仓位 / 行业集中度）+ `MarketFilter`（实时涨跌停 / ST 标记）。

### 5. 配置面（`config/settings.yaml`）

- `strategy.sub_strategies.*`：4 套子策略的融合权重 + 全部因子超参（**真实生效面**）。
- `strategy.selection.*`：筛选 / 持仓 / 风控 + 一组 legacy `score_*` 字段与 5 因子权重。
- `strategy.default.min_score_threshold=60` / `strategy.selection.min_score_threshold=50` / `SelectionConfig.from_config` 默认 70 / dataclass 默认 50 —— **四处默认值矛盾**。
- `strategy.missing_data.mode=redistribute`（真实生效）。

---

## 第二部分：问题诊断

### 🔴 关键缺口 1：基本面因子从未真正生效

`QualityStrategy._score_fundamental` 直接读 `latest.get("pe_ttm"/"pb"/"roe"/"debt_to_equity")`，但：

1. `prepare()` → `TechnicalIndicators.add_all_indicators()` **不产出任何基本面列**；
2. `FundamentalIndicators.add_fundamental_to_dataframe()` 写的是 `fundamental_*` 前缀列，与子策略读取的裸列名不匹配；
3. `TushareProvider.get_daily_basic()` 虽能取 `pe/pe_ttm/pb`（无 `roe`/`debt_to_equity`），但 `fetch_daily_data()` 主流程**根本不调用它**，OHLCV 数据帧里没有这些列。

结果：在默认 `redistribute` 模式下，`fundamental` 因子**永远缺失**，其 30% 权重被静默重新分配给波动率 / 偏度 / 下行风险。即 QualityStrategy 实际退化为「纯风险维度」策略，基本面维度形同虚设。

### 🟡 问题 2：打分是绝对阈值映射，缺乏横截面可比性

每个因子通过硬编码阈值把指标值映射成 0~100 绝对分（如 `vol_ratio > 2.5 → 75`）。缺点：

- 分数含义随行情 regime 漂移（牛市里「放量」是常态，阈值区分度下降）；
- 不同股票之间的分不可比，Top-N 排序对阈值设定敏感；
- 无法回答「相对全市场，这只股的量价/动量处于什么分位」。

### 🟡 问题 3：融合权重固定，不随行情切换

4 套子策略的融合权重（30/25/25/20）写死。但趋势市应放大 Trend，震荡 / 熊市应放大 Momentum / Quality。当前无任何 regime 检测信号（`MarketFilter` 仅记录涨跌停 / ST，无趋势 / 波动状态判断）。

### 🟡 问题 4：代码重复与死代码

- `prepare()` 在 4 个子策略 + `SelectionStrategy` 中**逐字重复**（仅 `VolumePriceStrategy` / 门面多算 `turn`）；`score_stock()` 的「空数据 / 价格校验 → 因子字典 + 权重字典 → `_redistribute_scores` → completeness → debug 日志」模板也逐字重复。
- 死代码：`VotingCombiner`、`StrategyCombiner.score_combined` / `execute_combined`（后者还有 bug：`prepared_df[prepared_df["code"] == ctx.positions.keys()]` 用 `==` 比较标量列表）、`TechnicalIndicators.calculate_ma_score / calculate_rsi_score / calculate_macd_score / calculate_volume_score / calculate_composite_score`（旧版评分，未被子策略调用）、`SelectionConfig` 中 ~30 个 legacy `score_*` / `ma_alignment_weight` 等字段及其 `to_config_dict` 对应项。
- `min_score_threshold` 默认值四处矛盾（见 5）。

### 🟢 问题 5：指标层冗余

- `add_bollinger_bands` 算了 `bb_*` 列，但子策略未使用（仅 Web 图表可能用，删除前需确认）。
- `FundamentalIndicators` 大量 `calculate_*` 方法（PE/PB/PS/ROE/ROA/毛利率…）未被策略层调用。

---

## 第三部分：三维度优化建议

### 维度一：策略优化（因子 / 架构层面）

| # | 建议 | 优先级 | 说明 |
|---|------|--------|------|
| S1 | **接通基本面**（修复缺口 1） | P0 | ① 对齐列名（子策略读 `pe_ttm/pb/roe/debt_to_equity`，或改为读 `fundamental_*`）；② 在 `prepare()` 阶段把 `get_daily_basic()` 的 `pe/pe_ttm/pb` 合并进数据帧；③ `roe/debt_to_equity` 数据缺失时按 redistribute 优雅降级，不报错。 |
| S2 | **横截面标准化打分** | P1 | 对全股票池先算各因子「原始指标值」，再横截面 z-score / rank 归一化映射到 0~100。使打分跨股票可比、对 regime 鲁棒。新增 `cross_sectional.enabled` 开关（**默认关**，向后兼容）。 |
| S3 | **行情自适应权重（regime）** | P1 | 基于宽基指数（沪深300）MA 趋势 + 全市场波动率判定 bull/trend/volatile/bear；动态切换 4 子策略融合权重（趋势市→Trend 加权，熊市→Quality/Momentum 加权）。新增 `regime` 配置节点与开关。 |
| S4 | **因子正交性增强** | P2 | Trend 与 Momentum 的 `ma` / `multi_momentum` 仍有一定共线（都依赖价格趋势），可引入横截面 rank 后的相关性监控，或增加「低相关因子」如换手率稳定性、机构持仓变化。 |
| S5 | 基本面因子扩展 | P2 | 在 S1 基础上引入 ROE 同比、资产负债率、营收增速（需补数据管道），提升 Quality 维度信息量。 |

### 维度二：超参优化

| # | 建议 | 优先级 | 说明 |
|---|------|--------|------|
| H1 | **统一 `min_score_threshold` 单一来源** | P0 | 当前四处默认值矛盾（60/50/70/50）。建议唯一来源 = `strategy.selection.min_score_threshold`，默认 50；删除其余兜底或对齐。 |
| H2 | 阈值灵敏度审计 | P1 | 现有阈值（如量比、动量边界）多为经验值。建议对关键阈值做单因子单调性 / 区分度检验（IC / 分组收益）。 |
| H3 | 因子权重寻优 | P1 | 4 子策略融合权重 + 子策略内因子权重，可用历史收益做约束优化。 |
| H4 | 缺失数据模式选择 | P2 | 回测对比 `redistribute` vs `penalize` 对选股质量的影响，给出场景建议。 |

> 📌 **超参自动寻优框架（IC 驱动权重 / 阈值寻优）**：属 Option 4，本次**不做**，仅列为后续方向。建议的落地形态：① 因子值 → 未来 N 日收益 的 IC/IR 计算；② 按 IC 归一化得到因子权重（替代手工权重）；③ 阈值网格搜索取分组收益最优。需配套历史标注数据与回测闭环。

### 维度三：代码精简

| # | 建议 | 优先级 | 说明 |
|---|------|--------|------|
| C1 | **抽取公共 `prepare()` 到 `BaseStrategy`** | P0 | 统一「分组 / 单股」路径；`VolumePriceStrategy` 仅需 `compute_turn=True` 或钩子覆盖。 |
| C2 | **抽取 `score_stock()` 模板 + `finalize_score()`** | P0 | 子策略只保留各因子评分函数；模板统一处理 空数据/价格校验 → 因子+权重字典 → `_redistribute_scores` → completeness → debug 日志。 |
| C3 | **删除确认无调用的死代码** | P1 | `VotingCombiner`、`score_combined` / `execute_combined`（含 bug）、旧版 `calculate_*_score` / `calculate_composite_score`、`SelectionConfig` legacy `score_*` 字段。删除前用代码检索确认无引用。 |
| C4 | **精简 `SelectionConfig`** | P1 | 仅保留 Web 实际使用的 5 因子权重 + `min_score_threshold` + 筛选 / 风控字段；同步清理 `schemas.py` / `routers/strategy.py` / `web/app.py` / `StrategyConfigView.vue` 中的 legacy 字段。 |
| C5 | 指标层去冗余 | P2 | 确认 `add_bollinger_bands`（bb 列）与 `FundamentalIndicators.calculate_*` 无引用后清理（Web 图表用到则保留）。 |

---

## 第四部分：本次交付范围与落地计划

- ✅ 交付物一：`docs/strategy_analysis.md`（本文件，架构清单 + 三维度建议 + 后续方向）。
- ✅ 交付物二（代码精简 / 去重，低风险）：C1 / C2 / C3 / C4 + H1。
- ✅ 交付物三（策略与因子优化，中风险）：S1 接通基本面 / S2 横截面标准化（开关默认关）/ S3 自适应权重（开关默认关）。
- ⏸️ 不做：Option 4 超参自动寻优框架（仅保留为后续方向）。

**向后兼容原则**：所有新增能力（`cross_sectional` / `regime`）均为可选开关且默认关闭；既有子策略超参语义不变；Web / API 不破坏。改造后通过既有选股 / 回测入口与 `debug_missing.py` 回归验证。

---

## 第五部分：实现状态（代码已落地）

| 项 | 状态 | 落地说明 |
|----|------|----------|
| C1 公共 `prepare()` | ✅ 已落地 | `BaseStrategy.prepare(df, compute_turn=False)` 统一分组/单股路径；`VolumePriceStrategy` 仅 `compute_turn=True`。 |
| C2 公共 `score_stock` 模板 | ✅ 已落地 | 子策略仅实现 `build_factor_scores()`；`BaseStrategy.finalize_score()` 统一处理 缺失再分配 + completeness + debug 日志。 |
| C3 死代码删除 | ✅ 已落地 | 删除 `VotingCombiner`、`score_combined`/`execute_combined`（含 bug）、`TechnicalIndicators.calculate_*_score`/`calculate_composite_score`、`SelectionConfig` 全部 legacy `score_*` 与 `ma_alignment_weight` 等字段（同步清理 `schemas.py`/`routers/strategy.py`/`settings.yaml`）。 |
| C4 精简 `SelectionConfig` | ✅ 已落地 | 仅保留 5 因子权重 + `min_score_threshold` + 筛选/风控字段；Web `StrategyConfigView.vue` 同步（无 legacy 控件残留）。 |
| C5 指标层去冗余 | ⏸️ 暂缓 | `add_bollinger_bands` 与 `FundamentalIndicators.calculate_*` 仍被 Web 图表/潜在路径引用，暂不删；`indicators.weights` 节点随 `calculate_composite_score` 失效已变为 dead config（无害，留待后续）。 |
| H1 统一 `min_score_threshold` | ✅ 已落地 | 唯一来源 = `strategy.selection.min_score_threshold`（默认 50）；删除 `strategy.default.min_score_threshold=60` 与 `SelectionConfig.from_config` 的 70 兜底。 |
| S1 接通基本面 | ✅ 已落地 | `TushareProvider` 新增 `get_daily_basic_history` + `_merge_daily_basic`，将 `pe_ttm/pb/total_mv` 等合并进日线数据（缺失优雅跳过）；`QualityStrategy._score_fundamental` 列名对齐（裸名 + `fundamental_*` 前缀回退）并优雅降级。 |
| S2 横截面标准化 | ✅ 已落地（默认关） | 新增 `src/indicators/factor_normalizer.py`（`FactorNormalizer`：zscore / rank → 0-100）；`SelectionStrategy.score_universe()` 两阶段打分；`strategy.cross_sectional` 配置节点 + `SelectionConfig.cross_sectional_enabled` 开关 + Web 开关。 |
| S3 行情自适应权重 | ✅ 已落地（默认关） | 新增 `src/strategy/regime.py`（`RegimeDetector`：由 universe 广度/波动率推导 BULL/TREND/RANGE/BEAR 并切换子策略权重）；`SelectionStrategy.score_universe()` 集成；`strategy.regime` 配置节点 + `SelectionConfig.regime_enabled` 开关 + Web 开关。 |

### 回归验证

- 单元测试式冒烟：4 子策略 + `SelectionStrategy` 默认 `score_stock` 正常；`FundamentalIndicator` 在含 `pe_ttm/pb` 时打分（不再误判缺失）；`FactorNormalizer` 两种方法与 `RegimeDetector` 三态检测正确。
- `debug_missing.py` 端到端回归通过（真实数据 16 只入选，路径一致）。
- 选股路由（`/api/selection/run`）重构为「先收集通过筛选的股票，再按需走 `score_universe` 横截面/regime 路径」；默认（开关关闭）路径行为与原逐股路径完全一致。

### 已知限制 / 后续

- `roe` / `debt_to_equity` 不在 tushare `daily_basic` 内（属财报数据），当前在 `QualityStrategy` 中优雅降级为缺失；如需接通需接入 `fina_indicator` 抓取（后续方向）。
- 超参自动寻优（IC 驱动权重/阈值，Option 4）未做，保留为后续方向。
- `indicators.weights` 配置节点与 `FundamentalIndicators.calculate_*` 为 dead code，后续可清理。

