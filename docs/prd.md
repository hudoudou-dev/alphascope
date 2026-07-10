# AlphaScope PRD

## 1. Product Overview

AlphaScope 是一个面向 A 股市场的 Python 量化选股与回测平台。

它是一个融合数据中台 + 策略引擎 + 回测系统 + Web平台 + 自动通知的一体化量化研究平台。

系统支持：

- 自动化股票数据下载（含基本面 PE/PB/市值）
- 多策略选股（4 套子策略并行打分 + 加权融合）
- 横截面标准化打分（可选）
- 行情自适应权重（可选）
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

1. 获取 A 股市场数据（含基本面）
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
- 支持基本面数据合并（PE/PB/市值）

### Data Sources

- Akshare
- Baostock
- Tushare（含 daily_basic 基本面接口）

### Data Fields

包括但不限于：

- 股票代码、股票名称
- 开盘价、收盘价、最高价、最低价
- 成交量、成交额、涨跌幅、换手率
- 总市值、流通市值、PE_TTM、PB

### Storage

- Parquet + Snappy Compression
- 原始数据：`./data/raw/`
- 预处理数据：`./data/processed/`

---

## 3.2 Strategy Engine

### Features

- 支持 Web 配置选股策略
- 支持策略插件化
- 支持多维度评分

### 子策略体系（4 套并行打分）

| 子策略 | 权重 | 因子 | 适用场景 |
|--------|------|------|----------|
| TrendStrategy | 30% | ADX、MA排列、MACD、回调买点 | 单边趋势市 |
| MomentumStrategy | 25% | 短期反转、多周期动量、RSI | 震荡市/超跌反弹 |
| VolumePriceStrategy | 25% | 量比、换手率、量价相关、OBV、缩量止跌 | 放量突破/缩量企稳 |
| QualityStrategy | 20% | 波动率、偏度、下行风险、基本面 | 防御/熊市 |

### 可选增强

- **横截面标准化**（cross_sectional）：将绝对分转为全市场相对排名分
- **行情自适应**（regime）：根据市场状态（牛/趋势/震荡/熊）动态切换子策略权重

### Supported Factors

- 趋势类：ADX、MA排列、MACD、回调买点
- 动量类：短期反转、多周期动量(10/20/60)、RSI
- 量价类：量比、换手率、量价相关、OBV、缩量止跌
- 质量类：波动率、偏度、下行波动率、PE/PB

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

- K线展示（含股票名称）
- 参数配置（与 settings.yaml 双向同步）
- 多策略超参管理
- Top-N 股票展示（按得分排序）
- 回测结果可视化

### 技术栈

- 后端：FastAPI
- 前端：Vue.js 3 + ECharts

### 页面结构

1. **首页** — 项目介绍
2. **股票走势概览** — 数据总览 + 单股明细 + K线验真
3. **股票数据更新** — 下载配置 + 进度监控 + 日志流
4. **选股策略配置** — 超参配置，与 settings.yaml 同步
5. **选股生成结果** — 运行选股，展示候选股票清单
6. **回测分析展示** — 回测结果可视化

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
- 4 套子策略全部超参（因子阈值、权重等）
- 选股筛选条件
- 回测参数
- 通知参数
- 横截面标准化参数
- 行情自适应参数
- 缺失数据处理策略

---

# 6. Recommended Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python + FastAPI |
| Frontend | Vue.js 3 + ECharts |
| Data | Pandas + Parquet |
| Indicators | pandas 向量化 |
| Scheduler | APScheduler |
| Storage | Local FS |
| Visualization | Plotly / ECharts |

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

## 8.1 交易日历模块

### Features

A股不是每天交易。必须支持：
- 是否交易日
- 上一个交易日
- 下一个交易日
- 节假日
- 收盘后触发

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
- 行业集中度限制

---

## 8.4 日志与审计

### Features

增加结构化日志模块：
- 数据下载
- 回测
- Web
- 通知
- 异常
- 子策略数据完整度警告

---

## 8.5 多策略选股引擎（v2 新增）

### Features

- 4 套独立子策略并行打分
- 加权平均融合
- 缺失数据自动降级（redistribute/neutral/penalize/exclude）
- 横截面标准化（z-score/rank，默认关闭）
- 行情自适应权重（BULL/TREND/RANGE/BEAR，默认关闭）
- 基本面因子接入（PE/PB，缺失时优雅降级）
