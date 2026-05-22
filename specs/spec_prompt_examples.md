

-----------------

场景1：请基于以下规范生成：

- spec-kit/constitution.md
- spec-kit/specify.md
- spec-kit/contracts/strategy_contract.md
- spec-kit/schemas/strategy.schema.yaml

实现一个 MA 金叉策略：

要求：
1. 继承 BaseStrategy
2. 禁止 future leakage
3. 支持 YAML 参数配置
4. 包含完整 typing
5. 自动生成 pytest
6. 输出 deterministic score
7. 使用 pandas vectorized computation

请同时：
- 生成 strategy 文件
- 生成 test 文件
- 生成 example yaml
- 更新 strategy_contract.md 中的 example section

-----------------------------

场景2：生成 Data Provider

请阅读以下规范：

- spec-kit/constitution.md
- spec-kit/specify.md
- spec-kit/contracts/data_contract.md
- spec-kit/schemas/data.schema.yaml
- spec-kit/standards/coding_standard.md

现在实现：

src/data/providers/akshare_provider.py

要求：

1. 实现 BaseDataProvider
2. 支持：
   - 日线数据下载
   - 增量更新
   - parquet 持久化
3. 使用 pyarrow + snappy
4. 必须进行 schema validation
5. 支持 retry
6. 支持 structured logging
7. 不允许 future date
8. 必须兼容 Asia/Shanghai timezone

同时生成：

- pytest 单元测试
- example parquet schema
- mock data fixture

禁止：
- hardcoded config
- silent exception
- mutable global state



-----------------------------

场景3：生成 Strategy

请基于以下规范：

- spec-kit/constitution.md
- spec-kit/specify.md
- spec-kit/contracts/strategy_contract.md
- spec-kit/schemas/strategy.schema.yaml
- spec-kit/standards/testing_standard.md

实现：

src/strategy/ma_cross_strategy.py

要求：

1. 继承 BaseStrategy
2. 实现：
   - prepare
   - should_buy
   - should_sell
   - score_stock
3. 使用：
   - MA5
   - MA20
4. 使用 pandas vectorized computation
5. 禁止 future leakage
6. score 输出范围必须为 0~100
7. 所有参数来自 YAML

同时生成：

- pytest
- edge case tests
- replay test
- example yaml

测试必须验证：

- deterministic output
- no future leakage
- schema compatibility


-----------------------------

场景4：生成 Backtest Engine

请阅读：

- spec-kit/contracts/backtest_contract.md
- spec-kit/contracts/strategy_contract.md
- spec-kit/constitution.md
- spec-kit/specify.md

实现：

src/backtest/backtest_engine.py

要求：

1. 严格 chronological execution
2. 禁止 future leakage
3. 支持：
   - buy
   - sell
   - stop loss
   - take profit
4. 保存 transaction history
5. 输出：
   - total_return
   - annual_return
   - max_drawdown
   - sharpe_ratio

必须：

- deterministic replay
- typed dataclass
- structured logging

同时生成：

- pytest
- replay test
- future leakage test



-----------------------------
场景5：让 AI 做“代码审查”（非常强）

请 review 当前 backtest 模块。

重点检查：

1. 是否违反：
   - constitution.md
   - specify.md
   - backtest_contract.md

2. 是否存在：
   - future leakage
   - mutable global state
   - schema drift
   - hidden side effect
   - replay inconsistency

3. 是否符合：
   - structured logging
   - typing
   - deterministic replay

请输出：

- 风险等级
- 问题列表
- 修复建议
- 推荐 patch



-----------------------------


场景6：Schema 演化（非常重要）

现在需要为 OHLCV schema 增加：

- float_share_market_cap
- pe_ratio
- pb_ratio

请：

1. 更新：
   - data.schema.yaml
   - data_contract.md

2. 检查：
   - parquet compatibility
   - backward compatibility

3. 自动生成：
   - migration logic
   - schema version upgrade

4. 分析：
   - 对 strategy module 的影响
   - 对 backtest module 的影响

禁止破坏旧 parquet 文件读取能力。




策略清单：
MA 金叉	ma_cross
涨停板	limit_up
RSI 超卖	rsi_strategy
多因子	multi_factor
龙头股	leader_stock
AI评分	llm_score


-----------------------------

真正高级的 Prompt（你未来会大量使用）


请基于当前：

- contracts/
- schemas/
- constitution.md
- specify.md

分析当前系统是否适合：

“多策略并行回测”

请输出：

1. 当前架构瓶颈
2. schema 是否需要扩展
3. strategy contract 是否足够
4. replay consistency 风险
5. multiprocessing 风险
6. parquet IO 风险

并输出推荐重构方案。


------------------------------------------------------------

step-2

本节要点：实现data provider能力

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

现在实现：

src/data/providers/base_data_provider.py
src/data/providers/akshare_provider.py
src/data/providers/baostock_provider.py
src/data/providers/tushare_provider.py

要求：

0. 实现 BaseDataProvider
1. 实现AKshareProvider、BaoStockProvider、TushareProvider，都继承于基类BaseDataProvider
2. 支持：
   - 日线数据下载
   - 增量更新
   - parquet 持久化
3. 使用 pyarrow + snappy
4. 必须进行 schema validation
5. 支持 retry
6. 支持 structured logging
7. 不允许 future date
8. 必须兼容 Asia/Shanghai timezone

同时生成：

- pytest 单元测试
- example parquet schema
- mock data fixture

禁止：
- hardcoded config
- silent exception
- mutable global state



------------------------------------------------------------

step-3

好的，我们开始下一个任务，按你的建议，我们推进data_center_summary.md内，下一步计划章节中的：策略引擎 - BaseStrategy、技术指标模块的实现。

本节要点：实现BaseStrategy、技术指标模块。

BaseStrategy类的实现可以参考./specs/contracts/strategy_contract.md文件，策略的基本框架和接口定义在该文件内。派生策略类可以继承于BaseStrategy，实现具体的技术指标计算逻辑。

技术指标模块用于计算股票的技术指标，如移动平均线、相对强弱指标、近期涨跌停累计数数量等，这些指标可以帮助策略判断股票的价格趋势和风险，也应该是一个融合多策略、多维度的指标系统，最后再根据这些指标计算出来的多维、加权打分，来对候选股票做一个top-N的排序打分。这里面会涉及到很多超参、权重，包括买入、卖出、组合策略、多股持仓、top-N score的打分权重等，我建议统一在一个.YAML文件内管理，可以参考./configs/settings.yaml文件。


请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md
- specs/contracts/strategy_contract.md

需求参考文件：
- ./docs/data_center_summary.md文件，下一步计划章节中的：策略引擎 - BaseStrategy、技术指标模块


你需要进一步完善：
1. `prepare` 和 `score_stock` 应该作为抽象方法（@abstractmethod），强制子类必须实现。
4. `should_buy` 和 `should_sell` 在基类中提供基础的逻辑（如：默认的风控硬限制、基础的固定比例止损止盈），允许子类重写。
5. 提供一个统一的 `execute(self, ctx)` 模板方法，用来规范这四个方法在单个交易日或回测生命周期中的调用顺序。


需求：
1. 实现BaseStrategy能力，用于定义策略的基本框架和接口。参考specify.md内的 Strategy 模块规范，所有策略必须继承：BaseStrategy基类，且基类必须提供prepare、should_buy、should_sell、score_stock等方法的接口和基本功能，子类策略进一步继承后实现具体逻辑。
2. 参考specs/contracts/strategy_contract.md内对四个函数的描述和定位，完成基础功能与实现。
3. 必须进行 schema validation
4. 支持 retry
5. 支持 structured logging
6. 不允许 future date
7. 必须兼容 Asia/Shanghai timezone
8. 完成验证并更新后，将更新data_center_summary.md文件内的下一步计划中，对BaseStrategy、技术指标模块的需求描述，并标识已经完成该项任务


同时生成：

- pytest 单元测试
- example parquet schema
- mock data fixture

禁止：
- hardcoded config
- silent exception
- mutable global state


------------------------------------------------------------

step-4

好的，我们开始下一个任务，按你的建议，我们推进data_center_summary.md内，下一步计划章节中的，回测引擎 - 回测框架、风控模块的实现。

本节要点：实现回测引擎、风控模块。

BacktestEngine类的实现可以参考./specs/contracts/backtest_contract.md文件，基于两个结构体：PortfolioState、Transaction记录回测的交易数据，用作最终的回测结果输出，回测相关指标包括：总_return、年化_return、最大回撤、夏普比率、交易明细记录。也需要保留每个交易的详细信息，包括交易时间、股票代码、交易数量、交易价格、交易手续费等，用作最终可追溯完成的交易记录、可视化展示交易策略等。

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md
- specs/contracts/backtest_contract.md

需求参考文件：
- ./specs/specify.md文件，下一步计划章节中的：策略引擎 - BaseStrategy、技术指标模块
- ./specs/contracts/backtest_contract.md，参考回测规约要求执行回测引擎的实现，包含核心设计逻辑和接口契约

实现细节：
(1) BacktestEngine中实现的核心逻辑：
* **初始化 (`__init__`)**：接收初始资金 (`initial_cash`)、手续费率 (`commission_rate`)、策略实例 (`strategy`) 以及历史行情数据集。
* **主循环 (`run`)**：
  1. 按照时间序列（逐日/逐根K线）向前推进。
  2. 每日开盘前，调用 `strategy.prepare()` 预处理数据。
  3. 盘中调用 `strategy.should_sell()` 检查当前持仓是否触发卖出信号或基类的硬止损。若触发，扣减持仓、增加现金，并生成 `Transaction` 记录。
  4. 盘中调用 `strategy.score_stock()` 和 `strategy.should_buy()` 动态筛选买入标的。根据剩余可用资金计算可买数量，扣减现金、增加持仓，并生成 `Transaction` 记录。
  5. 每日收盘后，计算当日的 `PortfolioState` 并压入历史资产列表中。

(2) 回测指标计算与输出
回测结束后，引擎必须输出一个结构化的报告，至少包含以下量化指标（请使用标准的量化公式进行计算，并在代码中处理分母为 0 的异常情况）：
* **总收益率 (Total Return)**
* **年化收益率 (Annualized Return)**（假设一年 252 个交易日）
* **最大回撤 (Maximum Drawdown)**（基于每日总资产曲线计算最高点到最低点的最大跌幅）
* **夏普比率 (Sharpe Ratio)**（假设无风险利率为 0 或可配置，计算超额收益与收益率标准差的比值）
* **交易明细列表**：完整的 `List[Transaction]`，用于后续可视化与策略追溯。
* **资产曲线列表**：完整的 `List[PortfolioState]`，记录每日总资产变化。


需求：
1. 实现BacktestEngine能力，可以新生成一个文件：src/backtest/backtest_engine.py
2. 严格 chronological execution
3. 禁止 future leakage
4. 必须进行 schema validation
5. 支持：
   - buy
   - sell
   - stop loss
   - take profit
5. 输出：
   - total_return
   - annual_return
   - max_drawdown
   - sharpe_ratio
5. 保存 transaction history，保存至./logs/transaction_history.parquet 文件中即可，并支持可视化查看历史交易记录
4. 支持 retry
5. 支持 structured logging
6. 不允许 future date
7. 必须兼容 Asia/Shanghai timezone
8. 完成验证并更新后，将更新data_center_summary.md文件内的下一步计划中，对BaseStrategy、技术指标模块的需求描述，并标识已经完成该项任务


同时生成：

- pytest 单元测试
- example parquet schema
- mock data fixture
- replay test
- future leakage test

必须：
- deterministic replay
- typed dataclass
- structured logging

禁止：
- hardcoded config
- silent exception
- mutable global state


------------------------------------------------------------


step-5

好的，我们开始下一个任务，按你的建议，我们推进data_center_summary.md内，下一步计划章节中的，Web平台 - 可视化展示的实现。

本节要点：Web平台 - 可视化展示模块，技术栈就先使用Python Streamlit + React + Echarts实现。

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

需求如下：
1. 页面布局结构 (Layout)
   界面采用标准的大屏看板/工作台布局，分为三个核心区域：
* **左侧/顶部 - 控制面板 (Control Panel)**：回测超参配置区（支持滑块调整止损线、输入框配置初始资金、下拉框选择策略与基准指数、日期选择器选择回测区间），并包含一个醒目的“启动回测”按钮。
* **中央主显示区 - 数据可视化 (Data Visualization)**：采用标签页 (Tabs) 切换不同的图表。
* **底部/侧边 - 数据明细 (Data Tables & Logs)**：展示交易流水账和引擎日志。

2. 图表联动与可视化要求 (Charts Specification)
请实现以下核心图表，要求支持局部放大 (Zoom)、鼠标悬浮提示 (Tooltip) 和图例联动：
a. 资产净值与回撤图 (Equity & Drawdown)：
   - 主图：折线图。同时绘制策略每日总价值（来自 `PortfolioState`）与基准指数走势，两条曲线需做归一化处理（从 1.0 开始）。
   - 副图（或同图阴影）：面积图。展示动态回撤百分比（0% 到 -100%），用淡红色或灰色阴影高亮最大回撤区间。
b. 微观交易标的图 (Stock K-Line & Signals)：
   - 提供一个股票代码搜索/下拉框。
   - 绘制该股票的回测区间 K 线图（开盘、最高、最低、收盘）。
   - 依据 `Transaction` 记录，在 K 线上精准叠加 B（买入，绿色向上三角）和 S（卖出，红色向下三角）标记。
c. 统计分析图组 (Performance Diagnostics)：
   - 核心指标卡 (Metrics Cards)：用大字号看板高亮展示：总收益率、年化收益率、最大回撤、夏普比率、总交易次数、胜率。
   - 收益热力图 (Monthly Returns)：一个月份×年份的矩阵网格，用颜色深浅（红利绿损）直观展示每个月的收益率。
   - 行业/个股持仓权重图：柱状图或饼图，展示回测结束时（或选定日期）的持仓资产分布。

3. 数据明细与表格要求 (Data Tables)
a. 交易明细表 (Transaction Ledger)：支持分页和按股票代码/交易类型过滤的表格，展示：交易时间、股票代码、方向、数量、价格、手续费、成交额。
b. 每日状态表 (Daily Portfolio States)：展示历史每日的现金、持仓市值、总资产明细，支持导出为 CSV。

4. 代码与用户体验规范
a. 交互流畅：调整超参并点击回测后，图表数据应平滑渲染，有 Loading 加载状态提示。
b. 异常处理：若回测结果中无任何交易（交易明细为空），界面应友好提示“当前参数未触发任何交易信号”，而不是直接报错或渲染空白图表。
c. 样式美观：整体采用暗色调（Dark Mode）或严谨的工业风配色，提升量化分析的专业感。


需求：
1. 实现BacktestEngine能力，可以新生成一个文件：src/backtest/backtest_engine.py
2. 必须进行 schema validation
3. 支持 retry
4. 支持 structured logging
5. 不允许 future date
6. 必须兼容 Asia/Shanghai timezone
7. 完成验证并更新后，将更新data_center_summary.md文件内的下一步计划中，并标识已经完成该项任务


同时生成：
- pytest 单元测试
- example parquet schema
- mock data fixture
- replay test
- future leakage test

必须：
- deterministic replay
- typed dataclass
- structured logging

禁止：
- hardcoded config
- silent exception
- mutable global state


