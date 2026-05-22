<!--
 * @Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
 * @Date: 2026-05-21 17:18:15
 * @LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
 * @LastEditTime: 2026-05-21 17:56:47
 * @FilePath: /alphascope/docs/prd.md
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
# AlphaScope PRD

## 1. Product Overview

AlphaScope 是一个面向 A 股市场的 Python 量化选股与回测平台。

它是一个融合数据中台 + 策略引擎 + 回测系统 + Web平台 + 自动通知的一体化量化研究平台。

系统支持：

- 自动化股票数据下载
- 多策略选股
- 历史数据回测
- Web 可视化展示与分析
- 自动通知推送

目标用户为具备一定技术能力、希望实现选股自动化与策略验证的投资者。

从产品设计角度，包括：
- 数据层
- 策略层
- 回测层
- 展示层
- 自动化层
- 运维层

---

# 2. Product Goals

## 2.1 Core Goals

系统每日自动：

1. 获取 A 股市场数据
2. 更新本地历史数据库
3. 根据策略筛选股票
4. 生成推荐买入/卖出列表
5. 推送分析结果

---

# 3. Functional Requirements

## 3.1 Data Center

### Features

- 支持全市场股票数据下载
- 支持沪深、创业板、科创板
- 多线程并发下载
- 支持增量更新
- 支持滑动窗口历史清理

### Data Sources

- Akshare
- Baostock
- Tushare

### Data Fields

包括但不限于：

- 股票代码
- 股票名称
- 开盘价
- 收盘价
- 最高价
- 最低价
- 成交量
- 成交额
- 涨跌幅
- 换手率
- 总市值
- 流通市值

### Storage

- Parquet
- Snappy Compression

---

## 3.2 Strategy Engine

### Features

- 支持 Web 配置选股策略
- 支持策略插件化
- 支持多维度评分

### Supported Factors

- 市值
- 股价
- 涨跌幅
- MA
- RSI
- MACD
- 成交量

### Strategy Constraints

- 不允许未来数据泄露
- 支持前复权/后复权

---

## 3.3 Backtest Engine

### Features

- 历史回测
- 资金曲线生成
- 最大回撤统计
- 夏普比率统计
- 交易明细记录

### Backtest Rules

- 严禁使用未来数据
- 自动生成技术指标
- 支持滑点与手续费

---

## 3.4 Web Platform

### Features

- K线展示
- 参数配置
- 策略管理
- Top-N 股票展示
- 回测结果可视化

---

## 3.5 Notification System

### Features

- 飞书 Webhook
- 钉钉 Webhook
- 自动异常通知
- 每日收盘推送

---

# 4. Non-functional Requirements

## Stability

系统需支持长期稳定运行。

## Performance

- 支持 5000+ 股票处理
- 支持并发下载
- 支持缓存优化

## Storage Control

数据目录不可无限增长。

采用：

- 滑动窗口
- 数据归档
- 历史压缩

---

# 5. Configuration Management

所有超参数统一由 YAML 管理。

包括：

- 数据下载
- 策略参数
- 回测参数
- 通知参数

---

# 6. Recommended Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python + FastAPI |
| Frontend | Vue3 / Streamlit |
| Data | Pandas + Parquet |
| Indicators | pandas-ta |
| Scheduler | APScheduler |
| Storage | Local FS |
| Cache | Redis |
| Visualization | Plotly |

---

# 7. Acceptance Criteria

## Functional

- 正确完成每日选股
- 正确生成回测结果
- Web 页面可正常展示

## Technical

- 无未来数据泄露
- 数据下载失败可恢复
- 系统支持异常告警

## Performance

- 单次全市场更新 ≤ 30 分钟
- Web 查询响应 ≤ 2 秒

# 8. Supplements 

## 8.1 增加交易日历模块

### Features

A股不是每天交易。必须支持：
- 是否交易日
- 上一个交易日
- 下一个交易日
- 节假日
- 收盘后触发

否则：
- 定时任务会错
- 回测会错
- MA/RSI窗口会错
- 数据缺失会错

---

## 8.2 数据质量校验

### Features

确保数据源稳定性，降低多源数据校验的格式冲突问题，需校验：
- 缺失值
- 停牌
- 成交量异常
- 时间连续性
- 复权一致性
- 股票退市

否则回测结果可能出错

---


## 8.3 风险控制模块

### Features

增加模块：
- 单票最大仓位
- 最大回撤止损
- 黑名单
- ST过滤
- 涨停不可买
- 跌停不可卖

否则回测严重失真。

---


## 8.4 日志与审计

### Features

增加结构化日志模块：
- 数据下载
- 回测
- Web
- 通知
- 异常

---





├── specs/
│
│   ├── constitution.md
│   ├── specify.md
│
│   ├── contracts/
│   │
│   │   ├── data_contract.md
│   │   ├── strategy_contract.md
│   │   ├── backtest_contract.md
│   │   ├── notification_contract.md
│   │   ├── api_contract.md
│   │   └── plugin_contract.md
│   │
│   ├── schemas/
│   │
│   │   ├── strategy.schema.yaml
│   │   ├── backtest.schema.yaml
│   │   ├── data.schema.yaml
│   │   ├── scheduler.schema.yaml
│   │   ├── notification.schema.yaml
│   │   └── storage.schema.yaml
│   │
│   ├── standards/
│   │
│   │   ├── coding_standard.md
│   │   ├── logging_standard.md
│   │   ├── testing_standard.md
│   │   ├── naming_standard.md
│   │   ├── git_standard.md
│   │   └── ai_generation_standard.md
│   │
│   ├── prompts/
│   │
│   │   ├── strategy_generation.md
│   │   ├── factor_generation.md
│   │   ├── backtest_generation.md
│   │   ├── code_review.md
│   │   └── bugfix.md
│   │
│   └── examples/
│       ├── strategy_example.yaml
│       ├── backtest_example.yaml
│       ├── parquet_example.md
│       └── replay_example.md
│