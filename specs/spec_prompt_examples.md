

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
c. 样式美观：整体采用淡色调（Light Mode）或严谨的工业风配色，提升量化分析的专业感。


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


------------------------------------------------------------


step-6

好的，我们开始下一个任务的推进，我需要优化UI设计模块。

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

需求：
1. 页面布局结构 (Layout)
采用标准的“左边配置管理，右边数据预览”或标签页（Tabs）布局：
* Tab 1：数据下载与同步工作台 (Data Downloader)：负责数据抓取、任务控制与进度监控。
* Tab 2：本地库存与K线验真 (Data Browser & K-Line)：负责查看本地已下载的数据资产，并进行可视化抽查。

2. 核心功能及前端交互规约 (Functional Specifications)

2.1. 数据下载配置面板 (Tab 1)
* **下载范围控制**（三选一标签页或单选框切换）：
  1. *单股下载*：提供文本输入框。
  2. *批量清单*：提供大文本域（TextArea）支持换行/逗号分隔输入，或提供文件上传组件（支持 .csv/.txt）。
  3. *全量下载*：提供一个“全选A股股票（含主板/创业板/科创板）”的复选框。
* **时间与复权配置**：
  - 日期选择器：开始日期、结束日期（默认到今天）。
  - 选择框：复权类型（前复权 / 后复权 / 不复权）。
  - 选择框：时间频度（日线 / 周线 / 5分钟线 / 1分钟线）。
* **全量数据更新逻辑（增量同步）**：
  - 提供“一键智能更新”按钮。触发时，前端需调用后端接口，自动查询本地数据库各股票的最大日期，将下载开始时间自动设为 `[本地最大日期 + 1天]`，结束时间设为 `[当前操作日当天]`。

2.2 下载执行与监控组件 (Tab 1)
* **动态进度条 (Progress Bar)**：点击“开始下载/更新”后，界面进入 Loading 状态，并实时展示一个进度条，显示 `当前进度: XX% (已完成 N/M 只股票)`。
* **实时吞吐量面板**：高亮显示当前正在下载的股票代码、下载速率（e.g., 5 只/秒）、预计剩余时间（ETA）。
* **控制台流日志 (Stream Log)**：在下方提供一个滚动文本框，实时打印底层的下载日志（如：`[INFO] 600519.SH 下载成功，共导入 1200 行数据...`），若遇到限流或网络错误，用红字突出显示。

2.3 本地库存与 K 线浏览器 (Tab 2)
* **本地资产看板 (Stock Inventory Table)**：
  - 展示一个带分页、支持搜索和排序的表格，列名包括：股票代码、股票名称、本地数据开始日期、本地数据结束日期、总记录条数、最后更新时间。
* **K 线联动预览区 (K-Line & Volume Viewer)**：
  - 选中表格中的某只股票，或在搜索框输入代码，右侧/下方立即联动渲染该股票的历史 K 线图（Candlestick Chart）。
  - K 线图包含：主图（Candlestick，鼠标悬浮显示 OHLC 价格），副图（柱状图，展示每日成交量 Volume）。
  - 支持横向滚动轴放大缩小（DataZoom），方便进行数据质量的肉眼排查。

3. 代码异常处理与健壮性规范
* **防重复触发**：当下载任务正在执行时，所有下载配置项和“开始下载”按钮必须置灰（Disabled），防止重复点击导致线程冲突。
* **容错提示**：如果由于 API 限流或网络中断导致某几只股票下载失败，不能中断整个下载任务。应该跳过并记录在失败队列中，在下载结束后弹窗友好提示：“下载完成！成功 X 只，失败 Y 只”，并提供失败清单。
* **异步处理**：下载属于长耗时任务，必须在后端使用异步（Async）或多线程/进程处理，前端通过轮询（Polling）或 WebSocket 动态获取进度，严禁阻塞前端 UI 渲染。



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


step-7

我觉得不应该设计为两个不同的页面，而应该合并为一个页面，包含数据下载、同步、本地库存、K线验真等功能。
你需要将src/web/app_v2.py、src/web/app.py合并为一个文件，实现以上功能。只需要在左边的导航栏进行界面切换就好。

另外两个需求：
1. 数据下载不应该需要人工配置数据源，目前有三个数据源：akshare、baostock、tushare，默认使用akshare，当数据下载失败时，自动切换到下一个数据源，若长时间等待，提示用户检查网络连接。以及在页面同步显示下载进度。
2. 已下载的数据，应该在本地进行存储，而不是直接在内存中进行处理。按照prd.md设计，每个股票的K线数据存储在一个parquet文件中；如果是已经完成预处理、并压缩成.parquet文件，那就保存在./data/processed/目录下。

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

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

step-8

好的，我们可以开始下一步任务，我现在已经运行起整套系统，但发现数据下载模块就存在较多问题，亟需优化。

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

数据下载页面需优化项：
1. 股票代码：仅配置6位股票代码即可，不需要人工添加.SH、.SZ后缀，后台即可根据股票代码自动判断股票所属交易所、后缀，如：600519自动添加为600519.SH，再下载对应数据即可。
2. 数据下载保存路径：需要将下载的.parquet文件保存至默认的./data/raw/目录下，每个股票的K线数据存储在一个.parquet文件中。但我刚才测试发现下载的数据直接保存在./data目录，亟需调整。
3. 下载进度展示栏：在页面下方展示一个动态进度条，显示当前下载进度（如：`当前进度: 50% (已完成 100/200 只股票的下载)`），并实时更新。
4. 下载日志：在下方提供一个滚动文本框，实时打印底层的下载日志（如：`[INFO] 600519.SH 下载成功，共导入 1200 行数据...`），若遇到限流或网络错误，用红字突出显示。
5. 下载完成：在下载完成后，在下载进度展示栏实时提示：“下载完成！成功 X 只，失败 Y 只”，并提供失败清单。
6. 下载失败：若下载过程中遇到严重错误，如网络中断、数据源不可用等，在下载日志中记录错误信息，如：“下载失败！请检查网络连接或数据源状态。”

2. 核心功能及前端交互规约 (Functional Specifications)

2.1. 数据下载配置面板 (Tab 1)
* **下载范围控制**（三选一标签页或单选框切换）：
  1. *单股下载*：提供文本输入框，不需要输入.SH、.SZ后缀，只需要输入6位数字；
  2. *批量清单*：提供大文本域（TextArea）支持换行/逗号分隔输入，或提供文件上传组件（支持 .csv/.txt）。
  3. *全量下载*：提供一个“全选A股股票（含主板/创业板/科创板）”的复选框。
* **时间与复权配置**：
  - 日期选择器：开始日期、结束日期（默认到今天）。
  - 选择框：复权类型（前复权 / 后复权 / 不复权）。
  - 选择框：时间频度（日线 / 周线 / 5分钟线 / 1分钟线）。
* **全量数据更新逻辑（增量同步）**：
  - 提供“一键智能更新”按钮。触发时，前端需调用后端接口，自动查询本地./data/raw/目录下所有股票K线数据文件的最大日期，将下载开始时间自动设为 `[本地最大日期 + 1天]`，结束时间设为 `[当前操作日当天]`。

2.2 下载执行与监控组件 (Tab 1)
* **动态进度条 (Progress Bar)**：点击“开始下载”后，界面进入 Loading 状态，并实时展示一个进度条，在下载进度展示栏，显示 `当前进度: XX% (已完成 N/M 只股票的下载)`。
* **实时吞吐量面板**：高亮显示当前正在下载的股票代码、下载速率（e.g., 5 只/秒）、预计剩余时间（ETA）。
* **控制台流日志 (Stream Log)**：在下方提供一个滚动文本框，实时打印底层的下载日志（如：`[INFO] 600519.SH 下载成功，共导入 1200 行数据...`），若遇到限流或网络错误，用红字突出显示。

3. 代码异常处理与健壮性规范
* **防重复触发**：当下载任务正在执行时，所有下载配置项和“开始下载”按钮必须置灰（Disabled），防止重复点击导致线程冲突。数据下载期间，若在导航栏切换Tab，必须提示用户等待下载完成后再切换。
* **容错提示**：如果由于 API 限流或网络中断导致某几只股票下载失败，不能中断整个下载任务。应该跳过并记录在失败队列中，在下载结束后弹窗友好提示：“下载完成！成功 X 只，失败 Y 只”，并提供失败清单。
* **异步处理**：下载属于长耗时任务，必须在后端使用异步（Async）或多线程/进程处理，前端通过轮询（Polling）或 WebSocket 动态获取进度，严禁阻塞前端 UI 渲染。


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


step-9

我们重新设计下导航页面，也就是修改下app.py文件的内容，需要调整下几个页面的布局。

请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

导航栏页面布局结构：
1. 首页：新增页面。打开的默认页面，简单界介绍本项目的核心功能，使用简单的文字描述即可：如，股票数据下载、K线查看、选股超参配置、候选股票排序，回测结果展示等。
2. 股票走势概览：合并现有的“本地库存”、“K线验真”页面。分为三部分。上部分展示整体数据情况，如，总股票数、总数据行数、总文件大小等；中间部分用于展示特定股票的数据，支持下拉框检索，按股票代码检索本地已下载的股票数据，并在表格内展示该股票的全量数据，如，每日股票明细：日期、开盘价、收盘价、成交量、成交额、涨跌幅、换手率等等。下部分用于展示该股票的历史K线图，一旦在中间部分选定特定股票后，在下部分就同步对应股票的K线数据，支持滚动轴放大缩小（DataZoom），方便进行数据质量的肉眼排查。
3. 股票数据更新：调整现有的“数据下载”页面。当前页面功能基本满足要求，但需要增加简单的备注信息。数据更新策略也需要优化，如果一个股票数据已下载，那么只更新新增数据，而不是全部重新下载。也即，要区分全量股票的增量式更新、指定股票的更新、全局股票更新等策略；
4. 选股策略配置：新增页面，可以把现有"回测分析"页面的控制面板数据，调整到这个页面。具体页面布局和功能上也需要调整，如，可以划分为任务配置（如，定时任务启停时间、日记级别等）、数据抓取配置（数据源优先级、最大重试次数、数据滑窗保留天数、并行工作线程数等）、选股策略超参（如，总市值区间、股价区间、正跌停数量区间、涨跌停区间配置、初始资金量、最大持仓股票数量、涨跌停统计周期、符合选股策略的top-N数据配置等）、评分权重配置（如，价格、涨停、市值、价格变化、60日走势等，可以设置为滚动条模式）等子模块。这些超参都可以配置，并且需要与./config/settings.yaml文件内的超参同步；
5. 选股生成结果：新增页面。基于选股策略配置，展示符合选股条件的股票清单。可以将"选股策略配置"页面的代表新超参，直接展示在该页面。通过点击“运行选股策略”按钮，触发选股策略的执行，展示符合选股条件的股票清单，按评分权重倒排排序，展示符合要求的股票代码、得分、可以交易的股票区间等。
6. 回测分析展示：新增页面。通过"选股生成结果"，获取了符合选股条件的股票清单top-N，可以将top-N的股票代码，作为回测分析的输入，展示回测结果，简单备注会在本页面对这些股票进行回测分析。并提供的简单的超参配置页面，如回测开始日期、回测结束日期、初始资金量、最大持仓股票数量、最大回调结果等。点击“运行回测”按钮，触发回测分析的执行，简单展示中间计算过程的进展（如，回测计算进度百分比），计算完毕后。在同页面新增展示回测结果概览，包括：总收益率、年化收益率、最大回测比例、总交易次数、成交胜率；并展示按时间轴维度的总资产变化数量、持仓股票数量与股票代码清单，并在最下面部分展示回测阶段的交易记录，如交易时间、交易代码、操作（如，买入、卖出），交易股价、交易股票数、交易金额、交易时选股策略的得分，卖出的盈利金额、盈利率、总持仓金额、总剩余资金、总资金（持仓金额+剩余金额）等。


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

step-10

我刚才已经查看页面设计的功能，还有几个小模块需要优化，具体如下：

修改前，请阅读以下规范：

- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml
- specs/standards/coding_standard.md

详细需求如下：
1. 增加股票名称字段：具体地，在股票数据更新模块，需要同时下载股票名称字段，并保存至.parquet数据表中，且保存的文件命名中增加股票名称（如，原名称为：300750.SZ.parquet，调整后为：300750.SZ.宁德时代.parquet）；在股票走势概览中，也需要展示股票名，具体地，整体数据概览模块的表格中，在股票代码右侧一栏，增加股票名称字段；K线图可视化模块，K线图的命名上，也需要展示股票名称（如，原名称为：300750.SZ K线图，调整后为：300750.SZ.宁德时代 K线图）；
2. 股票走势概览：股票数据明细，展示股票数据明细时，选择按日期倒序排序，优先展示最近交易日数据
3. 选股生成结果：点击“运行选股策略”后，弹出的是候选股票清单，并不是来自本地已下载的股票数据（如，我没有下载茅台、平台银行的股票，展示的数据却包含茅台）
4. 选股策略配置：任务配置模块，取消任务状态子模块。因为页面能打开，说明任务就是启动的，启动任务、停止任务的功能本身没有意义。评分权重配置模块，请结合代码内对选股评分的多个因子，选择有实际意义的权重。
5. 回测分析展示：需要基于选股生成的股票池，进一步推进回测流程。

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



数据全量下载的校验；选股超参的可视化配置；选股股票清单展示；回测结果可视化展示；自动地数据下载、策略、回测、推送闭环等

选股策略配置页面的参数 完全没有 与./config/settings.yaml文件打通与同步！需要实现以下功能：

1. 从./config/settings.yaml文件中读取参数的默认值
2. 将用户修改的参数保存到./config/settings.yaml文件中
3. 确保参数的一致性



选股策略设计。