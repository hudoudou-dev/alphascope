# AlphaScope AI 开发规范（Specify）

版本：2.0

---

# 1. 文档目标

本文件用于定义：

AI Agent 与开发者如何在 AlphaScope 项目中：

- 生成代码
- 修改代码
- 编写测试
- 扩展模块
- 保持架构一致性

目标：

- 保持长期可维护
- 保持 schema 稳定
- 保持模块边界清晰
- 保持 AI 可持续协作

---

# 2. AI 开发工作流

所有功能开发必须遵循：

1. 定义 Spec
2. 定义 Contract
3. 定义 Schema
4. 定义测试
5. 实现代码
6. 验证结果
7. 更新文档

禁止直接跳过规范阶段进行编码。

---

# 3. 模块生成规范

## 3.1 Data 模块规范

数据模块必须：

- 支持增量更新
- 支持 parquet 存储（`./data/raw/` 或 `./data/processed/`）
- 支持 schema 校验
- 支持失败重试
- 隔离不同数据源逻辑
- 支持基本面数据合并（PE/PB/市值，通过 daily_basic 接口）

所有数据源必须继承：

```python
BaseDataProvider
```

---

## 3.2 Strategy 模块规范

### 3.2.1 策略基类

所有策略必须继承：

```python
BaseStrategy
```

基类已提供公共能力：

```python
prepare(df, compute_turn=False)      # 统一技术指标计算 + 按股票分组
score_stock(code, stock_data) -> float  # 模板方法：因子字典 → 缺失再分配 → 返回分
finalize_score(factor_scores, weights) -> float  # 最终得分配置化
build_factor_scores(code, stock_data) -> tuple  # 子类必须实现
```

### 3.2.2 子策略接口

每个子策略必须实现：

```python
def build_factor_scores(
    self, code: str, stock_data: pd.DataFrame
) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]:
    """
    返回：
    - factor_scores: {因子名: (得分, 是否缺失)}
    - weights: {因子名: 权重}
    """
```

### 3.2.3 选股门面

`SelectionStrategy` 是唯一对外入口：

- 持有 `StrategyCombiner` + 4 套子策略
- `score_stock()` — 单股综合评分
- `score_universe()` — 全市场两阶段评分（cross_sectional/regime）
- `filter_stock()` — 价格/市值/涨跌停/风控过滤

策略必须：

- 禁止未来函数
- 禁止直接写文件
- score 阶段保持无状态

---

## 3.3 Backtest 模块规范

回测模块必须：

- 严格按时间顺序执行
- 支持 deterministic replay
- 保存参数快照
- 保存交易历史
- 支持滑点模拟

禁止：

- 修改原始数据
- 使用未来指标
- 跳过交易日校验

---

## 3.4 Indicator 模块规范

指标模块必须：

- 支持向量化计算
- 输出稳定
- 支持 rolling computation

已有指标：

- 趋势类：MA(5/10/20/60)、MACD、ADX、PDI、MDI
- 动量类：RSI、多周期动量
- 波动类：Bollinger Bands、ATR、历史波动率、偏度、下行波动率
- 量价类：量比、换手率、量价相关性(vp_corr)、OBV
- 标准化器：横截面 z-score / rank 归一化（FactorNormalizer）

建议：

- 使用 pandas DataFrame
- 避免副作用

---

## 3.5 Regime Detection 模块规范

行情状态检测必须：

- 从全市场横截面统计推导（不依赖单一指数）
- 基于多头广度（breadth）+ 平均波动率
- 输出 4 种状态：BULL / TREND / RANGE / BEAR
- 对应 4 套预定义子策略权重

默认关闭，仅当 `strategy.regime.enabled=true` 时启用。

---

## 3.6 Notification 模块规范

通知模块必须：

- 支持 retry
- 隔离 webhook provider
- 隐藏敏感信息

---

# 4. 配置规范

所有运行参数必须来自 YAML。

配置分类：

```yaml
data:
strategy:
  sub_strategies:   # 4 套子策略权重与超参
    trend: {}
    momentum: {}
    volume_price: {}
    quality: {}
  selection:        # 选股筛选/风控/因子权重
  missing_data:     # 缺失数据处理模式
  cross_sectional:  # 横截面标准化开关
  regime:           # 行情自适应开关
backtest:
notification:
scheduler:
risk_control:
storage:
```

禁止隐藏配置。

---

# 5. Schema 规范

所有 schema 必须：

- 可版本化
- 向后兼容
- 定义 required fields
- 定义 nullable fields

---

# 6. 测试规范

所有生成模块必须包含：

- happy path test
- edge case test
- failure test

策略测试必须验证：

- 无未来函数
- 输出稳定
- score 可重复

---

# 7. 日志规范

所有生成模块必须记录：

- 开始执行
- 结束执行
- retry
- failure
- timing
- 数据完整度警告（子策略 completeness）

禁止日志泄露敏感信息。

---

# 8. 性能规范

所有生成模块应：

- 使用 pandas 向量化
- 避免嵌套循环
- 减少内存复制

---

# 9. 文件组织规范

生成代码必须遵循：

```text
src/
├── api/             # FastAPI 后端
│   ├── main.py
│   ├── schemas.py
│   ├── deps.py
│   └── routers/
├── core/            # 配置与日志
├── data/            # 数据提供者
├── calendar/        # 交易日历
├── indicators/      # 技术指标 + 标准化器
├── strategy/        # 策略基类 + 子策略 + 组合器 + 行情检测 + 风控
├── backtest/        # 回测引擎
├── notifier/        # 通知系统
└── web/             # Streamlit 兼容
```

---

# 10. 文档规范

所有模块必须包含：

- 模块说明
- 参数定义
- 输入输出 schema
- 示例代码

---

# 11. AI 协作规范

Agent 生成代码时必须：

优先读取：

```text
specs/contracts/
specs/schemas/
specs/standards/
specs/constitution.md
specs/specify.md
```

禁止：

- 自行猜测字段
- 自行新增 schema
- 自行修改 contract
- 自行发明命名

新增字段前必须同步更新：

- schema
- contract
- 配置（settings.yaml）
- 文档

---

# 12. AI 安全规则

AI 生成代码禁止：

- mutable global state
- silent exception
- hardcoded secret
- undocumented schema mutation

---

# 13. Pull Request 检查清单

所有提交必须验证：

- tests passed
- schema 未破坏
- typing 完整
- logging 完整
- 文档已同步
- 向后兼容（新增功能默认关闭或不影响既有行为）
