# AlphaScope 架构文档

## 一、系统架构

AlphaScope 是一个面向 A 股市场的量化选股与回测平台，采用前后端分离 + 多层模块化设计：

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Layer                                 │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │  Vue.js 前端 (web/) │  │  FastAPI 后端 (src/api/)     │  │
│  │  - 股票走势概览     │  │  - /api/data/*    数据管理   │  │
│  │  - 选股策略配置     │  │  - /api/selection/* 选股    │  │
│  │  - 选股结果展示     │  │  - /api/strategy/* 策略配置  │  │
│  │  - 回测分析展示     │  │                              │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Strategy Layer                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SelectionStrategy（选股门面，唯一对外入口）          │   │
│  │  ├─ TrendStrategy        趋势跟踪 (30%)               │   │
│  │  ├─ MomentumStrategy     动量反转 (25%)               │   │
│  │  ├─ VolumePriceStrategy  量价共振 (25%)               │   │
│  │  └─ QualityStrategy      低波质量 (20%)               │   │
│  │       ↓ StrategyCombiner + WeightedAverage            │   │
│  │  [可选] FactorNormalizer  横截面标准化                 │   │
│  │  [可选] RegimeDetector    行情自适应权重               │   │
│  │       ↓ RiskControl + MarketFilter                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  BacktestEngine（回测引擎）                            │   │
│  │  - 交易日历过滤、滑点模拟、基准对比                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Indicator Layer                           │
│  ┌────────────────────┐ ┌────────────────────────────────┐  │
│  │ TechnicalIndicators│ │ FundamentalIndicators          │  │
│  │ MA/RSI/MACD/ADX    │ │ PE/PB/ROE 评分                 │  │
│  │ ATR/OBV/波动率/偏度 │ │                                │  │
│  │ 量比/量价相关/换手 │ │                                │  │
│  └────────────────────┘ └────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FactorNormalizer（横截面标准化器）                      │ │
│  │ z-score / rank → 0-100 跨股票可比的相对得分            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ AKShareProvider  │ │BaoStockProvider│ │TushareProvider│  │
│  │                  │ │              │ │ + daily_basic  │  │
│  └──────────────────┘ └──────────────┘ └────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ TradingCalendarService（交易日历）                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 二、核心模块

### 2.1 数据层

| 模块 | 说明 |
|------|------|
| `BaseDataProvider` | 数据提供者抽象基类 |
| `AKShareProvider` | AKShare 数据源 |
| `BaoStockProvider` | BaoStock 数据源 |
| `TushareProvider` | Tushare 数据源，含 `get_daily_basic_history()` 基本面数据合并 |
| `TradingCalendarService` | 交易日历服务 |

### 2.2 指标层

| 模块 | 说明 |
|------|------|
| `TechnicalIndicators` | 技术指标计算（20+ 指标） |
| `FundamentalIndicators` | 基本面指标评分（PE/PB/ROE/资产负债率） |
| `FactorNormalizer` | 横截面标准化器（z-score / rank） |

### 2.3 策略层

| 模块 | 说明 |
|------|------|
| `BaseStrategy` | 策略基类（公共 prepare/score_stock 模板） |
| `TrendStrategy` | 趋势跟踪子策略（ADX+MA+MACD+回调买点） |
| `MomentumStrategy` | 动量反转子策略（短期反转+多周期动量+RSI） |
| `VolumePriceStrategy` | 量价共振子策略（量比+换手率+量价相关+OBV+缩量止跌） |
| `QualityStrategy` | 低波质量子策略（波动率+偏度+下行风险+基本面） |
| `SelectionStrategy` | 选股门面（多策略组合 + 筛选 + 风控） |
| `StrategyCombiner` | 策略组合器（加权平均融合） |
| `RegimeDetector` | 行情状态检测（BULL/TREND/RANGE/BEAR） |
| `RiskControl` | 风控模块（ST/涨停/仓位/行业集中度） |
| `MarketFilter` | 市场过滤器（涨跌停/ST 实时标记） |

### 2.4 回测层

| 模块 | 说明 |
|------|------|
| `BacktestEngine` | 回测引擎（交易日历过滤、滑点模拟、基准对比） |

### 2.5 API 层

| 模块 | 说明 |
|------|------|
| `routers/data.py` | 数据下载/查询 API |
| `routers/selection.py` | 选股运行 API |
| `routers/strategy.py` | 策略配置 API |

## 三、数据流

```
数据下载 → 数据校验 → Parquet 存储 → 指标计算 → 多策略评分 → 风控过滤 → Top-N 输出
    ↓           ↓           ↓            ↓           ↓           ↓           ↓
Provider   Validator   ./data/raw/   Technical   4子策略     筛选+风控   API/Vue.js
                                  Indicators  并行打分
                                              ↓
                                    [可选] 横截面标准化
                                    [可选] 行情自适应权重
```

## 四、Web 平台功能

### 4.1 Vue.js 前端（主要）

1. **首页** — 项目介绍与功能导航
2. **股票走势概览** — 整体数据统计 + 单股数据明细 + K 线可视化和验真
3. **股票数据更新** — 单股/批量/全量下载 + 进度监控 + 日志流
4. **选股策略配置** — 超参可视化配置，与 `settings.yaml` 双向同步
5. **选股生成结果** — 运行选股策略，展示候选股票清单（按得分排序）
6. **回测分析展示** — 基于选股结果的回测分析 + 可视化

### 4.2 FastAPI 后端

- `GET/POST /api/data/*` — 数据管理（下载/查询/股票列表）
- `POST /api/selection/run` — 运行选股策略
- `GET/POST /api/strategy/*` — 策略配置读写

## 五、扩展机制

### 5.1 数据源插件

继承 `BaseDataProvider`，实现 `fetch_daily_data` 方法即可添加新数据源。

### 5.2 策略插件

继承 `BaseStrategy`，实现 `build_factor_scores` 方法，通过 `StrategyCombiner.add_strategy()` 注册。

子策略只需关注因子评分逻辑，基类已提供公共的 `prepare`、`score_stock`、`_redistribute_scores` 模板。

### 5.3 标准化器扩展

继承或替换 `FactorNormalizer`，实现新的归一化方法（如 min-max、robust scaler）。

### 5.4 通知渠道

继承 `BaseNotifier`，实现 `send` 方法即可添加新的通知渠道。
