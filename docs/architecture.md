# AlphaScope 架构文档

## 一、系统架构

AlphaScope 是一个面向 A 股市场的量化选股与回测平台，采用模块化设计，主要包含以下层次：

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Layer (Streamlit)                     │
│  - 统一 Web 平台 (src/web/app.py)                            │
│  - 实时 K 线可视化                                            │
│  - 回测结果展示                                               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  - Pipeline 编排层 (src/pipeline/daily_pipeline.py)         │
│  - 调度服务 (src/scheduler/scheduler_service.py)            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Strategy Layer                            │
│  - 策略基类 (src/strategy/base_strategy.py)                  │
│  - 策略组合 (src/strategy/strategy_combiner.py)              │
│  - 风控模块 (src/strategy/risk_control.py)                   │
│  - 策略插件 (src/strategy/plugins.py)                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  - DataManager (src/data/data_manager.py)                   │
│  - 数据清理 (src/data/data_cleaner.py)                       │
│  - 数据校验 (src/data/schema.py)                             │
│  - Provider 抽象 (src/data/providers/)                       │
└─────────────────────────────────────────────────────────────┘
```

## 二、核心模块

### 2.1 数据层

| 模块 | 说明 |
|------|------|
| `AKShareProvider` | AKShare 数据源 |
| `BaoStockProvider` | BaoStock 数据源 |
| `TushareProvider` | Tushare 数据源 |
| `DataManager` | 统一数据入口，支持多 Provider 切换 |
| `DataCleaner` | 数据清理与滑动窗口 |

### 2.2 策略层

| 模块 | 说明 |
|------|------|
| `BaseStrategy` | 策略基类，定义 prepare/score/execute 接口 |
| `SimpleMAStrategy` | 简单均线策略实现 |
| `StrategyCombiner` | 多策略组合器 |
| `RiskControl` | 风控模块 |
| `StrategyPluginRegistry` | 策略插件注册表 |

### 2.3 回测层

| 模块 | 说明 |
|------|------|
| `BacktestEngine` | 回测引擎，支持交易日历过滤和滑点模拟 |
| `SlippageModel` | 滑点模型（固定/成交量） |
| `TradingCalendarFilter` | 交易日历过滤器 |
| `BacktestStorage` | 回测结果持久化 |
| `Benchmark` | 基准对比分析 |

### 2.4 调度层

| 模块 | 说明 |
|------|------|
| `DailyPipeline` | 每日流水线：检查交易日→下载数据→执行回测→发送通知 |
| `SchedulerService` | APScheduler 调度服务 |

## 三、数据流

```
数据下载 → 数据校验 → 数据存储 → 策略评分 → 回测验证 → 通知推送
    ↓           ↓           ↓           ↓           ↓           ↓
Provider   DataValidator  Parquet   Technical   BacktestEngine  Notifier
                         Files    Indicators
```

## 四、Web 平台功能

1. **数据下载**：支持单股/批量/全量下载，自动切换数据源
2. **本地库存**：查看已下载股票数据
3. **K线验真**：可视化 K 线图，均线叠加
4. **回测分析**：配置策略参数，执行回测，展示结果

## 五、扩展机制

### 5.1 数据源插件

继承 `BaseDataProvider`，实现 `fetch_daily_data` 方法即可添加新数据源。

### 5.2 策略插件

继承 `BaseStrategy`，实现 `prepare`、`score_stock` 方法，通过 `StrategyPluginRegistry` 注册。

### 5.3 通知渠道

继承 `BaseNotifier`，实现 `send` 方法即可添加新的通知渠道（如企业微信、邮件等）。