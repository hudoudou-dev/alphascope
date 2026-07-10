# AlphaScope

<div align="center">

**A股量化选股与回测平台**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📖 项目简介

AlphaScope 是一个功能完整的 A 股量化选股与回测平台，提供从数据获取、策略开发、回测分析到可视化展示的全流程解决方案。

### 核心特性

- 🔄 **多数据源支持** - AKShare、BaoStock、Tushare 三大数据源，自动切换
- 📅 **交易日历服务** - 自动判断交易日、节假日、市场状态
- 🧠 **多策略选股引擎** - 4 套子策略（趋势/动量/量价/质量）并行打分 + 加权融合
- 🎯 **行情自适应** - 市场状态检测（牛/趋势/震荡/熊），动态调整子策略权重（可选开关）
- 📊 **横截面标准化** - 全市场相对排名打分（z-score/rank），使选股结果跨行情可比（可选开关）
- 📈 **技术指标** - MA、RSI、MACD、Bollinger Bands、ADX、ATR、OBV、波动率、偏度等 20+ 指标
- 💹 **回测引擎** - 完整的回测框架，支持交易日历、滑点模拟、基准对比
- 🌐 **Web 平台** - FastAPI 后端 + Vue.js 前端，交互式图表
- 📢 **通知系统** - 钉钉、飞书机器人推送
- ⚙️ **配置化** - 所有参数可配置，无需修改代码

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+（Web 前端）
- pip 或 conda

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/hudoudou-dev/alphascope.git
cd alphascope

# 安装 Python 依赖
pip install -r requirements.txt
```

### 配置

```bash
cp config/settings.yaml config/settings.yaml
```

修改配置（可选）：

```yaml
data:
  providers:
    tushare:
      token: ${TUSHARE_TOKEN}  # 设置 Tushare Token（环境变量）
```

```bash
export TUSHARE_TOKEN="your_token_here"
```

### 启动服务

```bash
# 启动 FastAPI 后端（端口 8000）
python -m src.api.main

# 启动 Vue.js 前端（端口 5173）
cd web && npm install && npm run dev
```

访问 http://localhost:5173

---

## 📁 项目结构

```
alphascope/
├── config/                          # 配置文件
│   └── settings.yaml               # 主配置文件（数据/策略/回测/通知等全部超参）
│
├── data/                            # 数据存储目录
│   ├── raw/                         #   原始下载数据（按股票.parquet）
│   └── processed/                   #   预处理后数据
│
├── logs/                            # 日志目录
│
├── docs/                            # 文档
│   ├── architecture.md              #   架构设计
│   ├── configuration_guide.md       #   配置指南
│   ├── data_center_summary.md       #   模块总结
│   ├── deployment.md                #   部署指南
│   ├── prd.md                       #   产品需求文档
│   ├── risk_model.md                #   风险模型
│   ├── roadmap.md                   #   开发路线图
│   ├── strategy_analysis.md         #   选股策略架构分析 & 优化建议
│   └── strategy_upgrade_proposal.md #   多策略组合升级方案
│
├── specs/                           # 规范文档
│   ├── contracts/                   #   接口契约
│   ├── schemas/                     #   数据模式
│   ├── standards/                   #   开发标准
│   ├── constitution.md              #   项目宪法
│   ├── specify.md                   #   AI 开发规范
│   ├── spec_prompt_examples.md      #   规范使用示例
│   └── todo_unified.md              #   统一 TODO 清单
│
├── src/                             # 源代码
│   ├── api/                         #   FastAPI 后端
│   │   ├── main.py                  #     应用入口
│   │   ├── schemas.py               #     Pydantic 模型
│   │   ├── deps.py                  #     依赖注入
│   │   └── routers/                 #     路由
│   │       ├── data.py              #       数据下载/查询
│   │       ├── selection.py         #       选股运行
│   │       └── strategy.py          #       策略配置
│   │
│   ├── core/                        #   核心模块
│   │   ├── config.py                #     配置加载器
│   │   └── logger.py                #     日志系统
│   │
│   ├── data/                        #   数据模块
│   │   ├── providers/               #     数据提供者
│   │   │   ├── base_data_provider.py
│   │   │   ├── akshare_provider.py
│   │   │   ├── baostock_provider.py
│   │   │   └── tushare_provider.py  #     含基本面子模块（PE/PB/市值）
│   │   └── schema.py                #     数据校验
│   │
│   ├── calendar/                    #   交易日历模块
│   │   └── trading_calendar.py
│   │
│   ├── indicators/                  #   指标模块
│   │   ├── technical_indicators.py  #     技术指标（MA/RSI/MACD/ADX/ATR/OBV/波动率/偏度等）
│   │   ├── fundamental_indicators.py #    基本面指标
│   │   └── factor_normalizer.py     #     横截面标准化器（z-score/rank）
│   │
│   ├── strategy/                    #   策略模块
│   │   ├── base_strategy.py         #     策略基类（公共 prepare/score_stock 模板）
│   │   ├── sub_strategies.py        #     4 套子策略（Trend/Momentum/VolumePrice/Quality）
│   │   ├── selection_strategy.py    #     选股门面（多策略组合 + 筛选 + 风控）
│   │   ├── strategy_combiner.py     #     策略组合器（加权平均融合）
│   │   ├── regime.py                #     行情状态检测器（牛/趋势/震荡/熊）
│   │   ├── risk_control.py          #     风控模块
│   │   └── plugins.py               #     策略插件注册
│   │
│   ├── backtest/                    #   回测模块
│   │   └── backtest_engine.py
│   │
│   ├── notifier/                    #   通知模块
│   │   └── notification_manager.py
│   │
│   └── web/                         #   Web 应用（兼容 Streamlit）
│       └── app.py
│
├── web/                             # Vue.js 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── StockOverviewView.vue    # 股票走势概览
│   │   │   ├── StrategyConfigView.vue   # 选股策略配置
│   │   │   └── SelectionResultView.vue  # 选股生成结果
│   │   ├── components/                  # 通用组件
│   │   └── ...
│   └── package.json
│
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
└── debug_missing.py                # 调试/回归验证脚本
```

---

## 💡 核心设计

### 多策略选股架构

```
数据源 (parquet)
   │
   ▼
TechnicalIndicators.add_all_indicators(df)   ← 统一指标层（20+ 指标）
   │
   ▼
SelectionStrategy.prepare(df)                ← 门面：按股票分组计算指标
   │
   ▼
StrategyCombiner.score_stock_unified(code, df)
   ├─ TrendStrategy         (融合权重 30%)  ADX + MA排列 + MACD + 回调买点
   ├─ MomentumStrategy      (融合权重 25%)  短期反转 + 多周期动量 + RSI
   ├─ VolumePriceStrategy   (融合权重 25%)  量比 + 换手率 + 量价相关 + OBV + 缩量止跌
   └─ QualityStrategy       (融合权重 20%)  波动率 + 偏度 + 下行风险 + 基本面
   │
   ▼
WeightedAverageCombiner.combine()            ← 加权融合
   │
   ▼
[可选] FactorNormalizer                      ← 横截面标准化（z-score/rank）
[可选] RegimeDetector                       ← 行情自适应权重
   │
   ▼
filter_stock() + RiskControl + MarketFilter  ← 价格/市值/涨跌停/ST 过滤
   │
   ▼
API (/api/selection/run) → Vue.js 展示
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 API | Python + FastAPI |
| 前端 | Vue.js 3 + ECharts |
| 数据处理 | Pandas + Parquet (snappy) |
| 指标计算 | pandas 向量化 |
| 调度 | APScheduler |
| 可视化 | Plotly / ECharts |
| 通知 | 钉钉 Webhook / 飞书 Webhook |

---

## ⚙️ 配置说明

所有配置参数在 `config/settings.yaml` 中统一管理：

- **data** - 数据源、存储、更新策略
- **strategy.sub_strategies** - 4 套子策略的全部超参（因子阈值、权重等）
- **strategy.selection** - 选股筛选条件（价格/市值区间、涨跌停配置、Top-N、风控等）
- **strategy.cross_sectional** - 横截面标准化配置（默认关闭）
- **strategy.regime** - 行情自适应配置（默认关闭）
- **strategy.missing_data** - 缺失数据处理策略（redistribute/neutral/penalize/exclude）
- **backtest** - 初始资金、佣金、印花税、滑点
- **notification** - 钉钉、飞书配置
- **indicators** - MA、RSI、MACD 等指标参数

详细配置说明请参考 [docs/configuration_guide.md](docs/configuration_guide.md)

---

## 📚 文档

- [架构设计](docs/architecture.md) - 系统架构与模块关系
- [配置指南](docs/configuration_guide.md) - 全部配置参数说明
- [部署指南](docs/deployment.md) - 生产环境部署
- [产品需求文档](docs/prd.md) - 功能需求与验收标准
- [开发路线图](docs/roadmap.md) - 开发进度与规划
- [策略分析报告](docs/strategy_analysis.md) - 选股策略架构分析与优化建议
- [策略升级方案](docs/strategy_upgrade_proposal.md) - 多维度多策略组合选股方案
- [风险模型](docs/risk_model.md) - 风险控制设计

---

## 🛠️ 开发规范

### 代码规范

- 遵循 PEP 8 编码规范
- 使用 type hints 类型注解
- 编写完整的文档字符串
- 保持代码简洁清晰

### 测试规范

- 每个模块必须有对应的测试
- 测试覆盖率 > 80%
- 使用 pytest 框架
- 测试命名规范：test_*.py

详见 [specs/standards/coding_standard.md](specs/standards/coding_standard.md)

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📞 联系方式

- 项目地址: https://github.com/hudoudou-dev/alphascope
- 问题反馈: https://github.com/hudoudou-dev/alphascope/issues

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！⭐**

</div>
